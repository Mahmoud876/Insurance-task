from enum import StrEnum
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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


def decode_jwt_token(token: str) -> AuthContext:
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

    sub = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    raw_roles = payload.get("roles")
    if (
        not isinstance(sub, str)
        or not isinstance(tenant_id, str)
        or not isinstance(raw_roles, list)
    ):
        raise ValueError("Invalid authentication claims")

    return AuthContext(
        user_id=UUID(sub),
        tenant_id=UUID(tenant_id),
        roles=[Role(role) for role in raw_roles],
    )


async def get_auth_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> AuthContext:
    token = credentials.credentials

    try:
        auth_ctx = decode_jwt_token(token)
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    request.state.auth_context = auth_ctx
    return auth_ctx
