from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.claims.models.claim import Claim
from app.modules.claims.models.patient_procedure_history import PatientProcedureHistory

if TYPE_CHECKING:
    from app.core.tenant import Tenant
    from app.modules.claims.models.insurance_policy import InsurancePolicy


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

    claims: Mapped[list[Claim]] = relationship("Claim", back_populates="patient")

    procedure_history: Mapped[list[PatientProcedureHistory]] = relationship(
        "PatientProcedureHistory", back_populates="patient", cascade="all, delete-orphan"
    )
