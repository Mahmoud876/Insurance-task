import logging
import time
from datetime import UTC, date, datetime

from app.core.normalization.tooth import parse_fdi
from app.core.telemetry import (
    DCS_RULE_ERRORS_TOTAL,
    DCS_RULE_HITS_TOTAL,
    DCS_SCRUB_DURATION_SECONDS,
    DCS_SCRUB_FINDINGS_TOTAL,
    tracer,
)
from app.modules.rules.operators.generic import age_at_service
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


_CATEGORY_PREFIX: dict[str, str] = {
    "P1_": "structural",
    "P2_": "format",
    "P3_": "clinical",
    "P4_": "coverage",
    "P5_": "documentation",
    "DCS-ENGINE": "engine_error",
}


def _category_for_rule(rule_id: str) -> str:
    key = rule_id.upper()
    for prefix, category in _CATEGORY_PREFIX.items():
        if key.startswith(prefix):
            return category
    return "other"


def _emit_findings_metrics(findings: list[Finding]) -> None:
    for f in findings:
        DCS_SCRUB_FINDINGS_TOTAL.labels(
            severity=f.severity.value,
            category=_category_for_rule(f.rule_id),
        ).inc()


def normalize_snapshot(snapshot: ClaimSnapshot) -> ClaimSnapshot:
    """Normalizes tooth formatting, surface capitalization, and line order."""
    normalized_lines = []
    for line in sorted(snapshot.lines, key=lambda item: item.line_number):
        tooth_clean = line.tooth_number.strip().upper() if line.tooth_number else None

        if tooth_clean and tooth_clean.isdigit():
            ret = parse_fdi(int(tooth_clean))
            if ret.success and ret.canonical_fdi:
                tooth_clean = str(ret.canonical_fdi)

        normalized_lines.append(
            line.model_copy(
                update={
                    "procedure_code": line.procedure_code.strip().upper(),
                    "tooth_number": tooth_clean,
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
    age_years = age_at_service(snapshot.patient_dob, snapshot.service_date_from)

    total_months = (snapshot.service_date_from.year - snapshot.patient_dob.year) * 12 + (
        snapshot.service_date_from.month - snapshot.patient_dob.month
    )
    if snapshot.service_date_from.day < snapshot.patient_dob.day:
        total_months -= 1

    age_months = max(0, total_months)

    # 24 month history filter cutoff
    try:
        cutoff_date = date(
            snapshot.service_date_from.year - 2,
            snapshot.service_date_from.month,
            snapshot.service_date_from.day,
        )
    except ValueError:
        # Leap year: use Feb 28 for non leap years
        cutoff_date = date(
            snapshot.service_date_from.year - 2, snapshot.service_date_from.month, 28
        )

    enriched_lines: list[EnrichedLineContext] = []
    lines_by_tooth: dict[str, list[EnrichedLineContext]] = {}

    for line in snapshot.lines:
        # History count matching code and tooth in past 24 months
        history_count = sum(
            1
            for item in reference.patient_history
            if item.procedure_code == line.procedure_code
            and (line.tooth_number is None or item.tooth_number == line.tooth_number)
            and cutoff_date <= item.service_date < snapshot.service_date_from
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
    findings: list[Finding] = []
    if not rule.operator:
        return findings

    try:
        handler = OperatorRegistry.get(rule.operator)
        is_violated = handler.fn(context, *rule.args)

        if is_violated:
            severity_str = rule.severity or "REJECT"

            # Primary feedback loop metric
            DCS_RULE_HITS_TOTAL.labels(
                rule_code=rule.rule_id,
                severity=severity_str,
            ).inc()

            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    severity=FindingSeverity(severity_str),
                    message_key=rule.message_key or "ERR_RULE_VIOLATION",
                    message=f"Rule {rule.rule_id} failed check.",
                    line_number=getattr(rule, "line_number", None),
                )
            )

    except Exception as exc:
        DCS_RULE_ERRORS_TOTAL.labels(rule_code=rule.rule_id).inc()

        logger.warning(f"Rule evaluation exception on {rule.rule_id}: {exc}")
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
    with tracer.start_as_current_span(
        "scrub_claim", attributes={"claim.id": str(snapshot.claim_id)}
    ):
        # Phase 1: Normalize
        with tracer.start_as_current_span("phase_normalize"):
            start_time = time.perf_counter()
            normalized = normalize_snapshot(snapshot)
            DCS_SCRUB_DURATION_SECONDS.labels(phase="normalize").observe(
                time.perf_counter() - start_time
            )

        # Phase 2: Enrich
        with tracer.start_as_current_span("phase_enrich"):
            start_time = time.perf_counter()
            context = enrich_context(normalized, reference)
            DCS_SCRUB_DURATION_SECONDS.labels(phase="enrich").observe(
                time.perf_counter() - start_time
            )

        # Phase 3: Phased Evaluation
        with tracer.start_as_current_span("phase_evaluate"):
            start_time = time.perf_counter()
            raw_findings = evaluate_phased(context, ruleset)
            DCS_SCRUB_DURATION_SECONDS.labels(phase="evaluate").observe(
                time.perf_counter() - start_time
            )

        # Phase 4: Post-Process
        with tracer.start_as_current_span("phase_post_process"):
            start_time = time.perf_counter()
            findings, score, status, is_truncated = post_process_findings(raw_findings)
            DCS_SCRUB_DURATION_SECONDS.labels(phase="post_process").observe(
                time.perf_counter() - start_time
            )
        _emit_findings_metrics(findings)

    return ScrubResult(
        claim_id=snapshot.claim_id,
        readiness_score=score,
        status=status,
        findings=findings,
        pinned_version_ids=ruleset.pinned_version_ids,
        is_truncated=is_truncated,
        evaluated_at=datetime.now(UTC),
    )
