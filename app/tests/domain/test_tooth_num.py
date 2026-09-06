import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.tooth_num import (
    NormalizedTooth,
    ToothError,
    fdi_to_palmer,
    fdi_to_universal,
    normalize_tooth,
    parse_fdi,
    parse_palmer,
    parse_universal,
)

# Canonical list of all 32 valid permanent FDI numbers
ALL_PERMANENT_FDI = [
    18,
    17,
    16,
    15,
    14,
    13,
    12,
    11,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    38,
    37,
    36,
    35,
    34,
    33,
    32,
    31,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
]

# Canonical list of all 20 valid primary FDI numbers
ALL_PRIMARY_FDI = [
    55,
    54,
    53,
    52,
    51,
    61,
    62,
    63,
    64,
    65,
    71,
    72,
    73,
    74,
    75,
    81,
    82,
    83,
    84,
    85,
]

ALL_VALID_FDI = ALL_PERMANENT_FDI + ALL_PRIMARY_FDI


@pytest.mark.parametrize("fdi", ALL_PERMANENT_FDI)
@pytest.mark.parametrize("is_super", [False, True])
def test_exhaustive_permanent_fdi(fdi: int, is_super: bool):
    res = parse_fdi(fdi, is_supernumerary=is_super)
    assert res.success is True
    assert res.canonical_fdi == fdi
    assert res.dentition == "permanent"
    assert res.is_supernumerary is is_super


@pytest.mark.parametrize("fdi", ALL_PRIMARY_FDI)
@pytest.mark.parametrize("is_super", [False, True])
def test_exhaustive_primary_fdi(fdi: int, is_super: bool):
    res = parse_fdi(fdi, is_supernumerary=is_super)
    assert res.success is True
    assert res.canonical_fdi == fdi
    assert res.dentition == "primary"
    assert res.is_supernumerary is is_super


@given(
    fdi=st.sampled_from(ALL_VALID_FDI),
    is_super=st.booleans(),
)
def test_hypothesis_fdi_to_universal_round_trip(fdi: int, is_super: bool):
    u_str = fdi_to_universal(fdi, is_supernumerary=is_super)
    assert u_str is not None

    parsed = parse_universal(u_str)
    assert parsed.success is True
    assert parsed.canonical_fdi == fdi
    assert parsed.dentition == ("permanent" if fdi // 10 <= 4 else "primary")
    assert parsed.is_supernumerary is is_super


@given(
    fdi=st.sampled_from(ALL_VALID_FDI),
    is_super=st.booleans(),
)
def test_hypothesis_fdi_to_palmer_round_trip(fdi: int, is_super: bool):
    p_str = fdi_to_palmer(fdi, is_supernumerary=is_super)
    assert p_str is not None

    parsed = parse_palmer(p_str)
    assert parsed.success is True
    assert parsed.canonical_fdi == fdi
    assert parsed.dentition == ("permanent" if fdi // 10 <= 4 else "primary")
    assert parsed.is_supernumerary is is_super


@pytest.mark.parametrize(
    "raw_input, system, expected_fdi, expected_dentition",
    [
        ("8S", "UNIVERSAL", 11, "permanent"),
        ("58", "UNIVERSAL", 11, "permanent"),
        ("AS", "UNIVERSAL", 55, "primary"),
        ("11S", "FDI", 11, "permanent"),
        ("51S", "FDI", 51, "primary"),
        ("UR1S", "PALMER", 11, "permanent"),
        ("URAS", "PALMER", 51, "primary"),
    ],
)
def test_supernumerary_string_parsing(
    raw_input: str, system: str, expected_fdi: int, expected_dentition: str
):
    norm = normalize_tooth(raw_input, system=system)
    assert norm.success is True
    assert norm.canonical_fdi == expected_fdi
    assert norm.dentition == expected_dentition
    assert norm.is_supernumerary is True


@given(val=st.from_type(object))
def test_arbitrary_inputs_never_raise_unhandled(val):
    for sys_name in ["FDI", "UNIVERSAL", "PALMER", "UNKNOWN"]:
        res = normalize_tooth(val, system=sys_name)
        assert isinstance(res, NormalizedTooth)
        if not res.success:
            assert isinstance(res.error, ToothError)
            assert isinstance(res.error.code, str)
            assert isinstance(res.error.message, str)


@pytest.mark.parametrize(
    "bad_input, system, expected_code",
    [
        (None, "FDI", "NULL_INPUT"),
        (True, "FDI", "INVALID_INPUT_TYPE"),
        (False, "FDI", "INVALID_INPUT_TYPE"),
        ("", "FDI", "EMPTY_INPUT"),
        ("   ", "FDI", "EMPTY_INPUT"),
        ([11], "FDI", "INVALID_INPUT_TYPE"),
        ({"tooth": 11}, "FDI", "INVALID_INPUT_TYPE"),
        (99, "FDI", "INVALID_QUADRANT"),
        (19, "FDI", "INVALID_POSITION"),
        ("Z", "UNIVERSAL", "MALFORMED_UNIVERSAL"),
        ("XX1", "PALMER", "INVALID_QUADRANT"),
    ],
)
def test_specific_malformed_input_error_codes(bad_input, system, expected_code):
    res = normalize_tooth(bad_input, system=system)

    assert res.success is False
    assert res.error is not None
    assert res.error.code == expected_code
