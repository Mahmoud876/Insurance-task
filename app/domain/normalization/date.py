from datetime import date, datetime
from typing import Any

from app.domain.normalization.findings import NormalizationResult, Phase1Finding

# Normalizes ISO strings, formatted date strings, integer representations,
# and datetime/date objects into canonical datetime.date objects.

SUPPORTED_DATE_FORMATS: list[str] = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y%m%d",
]


def normalize_date(
    raw_value: Any,
    field_name: str = "date",
) -> NormalizationResult[date]:
    """Normalizes raw date inputs into a canonical datetime.date object.

    Returns a NormalizationResult containing a `date` on success or a `Phase1Finding`
    on failure. Never raises unhandled exceptions.
    """
    if raw_value is None or raw_value == "":
        return NormalizationResult(
            finding=Phase1Finding(
                code="EMPTY_DATE_INPUT",
                message="Date value cannot be null or empty.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    # Booleans inherit from int in Python (isinstance(True, int) is True).
    # Explicitly catch booleans before type checking integer inputs.
    if isinstance(raw_value, bool):
        return NormalizationResult(
            finding=Phase1Finding(
                code="UNSUPPORTED_DATE_TYPE",
                message="Date value cannot be a boolean.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    # Direct date/datetime handling
    # (datetime inherits from date, so check datetime first)
    if isinstance(raw_value, datetime):
        return NormalizationResult(value=raw_value.date())
    if isinstance(raw_value, date):
        return NormalizationResult(value=raw_value)

    if not isinstance(raw_value, (str, int)):
        return NormalizationResult(
            finding=Phase1Finding(
                code="UNSUPPORTED_DATE_TYPE",
                message=f"Date value must be a string, integer, or date object, got {type(raw_value).__name__}.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    # Safely convert input to string (handles custom objects or int representation)
    try:
        val_str = str(raw_value).strip()
    except Exception as exc:
        return NormalizationResult(
            finding=Phase1Finding(
                code="STRING_CONVERSION_FAILED",
                message=f"Failed to convert raw input to string: {str(exc)}",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    if not val_str:
        return NormalizationResult(
            finding=Phase1Finding(
                code="EMPTY_DATE_INPUT",
                message="Date value cannot be empty.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    try:
        iso_str = val_str.replace("Z", "+00:00")
        parsed_dt = datetime.fromisoformat(iso_str)
        return NormalizationResult(value=parsed_dt.date())
    except (ValueError, TypeError):
        pass

    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            parsed_dt = datetime.strptime(val_str, fmt)
            return NormalizationResult(value=parsed_dt.date())
        except ValueError:
            continue

    return NormalizationResult(
        finding=Phase1Finding(
            code="UNPARSABLE_DATE_FORMAT",
            message=f"Unable to parse date '{val_str}' with supported formats.",
            field_name=field_name,
            raw_value=raw_value,
        )
    )
