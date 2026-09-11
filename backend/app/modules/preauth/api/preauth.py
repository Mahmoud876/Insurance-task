from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security.auth import AuthContext
from app.deps import get_current_auth_context, get_db
from app.modules.claims.models.claim import Claim
from app.modules.preauth.models import PreAuthRequest
from app.modules.preauth.schemas import PreAuthCreateRequest, PreAuthResponse

router = APIRouter(prefix="/v1/preauth", tags=["Pre-Authorization"])


@router.post(
    "/requests",
    response_model=PreAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a prior authorization request stub",
)
def create_preauth_request(
    payload: PreAuthCreateRequest,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> PreAuthResponse:
    """Create a pending pre-authorization request for the authenticated tenant."""
    claim_id = _parse_uuid(payload.claim_id, "claim_id")
    payer_id = _parse_uuid(payload.payer_id, "payer_id")
    claim_exists = db.scalar(
        select(Claim.id).where(Claim.id == claim_id, Claim.tenant_id == auth_ctx.tenant_id)
    )
    if claim_exists is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    now = datetime.now(UTC)
    record = PreAuthRequest(
        id=f"PA-{uuid4().hex[:8].upper()}",
        claim_id=claim_id,
        payer_id=payer_id,
        status="pending",
        request_payload=payload.request_payload,
        response_payload={"message": "Pre-auth request queued for asynchronous evaluation."},
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return PreAuthResponse(
        id=record.id,
        claim_id=payload.claim_id,
        payer_id=payload.payer_id,
        status=record.status,
        request_payload=record.request_payload,
        response_payload=record.response_payload,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/requests/{preauth_id}",
    response_model=PreAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pre-authorization status stub",
)
def get_preauth_status(
    preauth_id: str,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> PreAuthResponse:
    """Fetch the current pre-authorization status for the authenticated tenant."""
    record = db.scalar(
        select(PreAuthRequest)
        .join(Claim, Claim.id == PreAuthRequest.claim_id)
        .where(PreAuthRequest.id == preauth_id, Claim.tenant_id == auth_ctx.tenant_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Pre-authorization request not found")
    return PreAuthResponse(
        id=record.id,
        claim_id=str(record.claim_id),
        payer_id=str(record.payer_id),
        status=record.status,
        request_payload=record.request_payload,
        response_payload=record.response_payload,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=f"Invalid {field_name}") from err
