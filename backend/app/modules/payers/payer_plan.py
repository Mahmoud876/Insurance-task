from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.core.tenant import Tenant
    from app.modules.claims.models.insurance_policy import InsurancePolicy
    from app.modules.payers.payer import Payer


class PayerPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payer_plan"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payer.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)

    tenant: Mapped[Tenant] = relationship("Tenant")
    payer: Mapped[Payer] = relationship("Payer", back_populates="plans")
    policies: Mapped[list[InsurancePolicy]] = relationship(
        "InsurancePolicy", back_populates="payer_plan"
    )
