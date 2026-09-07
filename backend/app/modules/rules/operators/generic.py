from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.core.age import (
    AGE_STRATEGIES,
    AgeCalculationStrategy,
    exact_age_strategy,
)
from app.core.constants import DEFAULT_CODE_SETS
from app.core.enums import AgeStrategyType, ProcedureCategory
from app.core.normalization.dates import normalize_date
from app.core.normalization.tooth import parse_fdi
from app.modules.claims.models.claim import Claim
from app.modules.claims.models.claim_line import ClaimLine
from app.modules.claims.models.insurance_policy import InsurancePolicy
from app.modules.rules.registry import OperatorRegistry

__all__ = [
    "tooth_is_posterior",
    "tooth_is_primary",
    "tooth_in_quadrant",
    "tooth_exists_for_age",
    "surfaces_valid_for_tooth",
    "surface_count",
    "code_in_set",
    "code_category",
    "age_at_service",
    "days_between",
    "policy_active_on",
    "has_attachment",
    "procedure_count_in_window",
    "same_tooth_same_day",
    "sum_lines",
]


@OperatorRegistry.register()
def tooth_is_posterior(n: int) -> bool | None:
    """Returns true if posterior, false if anterior"""

    tooth_ret = parse_fdi(n)
    if not tooth_ret.success or tooth_ret.canonical_fdi is None:
        return None

    tooth_position = tooth_ret.canonical_fdi % 10
    return tooth_position >= 4


@OperatorRegistry.register()
def tooth_is_primary(n: int) -> bool | None:
    """Returns true if primary, false if permanent"""
    tooth_ret = parse_fdi(n)
    if not tooth_ret.success or tooth_ret.canonical_fdi is None:
        return None

    fdi_quadrant = tooth_ret.canonical_fdi // 10
    return 5 <= fdi_quadrant <= 8


@OperatorRegistry.register()
def tooth_in_quadrant(n: int, q: int) -> bool | None:
    """Returns true if tooth is in quadrant q, false if not"""
    tooth_ret = parse_fdi(n)
    if not tooth_ret.success or tooth_ret.canonical_fdi is None:
        return None

    fdi_quadrant = tooth_ret.canonical_fdi // 10
    return fdi_quadrant == q


@OperatorRegistry.register()
def tooth_exists_for_age(n: int, age: int) -> bool | None:
    """Returns true if tooth exists for age, false if not"""
    is_primary = tooth_is_primary(n)
    if is_primary is None:
        return None
    return age < 12 if is_primary else age >= 12


@OperatorRegistry.register()
def surfaces_valid_for_tooth(surfaces: str, tooth: int) -> bool | None:
    # incisal only on anterior; occlusal only on posterior

    is_posterior = tooth_is_posterior(tooth)

    if is_posterior is None:
        return None

    norm_surfaces = {s.upper() for s in surfaces}

    # Mesial, Distal, Occlusal, Incisal, Buccal/Facial, Lingual/Palatal
    allowed = {"M", "D", "O", "I", "B", "L", "F", "P"}

    if not norm_surfaces.issubset(allowed):
        return False

    return "I" not in norm_surfaces if is_posterior else "O" not in norm_surfaces


@OperatorRegistry.register()
def surface_count(surfaces: str) -> int:
    allowed = {"M", "O", "I", "D", "B", "L", "F", "P"}
    return len({char.upper() for char in surfaces if char.upper() in allowed})


@OperatorRegistry.register()
def code_in_set(code: str, set_name: str) -> bool:
    """Checks if a procedure code belongs to a pre-defined code set."""
    if not code or not set_name:
        return False

    norm_code = str(code).strip().upper()
    norm_set = str(set_name).strip().upper()

    code_group = DEFAULT_CODE_SETS.get(norm_set)
    if not code_group:
        return False

    return norm_code in code_group


