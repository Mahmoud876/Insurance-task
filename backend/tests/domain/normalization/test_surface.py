import pytest

from app.core.normalization.surfaces import normalize_surface


@pytest.mark.parametrize(
    "raw_input, expected_set",
    [
        ("B", {"B"}),
        ("f", {"F"}),
        ("B/F", {"B", "F"}),
        ("M, D, O", {"D", "M", "O"}),
        ("MOD", {"D", "M", "O"}),
        ("Buccal / Facial", {"B", "F"}),
        ("Lingual-Palatal", {"L", "P"}),
        ("M O D B L", {"B", "D", "L", "M", "O"}),
    ],
)
def test_valid_surface_parsing(raw_input, expected_set):
    res = normalize_surface(raw_input)
    assert res.is_valid is True
    assert res.value == expected_set
    assert res.finding is None


def test_surface_alias_canonicalization():
    # B/F -> B, L/P -> L
    res = normalize_surface("B/F/L/P", canonicalize_aliases=True)
    assert res.is_valid is True
    assert res.value == {"B", "L"}


@pytest.mark.parametrize("invalid_input", ["", None, "   ", "XYZ", "123", "B/F/UNKNOWN"])
def test_invalid_surface_yields_finding(invalid_input):
    res = normalize_surface(invalid_input, field_name="tooth_surface")
    assert res.is_valid is False
    assert res.value is None
    assert res.finding is not None
    assert res.finding.field_name == "tooth_surface"
    assert res.finding.raw_value == invalid_input
    assert res.finding.code in ("EMPTY_SURFACE_INPUT", "INVALID_SURFACE_STRING")


def test_surface_scrubbing_collects_finding_without_exception():
    res = normalize_surface("INVALID_SURFACE", field_name="tooth_surface")
    assert res.is_valid is False
    assert res.finding is not None
    assert res.finding.field_name == "tooth_surface"
    assert res.finding.code == "INVALID_SURFACE_STRING"
