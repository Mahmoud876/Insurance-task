import os
from uuid import UUID

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

import app.db.models as _db_models  # noqa: F401  (registers all ORM mappers before first query)
from app.api.auth import router as auth_router
from app.core.database_session import (
    SessionLocal,
    apply_tenant_rls,
    clear_tenant_rls,
    current_tenant_id,
)
from app.core.errors import (
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging_config import setup_structured_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.request_logging import RequestLoggingMiddleware
from app.core.security.auth import AuthContext, decode_jwt_token
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.telemetry import configure_tracing, instrument_fastapi
from app.modules.analytics.api import router as analytics_router
from app.modules.autofix.api.autofix import router as autofix_router
from app.modules.claims.api.attachments import router as attachments_router
from app.modules.claims.api.claims import router as claims_router
from app.modules.ocr.api.ocr import router as ocr_router
from app.modules.preauth.api.preauth import router as preauth_router
from app.modules.scrubber.api.scrub import router as scrub_router
from app.modules.simulation.api.simulation import router as simulation_router

load_dotenv()

setup_structured_logging()

configure_tracing()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", ""),
    traces_sample_rate=0.2,
    send_default_pii=False,
    environment=os.getenv("ENVIRONMENT", "development"),
)

app = FastAPI(title="Dental Claims Engine")

instrument_fastapi(app)

app.add_exception_handler(
    StarletteHTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/health" or request.url.path.startswith("/auth"):
            return await call_next(request)

        auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
        tenant_id: UUID | None = auth_ctx.tenant_id if auth_ctx is not None else None
        token_res = current_tenant_id.set(tenant_id)

        db: Session = SessionLocal()
        try:
            await run_in_threadpool(apply_tenant_rls, db, tenant_id)
            request.state.db = db

            response = await call_next(request)
            return response
        finally:
            await run_in_threadpool(clear_tenant_rls, db)
            await run_in_threadpool(db.close)
            current_tenant_id.reset(token_res)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/health" or request.url.path.startswith("/auth"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        request.state.auth_context = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                request.state.auth_context = decode_jwt_token(token)
            except Exception:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or expired authentication token"},
                )

        return await call_next(request)


app.add_middleware(TenantIsolationMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS must be the outermost middleware so preflight OPTIONS requests
# (which have no Authorization header) get proper CORS headers before
# hitting auth/tenant logic. Added last = runs first in Starlette.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(auth_router)
app.include_router(claims_router, prefix="/api/v1")
app.include_router(attachments_router, prefix="/api/v1")
app.include_router(autofix_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(scrub_router, prefix="/api/v1")
app.include_router(simulation_router, prefix="/api")
app.include_router(ocr_router, prefix="/api")
app.include_router(preauth_router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
