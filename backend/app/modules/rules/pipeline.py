import logging
from datetime import UTC, date, datetime

from app.modules.rules.pipeline_types import (
    ClaimSnapshot,
    EnrichedClaimContext,
    EnrichedLineContext,
    Finding,
    FindingSeverity,
    ReferenceData,
    ScrubResult,
)
from app.modules.rules.registry import OperatorRegistry
from app.modules.rules.resolver import ResolvedRuleSet, RuleConfig

logger = logging.getLogger(__name__)


def normalize_snapshot(snapshot: ClaimSnapshot) -> ClaimSnapshot:
    """Normalizes tooth formatting, surface capitalization, and line order."""
    normalized_lines = []
    for line in sorted(snapshot.lines, key=lambda item: item.line_number):
        normalized_lines.append(
            line.model_copy(
                update={
                    "procedure_code": line.procedure_code.strip().upper(),
                    "tooth_number": line.tooth_number.strip().upper()
                    if line.tooth_number
                    else None,
                    "surface": "".join(sorted(line.surface.strip().upper()))
                    if line.surface
                    else None,
                }
            )
        )
    return snapshot.model_copy(update={"lines": normalized_lines})


def enrich_context(snapshot: ClaimSnapshot, reference: ReferenceData) -> EnrichedClaimContext:
    """Computes age, 24-month procedure history vectors, and indexes lines."""
    # Age calculation
    svc_date = snapshot.service_date_from
    dob = snapshot.patient_dob
    age_years = svc_date.year - dob.year - ((svc_date.month, svc_date.day) < (dob.month, dob.day))
    age_months = (svc_date.year - dob.year) * 12 + (svc_date.month - dob.month)

    # 24 month history filter cutoff
    cutoff_date = date(svc_date.year - 2, svc_date.month, svc_date.day)

    enriched_lines: list[EnrichedLineContext] = []
    lines_by_tooth: dict[str, list[EnrichedLineContext]] = {}

    for line in snapshot.lines:
        # History count matching code and tooth in past 24 months
        history_count = sum(
            1
            for item in reference.patient_history
            if item.procedure_code == line.procedure_code
            and (line.tooth_number is None or item.tooth_number == line.tooth_number)
            and cutoff_date <= item.service_date < svc_date
        )

        eline = EnrichedLineContext(
            line_number=line.line_number,
            procedure_code=line.procedure_code,
            tooth_number=line.tooth_number,
            surface_mask=line.surface,
            charge_amount=line.charge_amount,
            history_24mo_count=history_count,
        )
        enriched_lines.append(eline)

        if line.tooth_number:
            lines_by_tooth.setdefault(line.tooth_number, []).append(eline)

    return EnrichedClaimContext(
        claim_id=snapshot.claim_id,
        tenant_id=snapshot.tenant_id,
        patient_age_years=age_years,
        patient_age_months=age_months,
        service_date_from=snapshot.service_date_from,
        service_date_to=snapshot.service_date_to,
        lines=enriched_lines,
        lines_by_tooth=lines_by_tooth,
        reference=reference,
    )


def evaluate_rule_safe(rule: RuleConfig, context: EnrichedClaimContext) -> list[Finding]:
    """Fault-isolated operator invoker. Converts runtime errors to DCS-ENGINE-0001."""
    findings: list[Finding] = []
    if not rule.operator:
        return findings

    try:
        handler = OperatorRegistry.get(rule.operator)
        # Pass context and rule args to operator
        is_violated = handler.fn(context, *rule.args)

        if is_violated:
            severity_enum = FindingSeverity(rule.severity or "REJECT")
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    severity=severity_enum,
                    message_key=rule.message_key or "ERR_RULE_VIOLATION",
                    message=f"Rule {rule.rule_id} failed check.",
                )
            )
    except Exception as exc:
        logger.warning(f"Rule evaluation exception on {rule.rule_id}: {exc}")
        # System error caught in fault sandbox -> DCS-ENGINE-0001 INFO finding
        findings.append(
            Finding(
                rule_id=rule.rule_id,
                severity=FindingSeverity.INFO,
                message_key="DCS-ENGINE-0001",
                message=f"Rule engine execution error: {str(exc)}",
            )
        )
    return findings


