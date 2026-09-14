from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security.auth import AuthContext
from app.core.uploads import read_upload_with_cap_sync, sniff_mime_type
from app.deps import get_current_auth_context, get_db
from app.modules.ocr.engine import OcrEngineUnavailableError, get_ocr_engine
from app.modules.ocr.schemas import CardOCRResponse
from app.modules.ocr.service import ocr_card_from_bytes, upsert_policy_from_ocr

router = APIRouter(prefix="/v1/insurance-cards", tags=["Insurance Cards / OCR"])


@router.post(
    "/ocr",
    response_model=CardOCRResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract insurance card details via OCR",
)
def process_card_ocr(
    auth_ctx: Annotated[AuthContext, Depends(get_current_auth_context)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    patient_id: UUID | None = Query(
        default=None,
        description="When provided, the extracted data is persisted as an InsurancePolicy for this patient.",
    ),
    payer_plan_id: UUID | None = Query(
        default=None,
        description="Optional payer plan override; otherwise resolved from the extracted payer.",
    ),
) -> CardOCRResponse:
    data = read_upload_with_cap_sync(file, settings.MAX_UPLOAD_SIZE_BYTES)
    file_type = sniff_mime_type(data, file.content_type)

    try:
        extract = ocr_card_from_bytes(data, file_type, engine=get_ocr_engine())
    except OcrEngineUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    policy_id = None
    if patient_id is not None:
        policy = upsert_policy_from_ocr(
            db,
            auth_ctx.tenant_id,
            extract,
            patient_id=patient_id,
            payer_plan_id=payer_plan_id,
        )
        if policy is not None:
            policy_id = policy.id

    return CardOCRResponse(
        payer_name=extract.payer_name,
        payer_id=extract.payer_id,
        member_id=extract.member_id,
        group_number=extract.group_number,
        subscriber_name=extract.subscriber_name,
        confidence_score=extract.confidence_score,
        policy_id=policy_id,
    )
