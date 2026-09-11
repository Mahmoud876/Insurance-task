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
    response = RedirectResponse(build_authorization_url(state, generate_pkce_challenge(verifier)), status_code=status.HTTP_302_FOUND)
    _set_auth_flow_cookie(response, settings.AUTH_STATE_COOKIE_NAME, state)
    _set_auth_flow_cookie(response, settings.AUTH_PKCE_COOKIE_NAME, verifier)
    return response


@router.get("/callback")
def callback(request: Request, code: str | None = None, state: str | None = None) -> RedirectResponse:
    expected_state = request.cookies.get(settings.AUTH_STATE_COOKIE_NAME)
    verifier = request.cookies.get(settings.AUTH_PKCE_COOKIE_NAME)
    if not code or not state or not expected_state or not verifier:
        raise HTTPException(status_code=400, detail="Missing or incomplete OIDC callback context")
    if state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid OIDC state")
    payload = exchange_authorization_code(code, verifier)
    refresh_token = payload.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise HTTPException(status_code=502, detail="OIDC provider did not return a refresh token")
    response = RedirectResponse(f"{settings.FRONTEND_BASE_URL.rstrip('/')}/dashboard", status_code=302)
    _set_refresh_token_cookie(response, refresh_token)
    response.delete_cookie(settings.AUTH_STATE_COOKIE_NAME, path=settings.AUTH_COOKIE_PATH, domain=settings.AUTH_COOKIE_DOMAIN)
    response.delete_cookie(settings.AUTH_PKCE_COOKIE_NAME, path=settings.AUTH_COOKIE_PATH, domain=settings.AUTH_COOKIE_DOMAIN)
    return response


@router.post("/refresh")
def refresh(request: Request) -> JSONResponse:
    token = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token cookie")
    payload = exchange_refresh_token(token)
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(status_code=502, detail="OIDC provider did not return an access token")
    response = JSONResponse({"access_token": access_token, "token_type": payload.get("token_type", "Bearer"), "expires_in": payload.get("expires_in")})
    if isinstance(payload.get("refresh_token"), str):
        _set_refresh_token_cookie(response, payload["refresh_token"])
    return response


@router.post("/logout")
def logout(request: Request) -> JSONResponse:
    token = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if token:
        logout_session(token)
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(settings.AUTH_REFRESH_COOKIE_NAME, path=settings.AUTH_COOKIE_PATH, domain=settings.AUTH_COOKIE_DOMAIN)
    return response


def _set_auth_flow_cookie(response: Response, key: str, value: str) -> None:
    response.set_cookie(key, value, httponly=True, secure=settings.AUTH_COOKIE_SECURE, samesite="lax", max_age=settings.AUTH_CALLBACK_COOKIE_MAX_AGE_SECONDS, path=settings.AUTH_COOKIE_PATH, domain=settings.AUTH_COOKIE_DOMAIN)


def _set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(settings.AUTH_REFRESH_COOKIE_NAME, refresh_token, httponly=True, secure=settings.AUTH_COOKIE_SECURE, samesite="lax", max_age=settings.AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS, path=settings.AUTH_COOKIE_PATH, domain=settings.AUTH_COOKIE_DOMAIN)
