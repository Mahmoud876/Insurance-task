from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenant import Tenant
from app.modules.claims.api import attachments as attachments_api
from app.modules.claims.models.claim import Claim
from app.modules.claims.models.claim_attachment import (
    ClaimAttachment,
    is_primary_eob_doc_type,
    normalize_doc_type,
)
from app.modules.claims.models.claim_line import ClaimLine
from app.modules.claims.models.patient import Patient
from app.modules.claims.models.patient_procedure_history import (
    PatientProcedureHistory,
    ProcedureHistorySource,
)
from app.modules.claims.models.provider import Provider
from app.modules.claims.service.claim_loader import load_reference_data
from app.modules.ocr.engine import OcrEngineUnavailableError, OcrLine
from app.modules.ocr.eob import EobExtract, EobProcedure, parse_eob_text, upsert_eob_history
from tests.conftest import auth_headers

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"payload-bytes"

EOB_LINES = [
    OcrLine(text="SMILE DENTAL INSURANCE", confidence=0.98, y0=10.0),
    OcrLine(text="MEMBER ID: 77123ABC45", confidence=0.97, y0=30.0),
    OcrLine(text="DATE OF SERVICE: 05/14/2026", confidence=0.96, y0=50.0),
    OcrLine(text="D0120 PERIODIC ORAL EVALUATION 45.00 37.00 PAID", confidence=0.95, y0=70.0),
    OcrLine(text="D0150 COMPREHENSIVE ORAL EXAM 60.00 48.00 PAID", confidence=0.94, y0=90.0),
    OcrLine(text="TOTAL ALLOWED: 85.00", confidence=0.90, y0=110.0),
]


class FakeEngine:
    def __init__(self, lines: list[OcrLine]) -> None:
        self._lines = lines

    def text_lines(self, image) -> list[OcrLine]:
        return self._lines


def create_claim(db: Session, *, is_secondary_claim: bool = False) -> tuple[Tenant, Claim]:
    tenant = Tenant(name="EOB Tenant", slug=f"eob-{uuid4()}")
    db.add(tenant)
    db.flush()

    patient = Patient(
        tenant_id=tenant.id,
        first_name="Eva",
        last_name="Eob",
        dob=date(1990, 1, 1),
    )
    provider = Provider(
        tenant_id=tenant.id,
        npi="9990001111",
        first_name="Dr",
        last_name="Eob",
    )
    db.add_all([patient, provider])
    db.commit()
    db.refresh(patient)
    db.refresh(provider)

    claim = Claim(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_id=provider.id,
        total_amount=Decimal("50.00"),
        service_date_from=date(2026, 6, 1),
        service_date_to=date(2026, 6, 1),
        is_secondary_claim=is_secondary_claim,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return tenant, claim


def stub_upload_ocr(monkeypatch, lines: list[OcrLine]) -> None:
    monkeypatch.setattr(attachments_api, "get_ocr_engine", lambda: FakeEngine(lines))
    monkeypatch.setattr(
        attachments_api, "ocr_lines_from_bytes", lambda data, media_type, engine: lines
    )


def test_parse_eob_text_extracts_procedure_entries() -> None:
    result = parse_eob_text(EOB_LINES)

    assert result.payer_name == "SMILE DENTAL INSURANCE"
    assert result.member_id == "77123ABC45"
    assert result.service_date_from == date(2026, 5, 14)
    assert result.service_date_to == date(2026, 5, 14)
    assert result.total_allowed == pytest.approx(85.00)

    codes = [
        (entry.procedure_code, entry.service_date, entry.allowed_amount)
        for entry in result.procedure_entries
    ]
    assert codes == [
        ("D0120", date(2026, 5, 14), 37.00),
        ("D0150", date(2026, 5, 14), 48.00),
    ]


def test_parse_eob_text_ignores_non_eob_content() -> None:
    result = parse_eob_text(
        [
            OcrLine(text="Periodic x-ray of the right maxillary region", confidence=0.6, y0=10.0),
            OcrLine(text="0012-Report", confidence=0.5, y0=30.0),
        ]
    )

    assert result.procedure_entries == ()
    assert not result.has_entries


def test_doc_type_normalization_and_primary_eob_alias() -> None:
    assert normalize_doc_type("Primary EOB") == "primary_eob"
    assert normalize_doc_type("EOB") == "eob"
    assert normalize_doc_type("X-RaY") == "x-ray"
    assert normalize_doc_type("") == "attachment"
    assert normalize_doc_type(None) == "attachment"

    assert is_primary_eob_doc_type("eob")
    assert is_primary_eob_doc_type("primary_eob")
    assert is_primary_eob_doc_type("primary-eob")
    assert not is_primary_eob_doc_type("xray")
    assert not is_primary_eob_doc_type("attachment")


def test_upload_attachment_stores_doc_type_and_ocr_text(client, db_session, monkeypatch) -> None:
    stub_upload_ocr(monkeypatch, EOB_LINES)

    tenant, claim = create_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("eob.png", PNG_BYTES, "image/png")},
        data={"doc_type": "Primary EOB"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["doc_type"] == "primary_eob"
    assert body["ocr_text"] == "\n".join(line.text for line in EOB_LINES)

    row = db_session.get(ClaimAttachment, body["id"])
    assert row is not None
    assert row.doc_type == "primary_eob"
    assert row.ocr_text.startswith("SMILE DENTAL INSURANCE")


def test_upload_eob_imports_and_dedupes_procedure_history(client, db_session, monkeypatch) -> None:
    stub_upload_ocr(monkeypatch, EOB_LINES)

    tenant, claim = create_claim(db_session)
    headers = auth_headers(tenant.id)

    first = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=headers,
        files={"file": ("eob.png", PNG_BYTES, "image/png")},
        data={"doc_type": "EOB"},
    )
    assert first.status_code == 201

    history = list(db_session.scalars(select(PatientProcedureHistory)))
    assert len(history) == 2
    assert {row.procedure_code for row in history} == {"D0120", "D0150"}
    assert all(row.source == ProcedureHistorySource.EOB_IMPORT for row in history)
    assert all(row.service_date == date(2026, 5, 14) for row in history)

    second = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=headers,
        files={"file": ("eob.png", PNG_BYTES, "image/png")},
        data={"doc_type": "EOB"},
    )
    assert second.status_code == 201
    assert len(list(db_session.scalars(select(PatientProcedureHistory)))) == 2


