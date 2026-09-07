import json
from pathlib import Path

from faker import Faker

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden_corpus.json"
PROCEDURES = [
    "D0120",
    "D1110",
    "D2140",
    "D2392",
    "D2740",
    "D4355",
    "D7210",
    "D0274",
    "D2330",
    "D2750",
    "D4341",
    "D4910",
    "D7140",
    "D2391",
    "D2950",
    "D0220",
]
SURFACES = ["O", "B", "L", "M", "D"]


def money_string(amount_cents: int) -> str:
    return f"{amount_cents / 100:.2f}"


def build_golden_corpus() -> list[dict]:
    fixtures: list[dict] = []

    for index in range(25):
        fake = Faker()
        fake.seed_instance(2025 + index)

        patient = {
            "patient_id": f"PT-{index:04d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "dob": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
            "gender": fake.random_element(elements=("F", "M")),
        }
        provider = {
            "npi": str(fake.random_int(1000000000, 9999999999)),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
        }

        line_count = 1 + (index % 3)
        lines: list[dict] = []
        total_cents = 0

        for line_index in range(line_count):
            procedure = PROCEDURES[(index + line_index) % len(PROCEDURES)]
            tooth_number = (
                fake.random_element(elements=(12, 14, 18, 19, 20, 21, 28, 30, 31, 32, 8, 9, 11))
                if fake.boolean(0.8)
                else None
            )
            surface = fake.random_element(elements=SURFACES) if fake.boolean(0.7) else None
            charge_cents = fake.random_int(8500, 28500)
            total_cents += charge_cents
            lines.append(
                {
                    "procedure_code": procedure,
                    "tooth_number": tooth_number,
                    "surface": surface,
                    "charge_amount": money_string(charge_cents),
                }
            )

        fixtures.append(
            {
                "claim_id": f"CLM-{index:03d}",
                "status": "draft",
                "patient": patient,
                "provider": provider,
                "service_date_from": fake.date_between(start_date="-365d", end_date="+30d").isoformat(),
                "service_date_to": fake.date_between(start_date="-30d", end_date="+90d").isoformat(),
                "total_amount": money_string(total_cents),
                "line_items": lines,
            }
        )

    return fixtures


def test_golden_corpus_snapshot() -> None:
    assert len(build_golden_corpus()) == 25
    fixture_snapshot = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert build_golden_corpus() == fixture_snapshot
