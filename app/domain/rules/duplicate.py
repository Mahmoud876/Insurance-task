from .findings import RuleFinding
from .models import ExistingClaim, RuleClaim


LIKELY_DUPLICATE_CLAIM = "LIKELY_DUPLICATE_CLAIM"


def _claim_signature(claim: RuleClaim) -> tuple:
    line_signature = tuple(
        sorted(
            (
                line.procedure_code,
                line.tooth_number,
                line.surface,
                line.charge_amount,
            )
            for line in claim.lines
        )
    )

    return (
        str(claim.patient_id),
        str(claim.provider_id),
        claim.service_date_from,
        claim.service_date_to,
        claim.total_amount,
        line_signature,
    )


def _existing_claim_signature(claim: ExistingClaim) -> tuple:
    line_signature = tuple(
        sorted(
            (
                line.procedure_code,
                line.tooth_number,
                line.surface,
                line.charge_amount,
            )
            for line in claim.lines
        )
    )

    return (
        str(claim.patient_id),
        str(claim.provider_id),
        claim.service_date_from,
        claim.service_date_to,
        claim.total_amount,
        line_signature,
    )


def check_likely_duplicate(
    claim: RuleClaim,
    existing_claims: list[ExistingClaim],
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    current_signature = _claim_signature(claim)

    for existing in existing_claims:
        if str(existing.claim_id) == str(claim.claim_id):
            continue

        if current_signature == _existing_claim_signature(existing):
            findings.append(
                RuleFinding(
                    code=LIKELY_DUPLICATE_CLAIM,
                    message=(
                        f"Claim appears to duplicate existing claim "
                        f"{existing.claim_id}."
                    ),
                    field_name="claim",
                    raw_value=str(existing.claim_id),
                    severity="WARNING",
                )
            )

    return findings