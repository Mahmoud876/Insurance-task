from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.errors import (
    http_exception_handler,
    validation_exception_handler,
)
from app.api.v1.claims import router as claims_router
from app.core.auth import AuthContext, decode_jwt_token
from app.db.session import SessionLocal, apply_tenant_rls, clear_tenant_rls, current_tenant_id

load_dotenv()

app = FastAPI(title="Dental Claims Engine")

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
        if request.url.path == "/health":
            return await call_next(request)

        auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
        tenant_id: UUID | None = auth_ctx.tenant_id if auth_ctx is not None else None
        token_res = current_tenant_id.set(tenant_id)

        db: Session = SessionLocal()
        try:
            apply_tenant_rls(db, tenant_id)
            request.state.db = db
            response = await call_next(request)
            return response
        finally:
            clear_tenant_rls(db)
            db.close()
            current_tenant_id.reset(token_res)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/health":
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

# CORS must be the outermost middleware so preflight OPTIONS requests
# (which have no Authorization header) get proper CORS headers before
# hitting auth/tenant logic. Added last = runs first in Starlette.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
