from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SafeTransformType(StrEnum):
    DATE_FORMAT = "date_format"
    CODE_PADDING = "code_padding"
    QUADRANT_DERIVATION = "quadrant_derivation"
    ARCH_DERIVATION = "arch_derivation"
    SURFACE_ALIASES = "surface_aliases"
    TOTAL_RECOMPUTE = "total_recompute"


# Fields that can never be modified by autofix
FORBIDDEN_AUTOFIX_FIELDS = {
    "procedure_code",
    "code",
    "tooth_number",
    "tooth",
    "fee",
    "line_item_fee",
    "charged_amount",
    "amount",
}


class AutofixProposal(BaseModel):
    id: str = Field(..., description="Unique ID for this proposed fix")
    transform_type: SafeTransformType
    target_field: str = Field(
        ..., description="JSON path or field name being modified (e.g., 'lines[0].service_date')"
    )
    original_value: Any
    proposed_value: Any
    reason: str

    @field_validator("target_field")
    @classmethod
    def validate_target_field_not_forbidden(cls, field_path: str) -> str:
        # Extract leaf field name if path is dot/bracket notation
        leaf_field = field_path.split(".")[-1].split("[")[0].lower()
        if leaf_field in FORBIDDEN_AUTOFIX_FIELDS:
            raise ValueError(
                f"Field '{leaf_field}' is strictly forbidden from autofix remediation."
            )
        return field_path


class ApplyAutofixRequest(BaseModel):
    selected_proposal_ids: list[str] = Field(
        ...,
        min_length=1,
        description="IDs of proposed fixes explicitly approved by the user or upstream process",
    )


class AutofixAuditEvent(BaseModel):
    id: str
    claim_id: str
    transform_type: SafeTransformType
    target_field: str
    old_value: Any
    new_value: Any
    applied_by: str
    applied_at: datetime


class ApplyAutofixResponse(BaseModel):
    claim_id: str
    applied_count: int
    audit_events: list[AutofixAuditEvent]
    updated_claim: dict[str, Any]
