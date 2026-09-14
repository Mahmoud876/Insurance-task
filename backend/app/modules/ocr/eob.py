"""EOB (Explanation of Benefits) OCR text parsing and patient-history import.

The attached primary EOB is OCR'd at upload time; this module turns the
recognized line text into structured procedure entries and writes them as
``PatientProcedureHistory`` rows (source=EOB_IMPORT) so the scrub pipeline's
frequency/coverage rules see prior utilization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.claims.models.patient_procedure_history import (
    PatientProcedureHistory,
    ProcedureHistorySource,
)
from app.modules.ocr.engine import OcrLine

_CDT_CODE_RE = re.compile(r"\b(D\d{4})\b", re.IGNORECASE)
_DATE_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
_DATE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_AMOUNT_RE = re.compile(r"\d+\.\d{2}")
_TOTAL_RE = re.compile(
    r"total\s+(?:allowed|amount|benefit)\s*[:#]?\s*\$?\s*(\d+\.\d{2})", re.IGNORECASE
)
_MEMBER_ID_RE = re.compile(
    r"(?:member\s*(?:id|number|no\.?)|member\s*#)\s*[:#]?[\s\-]*([A-Z0-9][A-Z0-9\-]{3,})",
    re.IGNORECASE,
)

_PAYER_NAME_SKIP_RE = re.compile(
    r"(?:www\.|http|1[\s.\-]?800|member|subscriber|group|plan|policy|prepaid|"
    r"provider|npi|date|total|paid|allowed|claim|patient|service|est\.?|balance|"
    r"deductible|co.?insurance|payable|rendered|rendering|tel\.?|phone|address)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EobProcedure:
    procedure_code: str
    service_date: date | None = None
    allowed_amount: float | None = None
    raw_line: str = ""


@dataclass(frozen=True)
class EobExtract:
    payer_name: str = ""
    member_id: str = ""
    service_date_from: date | None = None
    service_date_to: date | None = None
    total_allowed: float | None = None
    procedure_entries: tuple[EobProcedure, ...] = ()

    @property
    def has_entries(self) -> bool:
        return bool(self.procedure_entries)


def _parse_date(text: str) -> date | None:
    match = _DATE_SLASH_RE.search(text)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None

    match = _DATE_ISO_RE.search(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    return None


def _extract_payer_name(texts: list[str]) -> str:
    for raw in texts:
        line = raw.strip(": -\t")
        if not line:
            continue
        if _CDT_CODE_RE.search(line) or _parse_date(line) is not None:
            continue
        if _PAYER_NAME_SKIP_RE.search(line):
            continue
        letters = sum(char.isalpha() for char in line)
        if len(line) >= 4 and letters / max(len(line), 1) > 0.6 and len(line) <= 40:
            return line
    return ""


def parse_eob_text(lines: list[OcrLine]) -> EobExtract:
    """Extracts payer header info and procedure entries from OCR'd EOB lines.

    CDT procedure codes are matched per line; each code is associated with the
    most recent date seen earlier in the document (falling back to the earliest
    document date). Non-EOB content produces an empty extract.
    """
    ordered = sorted(
        (line for line in lines if line.text.strip()), key=lambda line: (line.y0, line.text.lower())
    )
    texts = [re.sub(r"\s+", " ", line.text).strip() for line in ordered]
    joined = "\n".join(texts)

    dates = [value for text in texts if (value := _parse_date(text)) is not None]
    service_date_from = min(dates) if dates else None
    service_date_to = max(dates) if dates else None

    total_match = _TOTAL_RE.search(joined)
    total_allowed = float(total_match.group(1)) if total_match else None

    entries: list[EobProcedure] = []
    last_date = None

    for text in texts:
        parsed_date = _parse_date(text)
        if parsed_date is not None:
            last_date = parsed_date

        codes = _CDT_CODE_RE.findall(text)
        if not codes:
            continue

        amounts = [float(value) for value in _AMOUNT_RE.findall(text)]
        for code in codes:
            entries.append(
                EobProcedure(
                    procedure_code=code.upper(),
                    service_date=last_date or service_date_from,
                    allowed_amount=amounts[-1] if amounts else None,
                    raw_line=text,
                )
            )

    return EobExtract(
        payer_name=_extract_payer_name(texts),
        member_id=_extract_member_id(joined),
        service_date_from=service_date_from,
        service_date_to=service_date_to,
        total_allowed=total_allowed,
        procedure_entries=tuple(entries),
    )


def _extract_member_id(text: str) -> str:
    match = _MEMBER_ID_RE.search(text)
    return match.group(1).strip() if match else ""


def upsert_eob_history(
    db: Session,
    *,
    tenant_id: UUID,
    patient_id: UUID,
    payer_id: UUID | None,
    extract: EobExtract,
) -> int:
    """Writes EOB procedure entries as patient history rows (idempotent).

    Rows are skipped when an EOB_IMPORT row for the same patient + procedure
    code + service date already exists. Returns the number of rows created.
    """
    if not extract.has_entries:
        return 0

    existing = set(
        db.scalars(
            select(PatientProcedureHistory).where(
                PatientProcedureHistory.tenant_id == tenant_id,
                PatientProcedureHistory.patient_id == patient_id,
                PatientProcedureHistory.source == ProcedureHistorySource.EOB_IMPORT,
            )
        ).all()
    )

    def _key(row: PatientProcedureHistory) -> tuple[str, date]:
        return (row.procedure_code, row.service_date)

    seen = {_key(row) for row in existing}
    created = 0

    for entry in extract.procedure_entries:
        if entry.service_date is None:
            continue
        key = (entry.procedure_code, entry.service_date)
        if key in seen:
            continue
        db.add(
            PatientProcedureHistory(
                tenant_id=tenant_id,
                patient_id=patient_id,
                procedure_code=entry.procedure_code,
                service_date=entry.service_date,
                source=ProcedureHistorySource.EOB_IMPORT,
                payer_id=payer_id,
                notes=entry.raw_line[:500] or None,
            )
        )
        seen.add(key)
        created += 1

    db.flush()
    return created
