from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.ocr.engine import OcrLine

_MEMBER_ID_RE = re.compile(
    r"(?:member\s*(?:id|number|no\.?)|member\s*#|id\s*(?:number|no\.?))\s*[:#]?"
    r"[\s\-]*([A-Z0-9][A-Z0-9\-]{4,})",
    re.IGNORECASE,
)

_GROUP_NUMBER_RE = re.compile(
    r"(?:group\s*(?:number|no\.?)|group\s*#)\s*[:#]?[\s\-]*([A-Z0-9][A-Z0-9\-]{2,})",
    re.IGNORECASE,
)

_PAYER_ID_RE = re.compile(
    r"(?:payer|carrier|insurer)\s*(?:id|code)?\s*[:#]?[\s\-]*([A-Z0-9][A-Z0-9_\-]{3,})",
    re.IGNORECASE,
)

_SUBSCRIBER_NAME_RE = re.compile(
    r"(?:subscriber|member|insured)\s+name\s*[:#]?\s*"
    r"([A-Z][A-Za-z']+(?:\s+[A-Z][A-Za-z']+){0,3})",
    re.IGNORECASE,
)

_SUBSCRIBER_NAME_UPPER_RE = re.compile(
    r"(?:subscriber|member|insured)\s+name\s*[:#]?\s*"
    r"([A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})",
    re.IGNORECASE,
)

_PAYER_NAME_SKIP_RE = re.compile(
    r"(?:www\.|http|1[\s.\-]?800|member|subscriber|group|plan\s+name|policy|"
    r"effective|prepaid|claims?|customer|service|tel\.|phone|office|address)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CardOCRResult:
    payer_name: str
    payer_id: str
    member_id: str
    group_number: str
    subscriber_name: str
    confidence_score: float


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    return slug[:50]


def _extract(text: str, pattern: re.Pattern[str]) -> str:
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _extract_payer_name(lines: list[str]) -> str:
    for raw in lines:
        line = raw.strip(": -\t")
        if not line:
            continue
        if _PAYER_NAME_SKIP_RE.search(line):
            continue
        letters = sum(char.isalpha() for char in line)
        if len(line) >= 4 and letters / len(line) > 0.6 and len(line) <= 40:
            return line
    return ""


def parse_insurance_card(lines: list[OcrLine]) -> CardOCRResult:
    ordered = sorted(
        (line for line in lines if line.text.strip()), key=lambda line: (line.y0, line.text.lower())
    )
    texts = [re.sub(r"\s+", " ", line.text).strip() for line in ordered]
    joined = "\n".join(texts)

    payer_name = _extract_payer_name(texts)
    payer_id = _extract(joined, _PAYER_ID_RE)
    if not payer_id and payer_name:
        payer_id = _slugify(payer_name)

    member_id = _extract(joined, _MEMBER_ID_RE)
    group_number = _extract(joined, _GROUP_NUMBER_RE)
    subscriber_name = _extract(joined, _SUBSCRIBER_NAME_RE) or _extract(
        joined, _SUBSCRIBER_NAME_UPPER_RE
    )

    found = sum(
        bool(value) for value in (payer_name, member_id, group_number, subscriber_name, payer_id)
    )
    confidence_score = round(0.5 + (0.49 * found / 5), 2)

    return CardOCRResult(
        payer_name=payer_name,
        payer_id=payer_id,
        member_id=member_id,
        group_number=group_number,
        subscriber_name=subscriber_name,
        confidence_score=confidence_score,
    )
