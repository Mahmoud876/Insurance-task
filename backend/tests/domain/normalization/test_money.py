from decimal import Decimal

import pytest

from app.core.normalization.money import normalize_money


@pytest.mark.parametrize(
    "raw_input, expected_decimal",
    [
        ("$123.45", Decimal("123.45")),
        ("1,250.50", Decimal("1250.50")),
        ("($50.00)", Decimal("-50.00")),
        ("(1,200.00)", Decimal("-1200.00")),
        (100, Decimal("100")),
        (99.95, Decimal("99.95")),
        (Decimal("450.00"), Decimal("450.00")),
    ],
)
def test_valid_money_parsing(raw_input, expected_decimal):
    res = normalize_money(raw_input)
    assert res.is_valid is True
    assert res.value == expected_decimal
    assert res.finding is None


@pytest.mark.parametrize("invalid_input", ["", None, "$12ABC", "invalid", "NaN", "Infinity"])
def test_invalid_money_yields_finding(invalid_input):
    res = normalize_money(invalid_input, field_name="charged_amount")
    assert res.is_valid is False
    assert res.value is None
    assert res.finding is not None
    assert res.finding.field_name == "charged_amount"
    assert res.finding.code in (
        "EMPTY_MONEY_INPUT",
        "INVALID_MONEY_FORMAT",
        "INVALID_MONEY_NUMERIC",
    )


def test_money_scrubbing_collects_finding_without_exception():
    res = normalize_money("$12ABC", field_name="charged_amount")
    assert res.is_valid is False
    assert res.finding is not None
    assert res.finding.field_name == "charged_amount"
    assert res.finding.code in ("INVALID_MONEY_FORMAT", "INVALID_MONEY_NUMERIC")
