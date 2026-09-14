import logging
import re
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from app.core.telemetry import request_context


class RequestContextFilter(logging.Filter):
    """Populates the request metadata fields from the active request context.

    Lets any log emitted during a request carry request_id/tenant_id/user_id/route
    without each call site needing to pass `extra`. Defaults to "N/A" outside
    requests so the JSON schema stays stable.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = request_context.get() or {}
        record.request_id = ctx.get("request_id", "N/A")
        record.tenant_id = ctx.get("tenant_id", "N/A")
        record.user_id = ctx.get("user_id", "N/A")
        record.route = ctx.get("route", "N/A")
        record.duration_ms = ctx.get("duration_ms", 0.0)
        return True


class StructuredPHIRedactorFormatter(JsonFormatter):
    PHI_REGEX = re.compile(
        r"\b(\d{3}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\b|patient_dob|tooth_number|ssn",
        re.IGNORECASE,
    )

    def process_log_record(self, log_record: dict[str, Any]) -> dict[str, Any]:
        log_record["timestamp"] = log_record.get("asctime") or log_record.get("created")
        log_record["level"] = log_record.get("levelname")
        log_record["request_id"] = log_record.get("request_id", "N/A")
        log_record["tenant_id"] = log_record.get("tenant_id", "N/A")
        log_record["user_id"] = log_record.get("user_id", "N/A")
        log_record["route"] = log_record.get("route", "N/A")
        log_record["duration_ms"] = log_record.get("duration_ms", 0.0)

        # Apply PHI redaction across message string
        if "message" in log_record and isinstance(log_record["message"], str):
            log_record["message"] = self.PHI_REGEX.sub("[REDACTED_PHI]", log_record["message"])

        return super().process_log_record(log_record)


def setup_structured_logging() -> None:
    handler = logging.StreamHandler()
    formatter = StructuredPHIRedactorFormatter(
        "%(timestamp)s %(level)s %(message)s %(request_id)s %(tenant_id)s %(user_id)s %(route)s %(duration_ms)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
