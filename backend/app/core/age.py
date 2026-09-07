from datetime import date
from typing import Protocol

from app.core.enums import AgeStrategyType


class AgeCalculationStrategy(Protocol):
    def __call__(self, dob: date, service_date: date) -> int: ...


def exact_age_strategy(dob: date, service_date: date) -> int:
    """Exact calendar age on date of service."""
    return (
        service_date.year
        - dob.year
        - ((service_date.month, service_date.day) < (dob.month, dob.day))
    )


def calendar_year_age_strategy(dob: date, service_date: date) -> int:
    """Age based solely on service year minus birth year."""
    return service_date.year - dob.year


def benefit_year_start_strategy(dob: date, service_date: date) -> int:
    """Fixed age as of January 1st of the service year."""
    jan_1 = date(service_date.year, 1, 1)
    return jan_1.year - dob.year - ((jan_1.month, jan_1.day) < (dob.month, dob.day))


AGE_STRATEGIES: dict[str, AgeCalculationStrategy] = {
    AgeStrategyType.EXACT: exact_age_strategy,
    AgeStrategyType.CALENDAR_YEAR: calendar_year_age_strategy,
    AgeStrategyType.BENEFIT_YEAR_START: benefit_year_start_strategy,
}
