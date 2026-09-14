import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security.auth import AuthContext
from app.core.security.rbac import Permission
from app.core.storage import object_storage, random_object_key
from app.core.uploads import read_upload_with_cap_sync, sniff_mime_type
from app.deps import get_db, require_permission
from app.modules.claims.models.claim import Claim
from app.modules.claims.models.claim_attachment import (
    ClaimAttachment,
    is_primary_eob_doc_type,
    normalize_doc_type,
)
from app.modules.claims.schemas.attachment import (
    AttachmentPresignedUrlResponse,
    AttachmentResponse,
)
from app.modules.ocr.engine import get_ocr_engine
from app.modules.ocr.eob import parse_eob_text, upsert_eob_history
from app.modules.ocr.service import ocr_lines_from_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["claims-attachments"])


def _get_claim_or_404(db: Session, claim_id: UUID) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    return claim


def _get_attachment_or_404(db: Session, claim_id: UUID, attachment_id: UUID) -> ClaimAttachment:
    attachment = db.get(ClaimAttachment, attachment_id)
    if attachment is None or attachment.claim_id != claim_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    return attachment


@router.post(
    "/{claim_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a claim attachment (x-ray, EOB, narrative, ...)",
)
def upload_attachment(
    claim_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(require_permission(Permission.CLAIM_WRITE))],
    file: UploadFile = File(...),
    doc_type: str = Form(default="attachment"),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    claim = _get_claim_or_404(db, claim_id)

    data = read_upload_with_cap_sync(file, settings.MAX_UPLOAD_SIZE_BYTES)
    file_type = sniff_mime_type(data, file.content_type)
    normalized_doc_type = normalize_doc_type(doc_type)

    key = random_object_key(auth_ctx.tenant_id, claim_id, file.filename or "attachment.bin")
    object_storage.put_object(key, data, file_type)

    ocr_text = None
    try:
        engine = get_ocr_engine()
        lines = ocr_lines_from_bytes(data, file_type, engine)
    except Exception:
        logger.warning("OCR skipped for attachment on claim %s", claim_id, exc_info=True)
        lines = []

    if lines:
        ocr_text = "\n".join(line.text for line in lines)
        if is_primary_eob_doc_type(normalized_doc_type):
            try:
                upsert_eob_history(
                    db,
                    tenant_id=auth_ctx.tenant_id,
                    patient_id=claim.patient_id,
                    payer_id=claim.payer_id,
                    extract=parse_eob_text(lines),
                )
            except Exception:
                db.rollback()
                logger.warning(
                    "Failed to import EOB procedure history for claim %s", claim_id, exc_info=True
                )

    attachment = ClaimAttachment(
        tenant_id=auth_ctx.tenant_id,
        claim_id=claim_id,
        file_key=key,
        file_type=file_type,
        doc_type=normalized_doc_type,
        ocr_text=ocr_text,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return AttachmentResponse.model_validate(attachment)


@router.get(
    "/{claim_id}/attachments",
    response_model=list[AttachmentResponse],
    summary="List attachments for a claim",
)
def list_attachments(
    claim_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(require_permission(Permission.CLAIM_READ))],
    db: Session = Depends(get_db),
) -> list[AttachmentResponse]:
    _get_claim_or_404(db, claim_id)
    attachments = db.scalars(
        select(ClaimAttachment)
        .where(
            ClaimAttachment.claim_id == claim_id,
            ClaimAttachment.tenant_id == auth_ctx.tenant_id,
        )
        .order_by(ClaimAttachment.created_at.desc())
    ).all()
    return [AttachmentResponse.model_validate(attachment) for attachment in attachments]


@router.get(
    "/{claim_id}/attachments/{attachment_id}/url",
    response_model=AttachmentPresignedUrlResponse,
    summary="Get a 5-minute pre-signed download URL for an attachment",
)
def attachment_download_url(
    claim_id: UUID,
    attachment_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(require_permission(Permission.CLAIM_READ))],
    db: Session = Depends(get_db),
) -> AttachmentPresignedUrlResponse:
    attachment = _get_attachment_or_404(db, claim_id, attachment_id)
    if attachment.tenant_id != auth_ctx.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    expires_in = settings.S3_PRESIGN_EXPIRY_SECONDS
    url = object_storage.presign_download_url(attachment.file_key, expires_in)
    return AttachmentPresignedUrlResponse(
        url=url,
        expires_in=expires_in,
        content_type=attachment.file_type,
    )
