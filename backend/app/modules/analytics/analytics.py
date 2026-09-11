from datetime import date, datetime
from typing import Any

from sqlalchemy import BIGINT, JSON, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClaimDailyMetrics(Base):
    __tablename__ = "claim_daily_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    total_claims: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_claims: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flagged_claims: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    autofixed_claims: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_value_cents: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    metrics_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
