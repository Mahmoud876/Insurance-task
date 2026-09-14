from enum import StrEnum
from threading import Lock
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient  # type: ignore[attr-defined]
from pydantic import BaseModel, Field

from app.config import settings


class Role(StrEnum):
    ADMIN = "admin"
    BILLER = "biller"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class AuthContext(BaseModel):
    user_id: UUID
    tenant_id: UUID
    roles: list[Role] = Field(default_factory=list)


security = HTTPBearer()

_jwks_cache: PyJWKClient | None = None
_jwks_client_lock = Lock()


def _oidc_jwks_uri() -> str:
    return f"{settings.OIDC_ISSUER_URL.rstrip('/')}/protocol/openid-connect/certs"


def _jwks_client() -> PyJWKClient:
    global _jwks_cache
    if _jwks_cache is None:
        with _jwks_client_lock:
            if _jwks_cache is None:
                _jwks_cache = PyJWKClient(_oidc_jwks_uri())
    return _jwks_cache


def _extract_roles(payload: dict[str, object]) -> list[Role]:
    raw_roles = payload.get("roles")
    if not isinstance(raw_roles, list):
        realm_access = payload.get("realm_access")
        raw_roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
    roles: list[Role] = []
    for role in raw_roles:
        try:
            roles.append(Role(role))
        except ValueError:
            continue
    return roles


def _build_auth_context(sub: object, tenant_id: object, roles: list[Role]) -> AuthContext:
    if not isinstance(sub, str) or not isinstance(tenant_id, str):
        raise ValueError("Invalid authentication claims")
    return AuthContext(user_id=UUID(sub), tenant_id=UUID(tenant_id), roles=roles)


def _decode_app_token(token: str) -> AuthContext:
    payload = jwt.decode(
        token,
        key=settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": True,
            "require": ["sub", "tenant_id", "roles"],
        },
    )
    return _build_auth_context(
        payload.get("sub"), payload.get("tenant_id"), _extract_roles(payload)
    )


def _decode_oidc_token(token: str) -> AuthContext:
    signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    payload = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256", "RS384", "RS512"],
        options={"verify_aud": False},
    )
    if payload.get("iss") != settings.OIDC_ISSUER_URL.rstrip("/"):
        raise jwt.InvalidIssuerError(f"Invalid issuer: {payload.get('iss')!r}")
    return _build_auth_context(
        payload.get("sub"), payload.get("tenant_id"), _extract_roles(payload)
    )


def decode_jwt_token(token: str) -> AuthContext:
    """Decode a Bearer token into an AuthContext.

    Routes by token header algorithm so the two trust domains stay isolated:
    HS256 tokens (load-test / internal) are validated against the app secret,
    RS* tokens against the OIDC provider's JWKS.
    """
    header = jwt.get_unverified_header(token)
    if header.get("alg") == settings.JWT_ALGORITHM:
        return _decode_app_token(token)
    return _decode_oidc_token(token)


async def get_auth_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> AuthContext:
    token = credentials.credentials

    try:
        auth_ctx = decode_jwt_token(token)
    except Exception as err:
        # Trading domain includes PyJWKClientError (JWKS fetch) which is not a
        # PyJWTError subclass; any failure at this boundary is a 401.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    request.state.auth_context = auth_ctx
    return auth_ctx
