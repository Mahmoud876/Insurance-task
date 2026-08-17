from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.claim import Claim


class ClaimAttachment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "claim_attachment"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claim.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)

    claim: Mapped[Claim] = relationship("Claim", back_populates="attachments")
