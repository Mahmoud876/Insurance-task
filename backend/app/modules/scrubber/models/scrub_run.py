import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class ScrubRun(Base):
    __tablename__ = "scrub_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False, index=True)
    engine_version = Column(String(50), nullable=False)
    input_hash = Column(String(64), nullable=False)
    readiness_score = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)  # "ready" or "needs_review"
    snapshot = Column(JSONB, nullable=False)
    findings = Column(JSONB, nullable=False)
    ruleset_versions = Column(JSONB, nullable=False)
    duration_ms = Column(Float, nullable=False)
    is_truncated = Column(JSONB, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index(
            "uq_scrub_runs_claim_hash_engine",
            "claim_id",
            "input_hash",
            "engine_version",
            unique=True,
        ),
    )