@OperatorRegistry.register()
def code_category(code: str) -> str:
    if not code:
        return ProcedureCategory.UNKNOWN

    clean_code = str(code).upper()

    # CDT codes follow D + 4 digits ('D1110', 'D0120', etc)
    if clean_code.startswith("D") and len(clean_code) >= 5 and clean_code[1:5].isdigit():
        num = int(clean_code[1:5])

        if 100 <= num <= 999:
            return ProcedureCategory.DIAGNOSTIC
        if 1000 <= num <= 1999:
            return ProcedureCategory.PREVENTIVE
        if 2000 <= num <= 2999:
            return ProcedureCategory.RESTORATIVE
        if 3000 <= num <= 3999:
            return ProcedureCategory.ENDODONTICS
        if 4000 <= num <= 4999:
            return ProcedureCategory.PERIODONTICS
        if 5000 <= num <= 5899:
            return ProcedureCategory.PROSTHODONTICS_REMOVABLE
        if 6000 <= num <= 6199:
            return ProcedureCategory.IMPLANTS
        if 6200 <= num <= 6999:
            return ProcedureCategory.PROSTHODONTICS_FIXED
        if 7000 <= num <= 7999:
            return ProcedureCategory.ORAL_SURGERY
        if 8000 <= num <= 8999:
            return ProcedureCategory.ORTHODONTICS
        if 9000 <= num <= 9999:
            return ProcedureCategory.ADJUNCTIVE

    return ProcedureCategory.UNKNOWN


@OperatorRegistry.register()
def age_at_service(
    dob: date,
    service_date: date,
    strategy: AgeCalculationStrategy | str = AgeStrategyType.EXACT,
) -> int:
    """Calculates age at service date using the specified strategy, strategy can be a string or a function."""
    if not dob or not service_date:
        return 0

    if isinstance(strategy, str):
        calc_fn = AGE_STRATEGIES.get(strategy.upper(), exact_age_strategy)
    else:
        calc_fn = strategy

    return calc_fn(dob, service_date)


@OperatorRegistry.register()
def days_between(d1: date, d2: date) -> int:
    return abs((d2 - d1).days)


@OperatorRegistry.register()
def policy_active_on(policy: InsurancePolicy, target_date: date) -> bool:
    norm_res = normalize_date(target_date, "policy_active_on")
    if norm_res.finding or norm_res.value is None:
        return False

    check_date = norm_res.value

    if policy.effective_date and check_date < policy.effective_date:
        return False

    if policy.termination_date and check_date > policy.termination_date:
        return False

    return True


@OperatorRegistry.register()
def has_attachment(claim: Claim, doc_type: str) -> bool:
    claim_attachments = claim.attachments

    for att in claim_attachments:
        if att.file_type == doc_type:
            return True

    return False


@OperatorRegistry.register()
def procedure_count_in_window(history: Sequence[Any], code: str, days: int) -> int:
    if not history or not code or not days:
        return 0

    norm_code = str(code).upper()
    window_end = date.today()
    window_start = window_end - timedelta(days=days)

    return sum(
        1
        for item in history
        if item.procedure_code.upper() == norm_code
        and window_start <= item.service_date <= window_end
    )


@OperatorRegistry.register()
def same_tooth_same_day(lines: Sequence[ClaimLine], code_a: str, code_b: str) -> bool:
    """Returns True if code_a and code_b are billed for the same tooth on the claim."""

    if not lines or not code_a or not code_b:
        return False

    norm_code_a = str(code_a).upper()
    norm_code_b = str(code_b).upper()

    teeth_a: set[str] = set()
    teeth_b: set[str] = set()
    for line in lines:
        if not line.tooth_number:
            continue

        code = line.procedure_code.strip().upper()
        if code == norm_code_a:
            teeth_a.add(line.tooth_number)
        if code == norm_code_b:
            teeth_b.add(line.tooth_number)

    return bool(teeth_a & teeth_b)


@OperatorRegistry.register()
def sum_lines(lines: Sequence[ClaimLine], field: str = "charge_amount") -> Decimal:
    """Returns the sum of charge_amount for lines with the given code."""

    if not lines or not field:
        return Decimal("0.0")

    total = Decimal("0.0")
    for line in lines:
        value = getattr(line, field, None)
        if value is None:
            continue

        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        total += value

    return total
