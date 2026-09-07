import re
from datetime import datetime
from typing import Any

from app.modules.autofix.schemas import AutofixProposal, SafeTransformType

# Canonical mapping for common tooth surface aliases
SURFACE_ALIAS_MAP = {
    "O": "O",
    "OCCLUSAL": "O",
    "M": "M",
    "MESIAL": "M",
    "D": "D",
    "DISTAL": "D",
    "F": "F",
    "FACIAL": "F",
    "B": "B",
    "BUCCAL": "B",
    "L": "L",
    "LINGUAL": "L",
    "I": "I",
    "INCISAL": "I",
}

CANONICAL_SURFACE_ORDER = ["M", "O", "I", "D", "B", "L", "F"]


def transform_date_format(value: str) -> str:
    """Normalize various date strings (e.g., MM/DD/YYYY, YYYY/MM/DD) to ISO YYYY-MM-DD."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date format: {value}")


def transform_code_padding(value: str, target_length: int = 5, pad_char: str = "0") -> str:
    """Pad taxonomy, zip codes, or standard identifier codes to expected length."""
    clean_val = str(value).strip()
    return clean_val.rjust(target_length, pad_char)


def transform_quadrant_derivation(tooth_number: int | str) -> str:
    """Derive quadrant (UR, UL, LL, LR) from Universal Tooth Number (1-32)."""
    try:
        tooth = int(tooth_number)
    except ValueError as err:
        raise ValueError(f"Invalid tooth number for quadrant derivation: {tooth_number}") from err

    if 1 <= tooth <= 8:
        return "UR"
    elif 9 <= tooth <= 16:
        return "UL"
    elif 17 <= tooth <= 24:
        return "LL"
    elif 25 <= tooth <= 32:
        return "LR"
    else:
        raise ValueError(f"Tooth number {tooth} outside standard Universal system (1-32)")


def transform_arch_derivation(quadrant_or_tooth: int | str) -> str:
    """Derive arch (UA = Upper Arch, LA = Lower Arch) from quadrant or tooth number."""
    val_str = str(quadrant_or_tooth).upper().strip()
    if val_str in ("UR", "UL"):
        return "UA"
    if val_str in ("LL", "LR"):
        return "LA"

    # Fallback to tooth number check
    quadrant = transform_quadrant_derivation(quadrant_or_tooth)
    return "UA" if quadrant in ("UR", "UL") else "LA"


def transform_surface_aliases(surface_raw: str) -> str:
    """Normalize surface aliases (e.g., 'MODL') into deduplicated, canonically ordered characters."""
    canonical_chars = set()

    for token in re.findall(r"[A-Za-z]+", str(surface_raw).upper()):
        if token in SURFACE_ALIAS_MAP:
            canonical_chars.add(SURFACE_ALIAS_MAP[token])
        else:
            for char in token:
                if char in SURFACE_ALIAS_MAP:
                    canonical_chars.add(SURFACE_ALIAS_MAP[char])

    if not canonical_chars:
        raise ValueError(f"No valid surface characters found in '{surface_raw}'")

    # Sort according to standard dental canonical ordering
    sorted_surfaces = sorted(
        canonical_chars,
        key=lambda s: CANONICAL_SURFACE_ORDER.index(s) if s in CANONICAL_SURFACE_ORDER else 99,
    )
    return "".join(sorted_surfaces)


def transform_total_recompute(line_items: list[dict[str, Any]]) -> float:
    """Recalculate total sum based on individual line-item fee amounts."""
    total = sum(float(item.get("fee", 0.0)) for item in line_items)
    return round(total, 2)


def apply_transform(proposal: AutofixProposal, current_value: Any) -> Any:
    """Dispatcher executing the target transform logic safely."""
    match proposal.transform_type:
        case SafeTransformType.DATE_FORMAT:
            return transform_date_format(current_value)
        case SafeTransformType.CODE_PADDING:
            return transform_code_padding(current_value)
        case SafeTransformType.QUADRANT_DERIVATION:
            return transform_quadrant_derivation(current_value)
        case SafeTransformType.ARCH_DERIVATION:
            return transform_arch_derivation(current_value)
        case SafeTransformType.SURFACE_ALIASES:
            return transform_surface_aliases(current_value)
        case SafeTransformType.TOTAL_RECOMPUTE:
            if not isinstance(current_value, list):
                raise ValueError("TOTAL_RECOMPUTE expected a list of line items.")
            return transform_total_recompute(current_value)
        case _:
            raise NotImplementedError(f"Transform {proposal.transform_type} is not implemented.")
