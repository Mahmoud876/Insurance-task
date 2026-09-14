from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.claims.models.claim import Claim
from app.modules.rules.models import RulesetVersion
from app.modules.rules.resolver import (
    LayeredRuleResolver,
    ResolutionContext,
    ResolvedRuleSet,
    RuleConfig,
    RuleLayer,
    RuleSetVersion,
)
from app.modules.scrubber.rule_pack import get_default_rule_configs

DEFAULT_PACK_VERSION_ID = "default-pack-v1"


def build_default_ruleset() -> ResolvedRuleSet:
    """Builds a ResolvedRuleSet from the bundled phase-4 default rule pack."""
    version = RuleSetVersion(
        version_id=DEFAULT_PACK_VERSION_ID,
        layer=RuleLayer.DEFAULT,
        rules=get_default_rule_configs(),
    )
    return LayeredRuleResolver().resolve([version], ResolutionContext())


def _ruleset_from_payload(ruleset_row: RulesetVersion) -> ResolvedRuleSet:
    payload = ruleset_row.rules_payload if isinstance(ruleset_row.rules_payload, dict) else {}
    raw_rules = payload.get("rules", [])

    configs: list[RuleConfig] = []
    for raw in raw_rules:
        if not isinstance(raw, dict):
            continue
        normalized = dict(raw)
        if "id" in normalized and "rule_id" not in normalized:
            normalized["rule_id"] = normalized.pop("id")
        rule_id = normalized.get("rule_id")
        operator = normalized.get("operator")
        if not rule_id or not isinstance(operator, str) or not operator.strip():
            continue
        configs.append(
            RuleConfig(
                rule_id=str(rule_id),
                is_enabled=bool(normalized.get("is_enabled", True)),
                operator=operator,
                args=list(normalized.get("args", [])),
                message_key=normalized.get("message_key"),
                severity=normalized.get("severity"),
            )
        )

    version = RuleSetVersion(
        version_id=ruleset_row.id,
        layer=RuleLayer.DEFAULT,
        rules=configs,
    )
    return LayeredRuleResolver().resolve([version], ResolutionContext())


def resolve_ruleset_for_claim(db: Session, claim: Claim) -> ResolvedRuleSet:
    """Resolves the active tenant ruleset, falling back to the bundled default pack."""
    active = db.scalar(
        select(RulesetVersion)
        .where(
            RulesetVersion.tenant_id == str(claim.tenant_id),
            RulesetVersion.status == "active",
        )
        .order_by(RulesetVersion.created_at.desc())
        .limit(1)
    )
    if active is not None:
        return _ruleset_from_payload(active)
    return build_default_ruleset()
