from app.main import app
from app.modules.analytics.analytics import ClaimDailyMetrics


def test_analytics_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/analytics/summary" in paths
    assert "/api/v1/analytics/status-funnel" in paths
    assert "/api/v1/analytics/top-findings" in paths
    assert "/api/v1/analytics/payer-performance" in paths


def test_claim_daily_metrics_matches_rollup_contract() -> None:
    columns = set(ClaimDailyMetrics.__table__.columns.keys())
    assert {
        "id",
        "date",
        "tenant_id",
        "total_claims",
        "passed_claims",
        "flagged_claims",
        "autofixed_claims",
        "total_value_cents",
        "metrics_payload",
    } <= columns
