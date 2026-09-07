from pathlib import Path
from typing import Any

import yaml

from app.modules.rules.registry import ArityMismatchError, OperatorRegistry, UnknownOperatorError
from app.modules.rules.schemas import RuleDefinition, RulePack


class RuleValidationError(Exception):
    """Raised when a rule pack fails load-time validation."""

    pass


class DummyMessageCatalog:
    """Interface placeholder for message catalog resolution."""

    _keys: set[str] = {
        "ERR_SAME_TOOTH_SAME_DAY",
        "ERR_INVALID_AGE_SERVICE",
        "ERR_POLICY_INACTIVE",
        "ERR_MISSING_ATTACHMENT",
    }

    @classmethod
    def has_key(cls, key: str) -> bool:
        return key in cls._keys


class RuleLoader:
    def __init__(self, catalog: Any = DummyMessageCatalog):
        self.catalog = catalog

    def load_from_yaml(self, yaml_content: str) -> RulePack:
        """Parses and validates a YAML rule pack string."""
        try:
            raw_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise RuleValidationError(f"Invalid YAML format: {e}") from e

        try:
            pack = RulePack.model_validate(raw_data)
        except Exception as e:
            raise RuleValidationError(f"Rule pack schema validation failed: {e}") from e

        for rule in pack.rules:
            self._validate_rule(rule)

        return pack

    def load_from_file(self, file_path: Path | str) -> RulePack:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Rule pack file not found: {path}")
        return self.load_from_yaml(path.read_text(encoding="utf-8"))

    def _validate_rule(self, rule: RuleDefinition) -> None:
        # Operator exists
        try:
            OperatorRegistry.get(rule.operator)
        except UnknownOperatorError as e:
            raise RuleValidationError(
                f"Rule '{rule.id}' references unknown operator '{rule.operator}'."
            ) from e

        # Arity matches operator signature
        try:
            OperatorRegistry.validate_call(rule.operator, len(rule.args))
        except ArityMismatchError as e:
            raise RuleValidationError(f"Rule '{rule.id}' arity check failed: {e}") from e

        # message_key resolves in catalog
        if not self.catalog.has_key(rule.message_key):
            raise RuleValidationError(
                f"Rule '{rule.id}' references unresolved message_key '{rule.message_key}'."
            )

        # Fixtures declared (Handled by Pydantic)
        if not rule.fixtures:
            raise RuleValidationError(f"Rule '{rule.id}' does not declare any test fixtures.")
