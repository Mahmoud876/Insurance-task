import csv
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(tags=["reference"])

BASE_DIR = Path(__file__).resolve().parents[3]
PROCEDURE_CODES_PATH = BASE_DIR / "data" / "procedure_codes.csv"


def load_procedure_codes() -> list[dict[str, object]]:
    with PROCEDURE_CODES_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows: list[dict[str, object]] = []

        for row in reader:
            rows.append(
                {
                    "code": row["code"],
                    "category": row["category"],
                    "short_desc": row["short_desc"],
                    "requires_tooth": row["requires_tooth"].lower() == "true",
                    "requires_surface": row["requires_surface"].lower() == "true",
                    "requires_quadrant": row["requires_quadrant"].lower() == "true",
                    "requires_arch": row["requires_arch"].lower() == "true",
                }
            )

        return rows


@router.get("/reference/procedure-codes")
def list_procedure_codes(
    q: str = Query(default="", alias="query"),
    limit: int = Query(default=10, ge=1, le=25),
) -> list[dict[str, object]]:
    rows = load_procedure_codes()
    search = q.strip().lower()

    if search:
        rows = [
            row
            for row in rows
            if (
                search in str(row["code"]).lower()
                or search in str(row["short_desc"]).lower()
                or search in str(row["category"]).lower()
            )
        ]

    return rows[:limit]
