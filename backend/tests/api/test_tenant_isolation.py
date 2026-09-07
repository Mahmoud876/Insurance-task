from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.database_session import apply_tenant_rls, clear_tenant_rls, current_tenant_id
from app.core.security.auth import AuthContext
from app.core.security.rbac import Role
from app.core.tenant import Tenant
from app.modules.claims.models.claim import Claim, ClaimStatus
from app.modules.claims.service.claim_service import ClaimService
from tests.conftest import apply_test_tenant_context, make_test_claim


@pytest.fixture
def tenant_a(db_session: Session) -> Tenant:
    tenant = Tenant(id=uuid4(), name="Tenant Alpha")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def tenant_b(db_session: Session) -> Tenant:
    tenant = Tenant(id=uuid4(), name="Tenant Beta")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def token_tenant_a(tenant_a: Tenant) -> str:
    return f"Bearer token_user_a_{tenant_a.id}"


@pytest.fixture
def token_tenant_b(tenant_b: Tenant) -> str:
    return f"Bearer token_user_b_{tenant_b.id}"


def create_integration_app(db_session_override: Callable[[], Session]) -> FastAPI:
    app = FastAPI()

    class MockAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer token_user_a_"):
                tenant_id = auth_header.replace("Bearer token_user_a_", "")
                request.state.auth_context = AuthContext(
                    user_id=uuid4(),
                    tenant_id=UUID(tenant_id),
                    roles=[Role.BILLER],
                )
            elif auth_header.startswith("Bearer token_user_b_"):
                tenant_id = auth_header.replace("Bearer token_user_b_", "")
                request.state.auth_context = AuthContext(
                    user_id=uuid4(),
                    tenant_id=UUID(tenant_id),
                    roles=[Role.BILLER],
                )
            return await call_next(request)

    class PostgreSQLRLSMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
            tenant_id: UUID | None = auth_ctx.tenant_id if auth_ctx is not None else None
            token_res = current_tenant_id.set(tenant_id)

            db: Session = db_session_override()
            try:
                apply_tenant_rls(db, tenant_id)
                response = await call_next(request)
                return response
            finally:
                clear_tenant_rls(db)
                current_tenant_id.reset(token_res)

    app.add_middleware(PostgreSQLRLSMiddleware)
    app.add_middleware(MockAuthMiddleware)

    @app.get("/api/v1/claims/{claim_id}")
    def get_claim_endpoint(
        claim_id: str, request: Request, db: Session = Depends(db_session_override)
    ) -> Any:
        auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
        if not auth_ctx:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

        return ClaimService.get_claim(db, UUID(claim_id), auth_ctx)

    @app.get("/api/v1/tenant-debug")
    def tenant_debug(
        request: Request, db: Session = Depends(db_session_override)
    ) -> dict[str, str | None]:
        rls_setting = db.execute(text("SHOW app.tenant_id")).scalar()
        current_id = current_tenant_id.get()
        return {
            "context_tenant_id": str(current_id) if current_id else None,
            "pg_rls_tenant_id": str(rls_setting) if rls_setting is not None else None,
        }

    return app


def test_cross_tenant_read_returns_404_masking(
    db_session: Session, tenant_a: Tenant, tenant_b: Tenant, token_tenant_a: str
) -> None:
    """Verifies Tenant A receives 404 (not 403) when attempting to access Tenant B's claim."""
    claim_b = make_test_claim(db_session, tenant_b.id, status=ClaimStatus.DRAFT)
    db_session.commit()

    app = create_integration_app(lambda: db_session)
    client = TestClient(app)

    response = client.get(
        f"/api/v1/claims/{claim_b.id}",
        headers={"Authorization": token_tenant_a},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_header_spoofing_attempts_are_ignored(
    db_session: Session, tenant_a: Tenant, tenant_b: Tenant, token_tenant_a: str
) -> None:
    """Ensures X-Tenant-ID headers cannot override tenant context derived from validated tokens."""
    app = create_integration_app(lambda: db_session)
    client = TestClient(app)

    response = client.get(
        "/api/v1/tenant-debug",
        headers={
            "Authorization": token_tenant_a,
            "X-Tenant-ID": str(tenant_b.id),
        },
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["context_tenant_id"] == str(tenant_a.id)
    assert res_data["pg_rls_tenant_id"] == str(tenant_a.id)


def test_missing_or_invalid_authentication(db_session: Session) -> None:
    """Requests lacking authentication context are rejected with 401."""
    app = create_integration_app(lambda: db_session)
    client = TestClient(app)

    response = client.get(f"/api/v1/claims/{uuid4()}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_postgresql_rls_blocks_cross_tenant_direct_writes(db_session: Session) -> None:
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()

    apply_test_tenant_context(db_session, tenant_a_id)

    cross_tenant_claim = Claim(
        id=uuid4(),
        tenant_id=tenant_b_id,
        patient_id=uuid4(),
        provider_id=uuid4(),
        status=ClaimStatus.DRAFT,
        total_amount=Decimal("150.00"),
    )

    with pytest.raises(SQLAlchemyError):
        db_session.add(cross_tenant_claim)
        db_session.flush()


def test_tenant_context_cleanup_between_consecutive_requests(
    db_session: Session,
    tenant_a: Tenant,
    tenant_b: Tenant,
    token_tenant_a: str,
    token_tenant_b: str,
) -> None:
    """Ensures ContextVar and PostgreSQL RLS session variables are completely reset across requests."""
    app = create_integration_app(lambda: db_session)
    client = TestClient(app)

    res1 = client.get("/api/v1/tenant-debug", headers={"Authorization": token_tenant_a})
    assert res1.json()["pg_rls_tenant_id"] == str(tenant_a.id)

    res2 = client.get("/api/v1/tenant-debug", headers={"Authorization": token_tenant_b})
    assert res2.json()["pg_rls_tenant_id"] == str(tenant_b.id)

    res3 = client.get("/api/v1/tenant-debug")
    assert res3.json()["context_tenant_id"] is None
    assert res3.json()["pg_rls_tenant_id"] in (None, "")
