from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.autofix.engine import apply_transform
from app.modules.autofix.schemas import (
    ApplyAutofixRequest,
    AutofixProposal,
    SafeTransformType,
)
from app.modules.autofix.service import AutofixService


def proposal(
    transform_type: SafeTransformType, target_field: str, value: object
) -> AutofixProposal:
    return AutofixProposal(
        id=str(uuid4()),
        transform_type=transform_type,
        target_field=target_field,
        original_value=value,
        proposed_value=value,
        reason="test",
    )


@pytest.mark.parametrize(
    ("transform_type", "target_field", "value", "expected"),
    [
        (SafeTransformType.DATE_FORMAT, "service_date_from", "09/07/2026", "2026-09-07"),
        (SafeTransformType.CODE_PADDING, "provider_id", "123", "00123"),
        (SafeTransformType.QUADRANT_DERIVATION, "quadrant", 12, "UL"),
        (SafeTransformType.ARCH_DERIVATION, "arch", "UL", "UA"),
        (SafeTransformType.SURFACE_ALIASES, "surface", "distal mesial", "MD"),
        (
            SafeTransformType.TOTAL_RECOMPUTE,
            "total_amount",
            [{"fee": "10.25"}, {"fee": 4.75}],
            15.0,
        ),
    ],
)
def test_all_safe_transforms(transform_type, target_field, value, expected) -> None:
    assert apply_transform(proposal(transform_type, target_field, value), value) == expected


@pytest.mark.parametrize(
    "target_field", ["procedure_code", "lines[0].tooth_number", "lines[0].fee"]
)
def test_procedure_tooth_and_fee_are_forbidden(target_field: str) -> None:
    with pytest.raises(ValidationError):
        proposal(SafeTransformType.CODE_PADDING, target_field, "D0120")


class RecordingSession:
    def __init__(self) -> None:
        self.records: list[object] = []
        self.committed = False

    def add_all(self, records: list[object]) -> None:
        self.records.extend(records)

    def commit(self) -> None:
        self.committed = True


def test_apply_autofix_persists_audit_event() -> None:
    db = RecordingSession()
    service = AutofixService(cast(Session, db), uuid4())
    fix = proposal(SafeTransformType.DATE_FORMAT, "service_date_from", "09/07/2026")

    response = service.apply_autofixes(
        claim_id="claim-1",
        claim_payload={"service_date_from": "09/07/2026"},
        active_proposals=[fix],
        request=ApplyAutofixRequest(selected_proposal_ids=[fix.id]),
        actor_id="user-1",
    )

    assert response.applied_count == 1
    assert response.updated_claim["service_date_from"] == "2026-09-07"
    assert len(db.records) == 1
    assert db.committed is True
