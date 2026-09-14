from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.claims.models.claim import Claim


def normalize_doc_type(value: str | None) -> str:
    """Normalizes a client-supplied doc type to a snake_case token."""
    if not value:
        return "attachment"
    cleaned = re.sub(r"\s+", "_", value.strip().lower())
    cleaned = re.sub(r"[^a-z0-9_\-]", "", cleaned)
    return cleaned or "attachment"


PRIMARY_EOB_DOC_TYPES = frozenset(
    {
        "eob",
        "primary_eob",
        "primary-eob",
        "primaryeob",
        "primary",
        "explanation_of_benefits",
        "explanation-of-benefits",
    }
)


def is_primary_eob_doc_type(doc_type: str) -> bool:
    return doc_type.strip().lower() in PRIMARY_EOB_DOC_TYPES


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
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, default="attachment")
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    claim: Mapped[Claim] = relationship("Claim", back_populates="attachments")
