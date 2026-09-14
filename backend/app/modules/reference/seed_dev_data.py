import uuid
from datetime import date
from decimal import Decimal

from app.core.database_session import SessionLocal
from app.core.tenant import Tenant
from app.modules.claims.models.claim import Claim, ClaimStatus
from app.modules.claims.models.claim_line import ClaimLine
from app.modules.claims.models.patient import Patient
from app.modules.claims.models.provider import Provider


def seed_sample_claim() -> None:
    db = SessionLocal()
    try:
        tenant = Tenant(name="Seed Tenant", slug=f"seed-{uuid.uuid4().hex[:8]}")
        db.add(tenant)
        db.flush()

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

        db.commit()
        print(f"Seeded tenant_id: {tenant.id}, claim_id: {claim.id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_sample_claim()
