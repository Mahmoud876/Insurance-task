from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.tenant import Tenant
from app.main import app
from app.modules.claims.models.insurance_policy import InsurancePolicy
from app.modules.claims.models.patient import Patient
from app.modules.ocr import service as ocr_service
from app.modules.ocr.api import ocr as ocr_api
from app.modules.ocr.engine import OcrEngineUnavailableError, OcrLine
from app.modules.ocr.parser import parse_insurance_card
from app.modules.payers.payer import Payer
from app.modules.preauth.api.preauth import _parse_uuid
from tests.conftest import auth_headers

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"insurance-card-bytes"


class FakeEngine:
    def __init__(self, lines: list[OcrLine]) -> None:
        self._lines = lines

    def text_lines(self, image) -> list[OcrLine]:
        return self._lines


CARD_LINES = [
    OcrLine(text="DELTA DENTAL", confidence=0.98, y0=10.0),
    OcrLine(text="Member ID: C1098827404", confidence=0.97, y0=30.0),
    OcrLine(text="Group Number: DENT-88123", confidence=0.95, y0=50.0),
    OcrLine(text="Subscriber Name: Jane Doe", confidence=0.96, y0=70.0),
]


def stub_ocr(monkeypatch, lines: list[OcrLine] | None = None) -> None:
    monkeypatch.setattr(ocr_service, "image_from_bytes", lambda data, media_type: None)
    monkeypatch.setattr(ocr_api, "get_ocr_engine", lambda: FakeEngine(lines or CARD_LINES))


def test_parse_insurance_card_extracts_fields() -> None:
    result = parse_insurance_card(CARD_LINES)

    assert result.payer_name == "DELTA DENTAL"
    assert result.payer_id == "DELTA_DENTAL"
    assert result.member_id == "C1098827404"
    assert result.group_number == "DENT-88123"
    assert result.subscriber_name == "Jane Doe"
    assert result.confidence_score == pytest.approx(0.99)


def test_parse_insurance_card_uses_printed_payer_id() -> None:
    lines = CARD_LINES + [OcrLine(text="Payer ID: DEL_9981", confidence=0.99, y0=90.0)]

    result = parse_insurance_card(lines)

    assert result.payer_id == "DEL_9981"


def test_parse_insurance_card_missing_fields() -> None:
    result = parse_insurance_card([OcrLine(text="000-000", confidence=0.5)])

    assert result.payer_name == ""
    assert result.payer_id == ""
    assert result.member_id == ""
    assert result.group_number == ""
    assert result.subscriber_name == ""
    assert result.confidence_score == pytest.approx(0.5)


def test_ocr_endpoint_returns_extraction(client, monkeypatch) -> None:
    stub_ocr(monkeypatch)

    response = client.post(
        "/api/v1/insurance-cards/ocr",
        headers=auth_headers(uuid4()),
        files={"file": ("card.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["payer_id"] == "DELTA_DENTAL"
    assert body["member_id"] == "C1098827404"
    assert body["group_number"] == "DENT-88123"
    assert body["subscriber_name"] == "Jane Doe"
    assert body["policy_id"] is None


def test_ocr_endpoint_persists_policy(client, db_session, monkeypatch) -> None:
    stub_ocr(monkeypatch)

    tenant = Tenant(name="OCR Tenant", slug=f"ocr-{uuid4()}")
    db_session.add(tenant)
    db_session.flush()
    patient = Patient(
        tenant_id=tenant.id,
        first_name="Jane",
        last_name="Doe",
        dob=date(1990, 1, 1),
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    response = client.post(
        f"/api/v1/insurance-cards/ocr?patient_id={patient.id}",
        headers=auth_headers(tenant.id),
        files={"file": ("card.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    policy_id = UUID(body["policy_id"])

    policy = db_session.get(InsurancePolicy, policy_id)
    assert policy is not None
    assert policy.tenant_id == tenant.id
    assert policy.patient_id == patient.id
    assert policy.source == "ocr"
    assert policy.member_id == "C1098827404"
    assert policy.group_number == "DENT-88123"
    assert policy.verified_at is not None

    payer = db_session.get(Payer, policy.payer_plan.payer_id)
    assert payer is not None
    assert payer.name == "DELTA DENTAL"
    assert payer.payer_code == "DELTA_DENTAL"

    second = client.post(
        f"/api/v1/insurance-cards/ocr?patient_id={patient.id}",
        headers=auth_headers(tenant.id),
        files={"file": ("card.png", PNG_BYTES, "image/png")},
    )
    assert second.status_code == 200
    assert second.json()["policy_id"] == body["policy_id"]

    policies = list(db_session.scalars(select(InsurancePolicy)))
    assert len(policies) == 1


def test_ocr_endpoint_returns_503_when_engine_unavailable(client, monkeypatch) -> None:
    def raise_unavailable():
        raise OcrEngineUnavailableError("EasyOCR is not installed.")

    monkeypatch.setattr(ocr_api, "get_ocr_engine", raise_unavailable)

    response = client.post(
        "/api/v1/insurance-cards/ocr",
        headers=auth_headers(uuid4()),
        files={"file": ("card.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 503


def test_ocr_endpoint_returns_501_in_production(client, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    response = client.post(
        "/api/v1/insurance-cards/ocr",
        headers=auth_headers(uuid4()),
        files={"file": ("card.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 501


def test_ocr_rejects_unsupported_media(client) -> None:
    response = client.post(
        "/api/v1/insurance-cards/ocr",
        headers=auth_headers(uuid4()),
        files={"file": ("readme.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 415


def test_preauth_uuid_validation() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _parse_uuid("not-a-uuid", "claim_id")
    assert exc_info.value.status_code == 422


def test_ocr_and_preauth_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/insurance-cards/ocr" in paths
    assert "/api/v1/preauth/requests" in paths
    assert "/api/v1/preauth/requests/{preauth_id}" in paths
