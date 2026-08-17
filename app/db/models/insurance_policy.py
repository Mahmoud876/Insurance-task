from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.patient import Patient
    from app.db.models.payer_plan import PayerPlan
    from app.db.models.tenant import Tenant


class InsurancePolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "insurance_policy"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payer_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payer_plan.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    policy_number: Mapped[str] = mapped_column(String(100), nullable=False)
    group_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    tenant: Mapped[Tenant] = relationship("Tenant")
    patient: Mapped[Patient] = relationship("Patient", back_populates="policies")
    payer_plan: Mapped[PayerPlan] = relationship("PayerPlan", back_populates="policies")
