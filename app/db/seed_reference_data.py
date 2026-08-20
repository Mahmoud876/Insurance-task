
import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# Project root
BASE_DIR = Path(__file__).resolve().parents[2]

PROCEDURE_FILE = BASE_DIR / "data" / "procedure_codes.csv"
DIAGNOSIS_FILE = BASE_DIR / "data" / "diagnosis_codes.csv"
COMPATIBILITY_FILE = (
    BASE_DIR / "data" / "procedure_diagnosis_compat.csv"
)


def get_database_url():
    load_dotenv(BASE_DIR / ".env")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1,
        )

    return database_url


def load_csv(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def seed_procedures(connection):
    rows = load_csv(PROCEDURE_FILE)

    for row in rows:
        connection.execute(
            text(
                """
                INSERT INTO procedure_code (
                    code,
                    code_system,
                    short_desc,
                    category,
                    requires_tooth,
                    requires_surface,
                    requires_quadrant,
                    requires_arch,
                    allowed_surfaces,
                    is_posterior_only,
                    is_anterior_only,
                    is_primary_dentition_only,
                    typical_documentation,
                    valid_from,
                    valid_to
                )
                VALUES (
                    :code,
                    :code_system,
                    :short_desc,
                    :category,
                    :requires_tooth,
                    :requires_surface,
                    :requires_quadrant,
                    :requires_arch,
                    :allowed_surfaces,
                    :is_posterior_only,
                    :is_anterior_only,
                    :is_primary_dentition_only,
                    :typical_documentation,
                    :valid_from,
                    :valid_to
                )
                ON CONFLICT (code) DO UPDATE SET
                    code_system = EXCLUDED.code_system,
                    short_desc = EXCLUDED.short_desc,
                    category = EXCLUDED.category,
                    requires_tooth = EXCLUDED.requires_tooth,
                    requires_surface = EXCLUDED.requires_surface,
                    requires_quadrant = EXCLUDED.requires_quadrant,
                    requires_arch = EXCLUDED.requires_arch,
                    allowed_surfaces = EXCLUDED.allowed_surfaces,
                    is_posterior_only = EXCLUDED.is_posterior_only,
                    is_anterior_only = EXCLUDED.is_anterior_only,
                    is_primary_dentition_only =
                        EXCLUDED.is_primary_dentition_only,
                    typical_documentation =
                        EXCLUDED.typical_documentation,
                    valid_from = EXCLUDED.valid_from,
                    valid_to = EXCLUDED.valid_to
                """
            ),
            {
                **row,
                "requires_tooth": row["requires_tooth"] == "true",
                "requires_surface": row["requires_surface"] == "true",
                "requires_quadrant": row["requires_quadrant"] == "true",
                "requires_arch": row["requires_arch"] == "true",
                "is_posterior_only": row["is_posterior_only"] == "true",
                "is_anterior_only": row["is_anterior_only"] == "true",
                "is_primary_dentition_only":
                    row["is_primary_dentition_only"] == "true",
                "allowed_surfaces": (
                    row["allowed_surfaces"].split(",")
                    if row["allowed_surfaces"]
                    else None
                ),
                "typical_documentation": (
                    [row["typical_documentation"]]
                    if row["typical_documentation"]
                    else None
                ),
                "valid_to": (
                    row["valid_to"] or None
                ),
            },
        )

    print(f"Seeded {len(rows)} procedure codes.")


def seed_diagnoses(connection):
    rows = load_csv(DIAGNOSIS_FILE)

    for row in rows:
        connection.execute(
            text(
                """
                INSERT INTO diagnosis_code (
                    code,
                    code_system,
                    description,
                    is_billable,
                    valid_from,
                    valid_to
                )
                VALUES (
                    :code,
                    :code_system,
                    :description,
                    :is_billable,
                    :valid_from,
                    :valid_to
                )
                ON CONFLICT (code) DO UPDATE SET
                    code_system = EXCLUDED.code_system,
                    description = EXCLUDED.description,
                    is_billable = EXCLUDED.is_billable,
                    valid_from = EXCLUDED.valid_from,
                    valid_to = EXCLUDED.valid_to
                """
            ),
            {
                **row,
                "is_billable": row["is_billable"] == "true",
                "valid_to": row["valid_to"] or None,
            },
        )

    print(f"Seeded {len(rows)} diagnosis codes.")


def seed_compatibility(connection):
    rows = load_csv(COMPATIBILITY_FILE)

    for row in rows:
        connection.execute(
            text(
                """
                INSERT INTO procedure_diagnosis_compat (
                    procedure_code,
                    diagnosis_code,
                    compatibility
                )
                VALUES (
                    :procedure_code,
                    :diagnosis_code,
                    :compatibility
                )
                ON CONFLICT (
                    procedure_code,
                    diagnosis_code
                ) DO UPDATE SET
                    compatibility = EXCLUDED.compatibility
                """
            ),
            row,
        )

    print(f"Seeded {len(rows)} compatibility records.")


def main():
    database_url = get_database_url()

    engine = create_engine(database_url)

    with engine.begin() as connection:
        seed_procedures(connection)
        seed_diagnoses(connection)
        seed_compatibility(connection)

    print("Reference data seeding completed successfully.")


if __name__ == "__main__":
    main()
