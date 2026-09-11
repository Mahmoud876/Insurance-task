import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_claim_daily_metrics_rollup(db: Session, target_date: date | None = None) -> int:
    """Aggregate claims into the existing claim_daily_metrics rollup table."""
    target_date = target_date or (datetime.now(UTC) - timedelta(days=1)).date()
    query = text(
        """
        WITH daily AS (
            SELECT c.tenant_id::text AS tenant_id, CAST(:target_date AS date) AS metric_date,
                   COUNT(*) AS total_claims,
                   COUNT(*) FILTER (WHERE c.readiness_score = 100) AS passed_claims,
                   COUNT(*) FILTER (WHERE c.readiness_score < 100) AS flagged_claims,
                   COALESCE(SUM(ROUND(c.total_amount * 100)), 0)::bigint AS total_value_cents
            FROM claim c
            WHERE DATE(c.created_at) = :target_date
            GROUP BY c.tenant_id
        )
        INSERT INTO claim_daily_metrics (
            id, date, tenant_id, total_claims, passed_claims, flagged_claims,
            autofixed_claims, total_value_cents, metrics_payload
        )
        SELECT :metric_id, d.metric_date, d.tenant_id, d.total_claims,
               d.passed_claims, d.flagged_claims, 0, d.total_value_cents,
               jsonb_build_object(
                   'findings', COALESCE((
                       SELECT jsonb_agg(finding)
                       FROM claim c2,
                       LATERAL jsonb_array_elements(
                           COALESCE(c2.findings_summary::jsonb, '[]'::jsonb)
                       ) finding
                       WHERE c2.tenant_id::text = d.tenant_id
                         AND DATE(c2.created_at) = d.metric_date
                   ), '[]'::jsonb),
                   'payers', COALESCE((
                       SELECT jsonb_agg(payer_stats)
                       FROM (
                           SELECT jsonb_build_object(
                               'payer_id', COALESCE(c3.payer_id::text, 'unassigned'),
                               'claims_submitted', COUNT(*) FILTER (WHERE c3.status = 'SUBMITTED'),
                               'claims_created', COUNT(*),
                               'claims_clean_first_pass', COUNT(*) FILTER (WHERE c3.readiness_score = 100),
                               'claims_denied', COUNT(*) FILTER (WHERE c3.status = 'REJECTED'),
                               'total_billed', COALESCE(SUM(c3.total_amount), 0),
                               'avg_score', COALESCE(AVG(c3.readiness_score), 0)
                           ) AS payer_stats
                           FROM claim c3
                           WHERE c3.tenant_id::text = d.tenant_id
                             AND DATE(c3.created_at) = d.metric_date
                           GROUP BY c3.payer_id
                       ) payer_rows
                   ), '[]'::jsonb)
               )
        FROM daily d
        ON CONFLICT (date, tenant_id) DO UPDATE SET
            total_claims = EXCLUDED.total_claims,
            passed_claims = EXCLUDED.passed_claims,
            flagged_claims = EXCLUDED.flagged_claims,
            autofixed_claims = EXCLUDED.autofixed_claims,
            total_value_cents = EXCLUDED.total_value_cents,
            metrics_payload = EXCLUDED.metrics_payload;
        """
    )
    result = cast(
        CursorResult[Any],
        db.execute(query, {"target_date": target_date, "metric_id": str(uuid4())}),
    )
    db.commit()
    logger.info("Updated claim_daily_metrics for %s: %s rows", target_date, result.rowcount)
    return result.rowcount


async def arq_claim_daily_rollup_task(
    ctx: dict[str, Any], target_date_str: str | None = None
) -> None:
    """ARQ-compatible nightly rollup entrypoint."""
    from app.core.database_session import SessionLocal

    db: Session = SessionLocal()
    try:
        target_date = date.fromisoformat(target_date_str) if target_date_str else None
        run_claim_daily_metrics_rollup(db, target_date)
    finally:
        db.close()
