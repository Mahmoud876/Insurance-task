from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PreAuthCreateRequest(BaseModel):
    claim_id: str = Field(..., examples=["CLM-1001"])
    payer_id: str = Field(..., examples=["DEL_9981"])
    request_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured claim and clinical attachment facts for pre-authorization",
    )


class PreAuthResponse(BaseModel):
    id: str = Field(..., examples=["PA-88219"])
    claim_id: str
    payer_id: str
    status: str = Field(..., examples=["pending"], description="pending | approved | denied")
    request_payload: dict[str, Any]
    response_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
