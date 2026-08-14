from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.claim import Claim


class ClaimLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "claim_line"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claim.id", ondelete="CASCADE"), nullable=False, index=True
    )
    procedure_code: Mapped[str] = mapped_column(String(50), nullable=False)
    tooth_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    surface: Mapped[str | None] = mapped_column(String(20), nullable=True)
    charge_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    claim: Mapped[Claim] = relationship("Claim", back_populates="lines")
