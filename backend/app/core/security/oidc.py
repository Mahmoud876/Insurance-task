import hashlib
import json
import secrets
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status

from app.config import settings


def generate_pkce_verifier() -> str:
    return secrets.token_urlsafe(64)


def generate_pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return _base64url(digest)


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorization_url(state: str, code_challenge: str) -> str:
    params = urlencode(
        {
            "response_type": "code",
            "client_id": settings.OIDC_CLIENT_ID,
            "redirect_uri": oidc_redirect_uri(),
            "scope": settings.OIDC_SCOPE,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{oidc_authorization_endpoint()}?{params}"


def exchange_authorization_code(code: str, code_verifier: str) -> dict[str, Any]:
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": settings.OIDC_CLIENT_ID,
        "code": code,
        "redirect_uri": oidc_redirect_uri(),
        "code_verifier": code_verifier,
    }
    if settings.OIDC_CLIENT_SECRET:
        payload["client_secret"] = settings.OIDC_CLIENT_SECRET
    return _post_form(oidc_token_endpoint(), payload)


def exchange_refresh_token(refresh_token: str) -> dict[str, Any]:
    payload: dict[str, str] = {
        "grant_type": "refresh_token",
        "client_id": settings.OIDC_CLIENT_ID,
        "refresh_token": refresh_token,
    }
    if settings.OIDC_CLIENT_SECRET:
        payload["client_secret"] = settings.OIDC_CLIENT_SECRET
    return _post_form(oidc_token_endpoint(), payload)


def logout_session(refresh_token: str) -> None:
    payload: dict[str, str] = {
        "client_id": settings.OIDC_CLIENT_ID,
        "refresh_token": refresh_token,
    }
    if settings.OIDC_CLIENT_SECRET:
        payload["client_secret"] = settings.OIDC_CLIENT_SECRET
    _post_form(oidc_logout_endpoint(), payload, expect_json=False)


def oidc_authorization_endpoint() -> str:
    return f"{settings.OIDC_ISSUER_URL.rstrip('/')}/protocol/openid-connect/auth"


def oidc_token_endpoint() -> str:
    return f"{settings.OIDC_ISSUER_URL.rstrip('/')}/protocol/openid-connect/token"


def oidc_logout_endpoint() -> str:
    return f"{settings.OIDC_ISSUER_URL.rstrip('/')}/protocol/openid-connect/logout"


def oidc_redirect_uri() -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}{settings.OIDC_REDIRECT_PATH}"


def _base64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _post_form(url: str, data: Mapping[str, str], *, expect_json: bool = True) -> dict[str, Any]:
    payload = urlencode(data).encode("utf-8")
    request = Request(
        url=url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            if not expect_json:
                return {}
            parsed = _parse_json_response(raw)
            return parsed
    except HTTPError as err:
        error_body = err.read().decode("utf-8") if err.fp else ""
        detail = _extract_oidc_error(error_body) or f"OIDC provider returned HTTP {err.code}"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from err
    except URLError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC provider is unreachable",
        ) from err


def _parse_json_response(body: str) -> dict[str, Any]:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC provider returned a non-JSON response",
        ) from err
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC provider returned an invalid JSON object",
        )
    return parsed


def _extract_oidc_error(body: str) -> str | None:
    if not body:
        return None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    description = parsed.get("error_description")
    error = parsed.get("error")
    if isinstance(description, str):
        return description
    if isinstance(error, str):
        return error
    return None
