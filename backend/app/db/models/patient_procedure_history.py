from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, UUID, Date, ForeignKey, SmallInteger, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.claim_line import ClaimLine
    from app.db.models.patient import Patient
    from app.db.models.payer import Payer
    from app.db.models.tenant import Tenant


class ProcedureHistorySource(enum.StrEnum):
    INTERNAL_CLAIM = "INTERNAL_CLAIM"
    EOB_IMPORT = "EOB_IMPORT"
    EXTERNAL_EHR = "EXTERNAL_EHR"
    MANUAL_ENTRY = "MANUAL_ENTRY"


class PatientProcedureHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "patient_procedure_history"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True
    )
    procedure_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    tooth_canonical: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    surfaces: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    quadrant: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    arch: Mapped[str | None] = mapped_column(String(10), nullable=True)

    source: Mapped[ProcedureHistorySource] = mapped_column(
        SQLEnum(ProcedureHistorySource, name="procedure_history_source"),
        nullable=False,
        default=ProcedureHistorySource.INTERNAL_CLAIM,
    )
    claim_line_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("claim_line.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    payer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payer.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant")
    patient: Mapped[Patient] = relationship("Patient", back_populates="procedure_history")
    claim_line: Mapped[ClaimLine | None] = relationship("ClaimLine")
    payer: Mapped[Payer | None] = relationship("Payer")
