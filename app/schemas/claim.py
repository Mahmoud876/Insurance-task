from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.claim import ClaimStatus


class ClaimBase(BaseModel):
    patient_id: UUID
    provider_id: UUID
    payer_id: UUID | None = None
    service_date: date | None = None
    total_amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)


class ClaimCreate(ClaimBase):
    pass


class ClaimUpdate(BaseModel):
    patient_id: UUID | None = None
    provider_id: UUID | None = None
    payer_id: UUID | None = None
    service_date: date | None = None
    total_amount: Decimal | None = Field(default=None, gt=Decimal("0.00"), decimal_places=2)
    status: ClaimStatus | None = None


class ClaimResponse(ClaimBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime


class ClaimBoardPage(BaseModel):
    items: list[ClaimResponse]
    next_cursor: str | None = None
    has_more: bool = False
