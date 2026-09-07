import math

from app.modules.rules.pipeline_types import Finding, FindingSeverity


def calculate_readiness_score(findings: list[Finding]) -> int:
    e_count = 0
    w_count = 0
    i_count = 0
    has_phase_1_error = False

    for finding in findings:
        if finding.severity == FindingSeverity.REJECT:
            e_count += 1
            # Check if finding belongs to Phase 1 structural rules
            if getattr(finding, "phase", None) == 1 or finding.rule_id.startswith("P1_"):
                has_phase_1_error = True
        elif finding.severity == FindingSeverity.WARNING:
            w_count += 1
        elif finding.severity == FindingSeverity.INFO:
            i_count += 1

    # Zero-floor rule for Phase 1 structural failures
    if has_phase_1_error:
        return 0

    exponent = -(3.0 * e_count + 0.8 * w_count + 0.15 * i_count) / 6.0
    raw_score = 100.0 * math.exp(exponent)
    score = round(raw_score)

    return max(0, min(100, score))
