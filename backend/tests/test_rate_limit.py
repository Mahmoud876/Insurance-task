from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from app.config import settings
from app.core.rate_limit import InMemoryRateLimitStore, RateLimitMiddleware


def _limited_app(limit: int = 3) -> Starlette:
    app = Starlette()

    def index(request) -> JSONResponse:
        return JSONResponse({"ok": True})

    def health(request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app.add_route("/", index)
    app.add_route("/health", health)
    return app


def _limited_client(limit: int = 3) -> TestClient:
    wrapped = RateLimitMiddleware(_limited_app(limit), store=InMemoryRateLimitStore())
    return TestClient(wrapped)


def test_in_memory_store_enforces_fixed_window() -> None:
    store = InMemoryRateLimitStore()
    assert store.allow("k", 2, 60) == (True, 1)
    assert store.allow("k", 2, 60) == (True, 0)
    assert store.allow("k", 2, 60) == (False, 0)
    assert store.allow("other", 2, 60) == (True, 1)


def test_429_after_limit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 3)
    client = _limited_client()

    for _ in range(3):
        assert client.get("/").status_code == 200

    blocked = client.get("/")
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
    assert blocked.json()["detail"] == "Rate limit exceeded. Please try again later."


def test_allowed_requests_carry_rate_limit_headers(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 5)
    client = _limited_client()

    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"


def test_health_is_not_rate_limited(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT_PER_MINUTE", 1)
    client = _limited_client()

    for _ in range(10):
        assert client.get("/health").status_code == 200


def test_strict_bucket_uses_strict_limit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_STRICT_PER_MINUTE", 2)
    app = Starlette()

    def auth_route(request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app.add_route("/auth/anything", auth_route)
    wrapped = RateLimitMiddleware(app, store=InMemoryRateLimitStore())
    client = TestClient(wrapped)

    assert client.get("/auth/anything").status_code == 200
    assert client.get("/auth/anything").status_code == 200
    assert client.get("/auth/anything").status_code == 429
