from dataclasses import dataclass
from typing import Any


@dataclass
class ToothError:
    code: str
    message: str
    raw_input: Any


@dataclass
class NormalizedTooth:
    success: bool
    canonical_fdi: int | None = None
    dentition: str | None = None  # "permanent" or "primary"
    is_supernumerary: bool = False
    error: ToothError | None = None


UNIVERSAL_PRIMARY_TO_FDI: dict[str, int] = {
    "A": 55,
    "B": 54,
    "C": 53,
    "D": 52,
    "E": 51,
    "F": 61,
    "G": 62,
    "H": 63,
    "I": 64,
    "J": 65,
    "K": 71,
    "L": 72,
    "M": 73,
    "N": 74,
    "O": 75,
    "P": 81,
    "Q": 82,
    "R": 83,
    "S": 84,
    "T": 85,
}

FDI_TO_UNIVERSAL_PRIMARY: dict[int, str] = {v: k for k, v in UNIVERSAL_PRIMARY_TO_FDI.items()}

PALMER_QUADRANTS = {"UR", "UL", "LL", "LR"}


def create_error(code: str, message: str, raw_input: Any) -> NormalizedTooth:
    return NormalizedTooth(
        success=False, error=ToothError(code=code, message=message, raw_input=raw_input)
    )


def parse_fdi(raw_value: Any, is_supernumerary: bool = False) -> NormalizedTooth:
    if raw_value is None:
        return create_error("NULL_INPUT", "Tooth identifier cannot be None.", raw_value)
    if isinstance(raw_value, bool):
        return create_error(
            "INVALID_INPUT_TYPE", "Tooth identifier cannot be a boolean.", raw_value
        )
    if not isinstance(raw_value, (int, str)):
        return create_error(
            "INVALID_INPUT_TYPE",
            f"Tooth identifier must be a string or integer, got {type(raw_value).__name__}.",
            raw_value,
        )

    val_str = str(raw_value).strip().upper()
    if not val_str:
        return create_error("EMPTY_INPUT", "Tooth identifier cannot be empty.", raw_value)

    if len(val_str) > 1 and val_str.endswith("S"):
        is_supernumerary = True
        val_str = val_str[:-1].rstrip("-").strip()

    if not val_str.isdigit() or len(val_str) != 2:
        return create_error(
            "MALFORMED_FDI",
            f"FDI notation must be a 2-digit integer, got '{raw_value}'.",
            raw_value,
        )

    quadrant = int(val_str[0])
    position = int(val_str[1])

    if 1 <= quadrant <= 4:
        if not (1 <= position <= 8):
            return create_error(
                "INVALID_POSITION",
                f"Permanent FDI position must be between 1 and 8, got {position}.",
                raw_value,
            )
        dentition = "permanent"
    elif 5 <= quadrant <= 8:
        if not (1 <= position <= 5):
            return create_error(
                "INVALID_POSITION",
                f"Primary FDI position must be between 1 and 5, got {position}.",
                raw_value,
            )
        dentition = "primary"
    else:
        return create_error(
            "INVALID_QUADRANT", f"FDI quadrant must be between 1 and 8, got {quadrant}.", raw_value
        )

    canonical_fdi = int(val_str)
    return NormalizedTooth(
        success=True,
        canonical_fdi=canonical_fdi,
        dentition=dentition,
        is_supernumerary=is_supernumerary,
    )


def parse_universal(raw_value: Any, is_supernumerary: bool = False) -> NormalizedTooth:
    if raw_value is None:
        return create_error("NULL_INPUT", "Tooth identifier cannot be None.", raw_value)
    if isinstance(raw_value, bool):
        return create_error(
            "INVALID_INPUT_TYPE", "Tooth identifier cannot be a boolean.", raw_value
        )
    if not isinstance(raw_value, (int, str)):
        return create_error(
            "INVALID_INPUT_TYPE",
            f"Tooth identifier must be a string or integer, got {type(raw_value).__name__}.",
            raw_value,
        )

    val_str = str(raw_value).strip().upper()
    if not val_str:
        return create_error("EMPTY_INPUT", "Tooth identifier cannot be empty.", raw_value)

    if len(val_str) > 1 and val_str.endswith("S"):
        is_supernumerary = True
        val_str = val_str[:-1].rstrip("-").strip()

    # Numeric universal
    if val_str.isdigit():
        num = int(val_str)

        # Universal supernumerary range (51 to 82)
        if 51 <= num <= 82:
            num -= 50
            is_supernumerary = True

        if 1 <= num <= 8:
            fdi = 10 + (9 - num)
        elif 9 <= num <= 16:
            fdi = 20 + (num - 8)
        elif 17 <= num <= 24:
            fdi = 30 + (25 - num)
        elif 25 <= num <= 32:
            fdi = 40 + (num - 24)
        else:
            return create_error(
                "OUT_OF_BOUNDS",
                f"Numeric Universal tooth number must be 1-32 or 51-82, got {raw_value}.",
                raw_value,
            )

        return parse_fdi(fdi, is_supernumerary=is_supernumerary)

    # Letter Primary Universal (A - T)
    if val_str in UNIVERSAL_PRIMARY_TO_FDI:
        fdi = UNIVERSAL_PRIMARY_TO_FDI[val_str]
        return parse_fdi(fdi, is_supernumerary=is_supernumerary)

    return create_error(
        "MALFORMED_UNIVERSAL", f"Invalid Universal tooth notation '{raw_value}'.", raw_value
    )


