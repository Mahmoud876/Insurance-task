from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.claims.models.claim import Claim
from app.modules.claims.models.insurance_policy import InsurancePolicy
from app.modules.claims.models.patient_procedure_history import PatientProcedureHistory
from app.modules.rules.pipeline_types import (
    ClaimLineSnapshot,
    ClaimSnapshot,
    PatientHistoryItem,
    PolicyReference,
    ReferenceData,
)


def load_claim_snapshot(db: Session, claim: Claim) -> ClaimSnapshot:
    """Builds the pipeline ClaimSnapshot for a claim.

    The caller must preload `claim.patient` and `claim.lines` (e.g. via
    ``joinedload``) to avoid lazy loads. Line numbers are derived from sort
    order since ClaimLine has no numeric line_number column.
    """
    ordered_lines = sorted(claim.lines, key=lambda item: item.created_at)

    return ClaimSnapshot(
        claim_id=claim.id,
        tenant_id=claim.tenant_id,
        claim_number=claim.claim_number,
        patient_id=claim.patient_id,
        patient_dob=claim.patient.dob,
        patient_gender="",
        service_date_from=claim.service_date_from,
        service_date_to=claim.service_date_to,
        lines=[
            ClaimLineSnapshot(
                line_number=index,
                procedure_code=line.procedure_code,
                tooth_number=line.tooth_number,
                surface=line.surface,
                charge_amount=float(line.charge_amount),
                quantity=1,
            )
            for index, line in enumerate(ordered_lines, start=1)
        ],
    )


def load_reference_data(db: Session, claim: Claim) -> ReferenceData:
    """Loads policy and patient procedure history for a claim in 2 queries total."""
    policy: PolicyReference | None = None
    if claim.policy_id is not None:
        policy_row = db.get(InsurancePolicy, claim.policy_id)
        if policy_row is not None:
            effective = policy_row.effective_date
            termination = policy_row.termination_date
            policy = PolicyReference(
                policy_number=policy_row.policy_number,
                is_active=termination is None or termination > date.today(),
                effective_date=effective,
                termination_date=termination,
            )

    history_rows = db.scalars(
        select(PatientProcedureHistory)
        .where(
            PatientProcedureHistory.patient_id == claim.patient_id,
            PatientProcedureHistory.tenant_id == claim.tenant_id,
        )
        .order_by(PatientProcedureHistory.service_date.asc())
    ).all()

    patient_history = [
        PatientHistoryItem(
            procedure_code=row.procedure_code,
            tooth_number=str(row.tooth_canonical) if row.tooth_canonical is not None else None,
            surface="".join(row.surfaces) if row.surfaces else None,
            service_date=row.service_date,
        )
        for row in history_rows
    ]

    return ReferenceData(policy=policy, patient_history=patient_history, code_metadata={})
