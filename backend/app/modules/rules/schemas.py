from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RuleSeverity(StrEnum):
    REJECT = "REJECT"
    WARNING = "WARNING"
    INFO = "INFO"


class RuleFixture(BaseModel):
    name: str
    context: dict[str, Any] = Field(default_factory=dict)
    expected_result: bool


class RuleDefinition(BaseModel):
    id: str = Field(..., pattern=r"^[A-Z0-9_\-]+$")
    description: str
    operator: str
    args: list[Any] = Field(default_factory=list)
    message_key: str
    severity: RuleSeverity = RuleSeverity.REJECT
    fixtures: list[RuleFixture]

    @model_validator(mode="after")
    def validate_fixtures_not_empty(self) -> "RuleDefinition":
        if not self.fixtures:
            raise ValueError(f"Rule '{self.id}' must declare at least one test fixture.")
        return self


class RulePack(BaseModel):
    pack_id: str
    version: str
    description: str | None = None
    rules: list[RuleDefinition]
