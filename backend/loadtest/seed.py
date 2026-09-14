"""Seed a tenant, patient, provider, and N 20-line DRAFT claims for load testing."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

import app.db.models  # noqa: F401  (registers all ORM mappers)
from app.core.database_session import engine
from app.core.tenant import Tenant
from app.modules.claims.models.claim import Claim, ClaimStatus
from app.modules.claims.models.claim_line import ClaimLine
from app.modules.claims.models.insurance_policy import InsurancePolicy
from app.modules.claims.models.patient import Patient
from app.modules.claims.models.patient_procedure_history import (
    PatientProcedureHistory,
    ProcedureHistorySource,
)
from app.modules.claims.models.provider import Provider
from app.modules.payers.payer import Payer
from app.modules.payers.payer_plan import PayerPlan

TENANT_SLUG = "loadtest"
LINE_COUNT = 20
PROCEDURES = ["D0120", "D0274", "D1110", "D2391", "D2740", "D1351", "D0150"]

SeedState = dict[str, "str | list[str]"]


def _get_or_create_tenant(db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == TENANT_SLUG).first()
    if tenant is None:
        tenant = Tenant(
            name="Load Test Tenant",
            slug=TENANT_SLUG,
        )
        db.add(tenant)
        db.flush()
    return tenant


def _create_claim(
    db: Session,
    tenant: Tenant,
    patient: Patient,
    provider: Provider,
    payer: Payer,
    policy: InsurancePolicy,
) -> Claim:
    claim = Claim(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_id=provider.id,
        payer_id=payer.id,
        policy_id=policy.id,
        status=ClaimStatus.DRAFT,
        total_amount=Decimal(str(round(LINE_COUNT * 25.50, 2))),
        service_date_from=date(2026, 1, 15),
        service_date_to=date(2026, 1, 15),
    )
    db.add(claim)
    db.flush()

    for index in range(LINE_COUNT):
        db.add(
            ClaimLine(
                tenant_id=tenant.id,
                claim_id=claim.id,
                procedure_code=PROCEDURES[index % len(PROCEDURES)],
                tooth_number=str(11 + (index % 20)),
                surface="MOD" if index % 2 else "B",
                charge_amount=Decimal("25.50"),
            )
        )
    return claim


def seed() -> SeedState:
    with Session(engine) as db:
        tenant = _get_or_create_tenant(db)

        patient = Patient(
            tenant_id=tenant.id,
            first_name="Load",
            last_name="TestPatient",
            dob=date(1992, 3, 17),
        )
        provider = Provider(
            tenant_id=tenant.id,
            npi="4567890123",
            first_name="Dr",
            last_name="Load",
        )
        payer = Payer(tenant_id=tenant.id, name="Load Test Payer", payer_code="LTP")
        payer_plan = PayerPlan(tenant_id=tenant.id, plan_name="Load Test PPO")
        payer.plans.append(payer_plan)

        db.add_all([patient, provider, payer])
        db.flush()

        policy = InsurancePolicy(
            tenant_id=tenant.id,
            patient_id=patient.id,
            payer_plan_id=payer_plan.id,
            policy_number=f"POL-LOAD-{uuid4().hex[:8].upper()}",
            effective_date=date(2024, 1, 1),
            termination_date=None,
            source="manual",
        )
        db.add(policy)
        db.flush()

        for service_date, procedure in (
            (date(2025, 7, 1), "D0120"),
            (date(2025, 3, 15), "D0274"),
            (date(2024, 11, 20), "D1110"),
            (date(2025, 9, 5), "D0120"),
        ):
            db.add(
                PatientProcedureHistory(
                    tenant_id=tenant.id,
                    patient_id=patient.id,
                    procedure_code=procedure,
                    service_date=service_date,
                    tooth_canonical=11,
                    surfaces=["M", "O", "D"],
                    quadrant=1,
                    arch="upper",
                    source=ProcedureHistorySource.INTERNAL_CLAIM,
                )
            )

        claim_count = int(os.getenv("CLAIM_COUNT", "50"))
        claim_ids = [
            str(_create_claim(db, tenant, patient, provider, payer, policy).id)
            for _ in range(claim_count)
        ]

        db.commit()

        return {
            "tenant_id": str(tenant.id),
            "patient_id": str(patient.id),
            "provider_id": str(provider.id),
            "claim_id": claim_ids[0],
            "claim_ids": claim_ids,
            "claim_count": str(claim_count),
        }


if __name__ == "__main__":
    import json

    print(json.dumps(seed(), indent=2))
