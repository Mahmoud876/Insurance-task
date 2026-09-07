from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.database import Base


class ClaimDailyMetrics(Base):
    __tablename__ = "claim_daily_metrics"

    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    metric_date = Column(Date, nullable=False)
    payer_id = Column(PG_UUID(as_uuid=True), ForeignKey("payer.id"), nullable=True)

    claims_created = Column(Integer, nullable=False, default=0)
    claims_submitted = Column(Integer, nullable=False, default=0)
    claims_clean_first_pass = Column(Integer, nullable=False, default=0)
    claims_denied = Column(Integer, nullable=False, default=0)
    total_billed = Column(Numeric(14, 2), nullable=False, default=0.00)
    avg_readiness_score = Column(Numeric(5, 2), nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "metric_date", "payer_id", name="pk_claim_daily_metrics"),
    )
