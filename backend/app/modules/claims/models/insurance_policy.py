from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.core.field_encryption import decrypt_field, derive_member_last4, encrypt_field

if TYPE_CHECKING:
    from app.core.tenant import Tenant
    from app.modules.claims.models.patient import Patient
    from app.modules.payers.payer_plan import PayerPlan


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

    member_id_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    member_id_last4: Mapped[str | None] = mapped_column(String(10), nullable=True)

    @property
    def member_id(self) -> str | None:
        """Decrypted member ID. Adding this requirement here enforces field-level
        encryption at rest: the raw member number is never stored in plaintext."""
        return decrypt_field(self.member_id_enc)

    @member_id.setter
    def member_id(self, value: str | None) -> None:
        if value is None:
            self.member_id_enc = None
            self.member_id_last4 = None
            return
        self.member_id_enc = encrypt_field(value)
        self.member_id_last4 = derive_member_last4(value)

    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="manual")
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", lazy="selectin")
    patient: Mapped[Patient] = relationship("Patient", back_populates="policies", lazy="selectin")
    payer_plan: Mapped[PayerPlan] = relationship(
        "PayerPlan", back_populates="policies", lazy="selectin"
    )
