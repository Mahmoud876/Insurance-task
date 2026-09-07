from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field


class RuleLayer(IntEnum):
    DEFAULT = 1
    REGION = 2
    PAYER = 3
    PLAN = 4
    TENANT = 5


class RuleConfig(BaseModel):
    rule_id: str
    is_enabled: bool = True
    operator: str | None = None
    args: list[Any] = Field(default_factory=list)
    message_key: str | None = None
    severity: str | None = None


class RuleSetVersion(BaseModel):
    version_id: str
    layer: RuleLayer
    layer_target_id: str | None = None
    rules: list[RuleConfig] = Field(default_factory=list)


class ResolutionContext(BaseModel):
    region: str | None = None
    payer_id: str | None = None
    plan_id: str | None = None
    tenant_id: str | None = None


class ResolvedRuleSet(BaseModel):
    pinned_version_ids: list[str]
    effective_rules: dict[str, RuleConfig]


class LayeredRuleResolver:
    """Resolves rule sets across hierarchy layers with later-wins-by-code and is_enabled suppression."""

    PRECEDENCE_ORDER = [
        RuleLayer.DEFAULT,
        RuleLayer.REGION,
        RuleLayer.PAYER,
        RuleLayer.PLAN,
        RuleLayer.TENANT,
    ]

    def resolve(
        self,
        candidate_versions: list[RuleSetVersion],
        context: ResolutionContext,
    ) -> ResolvedRuleSet:
        # Filter candidate rule sets applicable to the given resolution context
        applicable_versions = self._filter_applicable(candidate_versions, context)

        # Sort versions strictly by layer precedence order (1 -> 5)
        sorted_versions = sorted(
            applicable_versions,
            key=lambda v: self.PRECEDENCE_ORDER.index(v.layer),
        )

        effective_rules: dict[str, RuleConfig] = {}
        pinned_version_ids: list[str] = []

        for version in sorted_versions:
            pinned_version_ids.append(version.version_id)
            for rule in version.rules:
                if not rule.is_enabled:
                    # Higher/later layer explicitly disables rule -> suppress
                    effective_rules.pop(rule.rule_id, None)
                else:
                    # Higher/later layer overrides or adds rule
                    existing = effective_rules.get(rule.rule_id)
                    if existing:
                        # Merge configuration fields if partial override, or replace completely
                        effective_rules[rule.rule_id] = self._merge_rule(existing, rule)
                    else:
                        effective_rules[rule.rule_id] = rule.model_copy()

        return ResolvedRuleSet(
            pinned_version_ids=pinned_version_ids,
            effective_rules=effective_rules,
        )

    def _filter_applicable(
        self,
        versions: list[RuleSetVersion],
        context: ResolutionContext,
    ) -> list[RuleSetVersion]:
        filtered: list[RuleSetVersion] = []
        for v in versions:
            if v.layer == RuleLayer.DEFAULT:
                filtered.append(v)
            elif v.layer == RuleLayer.REGION and v.layer_target_id == context.region:
                filtered.append(v)
            elif v.layer == RuleLayer.PAYER and v.layer_target_id == context.payer_id:
                filtered.append(v)
            elif v.layer == RuleLayer.PLAN and v.layer_target_id == context.plan_id:
                filtered.append(v)
            elif v.layer == RuleLayer.TENANT and v.layer_target_id == context.tenant_id:
                filtered.append(v)
        return filtered

    def _merge_rule(self, base: RuleConfig, override: RuleConfig) -> RuleConfig:
        return RuleConfig(
            rule_id=base.rule_id,
            is_enabled=override.is_enabled,
            operator=override.operator if override.operator is not None else base.operator,
            args=override.args if override.args else base.args,
            message_key=override.message_key
            if override.message_key is not None
            else base.message_key,
            severity=override.severity if override.severity is not None else base.severity,
        )
