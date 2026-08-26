from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_auth_context, get_db
from app.core.auth import AuthContext
from app.db.models.claim import ClaimStatus
from app.schemas.claim import ClaimBoardPage, ClaimCreate, ClaimUpdate
from app.services.claim_service import ClaimService

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("", response_model=ClaimBoardPage)
def list_claims(
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
    cursor: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    status_filter: ClaimStatus | None = Query(default=None, alias="status"),
    patient_search: str | None = Query(default=None, min_length=1, max_length=100),
    payer_id: UUID | None = None,
    service_date_from: date | None = None,
    service_date_to: date | None = None,
) -> ClaimBoardPage:
    return ClaimService.list_claims(
        db,
        auth_ctx,
        cursor=cursor,
        limit=limit,
        status_filter=status_filter,
        patient_search=patient_search,
        payer_id=payer_id,
        service_date_from=service_date_from,
        service_date_to=service_date_to,
    )


@router.get("/{claim_id}")
def get_claim(
    claim_id: UUID,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> Any:
    return ClaimService.get_claim(db, claim_id, auth_ctx)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_claim(
    payload: ClaimCreate,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> Any:
    return ClaimService.create_claim(db, payload, auth_ctx)


@router.put("/{claim_id}")
def update_claim(
    claim_id: UUID,
    payload: ClaimUpdate,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> Any:
    return ClaimService.update_claim(db, claim_id, payload, auth_ctx)


@router.post("/{claim_id}/scrub")
def scrub_claim(
    claim_id: UUID,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> Any:
    return ClaimService.scrub_claim(db, claim_id, auth_ctx)


@router.post("/{claim_id}/submit")
def submit_claim(
    claim_id: UUID,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> Any:
    return ClaimService.submit_claim(db, claim_id, auth_ctx)


@router.delete("/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim_id: UUID,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> Response:
    ClaimService.delete_claim(db, claim_id, auth_ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
