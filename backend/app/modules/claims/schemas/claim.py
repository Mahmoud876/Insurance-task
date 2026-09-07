from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.claims.models.claim import ClaimStatus


class ClaimBase(BaseModel):
    patient_id: UUID
    provider_id: UUID
    payer_id: UUID | None = None
    service_date_from: date = Field(default_factory=date.today)
    service_date_to: date = Field(default_factory=date.today)
    total_amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)


class ClaimCreate(ClaimBase):
    tenant_id: UUID | None = None


class ClaimUpdate(BaseModel):
    patient_id: UUID | None = None
    provider_id: UUID | None = None
    payer_id: UUID | None = None
    service_date_from: date | None = None
    service_date_to: date | None = None
    total_amount: Decimal | None = Field(default=None, gt=Decimal("0.00"), decimal_places=2)
    status: ClaimStatus | None = None


class ClaimResponse(ClaimBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    claim_number: str
    readiness_score: int
    findings_summary: list[dict[str, Any]]
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime


class ClaimListResponse(BaseModel):
    items: list[ClaimResponse]
    next_cursor: str | None = None
    has_more: bool = False


class ClaimBoardPage(ClaimListResponse):
    pass


class ClaimLineCreate(BaseModel):
    procedure_code: str
    tooth_number: str | None = None
    surface: str | None = None
    charge_amount: Decimal


class ClaimLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    procedure_code: str
    tooth_number: str | None
    surface: str | None
    charge_amount: Decimal
