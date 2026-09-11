from collections.abc import Callable
from typing import Any

from app.modules.rules.coverage_rules import (
    eval_p4_annual_maximum_exhausted,
    eval_p4_category_exclusion,
    eval_p4_cob_order,
    eval_p4_dependent_age_limit,
    eval_p4_frequency_limitation,
    eval_p4_policy_expired,
    eval_p4_policy_not_effective,
    eval_p4_waiting_period,
)

# Registry type for rule execution handlers
RuleEvaluator = Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]]

DEFAULT_RULE_PACK: dict[str, dict[str, Any]] = {
    "P4_POL_EXPIRED": {
        "rule_id": "P4_POL_EXPIRED",
        "name": "Policy Expired Check",
        "category": "eligibility",
        "handler": eval_p4_policy_expired,
        "enabled": True,
    },
    "P4_POL_NOT_EFFECTIVE": {
        "rule_id": "P4_POL_NOT_EFFECTIVE",
        "name": "Policy Not Yet Effective Check",
        "category": "eligibility",
        "handler": eval_p4_policy_not_effective,
        "enabled": True,
    },
    "P4_DEP_AGE_LIMIT": {
        "rule_id": "P4_DEP_AGE_LIMIT",
        "name": "Dependent Age Limit Exclusion",
        "category": "eligibility",
        "handler": eval_p4_dependent_age_limit,
        "enabled": True,
    },
    "P4_WAITING_PERIOD": {
        "rule_id": "P4_WAITING_PERIOD",
        "name": "Mandatory Waiting Period Check",
        "category": "coverage",
        "handler": eval_p4_waiting_period,
        "enabled": True,
    },
    "P4_ANNUAL_MAX_EXHAUSTED": {
        "rule_id": "P4_ANNUAL_MAX_EXHAUSTED",
        "name": "Annual Maximum Exhausted Check",
        "category": "coverage",
        "handler": eval_p4_annual_maximum_exhausted,
        "enabled": True,
    },
    "P4_CATEGORY_EXCLUSION": {
        "rule_id": "P4_CATEGORY_EXCLUSION",
        "name": "Procedure Category Exclusion",
        "category": "coverage",
        "handler": eval_p4_category_exclusion,
        "enabled": True,
    },
    "P4_FREQ_LIMITATION": {
        "rule_id": "P4_FREQ_LIMITATION",
        "name": "Procedure Frequency Limitation",
        "category": "coverage",
        "handler": eval_p4_frequency_limitation,
        "enabled": True,
    },
    "P4_COB_ORDER": {
        "rule_id": "P4_COB_ORDER",
        "name": "Coordination of Benefits (COB) Order Check",
        "category": "cob",
        "handler": eval_p4_cob_order,
        "enabled": True,
    },
}


def get_default_rule_pack() -> list[dict[str, Any]]:
    """Returns all enabled Phase-4 rules for the primary scrubbing pipeline."""
    return [rule for rule in DEFAULT_RULE_PACK.values() if rule.get("enabled", True)]
