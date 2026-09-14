import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.security.auth import AuthContext
from app.core.telemetry import DCS_HTTP_REQUESTS_TOTAL, request_context

logger = logging.getLogger("dcs.request")


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if path else "unmatched"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Generates a request id, emits structured request metadata and feeds
    dcs_http_requests_total. Prometheus /metrics scrapes are excluded so the
    counter and access log stay meaningful."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        is_metrics = request.url.path.startswith("/metrics")
        start = time.perf_counter()
        request_id: str = request.headers.get("X-Request-Id") or uuid4().hex

        token = request_context.set({"request_id": request_id})
        status_code: int | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
            ctx: dict[str, Any] = {
                "request_id": request_id,
                "tenant_id": str(auth_ctx.tenant_id) if auth_ctx else "N/A",
                "user_id": str(auth_ctx.user_id) if auth_ctx else "N/A",
                "route": _route_label(request),
                "duration_ms": round((time.perf_counter() - start) * 1000, 3),
            }
            request_context.set(ctx)
            if not is_metrics and status_code is not None:
                DCS_HTTP_REQUESTS_TOTAL.labels(route=ctx["route"], status=str(status_code)).inc()
                logger.info("request_completed")
            request_context.reset(token)

        response.headers["X-Request-Id"] = request_id
        return response
