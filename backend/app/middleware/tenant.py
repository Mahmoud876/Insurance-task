from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.database_session import current_tenant_id


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_uuid: UUID | None = None

        auth_context = getattr(request.state, "auth_context", None)
        if auth_context and getattr(auth_context, "tenant_id", None):
            raw_tenant_id = getattr(auth_context, "tenant_id", None)
            if isinstance(raw_tenant_id, UUID):
                tenant_uuid = raw_tenant_id
            elif isinstance(raw_tenant_id, str):
                try:
                    tenant_uuid = UUID(raw_tenant_id)
                except ValueError:
                    tenant_uuid = None

        token = current_tenant_id.set(tenant_uuid)
        request.state.tenant_id = tenant_uuid
        try:
            return await call_next(request)
        finally:
            current_tenant_id.reset(token)
