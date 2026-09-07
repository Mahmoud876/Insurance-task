from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    total_created: int
    total_submitted: int
    total_clean_first_pass: int
    total_denied: int
    total_billed_amount: Decimal
    first_pass_clean_rate: float
    average_readiness_score: float


class StatusFunnelResponse(BaseModel):
    created: int
    scrubbed: int
    ready: int
    submitted: int
    denied: int


class TopFindingMetrics(BaseModel):
    rule_code: str
    message_key: str
    occurrences: int
    affected_claims: int
    impact_percentage: float


class TopFindingsResponse(BaseModel):
    period_start: date
    period_end: date
    findings: list[TopFindingMetrics]


class PayerPerformanceMetrics(BaseModel):
    payer_id: UUID | None
    payer_name: str
    claims_submitted: int
    clean_pass_rate: float
    denial_rate: float
    total_billed: Decimal
    avg_readiness_score: float


class PayerPerformanceResponse(BaseModel):
    period_start: date
    period_end: date
    payers: list[PayerPerformanceMetrics]
