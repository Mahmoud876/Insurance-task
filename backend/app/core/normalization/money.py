import math
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.core.normalization.findings import NormalizationResult, Phase1Finding

# Regex for common currency symbols ($, €, £, ¥, ₹)
CURRENCY_SYMBOL_REGEX = re.compile(r"[$\u20AC\u00A3\u00A5\u20B9]")


def normalize_money(
    raw_value: Any,
    field_name: str = "amount",
    scale: int | None = None,
) -> NormalizationResult[Decimal]:
    """Normalizes currency values, numeric strings, floats, integers, and Decimals

    into standard Python Decimal objects.
    """
    if raw_value is None or raw_value == "":
        return NormalizationResult(
            finding=Phase1Finding(
                code="EMPTY_MONEY_INPUT",
                message="Money amount cannot be null or empty.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    # Catch booleans before numeric checks (isinstance(True, int) evaluates to True)
    if isinstance(raw_value, bool):
        return NormalizationResult(
            finding=Phase1Finding(
                code="UNSUPPORTED_MONEY_TYPE",
                message="Money amount cannot be a boolean.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    def apply_scale(val: Decimal) -> NormalizationResult[Decimal]:
        if scale is not None:
            try:
                target = Decimal("10") ** -scale if scale > 0 else Decimal("1")
                val = val.quantize(target, rounding=ROUND_HALF_UP)
            except Exception as exc:
                return NormalizationResult(
                    finding=Phase1Finding(
                        code="INVALID_MONEY_SCALE",
                        message=f"Could not quantize Decimal value to scale {scale}: {str(exc)}",
                        field_name=field_name,
                        raw_value=raw_value,
                    )
                )
        return NormalizationResult(value=val)

    if isinstance(raw_value, Decimal):
        if raw_value.is_nan() or raw_value.is_infinite():
            return NormalizationResult(
                finding=Phase1Finding(
                    code="INVALID_MONEY_NUMERIC",
                    message="Decimal value cannot be NaN or Infinite.",
                    field_name=field_name,
                    raw_value=raw_value,
                )
            )
        return apply_scale(raw_value)

    if isinstance(raw_value, (int, float)):
        if isinstance(raw_value, float) and (math.isnan(raw_value) or math.isinf(raw_value)):
            return NormalizationResult(
                finding=Phase1Finding(
                    code="INVALID_MONEY_NUMERIC",
                    message=f"Numeric money value '{raw_value}' cannot be NaN or Infinite.",
                    field_name=field_name,
                    raw_value=raw_value,
                )
            )
        try:
            dec_val = Decimal(str(raw_value))
            return apply_scale(dec_val)
        except InvalidOperation:
            return NormalizationResult(
                finding=Phase1Finding(
                    code="INVALID_MONEY_NUMERIC",
                    message=f"Numeric money value '{raw_value}' could not be converted to Decimal.",
                    field_name=field_name,
                    raw_value=raw_value,
                )
            )

    if not isinstance(raw_value, str):
        return NormalizationResult(
            finding=Phase1Finding(
                code="UNSUPPORTED_MONEY_TYPE",
                message=f"Money value must be a string, number, or Decimal, got {type(raw_value).__name__}.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    val_str = raw_value.strip()
    if not val_str:
        return NormalizationResult(
            finding=Phase1Finding(
                code="EMPTY_MONEY_INPUT",
                message="Money amount cannot be empty.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    # Check accounting negative format e.g. "(123.45)" or "($123.45)"
    is_accounting_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_accounting_negative = True
        val_str = val_str[1:-1].strip()

    # Clean out currency symbols, thousands separator commas, and spaces
    cleaned = CURRENCY_SYMBOL_REGEX.sub("", val_str)
    cleaned = cleaned.replace(",", "").replace(" ", "")

    if is_accounting_negative:
        cleaned = f"-{cleaned}"

    try:
        dec_val = Decimal(cleaned)
        if dec_val.is_nan() or dec_val.is_infinite():
            return NormalizationResult(
                finding=Phase1Finding(
                    code="INVALID_MONEY_FORMAT",
                    message=f"String value '{raw_value}' evaluates to a non-finite Decimal.",
                    field_name=field_name,
                    raw_value=raw_value,
                )
            )
        return apply_scale(dec_val)
    except InvalidOperation:
        return NormalizationResult(
            finding=Phase1Finding(
                code="INVALID_MONEY_FORMAT",
                message=f"String value '{raw_value}' is not a valid currency or Decimal representation.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )
