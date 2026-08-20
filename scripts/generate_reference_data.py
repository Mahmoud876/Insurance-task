import csv
from datetime import date
from pathlib import Path


OUTPUT = Path("data/procedure_codes.csv")


def generate_procedures():
    categories = [
        "diagnostic",
        "preventive",
        "restorative",
        "endo",
        "perio",
        "prostho_removable",
        "prostho_fixed",
        "oral_surgery",
        "ortho",
        "adjunctive",
    ]

    documentation = [
        "clinical_exam",
        "periapical_xray",
        "bitewing_xray",
        "narrative",
    ]

    rows = []

    for i in range(1, 201):
        code = f"D{i:04d}"

        requires_tooth = i % 2 == 0
        requires_surface = i % 3 == 0
        requires_quadrant = i % 5 == 0
        requires_arch = i % 7 == 0

        posterior = i % 4 == 0
        anterior = i % 11 == 0

        # Never allow both to be true.
        if posterior and anterior:
            anterior = False

        primary = i % 13 == 0

        surfaces = ""
        if requires_surface:
            surfaces = "O,B,L"

        rows.append(
            {
                "code": code,
                "code_system": "LOCAL",
                "short_desc": f"Synthetic dental procedure {i}",
                "category": categories[(i - 1) % len(categories)],
                "requires_tooth": str(requires_tooth).lower(),
                "requires_surface": str(requires_surface).lower(),
                "requires_quadrant": str(requires_quadrant).lower(),
                "requires_arch": str(requires_arch).lower(),
                "allowed_surfaces": surfaces,
                "is_posterior_only": str(posterior).lower(),
                "is_anterior_only": str(anterior).lower(),
                "is_primary_dentition_only": str(primary).lower(),
                "typical_documentation": documentation[
                    (i - 1) % len(documentation)
                ],
                "valid_from": "2026-01-01",
                "valid_to": "",
            }
        )

    return rows


def main():
    rows = generate_procedures()

    fieldnames = [
        "code",
        "code_system",
        "short_desc",
        "category",
        "requires_tooth",

        "requires_surface",
        "requires_quadrant",
        "requires_arch",
        "allowed_surfaces",
        "is_posterior_only",
        "is_anterior_only",
        "is_primary_dentition_only",
        "typical_documentation",
        "valid_from",
        "valid_to",
    ]

    with OUTPUT.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} procedure codes.")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()


















