from datetime import date, datetime

import pytest

from app.domain.normalization.date import normalize_date


@pytest.mark.parametrize(
    "raw_input, expected_date",
    [
        ("2026-08-18", date(2026, 8, 18)),
        ("08/18/2026", date(2026, 8, 18)),
        ("08-18-2026", date(2026, 8, 18)),
        ("2026/08/18", date(2026, 8, 18)),
        ("20260818", date(2026, 8, 18)),
        (date(2026, 8, 18), date(2026, 8, 18)),
        (datetime(2026, 8, 18, 14, 30), date(2026, 8, 18)),
    ],
)
def test_valid_date_parsing(raw_input, expected_date):
    res = normalize_date(raw_input)
    assert res.is_valid is True
    assert res.value == expected_date
    assert res.finding is None


@pytest.mark.parametrize(
    "invalid_input", ["", None, "invalid-date-string", "2026-13-45", 99999999999]
)
def test_invalid_date_yields_finding(invalid_input):
    res = normalize_date(invalid_input, field_name="service_date")
    assert res.is_valid is False
    assert res.value is None
    assert res.finding is not None
    assert res.finding.field_name == "service_date"
    assert res.finding.code in (
        "EMPTY_DATE_INPUT",
        "UNSUPPORTED_DATE_TYPE",
        "UNPARSABLE_DATE_FORMAT",
    )


def test_date_scrubbing_collects_finding_without_exception():
    res = normalize_date("2026-13-45", field_name="service_date")
    assert res.is_valid is False
    assert res.finding is not None
    assert res.finding.field_name == "service_date"
    assert res.finding.code in ("UNPARSABLE_DATE_FORMAT", "UNSUPPORTED_DATE_TYPE")
