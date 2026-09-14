from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.field_encryption import (
    decrypt_field,
    derive_member_last4,
    encrypt_field,
)
from app.core.tenant import Tenant
from app.modules.claims.models.insurance_policy import InsurancePolicy
from app.modules.claims.models.patient import Patient
from app.modules.payers.payer import Payer
from app.modules.payers.payer_plan import PayerPlan

MEMBER_ID = "MEM-10023485"


def test_encrypt_decrypt_roundtrip() -> None:
    ciphertext = encrypt_field(MEMBER_ID)
    assert ciphertext != MEMBER_ID.encode("utf-8")
    assert decrypt_field(ciphertext) == MEMBER_ID


def test_decrypt_none_returns_none() -> None:
    assert decrypt_field(None) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("MEM-10023485", "3485"),
        ("A123456789B", "6789"),
        ("NO-DIGITS", "GITS"),
        ("", ""),
    ],
)
def test_derive_member_last4(raw: str, expected: str) -> None:
    assert derive_member_last4(raw) == expected


def _policy(db: Session) -> InsurancePolicy:
    tenant = Tenant(name="Encryption Tenant", slug=f"enc-{uuid4()}")
    db.add(tenant)
    db.flush()

    patient = Patient(
        tenant_id=tenant.id,
        first_name="Enc",
        last_name="Test",
        dob=date(1990, 1, 1),
    )
    payer = Payer(
        tenant_id=tenant.id,
        name="Encryption Payer",
        payer_code=f"EP-{uuid4().hex[:6].upper()}",
    )
    payer_plan = PayerPlan(tenant_id=tenant.id, plan_name="Encryption PPO")
    payer.plans.append(payer_plan)
    db.add_all([patient, payer])
    db.flush()

    policy = InsurancePolicy(
        tenant_id=tenant.id,
        patient_id=patient.id,
        payer_plan_id=payer_plan.id,
        policy_number=f"POL-{uuid4().hex[:8].upper()}",
        effective_date=date(2025, 1, 1),
        member_id=MEMBER_ID,
    )
    db.add(policy)
    db.flush()
    return policy


def test_member_id_stored_encrypted_at_rest(db_session: Session) -> None:
    policy = _policy(db_session)

    assert policy.member_id_last4 == "3485"
    assert policy.member_id == MEMBER_ID
    assert policy.member_id_enc is not None
    assert MEMBER_ID.encode("utf-8") not in policy.member_id_enc
    assert MEMBER_ID not in str(policy.member_id_enc)
