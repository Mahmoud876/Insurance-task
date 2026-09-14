import os
import uuid
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

import app.db.models as _db_models  # noqa: F401  (registers all ORM mappers before first query)
from app.core.database_session import SessionLocal
from app.core.tenant import Tenant
from app.core.user import AppUser
from app.modules.claims.models.claim import Claim, ClaimStatus
from app.modules.claims.models.claim_line import ClaimLine
from app.modules.claims.models.patient import Patient
from app.modules.claims.models.provider import Provider

KEYCLOAK_DEV_USERS = ("ola@example.com", "tester@example.com")


def seed_sample_claim(tenant_id: UUID | None = None) -> None:
    db = SessionLocal()
    try:
        if tenant_id is None and os.getenv("SEED_TENANT_ID"):
            tenant_id = UUID(os.getenv("SEED_TENANT_ID"))
        tenant = db.get(Tenant, tenant_id) if tenant_id is not None else None
        if tenant is None:
            tenant = Tenant(name="Seed Tenant", slug=f"seed-{uuid.uuid4().hex[:8]}")
            if tenant_id is not None:
                tenant.id = tenant_id
            db.add(tenant)
            db.flush()

        existing = db.execute(
            select(Claim).filter(Claim.claim_number == "CLM-2026-001")
        ).scalar_one_or_none()
        if existing is not None:
            db.commit()
            print(f"Already seeded tenant_id: {tenant.id}, claim_id: {existing.id}; nothing to do")
            return

        patient = Patient(
            tenant_id=tenant.id,
            first_name="John",
            last_name="Doe",
            dob=date(1990, 5, 14),
        )
        provider = Provider(
            tenant_id=tenant.id,
            npi="1234567890",
            first_name="Jane",
            last_name="Smith",
        )
        db.add_all([patient, provider])
        db.flush()

        claim = Claim(
            tenant_id=tenant.id,
            claim_number="CLM-2026-001",
            patient_id=patient.id,
            provider_id=provider.id,
            status=ClaimStatus.DRAFT,
            total_amount=Decimal("150.00"),
            service_date_from=date(2026, 8, 1),
            service_date_to=date(2026, 8, 1),
        )
        db.add(claim)
        db.flush()

        line = ClaimLine(
            tenant_id=tenant.id,
            claim_id=claim.id,
            procedure_code="D2140",
            tooth_number="14",
            surface="MO",
            charge_amount=Decimal("150.00"),
        )
        db.add(line)

        app_users = [
            AppUser(tenant_id=tenant.id, email=email, role="admin") for email in KEYCLOAK_DEV_USERS
        ]
        db.add_all(app_users)

        db.commit()
        print(f"Seeded tenant_id: {tenant.id}, claim_id: {claim.id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_sample_claim()