def test_upload_attachment_succeeds_when_ocr_unavailable(client, db_session, monkeypatch) -> None:
    def raise_unavailable():
        raise OcrEngineUnavailableError("EasyOCR is not installed.")

    monkeypatch.setattr(attachments_api, "get_ocr_engine", raise_unavailable)

    tenant, claim = create_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("eob.png", PNG_BYTES, "image/png")},
        data={"doc_type": "EOB"},
    )

    assert response.status_code == 201
    assert response.json()["ocr_text"] is None
    assert len(list(db_session.scalars(select(PatientProcedureHistory)))) == 0


def test_upload_non_eob_does_not_import_history(client, db_session, monkeypatch) -> None:
    stub_upload_ocr(monkeypatch, EOB_LINES)

    tenant, claim = create_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("xray.png", PNG_BYTES, "image/png")},
        data={"doc_type": "XRAY"},
    )

    assert response.status_code == 201
    assert response.json()["doc_type"] == "xray"
    assert len(list(db_session.scalars(select(PatientProcedureHistory)))) == 0


def test_load_reference_data_exposes_cob_metadata(db_session) -> None:
    tenant, claim = create_claim(db_session, is_secondary_claim=True)

    attachment = ClaimAttachment(
        tenant_id=tenant.id,
        claim_id=claim.id,
        file_key="tenants/key/attachments/eob.png",
        file_type="image/png",
        doc_type="eob",
    )
    db_session.add(attachment)
    db_session.commit()

    reference = load_reference_data(db_session, claim)
    assert reference.code_metadata == {
        "is_secondary_claim": True,
        "primary_eob_attached": True,
    }

    other_tenant, plain_claim = create_claim(db_session)
    reference = load_reference_data(db_session, plain_claim)
    assert reference.code_metadata == {
        "is_secondary_claim": False,
        "primary_eob_attached": False,
    }


def test_scrub_warns_for_secondary_claim_without_eob_then_clears_after_upload(
    client, db_session, monkeypatch
) -> None:
    stub_upload_ocr(monkeypatch, EOB_LINES)

    tenant, claim = create_claim(db_session, is_secondary_claim=True)

    first = client.post(f"/api/v1/claims/{claim.id}/scrub", headers=auth_headers(tenant.id))
    assert first.status_code == 200
    cob_rules = [f for f in first.json()["findings_summary"] if f["rule_id"] == "P4_COB_ORDER"]
    assert cob_rules, "Secondary claim without primary EOB should raise P4_COB_ORDER"

    upload = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("eob.png", PNG_BYTES, "image/png")},
        data={"doc_type": "EOB"},
    )
    assert upload.status_code == 201

    second = client.post(f"/api/v1/claims/{claim.id}/scrub", headers=auth_headers(tenant.id))
    assert second.status_code == 200
    cob_rules = [f for f in second.json()["findings_summary"] if f["rule_id"] == "P4_COB_ORDER"]
    assert not cob_rules, "P4_COB_ORDER should clear once the primary EOB is attached"


def test_eob_imported_history_triggers_frequency_limitation(client, db_session) -> None:
    tenant, claim = create_claim(db_session)

    history_entries = EobExtract(
        service_date_from=date(2026, 1, 15),
        service_date_to=date(2026, 2, 15),
        procedure_entries=(
            EobProcedure(procedure_code="D4341", service_date=date(2026, 1, 15)),
            EobProcedure(procedure_code="D4341", service_date=date(2026, 2, 15)),
        ),
    )
    created = upsert_eob_history(
        db_session,
        tenant_id=tenant.id,
        patient_id=claim.patient_id,
        payer_id=None,
        extract=history_entries,
    )
    assert created == 2

    line = ClaimLine(
        tenant_id=tenant.id,
        claim_id=claim.id,
        procedure_code="D4341",
        charge_amount=Decimal("150.00"),
    )
    db_session.add(line)
    db_session.commit()

    response = client.post(f"/api/v1/claims/{claim.id}/scrub", headers=auth_headers(tenant.id))
    assert response.status_code == 200
    limits = [
        f for f in response.json()["findings_summary"] if f["rule_id"] == "P4_FREQ_LIMITATION"
    ]
    assert limits, "Two prior EOB-imported D4341s should exceed the frequency limitation"
    assert limits[0]["message_key"] == "DCS-POL-0007"