def evaluate_phased(context: EnrichedClaimContext, ruleset: ResolvedRuleSet) -> list[Finding]:
    """Executes Phase 1 (Structural) with gating before Phase 2 (Clinical)."""
    findings: list[Finding] = []

    # Phase 1: Structural & Administrative Rules
    phase_1_rules = [
        r
        for r in ruleset.effective_rules.values()
        if r.rule_id.startswith("P1_") or "STRUCTURAL" in r.rule_id
    ]
    # Remaining rules go to Phase 2
    phase_2_rules = [r for r in ruleset.effective_rules.values() if r not in phase_1_rules]

    # Evaluate Phase 1
    for rule in phase_1_rules:
        findings.extend(evaluate_rule_safe(rule, context))

    # Gating Check: If Phase 1 produced any REJECT finding, short-circuit Phase 2
    has_phase1_reject = any(f.severity == FindingSeverity.REJECT for f in findings)
    if has_phase1_reject:
        return findings

    # Evaluate Phase 2
    for rule in phase_2_rules:
        findings.extend(evaluate_rule_safe(rule, context))

    return findings


def post_process_findings(raw_findings: list[Finding]) -> tuple[list[Finding], int, str, bool]:
    """Deduplicates, orders by severity/line/rule, caps at 200, and calculates score."""
    # Deduplicate by (rule_id, line_number, message_key)
    deduped_map: dict[tuple[str, int | None, str], Finding] = {}
    for f in raw_findings:
        key = (f.rule_id, f.line_number, f.message_key)
        if key not in deduped_map:
            deduped_map[key] = f

    deduped = list(deduped_map.values())

    # Priority Sorting: REJECT (0) -> WARNING (1) -> INFO (2)
    severity_rank = {
        FindingSeverity.REJECT: 0,
        FindingSeverity.WARNING: 1,
        FindingSeverity.INFO: 2,
    }
    sorted_findings = sorted(
        deduped,
        key=lambda f: (
            severity_rank[f.severity],
            f.line_number if f.line_number is not None else -1,
            f.rule_id,
        ),
    )

    # Truncation at 200 items
    is_truncated = len(sorted_findings) > 200
    final_findings = sorted_findings[:200]

    # Readiness Score & Status Calculation
    reject_count = sum(1 for f in final_findings if f.severity == FindingSeverity.REJECT)
    warning_count = sum(1 for f in final_findings if f.severity == FindingSeverity.WARNING)

    if reject_count > 0:
        status = "REJECTED"
        score = max(0, 100 - (reject_count * 25) - (warning_count * 5))
    elif warning_count > 0:
        status = "WARNINGS"
        score = max(50, 100 - (warning_count * 10))
    else:
        status = "CLEAN"
        score = 100

    return final_findings, score, status, is_truncated


def scrub(
    snapshot: ClaimSnapshot,
    ruleset: ResolvedRuleSet,
    reference: ReferenceData,
) -> ScrubResult:
    """Pure scrub pipeline entrypoint: Normalize -> Enrich -> Phased Eval -> Post Process."""
    normalized = normalize_snapshot(snapshot)
    context = enrich_context(normalized, reference)
    raw_findings = evaluate_phased(context, ruleset)
    findings, score, status, is_truncated = post_process_findings(raw_findings)

    return ScrubResult(
        claim_id=snapshot.claim_id,
        readiness_score=score,
        status=status,
        findings=findings,
        pinned_version_ids=ruleset.pinned_version_ids,
        is_truncated=is_truncated,
        evaluated_at=datetime.now(UTC),
    )
