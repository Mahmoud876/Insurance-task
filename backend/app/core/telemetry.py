import logging
import os
from contextvars import ContextVar
from time import monotonic
from typing import Any

from opentelemetry import trace
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Tracer is created lazily against the globally installed TracerProvider, so it
# keeps working whether or not configure_tracing() was able to set up an SDK.
tracer = trace.get_tracer("dcs.scrubber")

# Context shared between the request-logging middleware and the logging formatter
# so every structured log line emitted during a request carries request metadata.
request_context: ContextVar[dict[str, Any] | None] = ContextVar("request_context", default=None)

# OTel SDK / exporter packages are optional at runtime: imports are guarded so the
# app runs identically when they are not installed (e.g. a bare dev environment).
try:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SDK_AVAILABLE = False

try:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    _OTLP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OTLP_AVAILABLE = False

_tracing_configured = False


def configure_tracing() -> None:
    """Configure the global OTel TracerProvider and library auto-instrumentation.

    Trace export only activates when OTEL_EXPORTER_OTLP_ENDPOINT is set; otherwise
    tracing stays a no-op so the app behaves identically without a collector.
    """
    global _tracing_configured
    if _tracing_configured:
        return
    _tracing_configured = True

    if _SDK_AVAILABLE and _OTLP_AVAILABLE:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if endpoint:
            resource = Resource.create(
                {"service.name": os.getenv("OTEL_SERVICE_NAME", "dental-claims-api")}
            )
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
            )
            trace.set_tracer_provider(provider)

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
    except ImportError:  # pragma: no cover
        pass


def instrument_fastapi(app: Any) -> None:
    """Attach FastAPI auto-instrumentation, keeping the manual scrub-phase spans."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    except ImportError:  # pragma: no cover
        pass


DCS_SCRUB_DURATION_SECONDS = Histogram(
    "dcs_scrub_duration_seconds",
    "Scrubbing execution time per phase in seconds",
    ["phase"],
)

DCS_SCRUB_FINDINGS_TOTAL = Counter(
    "dcs_scrub_findings_total",
    "Total findings by severity and rule category",
    ["severity", "category"],
)

DCS_RULE_HITS_TOTAL = Counter(
    "dcs_rule_hits_total",
    "Total times a rule condition evaluated to true (fired)",
    ["rule_code", "severity"],
)

DCS_RULE_ERRORS_TOTAL = Counter(
    "dcs_rule_errors_total",
    "Total unhandled rule evaluation exceptions caught by sandbox",
    ["rule_code"],
)

DCS_CLAIMS_BY_STATUS = Gauge(
    "dcs_claims_by_status",
    "Current claim count grouped by output status",
    ["status"],
)

DCS_FIRST_PASS_CLEAN_RATIO = Gauge(
    "dcs_first_pass_clean_ratio",
    "Proportion of claims passing without any findings",
)

DCS_HTTP_REQUESTS_TOTAL = Counter(
    "dcs_http_requests_total",
    "Total HTTP requests handled",
    ["route", "status"],
)

DCS_DB_QUERY_DURATION_SECONDS = Histogram(
    "dcs_db_query_duration_seconds",
    "Database execution time by repository",
    ["repository"],
)

DCS_DB_ACTIVE_CONNECTIONS = Gauge(
    "dcs_db_active_connections",
    "Currently checked-out connections in the SQLAlchemy pool",
)

DCS_DB_MAX_CONNECTIONS = Gauge(
    "dcs_db_max_connections",
    "Maximum connections the SQLAlchemy pool can reach (pool size + overflow)",
)

ARQ_QUEUE_DEPTH = Gauge(
    "arq_queue_depth",
    "Number of pending ARQ jobs (0 until the ARQ worker is deployed)",
)


_last_gauge_refresh: float = 0.0
_GAUGE_REFRESH_MIN_SECONDS = 15.0


def refresh_claim_gauges(db: Session) -> None:
    """Re-sync dcs_claims_by_status and dcs_first_pass_clean_ratio from the DB.

    Refreshing on every request would put a full-table GROUP BY on the hot
    write path, so refreshes are throttled per process.
    """
    global _last_gauge_refresh
    now = monotonic()
    if now - _last_gauge_refresh < _GAUGE_REFRESH_MIN_SECONDS:
        return
    _last_gauge_refresh = now

    rows = db.execute(text("SELECT status, COUNT(*) FROM claim GROUP BY status")).fetchall()
    total = 0
    for status_value, count in rows:
        DCS_CLAIMS_BY_STATUS.labels(status=str(status_value)).set(int(count))
        total += int(count)
    clean = db.scalar(text("SELECT COUNT(*) FROM claim WHERE readiness_score = 100")) or 0
    DCS_FIRST_PASS_CLEAN_RATIO.set(float(clean) / float(total) if total else 0.0)
