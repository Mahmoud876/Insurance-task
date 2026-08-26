import base64
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models.claim import Claim, ClaimStatus
from app.db.models.claim_line import ClaimLine
from app.schemas.claim import (
    ClaimCreate,
    ClaimLineCreate,
    ClaimLineResponse,
    ClaimListResponse,
    ClaimResponse,
    ClaimUpdate,
)

router = APIRouter(
    prefix="/claims",
    tags=["claims"],
)


def encode_cursor(claim_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(
        str(claim_id).encode()
    ).decode()


def decode_cursor(cursor: str) -> uuid.UUID:
    try:
        return uuid.UUID(
            base64.urlsafe_b64decode(cursor.encode()).decode()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor",
        )


def make_etag(claim: Claim) -> str:
    return f'"{claim.updated_at.isoformat()}"'


@router.post(
    "",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_claim(
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
) -> Claim:
    claim = Claim(
        tenant_id=claim_data.tenant_id,
        patient_id=claim_data.patient_id,
        provider_id=claim_data.provider_id,
        total_amount=claim_data.total_amount,
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    return claim


@router.get(
    "",
    response_model=ClaimListResponse,
)
def list_claims(
    status_filter: ClaimStatus | None = Query(
        default=None,
        alias="status",
    ),
    patient_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ClaimListResponse:

    query = select(Claim).order_by(Claim.id)

    if status_filter is not None:
        query = query.where(Claim.status == status_filter)

    if patient_id is not None:
        query = query.where(Claim.patient_id == patient_id)

    if from_date is not None:
        query = query.where(Claim.created_at >= from_date)

    if to_date is not None:
        query = query.where(Claim.created_at <= to_date)

    if cursor is not None:
        cursor_id = decode_cursor(cursor)
        query = query.where(Claim.id > cursor_id)

    claims = list(
        db.scalars(
            query.limit(limit + 1)
        ).all()
    )

    next_cursor = None

    if len(claims) > limit:
        claims = claims[:limit]
        next_cursor = encode_cursor(claims[-1].id)

    return ClaimListResponse(
        items=claims,
        next_cursor=next_cursor,
    )


@router.get(
    "/{claim_id}",
    response_model=ClaimResponse,
)
def get_claim(
    claim_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> Claim:

    claim = db.get(Claim, claim_id)

    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    response.headers["ETag"] = make_etag(claim)

    return claim


@router.patch(
    "/{claim_id}",
    response_model=ClaimResponse,
)
def update_claim(
    claim_id: uuid.UUID,
    claim_data: ClaimUpdate,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
) -> Claim:

    claim = db.get(Claim, claim_id)

    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="If-Match header is required",
        )

    current_etag = make_etag(claim)

    if if_match != current_etag:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Claim has been modified",
        )

    if claim_data.status is not None:
        claim.status = claim_data.status

    if claim_data.total_amount is not None:
        claim.total_amount = claim_data.total_amount

    db.commit()
    db.refresh(claim)

    response.headers["ETag"] = make_etag(claim)

    return claim


@router.delete(
    "/{claim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_claim(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:

    claim = db.get(Claim, claim_id)

    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    db.delete(claim)
    db.commit()


@router.put(
    "/{claim_id}/lines",
    response_model=list[ClaimLineResponse],
)
def replace_claim_lines(
    claim_id: uuid.UUID,
    lines: list[ClaimLineCreate],
    db: Session = Depends(get_db),
) -> list[ClaimLine]:

    claim = db.get(Claim, claim_id)

    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    for existing_line in list(claim.lines):
        db.delete(existing_line)

    db.flush()

    new_lines = []

    for line_data in lines:
        line = ClaimLine(
            tenant_id=claim.tenant_id,
            claim_id=claim.id,
            procedure_code=line_data.procedure_code,
            tooth_number=line_data.tooth_number,
            surface=line_data.surface,
            charge_amount=line_data.charge_amount,
        )

        db.add(line)
        new_lines.append(line)

    db.commit()

    for line in new_lines:
        db.refresh(line)

    return new_lines
