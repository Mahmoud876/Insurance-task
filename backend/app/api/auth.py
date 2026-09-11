from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.core.security.oidc import (
    build_authorization_url,
    exchange_authorization_code,
    exchange_refresh_token,
    generate_pkce_challenge,
    generate_pkce_verifier,
    generate_state,
    logout_session,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login() -> RedirectResponse:
    state = generate_state()
    verifier = generate_pkce_verifier()
    challenge = generate_pkce_challenge(verifier)
    authorize_url = build_authorization_url(state=state, code_challenge=challenge)

    response = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    _set_auth_flow_cookie(response, settings.AUTH_STATE_COOKIE_NAME, state)
    _set_auth_flow_cookie(response, settings.AUTH_PKCE_COOKIE_NAME, verifier)
    return response


@router.get("/callback")
def callback(
    request: Request, code: str | None = None, state: str | None = None
) -> RedirectResponse:
    expected_state = request.cookies.get(settings.AUTH_STATE_COOKIE_NAME)
    code_verifier = request.cookies.get(settings.AUTH_PKCE_COOKIE_NAME)

    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state")
    if not expected_state or not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing PKCE auth context"
        )
    if state != expected_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OIDC state")

    token_payload = exchange_authorization_code(code=code, code_verifier=code_verifier)
    refresh_token = token_payload.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC provider did not return a refresh token",
        )

    response = RedirectResponse(
        url=f"{settings.FRONTEND_BASE_URL.rstrip('/')}/dashboard",
        status_code=status.HTTP_302_FOUND,
    )
    _set_refresh_token_cookie(response, refresh_token)
    response.delete_cookie(
        key=settings.AUTH_STATE_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )
    response.delete_cookie(
        key=settings.AUTH_PKCE_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )
    return response


@router.post("/refresh")
def refresh(request: Request) -> JSONResponse:
    refresh_token = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token cookie"
        )

    token_payload = exchange_refresh_token(refresh_token)
    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC provider did not return an access token",
        )

    new_refresh_token = token_payload.get("refresh_token")
    response_payload: dict[str, Any] = {
        "access_token": access_token,
        "token_type": token_payload.get("token_type", "Bearer"),
        "expires_in": token_payload.get("expires_in"),
    }

    response = JSONResponse(content=response_payload)
    if isinstance(new_refresh_token, str) and new_refresh_token:
        _set_refresh_token_cookie(response, new_refresh_token)
    return response


@router.post("/logout")
def logout(request: Request) -> JSONResponse:
    refresh_token = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if refresh_token:
        logout_session(refresh_token)
    response = JSONResponse(content={"status": "logged_out"})
    response.delete_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )
    return response


def _set_auth_flow_cookie(response: Response, key: str, value: str) -> None:
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.AUTH_CALLBACK_COOKIE_MAX_AGE_SECONDS,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )


def _set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="strict",
        max_age=settings.AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )
