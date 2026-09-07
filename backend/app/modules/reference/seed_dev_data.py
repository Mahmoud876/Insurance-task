import uuid
from datetime import date

from app.core.database_session import SessionLocal
from app.modules.claims.models.claim import Claim
from app.modules.claims.models.claim_line import ClaimLine
from app.modules.claims.models.patient import Patient


def seed_sample_claim() -> None:
    db = SessionLocal()
    try:
        tenant_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        claim_id = uuid.uuid4()

        patient = Patient(
            id=patient_id,
            tenant_id=tenant_id,
            first_name="John",
            last_name="Doe",
            dob=date(1990, 5, 14),
            gender="M",
        )
        db.add(patient)

        claim = Claim(
            id=claim_id,
            tenant_id=tenant_id,
            patient_id=patient_id,
            claim_number="CLM-2026-001",
            status="draft",
            service_date_from=date(2026, 8, 1),
            service_date_to=date(2026, 8, 1),
        )
        db.add(claim)

        line = ClaimLine(
            id=uuid.uuid4(),
            claim_id=claim_id,
            line_number=1,
            procedure_code="D2140",
            tooth_number="14",
            surface="MO",
            charge_amount=150.00,
            quantity=1,
        )
        db.add(line)

        db.commit()
        print(f"Seeded claim_id: {claim_id}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_sample_claim()