def parse_palmer(raw_value: Any, is_supernumerary: bool = False) -> NormalizedTooth:
    if raw_value is None:
        return create_error("NULL_INPUT", "Tooth identifier cannot be None.", raw_value)
    if isinstance(raw_value, bool):
        return create_error(
            "INVALID_INPUT_TYPE", "Tooth identifier cannot be a boolean.", raw_value
        )
    if not isinstance(raw_value, (int, str)):
        return create_error(
            "INVALID_INPUT_TYPE",
            f"Tooth identifier must be a string or integer, got {type(raw_value).__name__}.",
            raw_value,
        )

    val_str = str(raw_value).strip().upper().replace(" ", "").replace("-", "")
    if not val_str:
        return create_error("EMPTY_INPUT", "Tooth identifier cannot be empty.", raw_value)

    if val_str.endswith("S"):
        is_supernumerary = True
        val_str = val_str[:-1]

    if len(val_str) < 3:
        return create_error(
            "MALFORMED_PALMER",
            f"Palmer notation must include quadrant and tooth ID (e.g., 'UR1'), got '{raw_value}'.",
            raw_value,
        )

    quad = val_str[:2]
    tooth_id = val_str[2:]

    if quad not in PALMER_QUADRANTS:
        return create_error(
            "INVALID_QUADRANT",
            f"Palmer quadrant must be one of UR, UL, LL, LR, got '{quad}'.",
            raw_value,
        )

    # Permanent (1-8)
    if tooth_id.isdigit():
        pos = int(tooth_id)
        if not (1 <= pos <= 8):
            return create_error(
                "INVALID_POSITION", f"Palmer permanent position must be 1-8, got {pos}.", raw_value
            )

        quad_map = {"UR": 1, "UL": 2, "LL": 3, "LR": 4}
        fdi = (quad_map[quad] * 10) + pos
        return parse_fdi(fdi, is_supernumerary=is_supernumerary)

    # Primary (A-E)
    if len(tooth_id) == 1 and "A" <= tooth_id <= "E":
        pos = ord(tooth_id) - ord("A") + 1
        quad_map = {"UR": 5, "UL": 6, "LL": 7, "LR": 8}
        fdi = (quad_map[quad] * 10) + pos
        return parse_fdi(fdi, is_supernumerary=is_supernumerary)

    return create_error(
        "MALFORMED_PALMER", f"Invalid Palmer tooth ID '{tooth_id}'. Expected 1-8 or A-E.", raw_value
    )


def fdi_to_universal(fdi_num: int, is_supernumerary: bool = False) -> str | None:
    res = parse_fdi(fdi_num, is_supernumerary=is_supernumerary)
    if not res.success or res.canonical_fdi is None:
        return None

    fdi = res.canonical_fdi
    quad = fdi // 10
    pos = fdi % 10
    is_sup = res.is_supernumerary

    if quad == 1:
        num = 9 - pos
    elif quad == 2:
        num = 8 + pos
    elif quad == 3:
        num = 25 - pos
    elif quad == 4:
        num = 24 + pos
    elif 5 <= quad <= 8:
        letter = FDI_TO_UNIVERSAL_PRIMARY.get(fdi)
        if not letter:
            return None
        return f"{letter}S" if is_sup else letter
    else:
        return None

    if is_sup:
        num += 50

    return str(num)


def fdi_to_palmer(fdi_num: int, is_supernumerary: bool = False) -> str | None:
    res = parse_fdi(fdi_num, is_supernumerary=is_supernumerary)
    if not res.success or res.canonical_fdi is None:
        return None

    fdi = res.canonical_fdi
    quad = fdi // 10
    pos = fdi % 10
    is_sup = res.is_supernumerary

    quad_map = {1: "UR", 2: "UL", 3: "LL", 4: "LR", 5: "UR", 6: "UL", 7: "LL", 8: "LR"}

    prefix = quad_map[quad]
    if 1 <= quad <= 4:
        base = f"{prefix}{pos}"
    else:
        letter = chr(ord("A") + pos - 1)
        base = f"{prefix}{letter}"

    return f"{base}S" if is_sup else base


def normalize_tooth(
    value: Any, system: str = "FDI", is_supernumerary: bool = False
) -> NormalizedTooth:
    try:
        if value is None:
            return create_error("NULL_INPUT", "Input value cannot be None.", value)

        if isinstance(value, bool):
            return create_error(
                "INVALID_INPUT_TYPE", "Tooth identifier cannot be a boolean.", value
            )

        sys_upper = str(system).strip().upper()

        if sys_upper == "FDI":
            return parse_fdi(value, is_supernumerary=is_supernumerary)
        elif sys_upper == "UNIVERSAL":
            return parse_universal(value, is_supernumerary=is_supernumerary)
        elif sys_upper == "PALMER":
            return parse_palmer(value, is_supernumerary=is_supernumerary)
        else:
            return create_error(
                "UNSUPPORTED_SYSTEM",
                f"Unsupported tooth numbering system '{system}'. Choose FDI, Universal, or Palmer.",
                value,
            )

    except Exception as exc:
        return create_error(
            "UNHANDLED_EXCEPTION",
            f"An unexpected error occurred during normalization: {str(exc)}",
            value,
        )
