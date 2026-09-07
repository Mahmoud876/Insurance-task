from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database_session import get_db
from app.modules.analytics.schemas import (
    AnalyticsSummaryResponse,
    PayerPerformanceMetrics,
    PayerPerformanceResponse,
    StatusFunnelResponse,
    TopFindingMetrics,
    TopFindingsResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get aggregated summary metrics over a date range",
)
def get_analytics_summary(
    tenant_id: UUID,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """Hits claim_daily_metrics rollup table strictly without scanning claim raw rows."""
    query = text("""
        SELECT
            COALESCE(SUM(claims_created), 0) AS total_created,
            COALESCE(SUM(claims_submitted), 0) AS total_submitted,
            COALESCE(SUM(claims_clean_first_pass), 0) AS total_clean_pass,
            COALESCE(SUM(claims_denied), 0) AS total_denied,
            COALESCE(SUM(total_billed), 0.00) AS total_billed,
            AVG(avg_readiness_score) AS avg_score
        FROM claim_daily_metrics
        WHERE tenant_id = :tenant_id
          AND metric_date BETWEEN :start_date AND :end_date
    """)

    res = db.execute(
        query,
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    ).fetchone()
    if res is None:
        raise RuntimeError("Analytics summary query returned no row")

    total_created = res.total_created or 0
    total_submitted = res.total_submitted or 0
    total_clean = res.total_clean_pass or 0

    clean_rate = (total_clean / total_created * 100.0) if total_created > 0 else 0.0
    avg_score = float(res.avg_score) if res.avg_score is not None else 0.0

    return AnalyticsSummaryResponse(
        start_date=start_date,
        end_date=end_date,
        total_created=total_created,
        total_submitted=total_submitted,
        total_clean_first_pass=total_clean,
        total_denied=res.total_denied or 0,
        total_billed_amount=Decimal(str(res.total_billed or 0.00)),
        first_pass_clean_rate=round(clean_rate, 2),
        average_readiness_score=round(avg_score, 2),
    )


@router.get(
    "/status-funnel",
    response_model=StatusFunnelResponse,
    summary="Get lifecycle status funnel metrics",
)
def get_status_funnel(
    tenant_id: UUID,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> StatusFunnelResponse:
    """Aggregates claim funnel counts purely from claim_daily_metrics rollup."""
    query = text("""
        SELECT
            COALESCE(SUM(claims_created), 0) AS created,
            COALESCE(SUM(claims_clean_first_pass), 0) AS clean_pass,
            COALESCE(SUM(claims_submitted), 0) AS submitted,
            COALESCE(SUM(claims_denied), 0) AS denied
        FROM claim_daily_metrics
        WHERE tenant_id = :tenant_id
          AND metric_date BETWEEN :start_date AND :end_date
    """)
    res = db.execute(
        query,
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    ).fetchone()
    if res is None:
        raise RuntimeError("Status funnel query returned no row")

    created = res.created or 0
    submitted = res.submitted or 0
    clean = res.clean_pass or 0

    return StatusFunnelResponse(
        created=created,
        scrubbed=created,  # Auto-scrubbed upon snapshot insertion
        ready=clean,
        submitted=submitted,
        denied=res.denied or 0,
    )


@router.get(
    "/top-findings",
    response_model=TopFindingsResponse,
    summary="Get most frequent rule violation findings",
)
def get_top_findings(
    tenant_id: UUID,
    limit: int = Query(default=10, le=50),
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> TopFindingsResponse:
    """Queries scrub_run findings JSONB via GIN index (`idx_scrub_findings_gin`) without scanning claims."""
    query = text("""
        WITH expanded_findings AS (
            SELECT
                sr.claim_id,
                finding->>'rule_id' AS rule_id,
                finding->>'message_key' AS message_key
            FROM scrub_run sr,
                 jsonb_array_elements(sr.findings) AS finding
            WHERE sr.tenant_id = :tenant_id
              AND DATE(sr.created_at) BETWEEN :start_date AND :end_date
        )
        SELECT
            rule_id,
            message_key,
            COUNT(*) AS occurrences,
            COUNT(DISTINCT claim_id) AS affected_claims
        FROM expanded_findings
        GROUP BY rule_id, message_key
        ORDER BY occurrences DESC
        LIMIT :limit
    """)

    rows = db.execute(
        query,
        {
            "tenant_id": tenant_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        },
    ).fetchall()

    findings_list = [
        TopFindingMetrics(
            rule_code=r.rule_id,
            message_key=r.message_key or "DCS-ERR-UNKNOWN",
            occurrences=r.occurrences,
            affected_claims=r.affected_claims,
            impact_percentage=0.0,
        )
        for r in rows
    ]

    return TopFindingsResponse(period_start=start_date, period_end=end_date, findings=findings_list)


@router.get(
    "/payer-performance",
    response_model=PayerPerformanceResponse,
    summary="Get breakdown of claim performance grouped by payer",
)
def get_payer_performance(
    tenant_id: UUID,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> PayerPerformanceResponse:
    """Breaks down performance by joining claim_daily_metrics rollup to payer reference table."""
    query = text("""
        SELECT
            m.payer_id,
            COALESCE(p.name, 'Unassigned / Direct') AS payer_name,
            SUM(m.claims_submitted) AS claims_submitted,
            SUM(m.claims_created) AS claims_created,
            SUM(m.claims_clean_first_pass) AS claims_clean_first_pass,
            SUM(m.claims_denied) AS claims_denied,
            SUM(m.total_billed) AS total_billed,
            AVG(m.avg_readiness_score) AS avg_score
        FROM claim_daily_metrics m
        LEFT JOIN payer p ON m.payer_id = p.id
        WHERE m.tenant_id = :tenant_id
          AND m.metric_date BETWEEN :start_date AND :end_date
        GROUP BY m.payer_id, p.name
        ORDER BY total_billed DESC
    """)

    rows = db.execute(
        query,
        {"tenant_id": tenant_id, "start_date": start_date, "end_date": end_date},
    ).fetchall()

    payers = []
    for r in rows:
        created = r.claims_created or 0
        submitted = r.claims_submitted or 0
        clean_pass = (r.claims_clean_first_pass / created * 100.0) if created > 0 else 0.0
        denial_rate = (r.claims_denied / submitted * 100.0) if submitted > 0 else 0.0

        payers.append(
            PayerPerformanceMetrics(
                payer_id=r.payer_id,
                payer_name=r.payer_name,
                claims_submitted=submitted,
                clean_pass_rate=round(clean_pass, 2),
                denial_rate=round(denial_rate, 2),
                total_billed=Decimal(str(r.total_billed or 0.00)),
                avg_readiness_score=round(float(r.avg_score or 0.0), 2),
            )
        )

    return PayerPerformanceResponse(period_start=start_date, period_end=end_date, payers=payers)
