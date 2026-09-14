from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.security.auth import Role
from app.core.storage import random_object_key, sanitize_extension
from app.core.tenant import Tenant
from app.modules.claims.models.claim import Claim
from app.modules.claims.models.claim_attachment import ClaimAttachment
from app.modules.claims.models.patient import Patient
from app.modules.claims.models.provider import Provider
from tests.conftest import auth_headers

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"payload-bytes"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"payload-bytes"


class FakeStorage:
    def __init__(self) -> None:
        self.puts: list[tuple[str, bytes, str]] = []

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.puts.append((key, data, content_type))

    def presign_download_url(self, key: str, expires_in: int) -> str:
        return f"https://minio.local/{key}?X-Amz-Expires={expires_in}&X-Amz-Signature=deadbeef"


def create_claim(db: Session) -> tuple[Tenant, Claim]:
    tenant = Tenant(name="Attach Tenant", slug=f"attach-{uuid4()}")
    db.add(tenant)
    db.flush()

    patient = Patient(
        tenant_id=tenant.id,
        first_name="Jo",
        last_name="Attach",
        dob=date(1990, 1, 1),
    )
    provider = Provider(
        tenant_id=tenant.id,
        npi="9990001111",
        first_name="Dr",
        last_name="Attach",
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
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return tenant, claim


def test_random_object_key_format_and_uniqueness() -> None:
    tenant_id = uuid4()
    claim_id = uuid4()
    key_a = random_object_key(tenant_id, claim_id, "x-ray.png")
    key_b = random_object_key(tenant_id, claim_id, "x-ray.png")

    assert key_a != key_b
    prefix = f"tenants/{tenant_id}/claims/{claim_id}/attachments/"
    assert key_a.startswith(prefix)
    assert key_a.endswith(".png")
    assert key_a.rsplit("/", 1)[1].split(".", 1)[0].isalnum()


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("x-ray.png", "png"),
        ("narrative", "bin"),
        ("eob.INSUANCE-CARD.PDF", "pdf"),
        ("scan.tar.gz", "gz"),
    ],
)
def test_sanitize_extension(filename: str, expected: str) -> None:
    assert sanitize_extension(filename) == expected


def test_upload_attachment_201_and_persisted(client, db_session, monkeypatch) -> None:
    from app.modules.claims import api as claims_api

    fake = FakeStorage()
    monkeypatch.setattr(claims_api.attachments, "object_storage", fake)

    tenant, claim = create_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("xray.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["claim_id"] == str(claim.id)
    assert body["file_type"] == "image/png"
    assert len(fake.puts) == 1
    key, data, content_type = fake.puts[0]
    assert data == PNG_BYTES
    assert content_type == "image/png"
    assert key.startswith(f"tenants/{tenant.id}/claims/{claim.id}/attachments/")

    row = db_session.get(ClaimAttachment, body["id"])
    assert row is not None
    assert row.file_key == key


def test_list_attachments_returns_uploads(client, db_session, monkeypatch) -> None:
    from app.modules.claims import api as claims_api

    monkeypatch.setattr(claims_api.attachments, "object_storage", FakeStorage())

    tenant, claim = create_claim(db_session)

    first = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("xray.png", PNG_BYTES, "image/png")},
        data={"doc_type": "x-ray"},
    )
    second = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("eob.png", PNG_BYTES, "image/png")},
        data={"doc_type": "Primary EOB"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
    )

    assert response.status_code == 200
    body = response.json()

    assert [item["id"] for item in body] == [second.json()["id"], first.json()["id"]]
    assert body[0]["doc_type"] == "primary_eob"
    assert body[0]["ocr_text"] is None


def test_list_attachments_404_for_missing_claim(client, db_session) -> None:
    tenant, _ = create_claim(db_session)

    response = client.get(
        f"/api/v1/claims/{uuid4()}/attachments",
        headers=auth_headers(tenant.id),
    )

    assert response.status_code == 404


def test_upload_rejects_mismatched_magic(client, db_session, monkeypatch) -> None:
    from app.modules.claims import api as claims_api

    fake = FakeStorage()
    monkeypatch.setattr(claims_api.attachments, "object_storage", fake)

    tenant, claim = create_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("xray.png", JPEG_BYTES, "image/png")},
    )

    assert response.status_code == 415
    assert fake.puts == []


def test_upload_403_for_viewer(client, db_session, monkeypatch) -> None:
    from app.modules.claims import api as claims_api

    monkeypatch.setattr(claims_api.attachments, "object_storage", FakeStorage())

    tenant, claim = create_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id, roles=[Role.VIEWER]),
        files={"file": ("xray.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 403


def test_upload_404_for_missing_claim(client, db_session, monkeypatch) -> None:
    from app.modules.claims import api as claims_api

    monkeypatch.setattr(claims_api.attachments, "object_storage", FakeStorage())

    tenant, _ = create_claim(db_session)

    response = client.post(
        f"/api/v1/claims/{uuid4()}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("xray.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 404


def test_presigned_url_5_minutes(client, db_session, monkeypatch) -> None:
    from app.modules.claims import api as claims_api

    fake = FakeStorage()
    monkeypatch.setattr(claims_api.attachments, "object_storage", fake)

    tenant, claim = create_claim(db_session)
    upload = client.post(
        f"/api/v1/claims/{claim.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("xray.png", PNG_BYTES, "image/png")},
    )
    attachment_id = upload.json()["id"]

    response = client.get(
        f"/api/v1/claims/{claim.id}/attachments/{attachment_id}/url",
        headers=auth_headers(tenant.id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 300
    assert "X-Amz-Expires=300" in body["url"]
    assert body["content_type"] == "image/png"


def test_presigned_url_404_for_wrong_claim(client, db_session, monkeypatch) -> None:
    from app.modules.claims import api as claims_api

    monkeypatch.setattr(claims_api.attachments, "object_storage", FakeStorage())

    tenant, claim_a = create_claim(db_session)
    upload = client.post(
        f"/api/v1/claims/{claim_a.id}/attachments",
        headers=auth_headers(tenant.id),
        files={"file": ("xray.png", PNG_BYTES, "image/png")},
    )
    attachment_id = upload.json()["id"]

    tenant_b, claim_b = create_claim(db_session)
    response = client.get(
        f"/api/v1/claims/{claim_b.id}/attachments/{attachment_id}/url",
        headers=auth_headers(tenant_b.id),
    )

    assert response.status_code == 404

    bad_claim = client.get(
        f"/api/v1/claims/{uuid4()}/attachments/{attachment_id}/url",
        headers=auth_headers(tenant.id),
    )
    assert bad_claim.status_code == 404
