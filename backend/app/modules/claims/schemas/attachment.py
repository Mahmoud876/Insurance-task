from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    file_type: str
    doc_type: str
    ocr_text: str | None = None
    created_at: datetime


class AttachmentPresignedUrlResponse(BaseModel):
    url: str = Field(..., description="Pre-signed S3 URL valid for `expires_in` seconds.")
    expires_in: int = Field(..., ge=1, le=900)
    content_type: str
