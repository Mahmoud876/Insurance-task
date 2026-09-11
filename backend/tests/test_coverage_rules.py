from datetime import date
from uuid import uuid4

import pytest

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
from app.modules.rules.pipeline_types import (
    EnrichedClaimContext,
    EnrichedLineContext,
    FindingSeverity,
    PolicyReference,
    ReferenceData,
)


def make_context(
    *,
    policy: PolicyReference | None = None,
    age: int = 30,
    lines: list[EnrichedLineContext] | None = None,
    metadata: dict[str, object] | None = None,
) -> EnrichedClaimContext:
    return EnrichedClaimContext(
        claim_id=uuid4(),
        tenant_id=uuid4(),
        patient_age_years=age,
        patient_age_months=age * 12,
        service_date_from=date(2026, 9, 7),
        service_date_to=date(2026, 9, 7),
        lines=lines or [],
        reference=ReferenceData(policy=policy, code_metadata=metadata or {}),
    )


@pytest.mark.parametrize(
    ("evaluator", "context", "rule_id", "severity"),
    [
        (
            eval_p4_policy_expired,
            make_context(
                policy=PolicyReference(
                    policy_number="P-1",
                    effective_date=date(2020, 1, 1),
                    termination_date=date(2026, 1, 1),
                )
            ),
            "P4_POL_EXPIRED",
            FindingSeverity.REJECT,
        ),
        (
            eval_p4_policy_not_effective,
            make_context(
                policy=PolicyReference(
                    policy_number="P-1",
                    effective_date=date(2027, 1, 1),
                )
            ),
            "P4_POL_NOT_EFFECTIVE",
            FindingSeverity.REJECT,
        ),
        (
            eval_p4_dependent_age_limit,
            make_context(age=26),
            "P4_DEP_AGE_LIMIT",
            FindingSeverity.WARNING,
        ),
        (
            eval_p4_waiting_period,
            make_context(
                policy=PolicyReference(
                    policy_number="P-1",
                    effective_date=date(2026, 8, 1),
                )
            ),
            "P4_WAITING_PERIOD",
            FindingSeverity.WARNING,
        ),
        (
            eval_p4_annual_maximum_exhausted,
            make_context(metadata={"annual_max_remaining": 0}),
            "P4_ANNUAL_MAX_EXHAUSTED",
            FindingSeverity.WARNING,
        ),
        (
            eval_p4_category_exclusion,
            make_context(
                lines=[
                    EnrichedLineContext(
                        line_number=1,
                        procedure_code="D2740",
                        tooth_number=None,
                        surface_mask=None,
                        charge_amount=100,
                    )
                ],
                metadata={
                    "excluded_categories": ["prosthodontics"],
                    "D2740": {"category": "prosthodontics"},
                },
            ),
            "P4_CATEGORY_EXCLUSION",
            FindingSeverity.WARNING,
        ),
        (
            eval_p4_frequency_limitation,
            make_context(
                lines=[
                    EnrichedLineContext(
                        line_number=1,
                        procedure_code="D1110",
                        tooth_number=None,
                        surface_mask=None,
                        charge_amount=100,
                        history_24mo_count=2,
                    )
                ],
                metadata={"D1110": {"max_24mo_freq": 2}},
            ),
            "P4_FREQ_LIMITATION",
            FindingSeverity.WARNING,
        ),
        (
            eval_p4_cob_order,
            make_context(metadata={"is_secondary_claim": True, "primary_eob_attached": False}),
            "P4_COB_ORDER",
            FindingSeverity.WARNING,
        ),
    ],
)
def test_phase_four_rule_fixture(evaluator, context, rule_id, severity) -> None:
    findings = evaluator(context)
    assert len(findings) == 1
    assert findings[0].rule_id == rule_id
    assert findings[0].severity == severity


def test_phase_four_rules_are_quiet_when_ambiguous() -> None:
    context = make_context(metadata={"annual_max_remaining": None})
    assert eval_p4_annual_maximum_exhausted(context) == []
    assert eval_p4_cob_order(context) == []
