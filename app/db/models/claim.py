from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, UUID, Date, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.patient import Patient

if TYPE_CHECKING:
    from app.db.models.claim_attachment import ClaimAttachment
    from app.db.models.claim_line import ClaimLine


class ClaimStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    SCRUBBED = "SCRUBBED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class Claim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "claim"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    claim_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        default=lambda: f"CLM-{uuid.uuid4().hex[:12].upper()}",
    )
    payer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer.id", ondelete="SET NULL"), nullable=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insurance_policy.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    status: Mapped[ClaimStatus] = mapped_column(
        SQLEnum(ClaimStatus, name="claim_status"),
        default=ClaimStatus.DRAFT,
        nullable=False,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    service_date_from: Mapped[date] = mapped_column(
        Date, nullable=False, default=lambda: date.today()
    )
    service_date_to: Mapped[date] = mapped_column(
        Date, nullable=False, default=lambda: date.today()
    )
    readiness_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    findings_summary: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )

    patient: Mapped[Patient] = relationship("Patient", back_populates="claims")

    lines: Mapped[list[ClaimLine]] = relationship("ClaimLine", back_populates="claim")
    attachments: Mapped[list[ClaimAttachment]] = relationship(
        "ClaimAttachment", back_populates="claim"
    )
