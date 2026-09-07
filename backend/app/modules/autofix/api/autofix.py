from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security.auth import AuthContext
from app.deps import get_current_auth_context, get_db
from app.modules.autofix.schemas import (
    ApplyAutofixRequest,
    ApplyAutofixResponse,
    AutofixProposal,
)
from app.modules.autofix.service import AutofixService
from app.modules.claims.models.claim import Claim

router = APIRouter(prefix="/claims", tags=["Autofix"])


def _fetch_claim_payload_and_proposals(
    claim_id: str, db: Session, auth_ctx: AuthContext
) -> tuple[dict[str, Any], list[AutofixProposal]]:
    """Load a tenant-scoped claim and its proposals from the latest claim snapshot."""
    try:
        parsed_claim_id = UUID(claim_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found"
        ) from err

    claim = db.scalar(
        select(Claim)
        .options(joinedload(Claim.lines))
        .where(Claim.id == parsed_claim_id, Claim.tenant_id == auth_ctx.tenant_id)
    )
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    claim_payload: dict[str, Any] = {
        "claim_id": str(claim.id),
        "claim_number": claim.claim_number,
        "patient_id": str(claim.patient_id),
        "provider_id": str(claim.provider_id),
        "payer_id": str(claim.payer_id) if claim.payer_id else None,
        "service_date_from": claim.service_date_from.isoformat(),
        "service_date_to": claim.service_date_to.isoformat(),
        "total_amount": str(claim.total_amount),
        "lines": [
            {
                "id": str(line.id),
                "procedure_code": line.procedure_code,
                "tooth_number": line.tooth_number,
                "surface": line.surface,
                "charge_amount": str(line.charge_amount),
                "fee": str(line.charge_amount),
            }
            for line in claim.lines
        ],
    }

    active_proposals: list[AutofixProposal] = []
    for finding in claim.findings_summary:
        if not isinstance(finding, dict):
            continue
        raw_proposals = finding.get("autofix_proposals", finding.get("proposals", []))
        if isinstance(raw_proposals, dict):
            raw_proposals = [raw_proposals]
        if not isinstance(raw_proposals, list):
            continue
        for raw_proposal in raw_proposals:
            if isinstance(raw_proposal, dict):
                active_proposals.append(AutofixProposal.model_validate(raw_proposal))

    return claim_payload, active_proposals


@router.post(
    "/{claim_id}/autofix",
    response_model=ApplyAutofixResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply proposed autofixes to a claim",
)
def apply_claim_autofix(
    claim_id: str,
    request: ApplyAutofixRequest,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
    actor_id: str = "system",  # Replace with current user/auth dependency if present
) -> ApplyAutofixResponse:
    """Executes selected approved autofix proposals, writes audit logs, and returns updated claim."""
    claim_payload, active_proposals = _fetch_claim_payload_and_proposals(claim_id, db, auth_ctx)
    service = AutofixService(db, auth_ctx.tenant_id)

    try:
        return service.apply_autofixes(
            claim_id=claim_id,
            claim_payload=claim_payload,
            active_proposals=active_proposals,
            request=request,
            actor_id=actor_id,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
