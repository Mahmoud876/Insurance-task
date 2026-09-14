from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import settings
from app.core.uploads import read_upload_with_cap, sniff_mime_type
from app.modules.ocr.schemas import CardOCRResponse

router = APIRouter(prefix="/v1/insurance-cards", tags=["Insurance Cards / OCR"])


@router.post(
    "/ocr",
    response_model=CardOCRResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract insurance card details via OCR",
)
async def process_card_ocr(file: UploadFile = File(...)) -> CardOCRResponse:
    """Returns mock OCR extracted data in dev/staging, and 501 in production."""
    env = getattr(settings, "ENVIRONMENT", "dev").lower()

    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OCR processing is not available in production environment.",
        )

    declared_type = file.content_type
    data = await read_upload_with_cap(file, settings.MAX_UPLOAD_SIZE_BYTES)
    sniff_mime_type(data, declared_type)

    # Dev/Staging mock response
    return CardOCRResponse(
        payer_name="Delta Dental PPO",
        payer_id="DEL_9981",
        member_id="MEM-10023485",
        group_number="GRP-88123",
        subscriber_name="Jane Doe",
        confidence_score=0.96,
    )
