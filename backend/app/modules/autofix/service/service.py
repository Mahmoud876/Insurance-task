import copy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.audit import AuditEvent
from app.modules.autofix.engine import apply_transform
from app.modules.autofix.schemas import (
    FORBIDDEN_AUTOFIX_FIELDS,
    ApplyAutofixRequest,
    ApplyAutofixResponse,
    AutofixAuditEvent,
    AutofixProposal,
)


def _get_leaf_field(path: str) -> str:
    """Extract leaf field name from dot or array path ('lines[0].service_date' -> 'service_date')."""
    return path.split(".")[-1].split("[")[0].lower()


def _get_nested_value(data: dict[str, Any], path: str) -> Any:
    """Retrieve value at a given path (supports basic dot and index notation)"""
    parts = path.replace("]", "").split(".")
    curr = data

    for part in parts:
        if "[" in part:
            key, idx_str = part.split("[")
            curr = curr[key][int(idx_str)]
        else:
            curr = curr[part]
    return curr


def _set_nested_value(data: dict[str, Any], path: str, value: Any) -> Any:
    """Mutate a dictionary value at a given path (supports basic dot and index notation)"""
    parts = path.replace("]", "").split(".")
    curr = data

    for part in parts[:-1]:
        if "[" in part:
            key, idx_str = part.split("[")
            curr = curr[key][int(idx_str)]
        else:
            curr = curr[part]

    last_part = parts[-1]
    if "[" in last_part:
        key, idx_str = last_part.split("[")
        old_val = curr[key][int(idx_str)]
        curr[key][int(idx_str)] = value
        return old_val
    else:
        old_val = curr.get(last_part)
        curr[last_part] = value
        return old_val


class AutofixService:
    def __init__(self, db: Session, tenant_id: Any):
        self.db = db
        self.tenant_id = tenant_id

    def apply_autofixes(
        self,
        claim_id: str,
        claim_payload: dict[str, Any],
        active_proposals: list[AutofixProposal],
        request: ApplyAutofixRequest,
        actor_id: str = "system",
    ) -> ApplyAutofixResponse:
        """Apply selected proposals to claim payload, record audit logs, and return updated state"""
        proposal_map = {p.id: p for p in active_proposals}
        audit_events: list[AutofixAuditEvent] = []
        updated_claim = copy.deepcopy(claim_payload)

        for proposal_id in request.selected_proposal_ids:
            proposal = proposal_map.get(proposal_id)
            if not proposal:
                continue

            # Verify target field isn't forbidden
            leaf_field = _get_leaf_field(proposal.target_field)
            if leaf_field in FORBIDDEN_AUTOFIX_FIELDS:
                raise ValueError(f"Forbidden operation: field '{leaf_field}' cannot be autofixed.")

            # Get current raw value from payload (fallback to proposal original value)
            try:
                current_raw_val = _get_nested_value(updated_claim, proposal.target_field)
            except (KeyError, IndexError, TypeError):
                current_raw_val = proposal.original_value

            # Compute transformed value using raw input
            new_val = apply_transform(proposal, current_raw_val)

            # Apply updated value to payload and extract previous value
            old_val = _set_nested_value(updated_claim, proposal.target_field, new_val)

            # Construct audit event schema
            audit_event_schema = AutofixAuditEvent(
                id=str(uuid4()),
                claim_id=claim_id,
                transform_type=proposal.transform_type,
                target_field=proposal.target_field,
                old_value=old_val,
                new_value=new_val,
                applied_by=actor_id,
                applied_at=datetime.now(UTC),
            )
            audit_events.append(audit_event_schema)

        # Persist audit events to database if any were generated
        if audit_events:
            db_audit_records = [
                AuditEvent(
                    id=uuid4(),
                    tenant_id=self.tenant_id,
                    action=f"autofix:{event.transform_type}",
                    resource_type="claim",
                    resource_id=event.claim_id,
                    payload={
                        "target_field": event.target_field,
                        "old_value": event.old_value,
                        "new_value": event.new_value,
                        "applied_by": event.applied_by,
                    },
                )
                for event in audit_events
            ]
            self.db.add_all(db_audit_records)
            self.db.commit()

        return ApplyAutofixResponse(
            claim_id=claim_id,
            applied_count=len(audit_events),
            audit_events=audit_events,
            updated_claim=updated_claim,
        )
