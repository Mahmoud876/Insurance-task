"""Rate limiting middleware.

Uses a Redis fixed-window counter when Redis is reachable and silently falls
back to an in-process store otherwise, so the API is still rate-limited even
with no Redis (though limits are per-process then).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Protocol

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.config import settings

logger = logging.getLogger(__name__)

_SKIP_PATHS = ("/health", "/metrics", "/openapi.json", "/docs", "/redoc", "/favicon.ico")
_STRICT_PREFIXES = (
    "/auth/",
    "/api/v1/insurance-cards/",
    "/api/v1/claims/",
)
_WINDOW_SECONDS = 60

RATE_LIMITED = "Rate limit exceeded. Please try again later."


class RateLimitStore(Protocol):
    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return (allowed, remaining) for a request on `key`."""


class InMemoryRateLimitStore:
    def __init__(self) -> None:
        self._counts: dict[tuple[str, int], int] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = int(time.monotonic())
        bucket = now // window_seconds
        with self._lock:
            cache_key = (key, bucket)
            count = self._counts.get(cache_key, 0) + 1
            self._counts[cache_key] = count
            if len(self._counts) > 100_000:
                cutoff = bucket - 2
                for stale in [k for k in self._counts if k[1] < cutoff]:
                    del self._counts[stale]
            return count <= limit, max(limit - count, 0)


class RedisRateLimitStore:
    def __init__(self, client: Any) -> None:
        self._redis = client

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        try:
            bucket = int(time.time()) // window_seconds
            redis_key = f"rl:{bucket}:{key}"
            count = int(self._redis.incr(redis_key))
            if count == 1:
                self._redis.expire(redis_key, window_seconds + 5)
            return count <= limit, max(limit - count, 0)
        except Exception:  # pragma: no cover - defensive; Redis may go down
            return True, limit


def build_rate_limit_store() -> RateLimitStore:
    try:
        import redis

        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        client.ping()
        logger.info("Rate limiting backed by Redis at %s", settings.REDIS_URL)
        return RedisRateLimitStore(client)
    except Exception:
        logger.warning(
            "Redis unavailable (%s); using in-process rate limit store",
            settings.REDIS_URL,
            exc_info=True,
        )
        return InMemoryRateLimitStore()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, store: RateLimitStore | None = None) -> None:
        super().__init__(app)
        self._store: RateLimitStore | None
        if store is not None:
            self._store = store
        elif settings.RATE_LIMIT_ENABLED:
            self._store = build_rate_limit_store()
        else:
            self._store = None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._store is None:
            return await call_next(request)

        path = request.url.path
        if any(path == skip or path.startswith(skip) for skip in _SKIP_PATHS):
            return await call_next(request)

        # CORS preflight has no auth; never rate-limit preflight.
        if request.method == "OPTIONS":
            return await call_next(request)

        ip = _client_ip(request)
        is_strict = any(path.startswith(prefix) for prefix in _STRICT_PREFIXES)
        key = f"{ip}:{'strict' if is_strict else 'default'}"
        limit = (
            settings.RATE_LIMIT_STRICT_PER_MINUTE
            if is_strict
            else settings.RATE_LIMIT_DEFAULT_PER_MINUTE
        )

        allowed, remaining = self._store.allow(key, limit, _WINDOW_SECONDS)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": RATE_LIMITED, "remaining": 0},
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
