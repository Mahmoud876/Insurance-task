import logging
import time
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.core.security.auth import AuthContext
from app.core.security.rbac import Permission
from app.core.telemetry import refresh_claim_gauges
from app.modules.claims.models.claim import Claim, ClaimStatus
from app.modules.claims.schemas.claim import ClaimResponse
from app.modules.claims.service.claim_loader import load_claim_snapshot, load_reference_data
from app.modules.claims.service.claim_service import ClaimService
from app.modules.rules.hashing import compute_input_hash
from app.modules.rules.pipeline import scrub
from app.modules.rules.pipeline_types import (
    ClaimSnapshot,
    ReferenceData,
    ScrubResult,
)
from app.modules.rules.resolver import ResolvedRuleSet
from app.modules.scrubber.models.scrub_run import ScrubRun
from app.modules.scrubber.service.ruleset import resolve_ruleset_for_claim

logger = logging.getLogger(__name__)

SCRUB_ENGINE_VERSION = "dcs-v1"


def execute_and_persist_scrub(db: Session, claim_id: UUID, auth_ctx: AuthContext) -> ClaimResponse:
    """Runs the full scrub pipeline for a claim and persists the result.

    The endpoint keeps ClaimService.scrub_claim untouched for backwards
    compatibility with legacy tests; this service is the real production path.
    """
    ClaimService._verify_permission(auth_ctx, Permission.CLAIM_SCRUB)

    claim = db.scalar(
        select(Claim)
        .options(joinedload(Claim.patient), joinedload(Claim.lines))
        .where(Claim.id == claim_id, Claim.tenant_id == auth_ctx.tenant_id)
    )
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status not in (ClaimStatus.DRAFT, ClaimStatus.SCRUBBED):
        raise HTTPException(
            status_code=400, detail=f"Cannot scrub claim in status '{claim.status}'"
        )

    snapshot = load_claim_snapshot(db, claim)
    reference = load_reference_data(db, claim)
    ruleset = resolve_ruleset_for_claim(db, claim)

    start_time = time.perf_counter()
    result = scrub(snapshot, ruleset, reference)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    finding_payloads = [finding.model_dump(mode="json") for finding in result.findings]

    claim.status = ClaimStatus.SCRUBBED
    claim.readiness_score = result.readiness_score
    claim.findings_summary = finding_payloads
    db.add(claim)

    _upsert_scrub_run(db, claim, snapshot, reference, ruleset, result, duration_ms)

    db.commit()

    db.refresh(claim)
    refresh_claim_gauges(db)
    logger.info(
        "Scrubbed claim %s score=%s status=%s findings=%s duration_ms=%.2f",
        claim.claim_number,
        result.readiness_score,
        result.status,
        len(result.findings),
        duration_ms,
    )
    return ClaimResponse.model_validate(claim)


def _upsert_scrub_run(
    db: Session,
    claim: Claim,
    snapshot: ClaimSnapshot,
    reference: ReferenceData,
    ruleset: ResolvedRuleSet,
    result: ScrubResult,
    duration_ms: float,
) -> None:
    input_hash = compute_input_hash(snapshot, ruleset, reference)
    run_status = "ready" if result.status == "CLEAN" else "needs_review"

    values = {
        "claim_id": claim.id,
        "engine_version": SCRUB_ENGINE_VERSION,
        "input_hash": input_hash,
        "readiness_score": result.readiness_score,
        "status": run_status,
        "snapshot": snapshot.model_dump(mode="json"),
        "findings": [finding.model_dump(mode="json") for finding in result.findings],
        "ruleset_versions": ruleset.pinned_version_ids,
        "duration_ms": duration_ms,
        "is_truncated": result.is_truncated,
    }

    excluded = pg_insert(ScrubRun).excluded
    statement = (
        pg_insert(ScrubRun)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[
                ScrubRun.claim_id,
                ScrubRun.input_hash,
                ScrubRun.engine_version,
            ],
            set_={
                field: getattr(excluded, field)
                for field in (
                    "engine_version",
                    "input_hash",
                    "readiness_score",
                    "status",
                    "snapshot",
                    "findings",
                    "ruleset_versions",
                    "duration_ms",
                    "is_truncated",
                )
            },
        )
    )
    db.execute(statement)
