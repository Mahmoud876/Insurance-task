from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router
from app.config import settings


def create_auth_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_callback_sets_strict_http_only_refresh_cookie(monkeypatch) -> None:
    client = create_auth_client()
    monkeypatch.setattr(
        "app.api.routes.auth.exchange_authorization_code",
        lambda code, code_verifier: {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 300,
        },
    )
    client.cookies.set(settings.AUTH_STATE_COOKIE_NAME, "test-state")
    client.cookies.set(settings.AUTH_PKCE_COOKIE_NAME, "pkce-verifier")

    response = client.get(
        "/auth/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )

    assert response.status_code == 302
    set_cookie = response.headers.get("set-cookie", "")
    assert f"{settings.AUTH_REFRESH_COOKIE_NAME}=refresh-token" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie


def test_refresh_uses_cookie_and_rotates_refresh_token(monkeypatch) -> None:
    client = create_auth_client()
    monkeypatch.setattr(
        "app.api.routes.auth.exchange_refresh_token",
        lambda refresh_token: {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 600,
        },
    )
    client.cookies.set(settings.AUTH_REFRESH_COOKIE_NAME, "old-refresh-token")

    response = client.post("/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access-token"
    set_cookie = response.headers.get("set-cookie", "")
    assert f"{settings.AUTH_REFRESH_COOKIE_NAME}=new-refresh-token" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie


def test_refresh_requires_cookie() -> None:
    client = create_auth_client()
    response = client.post("/auth/refresh")
    assert response.status_code == 401
