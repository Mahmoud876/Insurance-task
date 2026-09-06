from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class Phase1Finding:
    code: str
    message: str
    field_name: str
    raw_value: Any
    severity: str = "ERROR"


@dataclass
class NormalizationResult[T]:
    value: T | None = None
    finding: Phase1Finding | None = None

    @property
    def is_valid(self) -> bool:
        return self.finding is None
