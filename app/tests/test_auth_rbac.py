from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings
from app.core.auth import AuthContext
from app.core.rbac import Role
from app.db.models.claim import Claim, ClaimStatus
from app.db.models.tenant import Tenant
from app.db.session import apply_tenant_rls, clear_tenant_rls, current_tenant_id
from app.schemas.claim import ClaimCreate, ClaimUpdate
from app.services.claim_service import ClaimService
from app.tests.conftest import ensure_rls_role, make_test_claim, seed_patient_and_provider


def make_test_jwt(
    tenant_id: UUID,
    user_id: UUID,
    roles: list[Role] | list[str] | list[Any],
    exp_delta: timedelta = timedelta(hours=1),
    secret_key: str | None = None,
    issuer: str | None = None,
    audience: str | None = None,
) -> str:
    """Generates signed JWT tokens with customizable headers and claims for test scenarios."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": [r.value if isinstance(r, Role) else r for r in roles],
        "iss": issuer if issuer is not None else settings.JWT_ISSUER,
        "aud": audience if audience is not None else settings.JWT_AUDIENCE,
        "iat": now,
        "exp": now + exp_delta,
    }
    key = secret_key if secret_key is not None else settings.JWT_SECRET_KEY
    return jwt.encode(payload, key, algorithm=settings.JWT_ALGORITHM)


def decode_test_token(token: str) -> AuthContext:
    """Decodes and validates JWT claims for test requests."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        raw_roles: list[str] = payload.get("roles", [])
        roles = [Role(r) for r in raw_roles]
        return AuthContext(
            user_id=UUID(str(payload["sub"])),
            tenant_id=UUID(str(payload["tenant_id"])),
            roles=roles,
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token has expired") from e
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


def create_claims_api_app(db_session_factory: Callable[[], Session]) -> FastAPI:
    """Creates a FastAPI app instance wired with authentication, tenant context, and claims routes."""
    app = FastAPI()

    class JWTAndTenantMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
                try:
                    auth_ctx = decode_test_token(token)
                    request.state.auth_context = auth_ctx
                except HTTPException as exc:
                    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

            current_auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
            tenant_id: UUID | None = (
                current_auth_ctx.tenant_id if current_auth_ctx is not None else None
            )
            tenant_token = current_tenant_id.set(tenant_id)

            db: Session = db_session_factory()
            try:
                apply_tenant_rls(db, tenant_id)
                response = await call_next(request)
                return response
            finally:
                clear_tenant_rls(db)
                current_tenant_id.reset(tenant_token)

    app.add_middleware(JWTAndTenantMiddleware)

    def get_auth_context(request: Request) -> AuthContext:
        auth_ctx: AuthContext | None = getattr(request.state, "auth_context", None)
        if not auth_ctx:
            raise HTTPException(status_code=401, detail="Authentication required")
        return auth_ctx

    @app.get("/api/v1/claims/{claim_id}")
    def get_claim(
        claim_id: UUID,
        auth_ctx: AuthContext = Depends(get_auth_context),
        db: Session = Depends(db_session_factory),
    ) -> Any:
        return ClaimService.get_claim(db, claim_id, auth_ctx)

    @app.post("/api/v1/claims", status_code=201)
    def create_claim(
        payload: ClaimCreate,
        auth_ctx: AuthContext = Depends(get_auth_context),
        db: Session = Depends(db_session_factory),
    ) -> Any:
        return ClaimService.create_claim(db, payload, auth_ctx)

    @app.put("/api/v1/claims/{claim_id}")
    def update_claim(
        claim_id: UUID,
        payload: ClaimUpdate,
        auth_ctx: AuthContext = Depends(get_auth_context),
        db: Session = Depends(db_session_factory),
    ) -> Any:
        return ClaimService.update_claim(db, claim_id, payload, auth_ctx)

    @app.post("/api/v1/claims/{claim_id}/scrub")
    def scrub_claim(
        claim_id: UUID,
        auth_ctx: AuthContext = Depends(get_auth_context),
        db: Session = Depends(db_session_factory),
    ) -> Any:
        return ClaimService.scrub_claim(db, claim_id, auth_ctx)

    @app.post("/api/v1/claims/{claim_id}/submit")
    def submit_claim(
        claim_id: UUID,
        auth_ctx: AuthContext = Depends(get_auth_context),
        db: Session = Depends(db_session_factory),
    ) -> Any:
        return ClaimService.submit_claim(db, claim_id, auth_ctx)

    @app.delete("/api/v1/claims/{claim_id}", status_code=204)
    def delete_claim(
        claim_id: UUID,
        auth_ctx: AuthContext = Depends(get_auth_context),
        db: Session = Depends(db_session_factory),
    ) -> None:
        ClaimService.delete_claim(db, claim_id, auth_ctx)

    return app


@pytest.fixture
def tenant_a(db_session: Session) -> Tenant:
    tenant = Tenant(id=uuid4(), name="Tenant A")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def tenant_b(db_session: Session) -> Tenant:
    tenant = Tenant(id=uuid4(), name="Tenant B")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def test_client(db_session: Session) -> TestClient:
    app = create_claims_api_app(lambda: db_session)
    return TestClient(app)


def test_missing_authorization_header(test_client: TestClient) -> None:
    response = test_client.get(f"/api/v1/claims/{uuid4()}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_expired_jwt_token(test_client: TestClient, tenant_a: Tenant) -> None:
    token = make_test_jwt(
        tenant_id=tenant_a.id,
        user_id=uuid4(),
        roles=[Role.ADMIN],
        exp_delta=timedelta(hours=-1),
    )
    response = test_client.get(
        f"/api/v1/claims/{uuid4()}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_invalid_jwt_signature(test_client: TestClient, tenant_a: Tenant) -> None:
    token = make_test_jwt(
        tenant_id=tenant_a.id,
        user_id=uuid4(),
        roles=[Role.ADMIN],
        secret_key="wrong-secret-key",
    )
    response = test_client.get(
        f"/api/v1/claims/{uuid4()}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_invalid_issuer_or_audience(test_client: TestClient, tenant_a: Tenant) -> None:
    bad_iss_token = make_test_jwt(
        tenant_id=tenant_a.id, user_id=uuid4(), roles=[Role.ADMIN], issuer="invalid-iss"
    )
    res1 = test_client.get(
        f"/api/v1/claims/{uuid4()}", headers={"Authorization": f"Bearer {bad_iss_token}"}
    )
    assert res1.status_code == 401

    bad_aud_token = make_test_jwt(
        tenant_id=tenant_a.id, user_id=uuid4(), roles=[Role.ADMIN], audience="invalid-aud"
    )
    res2 = test_client.get(
        f"/api/v1/claims/{uuid4()}", headers={"Authorization": f"Bearer {bad_aud_token}"}
    )
    assert res2.status_code == 401


@pytest.mark.parametrize(
    "role, endpoint, http_method, payload, expected_status",
    [
        # VIEWER Role Capabilities
        (Role.VIEWER, "get", "GET", None, 200),
        (Role.VIEWER, "create", "POST", {"total_amount": 100.0}, 403),
        (Role.VIEWER, "update", "PUT", {"total_amount": 150.0}, 403),
        (Role.VIEWER, "scrub", "POST", None, 403),
        (Role.VIEWER, "submit", "POST", None, 403),
        (Role.VIEWER, "delete", "DELETE", None, 403),
        # BILLER Role Capabilities
        (Role.BILLER, "get", "GET", None, 200),
        (Role.BILLER, "create", "POST", {"total_amount": 100.0}, 201),
        (Role.BILLER, "update", "PUT", {"total_amount": 150.0}, 200),
        (Role.BILLER, "scrub", "POST", None, 200),
        (Role.BILLER, "submit", "POST", None, 400),
        (Role.BILLER, "delete", "DELETE", None, 403),
        # ADMIN Role Capabilities
        (Role.ADMIN, "get", "GET", None, 200),
        (Role.ADMIN, "create", "POST", {"total_amount": 100.0}, 201),
        (Role.ADMIN, "update", "PUT", {"total_amount": 150.0}, 200),
        (Role.ADMIN, "scrub", "POST", None, 200),
        (Role.ADMIN, "delete", "DELETE", None, 204),
    ],
)
def test_rbac_role_matrix_endpoints(
    test_client: TestClient,
    db_session: Session,
    tenant_a: Tenant,
    role: Role,
    endpoint: str,
    http_method: str,
    payload: dict[str, Any] | None,
    expected_status: int,
) -> None:
    patient, provider = seed_patient_and_provider(db_session, tenant_a.id)
    db_session.commit()

    token = make_test_jwt(tenant_id=tenant_a.id, user_id=uuid4(), roles=[role])
    headers = {"Authorization": f"Bearer {token}"}

    claim = make_test_claim(db_session, tenant_a.id, status=ClaimStatus.DRAFT, total_amount=100.0)
    db_session.commit()

    request_payload: dict[str, Any] | None = None
    if payload is not None and endpoint == "create":
        request_payload = {
            **payload,
            "patient_id": str(patient.id),
            "provider_id": str(provider.id),
        }
    elif payload is not None:
        request_payload = payload

    url_map = {
        "get": f"/api/v1/claims/{claim.id}",
        "create": "/api/v1/claims",
        "update": f"/api/v1/claims/{claim.id}",
        "scrub": f"/api/v1/claims/{claim.id}/scrub",
        "submit": f"/api/v1/claims/{claim.id}/submit",
        "delete": f"/api/v1/claims/{claim.id}",
    }

    url = url_map[endpoint]
    res: Any
    if http_method == "GET":
        res = test_client.get(url, headers=headers)
    elif http_method == "POST":
        res = test_client.post(url, json=request_payload, headers=headers)
    elif http_method == "PUT":
        res = test_client.put(url, json=request_payload, headers=headers)
    elif http_method == "DELETE":
        res = test_client.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported HTTP method: {http_method}")

    assert res.status_code == expected_status


def test_cross_tenant_operations_mask_as_404(
    test_client: TestClient, db_session: Session, tenant_a: Tenant, tenant_b: Tenant
) -> None:
    """Ensures that Tenant A attempting any action on Tenant B's claim receives 404 Not Found."""
    claim_b = make_test_claim(db_session, tenant_b.id, status=ClaimStatus.DRAFT)
    db_session.commit()

    token_a = make_test_jwt(tenant_id=tenant_a.id, user_id=uuid4(), roles=[Role.ADMIN])
    headers = {"Authorization": f"Bearer {token_a}"}

    res_get = test_client.get(f"/api/v1/claims/{claim_b.id}", headers=headers)
    assert res_get.status_code == 404
    assert res_get.json()["detail"] == "Claim not found"

    res_put = test_client.put(
        f"/api/v1/claims/{claim_b.id}", json={"total_amount": 999.0}, headers=headers
    )
    assert res_put.status_code == 404

    res_scrub = test_client.post(f"/api/v1/claims/{claim_b.id}/scrub", headers=headers)
    assert res_scrub.status_code == 404

    res_del = test_client.delete(f"/api/v1/claims/{claim_b.id}", headers=headers)
    assert res_del.status_code == 404


def test_pg_rls_transaction_isolation(
    db_session: Session, tenant_a: Tenant, tenant_b: Tenant
) -> None:
    """Validates PostgreSQL RLS isolation at database level across transaction boundaries."""
    ensure_rls_role(db_session)
    db_session.commit()

    seed_patient_and_provider(db_session, tenant_a.id)
    seed_patient_and_provider(db_session, tenant_b.id)

    claim_a = make_test_claim(db_session, tenant_a.id, status=ClaimStatus.DRAFT)
    claim_b = make_test_claim(db_session, tenant_b.id, status=ClaimStatus.DRAFT)
    db_session.commit()

    claim_a_id: UUID = claim_a.id
    claim_b_id: UUID = claim_b.id

    try:
        apply_tenant_rls(db_session, tenant_a.id)
        db_session.execute(text("SET LOCAL ROLE test_rls_role;"))
        db_session.expire_all()

        visible_claims_a = db_session.query(Claim).all()
        visible_ids_a = {c.id for c in visible_claims_a}

        assert claim_a_id in visible_ids_a
        assert claim_b_id not in visible_ids_a

        db_session.execute(text("RESET ROLE;"))
        apply_tenant_rls(db_session, tenant_b.id)
        db_session.execute(text("SET LOCAL ROLE test_rls_role;"))
        db_session.expire_all()

        visible_claims_b = db_session.query(Claim).all()
        visible_ids_b = {c.id for c in visible_claims_b}

        assert claim_b_id in visible_ids_b
        assert claim_a_id not in visible_ids_b

    finally:
        db_session.execute(text("RESET ROLE;"))
        clear_tenant_rls(db_session)
        db_session.commit()
