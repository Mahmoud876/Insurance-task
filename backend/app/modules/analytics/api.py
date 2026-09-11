from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security.auth import AuthContext
from app.deps import get_current_auth_context, get_db
from app.modules.analytics.schemas import (
    AnalyticsSummaryResponse,
    PayerPerformanceMetrics,
    PayerPerformanceResponse,
    StatusFunnelResponse,
    TopFindingMetrics,
    TopFindingsResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])


def _period_query() -> dict[str, date]:
    end_date = date.today()
    return {"start_date": end_date - timedelta(days=30), "end_date": end_date}


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> AnalyticsSummaryResponse:
    period = _period_query()
    start_date = start_date or period["start_date"]
    end_date = end_date or period["end_date"]
    row = db.execute(
        text(
            """
            SELECT COALESCE(SUM(total_claims), 0) AS total_created,
                   COALESCE(SUM(passed_claims), 0) AS total_clean,
                   COALESCE(SUM(flagged_claims), 0) AS total_denied,
                   COALESCE(SUM(total_value_cents), 0) AS total_value,
                   COALESCE(SUM(passed_claims)::numeric / NULLIF(SUM(total_claims), 0) * 100, 0) AS clean_rate
            FROM claim_daily_metrics
            WHERE tenant_id = :tenant_id AND date BETWEEN :start_date AND :end_date
            """
        ),
        {"tenant_id": str(auth_ctx.tenant_id), "start_date": start_date, "end_date": end_date},
    ).one()
    return AnalyticsSummaryResponse(
        start_date=start_date,
        end_date=end_date,
        total_created=int(row.total_created),
        total_submitted=0,
        total_clean_first_pass=int(row.total_clean),
        total_denied=int(row.total_denied),
        total_billed_amount=Decimal(row.total_value) / Decimal(100),
        first_pass_clean_rate=float(row.clean_rate),
        average_readiness_score=0.0,
    )


@router.get("/status-funnel", response_model=StatusFunnelResponse)
def get_status_funnel(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> StatusFunnelResponse:
    period = _period_query()
    start_date = start_date or period["start_date"]
    end_date = end_date or period["end_date"]
    row = db.execute(
        text(
            """
            SELECT COALESCE(SUM(total_claims), 0) AS created,
                   COALESCE(SUM(passed_claims), 0) AS ready,
                   COALESCE(SUM(flagged_claims), 0) AS denied
            FROM claim_daily_metrics
            WHERE tenant_id = :tenant_id AND date BETWEEN :start_date AND :end_date
            """
        ),
        {"tenant_id": str(auth_ctx.tenant_id), "start_date": start_date, "end_date": end_date},
    ).one()
    return StatusFunnelResponse(
        created=int(row.created),
        scrubbed=int(row.created),
        ready=int(row.ready),
        submitted=0,
        denied=int(row.denied),
    )


@router.get("/top-findings", response_model=TopFindingsResponse)
def get_top_findings(
    limit: int = Query(default=10, ge=1, le=50),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> TopFindingsResponse:
    period = _period_query()
    start_date = start_date or period["start_date"]
    end_date = end_date or period["end_date"]
    rows = db.execute(
        text(
            """
            SELECT finding->>'rule_id' AS rule_id,
                   finding->>'message_key' AS message_key,
                   COUNT(*) AS occurrences
            FROM claim_daily_metrics m,
                 LATERAL jsonb_array_elements(COALESCE(m.metrics_payload::jsonb->'findings', '[]'::jsonb)) finding
            WHERE m.tenant_id = :tenant_id AND m.date BETWEEN :start_date AND :end_date
            GROUP BY finding->>'rule_id', finding->>'message_key'
            ORDER BY occurrences DESC
            LIMIT :limit
            """
        ),
        {
            "tenant_id": str(auth_ctx.tenant_id),
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        },
    ).all()
    findings = [
        TopFindingMetrics(
            rule_code=row.rule_id or "unknown",
            message_key=row.message_key or "DCS-ERR-UNKNOWN",
            occurrences=int(row.occurrences),
            affected_claims=int(row.occurrences),
            impact_percentage=0.0,
        )
        for row in rows
    ]
    return TopFindingsResponse(period_start=start_date, period_end=end_date, findings=findings)


@router.get("/payer-performance", response_model=PayerPerformanceResponse)
def get_payer_performance(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> PayerPerformanceResponse:
    period = _period_query()
    start_date = start_date or period["start_date"]
    end_date = end_date or period["end_date"]
    rows = (
        db.execute(
            text(
                """
            SELECT payer
            FROM claim_daily_metrics m,
                 LATERAL jsonb_array_elements(COALESCE(m.metrics_payload::jsonb->'payers', '[]'::jsonb)) payer
            WHERE m.tenant_id = :tenant_id AND m.date BETWEEN :start_date AND :end_date
            """
            ),
            {"tenant_id": str(auth_ctx.tenant_id), "start_date": start_date, "end_date": end_date},
        )
        .scalars()
        .all()
    )
    totals: dict[str, dict[str, Any]] = {}
    for payer in rows:
        payer_id = str(payer.get("payer_id", "unassigned"))
        item = totals.setdefault(
            payer_id,
            {
                "submitted": 0,
                "created": 0,
                "clean": 0,
                "denied": 0,
                "billed": Decimal(0),
                "score": 0.0,
            },
        )
        item["submitted"] += int(payer.get("claims_submitted", 0))
        item["created"] += int(payer.get("claims_created", 0))
        item["clean"] += int(payer.get("claims_clean_first_pass", 0))
        item["denied"] += int(payer.get("claims_denied", 0))
        item["billed"] += Decimal(str(payer.get("total_billed", 0)))
        item["score"] += float(payer.get("avg_score", 0))
    payers = [
        PayerPerformanceMetrics(
            payer_id=None if payer_id == "unassigned" else UUID(payer_id),
            payer_name="Unassigned / Direct" if payer_id == "unassigned" else payer_id,
            claims_submitted=item["submitted"],
            clean_pass_rate=round(item["clean"] / item["created"] * 100, 2)
            if item["created"]
            else 0.0,
            denial_rate=round(item["denied"] / item["submitted"] * 100, 2)
            if item["submitted"]
            else 0.0,
            total_billed=item["billed"],
            avg_readiness_score=round(item["score"], 2),
        )
        for payer_id, item in totals.items()
    ]
    return PayerPerformanceResponse(period_start=start_date, period_end=end_date, payers=payers)
