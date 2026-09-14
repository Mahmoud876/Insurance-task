from decimal import Decimal

from .findings import RuleFinding
from .models import RuleClaim


LINE_FEES_DO_NOT_SUM_TO_TOTAL = "LINE_FEES_DO_NOT_SUM_TO_TOTAL"
NON_POSITIVE_FEE = "NON_POSITIVE_FEE"
FEE_EXCEEDS_ALLOWED_AMOUNT = "FEE_EXCEEDS_ALLOWED_AMOUNT"


def check_line_fees_sum_to_total(
    claim: RuleClaim,
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    line_total = sum(
        (line.charge_amount for line in claim.lines),
        Decimal("0.00"),
    )

    if line_total != claim.total_amount:
        findings.append(
            RuleFinding(
                code=LINE_FEES_DO_NOT_SUM_TO_TOTAL,
                message=(
                    f"Line fees total {line_total} but claim total "
                    f"is {claim.total_amount}."
                ),
                field_name="total_amount",
                raw_value=str(claim.total_amount),
            )
        )

    return findings


def check_non_positive_fees(
    claim: RuleClaim,
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for index, line in enumerate(claim.lines):
        if line.charge_amount <= Decimal("0.00"):
            findings.append(
                RuleFinding(
                    code=NON_POSITIVE_FEE,
                    message="Claim line fee must be greater than zero.",
                    field_name=f"line_items[{index}].charge_amount",
                    raw_value=str(line.charge_amount),
                )
            )

    return findings


def check_fee_exceeds_allowed_amount(
    claim: RuleClaim,
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for index, line in enumerate(claim.lines):
        if line.allowed_amount is None:
            continue

        if line.charge_amount > line.allowed_amount:
            findings.append(
                RuleFinding(
                    code=FEE_EXCEEDS_ALLOWED_AMOUNT,
                    message=(
                        f"Line fee {line.charge_amount} exceeds "
                        f"allowed amount {line.allowed_amount}."
                    ),
                    field_name=f"line_items[{index}].charge_amount",
                    raw_value=str(line.charge_amount),
                )
            )

    return findings
