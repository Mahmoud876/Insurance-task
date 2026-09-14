from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal 
from uuid import UUID

@dataclass(frozen=True)
class RuleLine:
    procedure_code: str
    charge_amount: Decimal
    tooth_number: str | None = None
    surface: str | None = None
    allowed_amount: Decimal | None = None

@dataclass(frozen=True)
class RuleAttachment:
    file_type: str
    file_size: int | None=None

@dataclass(frozen=True)
class ProcedureRequirements:
    requires_radiograph: bool = False
    requires_narrative: bool = False # require explanation 
    requires_pre_authorisation: bool = False

@dataclass
class RuleClaim:
    claim_id: UUID | str
    patient_id: UUID | str
    provider_id: UUID | str
    service_date_from: date
    service_date_to: date
    total_amount: Decimal

    lines: list[RuleLine] = field(default_factory=list)
    attachments: list[RuleAttachment] = field(default_factory=list)

    narrative: str | None = None
    authorization_number: str | None = None

    procedure_requirements: dict[str, ProcedureRequirements] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class ExistingClaim:
    claim_id: UUID | str
    patient_id: UUID | str
    provider_id: UUID | str
    service_date_from: date
    service_date_to: date
    total_amount: Decimal
    lines: tuple[RuleLine, ...] = ()

