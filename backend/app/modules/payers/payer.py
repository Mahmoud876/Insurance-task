from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.core.tenant import Tenant
    from app.modules.payers.payer_plan import PayerPlan


class Payer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payer"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    payer_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    tenant: Mapped[Tenant] = relationship("Tenant")
    plans: Mapped[list[PayerPlan]] = relationship("PayerPlan", back_populates="payer")
