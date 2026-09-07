import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_claim_daily_metrics_rollup(db: Session, target_date: date | None = None) -> int:
    """Aggregates claim activity into claim_daily_metrics table for a target date.

    Employs an INSERT ... ON CONFLICT DO UPDATE upsert to guarantee idempotency
    and support both nightly ARQ cron runs and real-time/incremental refreshes.
    Queries strictly aggregate tables/indices without full-table scans.
    """
    if target_date is None:
        target_date = (datetime.now(UTC) - timedelta(days=1)).date()

    upsert_query = text("""
        INSERT INTO claim_daily_metrics (
            tenant_id,
            metric_date,
            payer_id,
            claims_created,
            claims_submitted,
            claims_clean_first_pass,
            claims_denied,
            total_billed,
            avg_readiness_score
        )
        SELECT
            c.tenant_id,
            :target_date AS metric_date,
            pol.payer_id,
            COUNT(DISTINCT c.id) FILTER (WHERE DATE(c.created_at) = :target_date) AS claims_created,
            COUNT(DISTINCT c.id) FILTER (WHERE DATE(c.submitted_at) = :target_date) AS claims_submitted,
            COUNT(DISTINCT c.id) FILTER (
                WHERE DATE(c.created_at) = :target_date AND sr.readiness_score = 100
            ) AS claims_clean_first_pass,
            COUNT(DISTINCT c.id) FILTER (
                WHERE c.status = 'denied' AND DATE(c.updated_at) = :target_date
            ) AS claims_denied,
            COALESCE(SUM(c.total_fee) FILTER (WHERE DATE(c.created_at) = :target_date), 0.00) AS total_billed,
            ROUND(AVG(sr.readiness_score) FILTER (WHERE DATE(sr.created_at) = :target_date), 2) AS avg_readiness_score
        FROM claim c
        JOIN insurance_policy pol ON c.policy_id = pol.id
        LEFT JOIN scrub_run sr ON c.latest_scrub_run_id = sr.id
        WHERE DATE(c.created_at) = :target_date
           OR DATE(c.submitted_at) = :target_date
           OR DATE(c.updated_at) = :target_date
        GROUP BY c.tenant_id, pol.payer_id

        ON CONFLICT (tenant_id, metric_date, payer_id) DO UPDATE SET
            claims_created = EXCLUDED.claims_created,
            claims_submitted = EXCLUDED.claims_submitted,
            claims_clean_first_pass = EXCLUDED.claims_clean_first_pass,
            claims_denied = EXCLUDED.claims_denied,
            total_billed = EXCLUDED.total_billed,
            avg_readiness_score = EXCLUDED.avg_readiness_score;
    """)

    result = cast(CursorResult[Any], db.execute(upsert_query, {"target_date": target_date}))
    db.commit()
    logger.info(
        f"Successfully executed claim_daily_metrics rollup for {target_date}. Rows affected: {result.rowcount}"
    )
    return result.rowcount


# ARQ Worker Task Entrypoint
async def arq_claim_daily_rollup_task(
    ctx: dict[str, Any], target_date_str: str | None = None
) -> None:
    """ARQ background worker task."""
    from app.core.database_session import SessionLocal

    target_date = date.fromisoformat(target_date_str) if target_date_str else None
    db: Session = SessionLocal()
    try:
        run_claim_daily_metrics_rollup(db, target_date)
    finally:
        db.close()
