from app.modules.rules.pipeline_types import (
    EnrichedClaimContext,
    Finding,
    FindingSeverity,
)


def eval_p4_policy_expired(context: EnrichedClaimContext) -> list[Finding]:
    findings = []
    policy = context.reference.policy
    if policy and policy.termination_date and context.service_date_from:
        if context.service_date_from > policy.termination_date:
            findings.append(
                Finding(
                    rule_id="P4_POL_EXPIRED",
                    severity=FindingSeverity.REJECT,
                    message_key="DCS-POL-0001",
                    message=f"Service date {context.service_date_from} is after policy termination date {policy.termination_date}.",
                )
            )
    return findings


def eval_p4_policy_not_effective(context: EnrichedClaimContext) -> list[Finding]:
    findings = []
    policy = context.reference.policy
    if policy and policy.effective_date and context.service_date_from:
        if context.service_date_from < policy.effective_date:
            findings.append(
                Finding(
                    rule_id="P4_POL_NOT_EFFECTIVE",
                    severity=FindingSeverity.REJECT,
                    message_key="DCS-POL-0002",
                    message=f"Service date {context.service_date_from} is prior to policy effective date {policy.effective_date}.",
                )
            )
    return findings


def eval_p4_dependent_age_limit(
    context: EnrichedClaimContext, max_age_years: int = 26
) -> list[Finding]:
    findings = []
    if context.patient_age_years is not None and context.patient_age_years >= max_age_years:
        findings.append(
            Finding(
                rule_id="P4_DEP_AGE_LIMIT",
                severity=FindingSeverity.WARNING,
                message_key="DCS-POL-0003",
                message=f"Patient age ({context.patient_age_years}) meets or exceeds dependent age limit ({max_age_years}). Verify student or disability status.",
            )
        )
    return findings


def eval_p4_waiting_period(
    context: EnrichedClaimContext, waiting_period_days: int = 180
) -> list[Finding]:
    findings = []
    policy = context.reference.policy
    if policy and policy.effective_date and context.service_date_from:
        days_since_effective = (context.service_date_from - policy.effective_date).days
        if 0 <= days_since_effective < waiting_period_days:
            findings.append(
                Finding(
                    rule_id="P4_WAITING_PERIOD",
                    severity=FindingSeverity.WARNING,
                    message_key="DCS-POL-0004",
                    message=f"Service rendered {days_since_effective} days after policy inception (waiting period: {waiting_period_days} days). Verify prior coverage credit.",
                )
            )
    return findings


def eval_p4_annual_maximum_exhausted(context: EnrichedClaimContext) -> list[Finding]:
    findings = []
    meta = context.reference.code_metadata or {}
    remaining_max = meta.get("annual_max_remaining", None)
    if remaining_max is not None and remaining_max <= 0:
        findings.append(
            Finding(
                rule_id="P4_ANNUAL_MAX_EXHAUSTED",
                severity=FindingSeverity.WARNING,
                message_key="DCS-POL-0005",
                message="Patient annual benefit maximum has been exhausted. Verification required for secondary or rollover coverage.",
            )
        )
    return findings


def eval_p4_category_exclusion(context: EnrichedClaimContext) -> list[Finding]:
    findings = []
    code_metadata = context.reference.code_metadata or {}
    raw_excluded: object = code_metadata.get("excluded_categories", [])
    excluded_categories = (
        set(raw_excluded) if isinstance(raw_excluded, (list, set, tuple)) else set()
    )

    for line in context.lines:
        proc_meta = code_metadata.get(line.procedure_code, {})
        cat = proc_meta.get("category") if isinstance(proc_meta, dict) else None
        if cat in excluded_categories:
            findings.append(
                Finding(
                    rule_id="P4_CATEGORY_EXCLUSION",
                    severity=FindingSeverity.WARNING,
                    message_key="DCS-POL-0006",
                    line_number=line.line_number,
                    message=f"Procedure {line.procedure_code} belongs to excluded plan category '{cat}'. Verify medical necessity authorization.",
                )
            )
    return findings


def eval_p4_frequency_limitation(context: EnrichedClaimContext) -> list[Finding]:
    findings = []
    code_metadata = context.reference.code_metadata or {}

    for line in context.lines:
        proc_meta = code_metadata.get(line.procedure_code, {})
        max_allowed = 2

        if isinstance(proc_meta, dict):
            val = proc_meta.get("max_24mo_freq", 2)
            if isinstance(val, int):
                max_allowed = val
        elif isinstance(proc_meta, int):
            max_allowed = proc_meta

        if line.history_24mo_count >= max_allowed:
            findings.append(
                Finding(
                    rule_id="P4_FREQ_LIMITATION",
                    severity=FindingSeverity.WARNING,
                    message_key="DCS-POL-0007",
                    line_number=line.line_number,
                    message=f"Procedure {line.procedure_code} on line {line.line_number} exceeds 24-month frequency limit ({line.history_24mo_count}/{max_allowed}).",
                )
            )
    return findings


def eval_p4_cob_order(context: EnrichedClaimContext) -> list[Finding]:
    findings = []
    meta = context.reference.code_metadata or {}
    is_secondary = meta.get("is_secondary_claim", False)
    primary_eob_attached = meta.get("primary_eob_attached", False)

    if is_secondary and not primary_eob_attached:
        findings.append(
            Finding(
                rule_id="P4_COB_ORDER",
                severity=FindingSeverity.WARNING,
                message_key="DCS-POL-0008",
                message="Claim is marked as secondary COB but primary Payer EOB attachment is missing.",
            )
        )
    return findings
