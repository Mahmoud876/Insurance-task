import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.db.models.claim import ClaimStatus


class ClaimCreate(BaseModel):
    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    total_amount: Decimal = Decimal("0.00")


class ClaimUpdate(BaseModel):
    status: ClaimStatus | None = None
    total_amount: Decimal | None = None


class ClaimLineCreate(BaseModel):
    procedure_code: str
    tooth_number: str | None = None
    surface: str | None = None
    charge_amount: Decimal


class ClaimLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    procedure_code: str
    tooth_number: str | None
    surface: str | None
    charge_amount: Decimal


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    status: ClaimStatus
    total_amount: Decimal


class ClaimListResponse(BaseModel):
    items: list[ClaimResponse]
    next_cursor: str | None = None
