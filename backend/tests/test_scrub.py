from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.core.security.auth import Role
from app.core.tenant import Tenant
from app.modules.claims.models.claim import Claim, ClaimStatus
from app.modules.claims.models.claim_line import ClaimLine
from app.modules.claims.models.patient import Patient
from app.modules.claims.models.provider import Provider
from app.modules.scrubber.models.scrub_run import ScrubRun
from app.modules.scrubber.service.scrub_service import SCRUB_ENGINE_VERSION
from tests.conftest import auth_headers


def _seed_scrub_claim(db: Session, *, line_count: int = 20) -> tuple[Tenant, Claim]:
    tenant = Tenant(
        name="Scrub Tenant",
        slug=f"scrub-{uuid4()}",
    )
    db.add(tenant)
    db.flush()

    patient = Patient(
        tenant_id=tenant.id,
        first_name="Scrub",
        last_name="Patient",
        dob=date(1990, 5, 10),
    )
    provider = Provider(
        tenant_id=tenant.id,
        npi="9988776655",
        first_name="Dr",
        last_name="Scrubber",
    )
    db.add_all([patient, provider])
    db.flush()

    claim = Claim(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_id=provider.id,
        status=ClaimStatus.DRAFT,
        total_amount=Decimal(str(line_count * 25.50)),
        service_date_from=date(2024, 3, 1),
        service_date_to=date(2024, 3, 1),
    )
    db.add(claim)
    db.flush()

    for index in range(line_count):
        db.add(
            ClaimLine(
                tenant_id=tenant.id,
                claim_id=claim.id,
                procedure_code=f"D0{120 + index:03d}",
                tooth_number=str(11 + (index % 20)),
                surface="MOD" if index % 2 else "B",
                charge_amount=Decimal("25.50"),
            )
        )
    db.commit()
    db.refresh(claim)
    return tenant, claim


def test_scrub_runs_pipeline_and_persists_results(client, db_session):
    tenant, claim = _seed_scrub_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{claim.id}/scrub",
        headers=auth_headers(tenant.id),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(claim.id)
    assert data["status"] == "SCRUBBED"
    assert isinstance(data["readiness_score"], int)
    assert 0 <= data["readiness_score"] <= 100
    assert isinstance(data["findings_summary"], list)

    run = (
        db_session.execute(
            text(
                "SELECT engine_version, input_hash, readiness_score, status FROM scrub_runs WHERE claim_id = :cid"
            ),
            {"cid": claim.id},
        )
        .mappings()
        .one()
    )
    assert run["engine_version"] == SCRUB_ENGINE_VERSION
    assert len(run["input_hash"]) == 64
    assert run["readiness_score"] == data["readiness_score"]
    assert run["status"] in ("ready", "needs_review")

    assert (
        db_session.scalar(text("SELECT status FROM claim WHERE id = :cid"), {"cid": claim.id})
        == "SCRUBBED"
    )


def test_scrub_pipeline_query_count_is_bounded(client, db_session, db_engine):
    """The scrub path must not exhibit N+1 lazy loads per claim line."""
    tenant, claim = _seed_scrub_claim(db_session)

    counters: dict[str, int] = {"queries": 0}

    @event.listens_for(db_engine, "before_cursor_execute")
    def _count(conn, cursor, statement, parameters, context, executemany):
        if not statement.lower().startswith(("select", "insert", "update", "delete")):
            return
        counters["queries"] += 1

    try:
        response = client.post(
            f"/api/v1/claims/{claim.id}/scrub",
            headers=auth_headers(tenant.id),
        )
    finally:
        event.remove(db_engine, "before_cursor_execute", _count)

    assert response.status_code == 200
    assert counters["queries"] <= 15, (
        f"Scrub performed {counters['queries']} queries; suspected N+1 on {claim.lines.__len__()} lines"
    )


def test_scrub_requires_permission(client, db_session):
    tenant, claim = _seed_scrub_claim(db_session, line_count=1)

    response = client.post(
        f"/api/v1/claims/{claim.id}/scrub",
        headers=auth_headers(tenant.id, roles=[Role.VIEWER]),
    )

    assert response.status_code == 403
    assert (
        db_session.scalar(text("SELECT status FROM claim WHERE id = :cid"), {"cid": claim.id})
        == "DRAFT"
    )


def test_scrub_is_idempotent_and_reuses_scrub_run(client, db_session):
    tenant, claim = _seed_scrub_claim(db_session, line_count=3)

    first = client.post(f"/api/v1/claims/{claim.id}/scrub", headers=auth_headers(tenant.id))
    assert first.status_code == 200

    second = client.post(f"/api/v1/claims/{claim.id}/scrub", headers=auth_headers(tenant.id))
    assert second.status_code == 200
    assert second.json()["status"] == "SCRUBBED"

    rows = db_session.execute(
        text("SELECT id FROM scrub_runs WHERE claim_id = :cid"),
        {"cid": claim.id},
    ).all()
    assert len(rows) == 1


def test_scrub_run_model_registered():
    assert ScrubRun.__tablename__ == "scrub_runs"
