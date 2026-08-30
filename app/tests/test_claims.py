from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.claim import Claim, ClaimStatus
from app.db.models.patient import Patient
from app.db.models.provider import Provider
from app.db.models.tenant import Tenant


def create_test_data(db: Session):
    tenant = Tenant(
        name="Test Tenant",
        slug=f"test-{uuid4()}",
    )

    db.add(tenant)
    db.flush()

    patient = Patient(
        tenant_id=tenant.id,
        first_name="John",
        last_name="Doe",
        dob=date(1990, 1, 1),
    )

    provider = Provider(
        tenant_id=tenant.id,
        npi="1234567890",
        first_name="Jane",
        last_name="Smith",
    )

    db.add_all([patient, provider])
    db.commit()
    db.refresh(tenant)
    db.refresh(patient)
    db.refresh(provider)

    return tenant, patient, provider


def test_create_claim(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    response = client.post(
        "/v1/claims",
        json={
            "tenant_id": str(tenant.id),
            "patient_id": str(patient.id),
            "provider_id": str(provider.id),
            "total_amount": "100.00",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["patient_id"] == str(patient.id)
    assert data["provider_id"] == str(provider.id)
    assert data["status"] == "DRAFT"
    assert data["total_amount"] == "100.00"


def test_get_claim(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    claim = Claim(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_id=provider.id,
        total_amount=Decimal("200.00"),
    )

    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    response = client.get(f"/v1/claims/{claim.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(claim.id)
    assert "etag" in response.headers


def test_list_claims(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    for amount in ["100.00", "200.00", "300.00"]:
        db_session.add(
            Claim(
                tenant_id=tenant.id,
                patient_id=patient.id,
                provider_id=provider.id,
                total_amount=Decimal(amount),
            )
        )

    db_session.commit()

    response = client.get("/v1/claims")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 3


def test_filter_claims_by_status(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    db_session.add(
        Claim(
            tenant_id=tenant.id,
            patient_id=patient.id,
            provider_id=provider.id,
            status=ClaimStatus.SUBMITTED,
            total_amount=Decimal("100.00"),
        )
    )

    db_session.add(
        Claim(
            tenant_id=tenant.id,
            patient_id=patient.id,
            provider_id=provider.id,
            status=ClaimStatus.DRAFT,
            total_amount=Decimal("200.00"),
        )
    )

    db_session.commit()

    response = client.get("/v1/claims?status=SUBMITTED")

    assert response.status_code == 200
    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["status"] == "SUBMITTED"


def test_filter_claims_by_patient(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    patient2 = Patient(
        tenant_id=tenant.id,
        first_name="Another",
        last_name="Patient",
        dob=date(1991, 1, 1),
    )

    db_session.add(patient2)
    db_session.flush()

    db_session.add(
        Claim(
            tenant_id=tenant.id,
            patient_id=patient.id,
            provider_id=provider.id,
            total_amount=Decimal("100.00"),
        )
    )

    db_session.add(
        Claim(
            tenant_id=tenant.id,
            patient_id=patient2.id,
            provider_id=provider.id,
            total_amount=Decimal("200.00"),
        )
    )

    db_session.commit()

    response = client.get(f"/v1/claims?patient_id={patient.id}")

    assert response.status_code == 200

    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["patient_id"] == str(patient.id)


def test_cursor_pagination(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    for i in range(3):
        db_session.add(
            Claim(
                tenant_id=tenant.id,
                patient_id=patient.id,
                provider_id=provider.id,
                total_amount=Decimal(str(100 + i)),
            )
        )

    db_session.commit()

    response = client.get("/v1/claims?limit=2")

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 2
    assert data["next_cursor"] is not None

    cursor = data["next_cursor"]

    response2 = client.get(f"/v1/claims?limit=2&cursor={cursor}")

    assert response2.status_code == 200

    data2 = response2.json()

    assert len(data2["items"]) == 1


def test_patch_claim_with_etag(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    claim = Claim(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_id=provider.id,
        total_amount=Decimal("100.00"),
    )

    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    get_response = client.get(f"/v1/claims/{claim.id}")

    etag = get_response.headers["etag"]

    response = client.patch(
        f"/v1/claims/{claim.id}",
        headers={"If-Match": etag},
        json={"status": "SUBMITTED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"
    assert "etag" in response.headers


def test_patch_claim_with_stale_etag(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    claim = Claim(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_id=provider.id,
        total_amount=Decimal("100.00"),
    )

    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    response = client.get(f"/v1/claims/{claim.id}")

    old_etag = response.headers["etag"]

    response = client.patch(
        f"/v1/claims/{claim.id}",
        headers={"If-Match": old_etag},
        json={"status": "SUBMITTED"},
    )

    assert response.status_code == 200

    response = client.patch(
        f"/v1/claims/{claim.id}",
        headers={"If-Match": old_etag},
        json={"status": "PAID"},
    )

    assert response.status_code == 412
    assert response.json()["detail"] == "Claim has been modified"


def test_delete_claim(client, db_session):
    tenant, patient, provider = create_test_data(db_session)

    claim = Claim(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_id=provider.id,
        total_amount=Decimal("100.00"),
    )

    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)

    response = client.delete(f"/v1/claims/{claim.id}")

    assert response.status_code == 204

    response = client.get(f"/v1/claims/{claim.id}")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_get_missing_claim_returns_problem_json(client):
    claim_id = uuid4()

    response = client.get(f"/v1/claims/{claim_id}")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")

    data = response.json()

    assert data["status"] == 404
    assert data["detail"] == "Claim not found"
