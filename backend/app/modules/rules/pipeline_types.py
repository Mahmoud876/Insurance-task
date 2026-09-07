from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FindingSeverity(StrEnum):
    REJECT = "REJECT"
    WARNING = "WARNING"
    INFO = "INFO"


class ClaimLineSnapshot(BaseModel):
    line_number: int
    procedure_code: str
    tooth_number: str | None = None
    surface: str | None = None
    charge_amount: float = 0.0
    quantity: int = 1


class ClaimSnapshot(BaseModel):
    claim_id: UUID
    tenant_id: UUID
    claim_number: str
    patient_id: UUID
    patient_dob: date
    patient_gender: str
    service_date_from: date
    service_date_to: date
    lines: list[ClaimLineSnapshot] = Field(default_factory=list)


class PatientHistoryItem(BaseModel):
    procedure_code: str
    tooth_number: str | None = None
    surface: str | None = None
    service_date: date


class PolicyReference(BaseModel):
    policy_number: str
    is_active: bool = True
    effective_date: date
    termination_date: date | None = None


class ReferenceData(BaseModel):
    policy: PolicyReference | None = None
    patient_history: list[PatientHistoryItem] = Field(default_factory=list)
    code_metadata: dict[str, Any] = Field(default_factory=dict)


class EnrichedLineContext(BaseModel):
    line_number: int
    procedure_code: str
    tooth_number: str | None
    surface_mask: str | None
    charge_amount: float
    history_24mo_count: int = 0


class EnrichedClaimContext(BaseModel):
    claim_id: UUID
    tenant_id: UUID
    patient_age_years: int
    patient_age_months: int
    service_date_from: date
    service_date_to: date
    lines: list[EnrichedLineContext] = Field(default_factory=list)
    lines_by_tooth: dict[str, list[EnrichedLineContext]] = Field(default_factory=dict)
    reference: ReferenceData


class Finding(BaseModel):
    rule_id: str
    severity: FindingSeverity
    message_key: str
    message: str
    line_number: int | None = None


class ScrubResult(BaseModel):
    claim_id: UUID
    readiness_score: int
    status: str  # "CLEAN", "WARNINGS", "REJECTED"
    findings: list[Finding]
    pinned_version_ids: list[str] = Field(default_factory=list)
    is_truncated: bool = False
    evaluated_at: datetime
