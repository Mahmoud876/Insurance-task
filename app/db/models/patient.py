from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.insurance_policy import InsurancePolicy
    from app.db.models.tenant import Tenant


class Patient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "patient"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)

    tenant: Mapped[Tenant] = relationship("Tenant")
    policies: Mapped[list[InsurancePolicy]] = relationship(
        "InsurancePolicy", back_populates="patient"
    )
