import re
from typing import Any

from app.domain.normalization.findings import NormalizationResult, Phase1Finding

SURFACE_TEXT_MAP: dict[str, str] = {
    "BUCCAL": "B",
    "FACIAL": "F",
    "LABIAL": "F",
    "LINGUAL": "L",
    "PALATAL": "P",
    "MESIAL": "M",
    "DISTAL": "D",
    "OCCLUSAL": "O",
    "INCISAL": "I",
}

ALIAS_MAP: dict[str, str] = {
    "B": "B",  # Buccal
    "F": "F",  # Facial (B and F are equivalent facial/outer surfaces)
    "L": "L",  # Lingual
    "P": "P",  # Palatal (L and P are equivalent lingual/inner surfaces)
    "M": "M",  # Mesial
    "D": "D",  # Distal
    "O": "O",  # Occlusal
    "I": "I",  # Incisal
}

VALID_SURFACE_CODES: set[str] = set(ALIAS_MAP.keys())


def normalize_surface(
    raw_value: Any,
    field_name: str = "surface",
    canonicalize_aliases: bool = False,
) -> NormalizationResult[set[str]]:
    """Normalizes clinical dental surface strings into a canonical set of surface letters.

    Accepted codes:
        - M: Mesial
        - O: Occlusal
        - D: Distal
        - B: Buccal
        - F: Facial
        - L: Lingual
        - P: Palatal
        - I: Incisal

    Alias Behavior:
        - Buccal (B) and Facial (F) represent outer facial surfaces.
        - Lingual (L) and Palatal (P) represent inner lingual surfaces.
        - When `canonicalize_aliases=False` (default), original codes ('F', 'P', 'B', 'L') are preserved.
        - When `canonicalize_aliases=True`, 'F' is mapped to 'B', and 'P' is mapped to 'L'.

    Returns a NormalizationResult containing a Set[str] on success or a Phase1Finding on failure.
    Never raises unhandled exceptions.
    """
    if raw_value is None or raw_value == "":
        return NormalizationResult(
            finding=Phase1Finding(
                code="EMPTY_SURFACE_INPUT",
                message="Surface value cannot be null or empty.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    if isinstance(raw_value, bool):
        return NormalizationResult(
            finding=Phase1Finding(
                code="UNSUPPORTED_SURFACE_TYPE",
                message="Surface value cannot be a boolean.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    try:
        val_str = str(raw_value).strip().upper()
    except Exception as exc:
        return NormalizationResult(
            finding=Phase1Finding(
                code="STRING_CONVERSION_FAILED",
                message=f"Failed to convert surface input to string: {str(exc)}",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    if not val_str:
        return NormalizationResult(
            finding=Phase1Finding(
                code="EMPTY_SURFACE_INPUT",
                message="Surface value cannot be empty.",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    # Check direct full-word replacement
    words_replaced = val_str
    for word, code in SURFACE_TEXT_MAP.items():
        words_replaced = re.sub(r"\b" + word + r"\b", code, words_replaced)

    # Split on common delimiters: slash, comma, hyphen, period, underscore, whitespace
    tokens = re.split(r"[./,\-\_\s]+", words_replaced)

    extracted_surfaces: set[str] = set()
    invalid_tokens = []

    for token in tokens:
        if not token:
            continue

        # Single valid surface code
        if token in VALID_SURFACE_CODES:
            extracted_surfaces.add(token)
        # Concatenated string of single-letter surface codes (e.g., "MOD", "MODBL")
        elif all(char in VALID_SURFACE_CODES for char in token):
            for char in token:
                extracted_surfaces.add(char)
        else:
            invalid_tokens.append(token)

    if invalid_tokens or not extracted_surfaces:
        return NormalizationResult(
            finding=Phase1Finding(
                code="INVALID_SURFACE_STRING",
                message=f"Unrecognized surface character(s) or format: {invalid_tokens or val_str}",
                field_name=field_name,
                raw_value=raw_value,
            )
        )

    # Unify aliases (F -> B, P -> L) if canonicalization is requested
    if canonicalize_aliases:
        alias_unified: set[str] = set()
        for s in extracted_surfaces:
            if s == "F":
                alias_unified.add("B")
            elif s == "P":
                alias_unified.add("L")
            else:
                alias_unified.add(s)
        extracted_surfaces = alias_unified

    return NormalizationResult(value=extracted_surfaces)
