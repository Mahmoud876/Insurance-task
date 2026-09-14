import json
import logging

from app.core.logging_config import StructuredPHIRedactorFormatter
from app.core.telemetry import (
    DCS_RULE_ERRORS_TOTAL,
    DCS_RULE_HITS_TOTAL,
    DCS_SCRUB_DURATION_SECONDS,
)


def test_phi_redaction_and_structured_json():
    """Verifies PHI patterns (DOB, SSN) are masked and required 8 fields exist."""
    formatter = StructuredPHIRedactorFormatter(
        "%(timestamp)s %(level)s %(message)s %(request_id)s %(tenant_id)s %(user_id)s %(route)s %(duration_ms)s"
    )

    record = logging.LogRecord(
        name="dcs_test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=42,
        msg="Auditing patient with DOB 1985-11-23 and SSN 123-45-6789",
        args=(),
        exc_info=None,
    )

    # Context injected by middleware
    record.request_id = "req-test-uuid-001"
    record.tenant_id = "tenant-dental-clinic-a"
    record.user_id = "user-biller-99"
    record.route = "/api/v1/scrub"
    record.duration_ms = 45.12

    formatted_log = formatter.format(record)
    log_data = json.loads(formatted_log)

    # Assert PHI values are stripped
    assert "1985-11-23" not in log_data["message"]
    assert "123-45-6789" not in log_data["message"]
    assert "[REDACTED_PHI]" in log_data["message"]

    # Assert the 8 mandatory fields
    mandatory_fields = [
        "timestamp",
        "level",
        "message",
        "request_id",
        "tenant_id",
        "user_id",
        "route",
        "duration_ms",
    ]
    for field in mandatory_fields:
        assert field in log_data, f"Missing mandatory log field: {field}"


def test_prometheus_metrics_increment():
    """Ensures Prometheus counters and histograms record values cleanly without throwing runtime key errors."""
    rule_code = "P1_STRUCT_001"

    # Rule hit increment
    initial_hits = DCS_RULE_HITS_TOTAL.labels(rule_code=rule_code, severity="REJECT")._value.get()
    DCS_RULE_HITS_TOTAL.labels(rule_code=rule_code, severity="REJECT").inc()
    assert (
        DCS_RULE_HITS_TOTAL.labels(rule_code=rule_code, severity="REJECT")._value.get()
        == initial_hits + 1
    )

    # Rule error increment
    initial_errors = DCS_RULE_ERRORS_TOTAL.labels(rule_code=rule_code)._value.get()
    DCS_RULE_ERRORS_TOTAL.labels(rule_code=rule_code).inc()
    assert DCS_RULE_ERRORS_TOTAL.labels(rule_code=rule_code)._value.get() == initial_errors + 1

    # Duration histogram observation
    DCS_SCRUB_DURATION_SECONDS.labels(phase="normalize").observe(0.015)


def test_request_context_middleware_records_http_metric(client):
    """Requests must carry a request id and bump dcs_http_requests_total."""
    from app.core.telemetry import DCS_HTTP_REQUESTS_TOTAL

    label = DCS_HTTP_REQUESTS_TOTAL.labels(route="/health", status="200")
    before = label._value.get()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id")
    assert label._value.get() == before + 1


def test_db_pool_gauges_registered():
    """Pool saturation gauges are defined and seeded after engine creation."""
    from app.core.database_session import engine
    from app.core.telemetry import DCS_DB_ACTIVE_CONNECTIONS, DCS_DB_MAX_CONNECTIONS

    assert DCS_DB_MAX_CONNECTIONS._value.get() > 0
    assert DCS_DB_ACTIVE_CONNECTIONS._value.get() >= 0
    assert engine.pool is not None


def test_refresh_claim_gauges(db_session):
    """Claim status + first-pass-clean gauges reflect the database without error."""
    from app.core import telemetry
    from app.core.telemetry import DCS_FIRST_PASS_CLEAN_RATIO, refresh_claim_gauges

    telemetry._last_gauge_refresh = 0.0
    refresh_claim_gauges(db_session)
    assert isinstance(DCS_FIRST_PASS_CLEAN_RATIO._value.get(), float)
