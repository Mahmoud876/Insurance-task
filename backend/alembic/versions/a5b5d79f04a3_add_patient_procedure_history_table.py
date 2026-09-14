"""add_patient_procedure_history_table

Revision ID: a5b5d79f04a3
Revises: 7a97282424a2
Create Date: 2026-09-13 17:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a5b5d79f04a3"
down_revision: str | Sequence[str] | None = "7a97282424a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

procedure_history_source_enum = sa.Enum(
    "INTERNAL_CLAIM",
    "EOB_IMPORT",
    "EXTERNAL_EHR",
    "MANUAL_ENTRY",
    name="procedure_history_source",
)


def upgrade() -> None:
    """Create patient_procedure_history table (procedure frequency/coverage inputs)."""
    op.create_table(
        "patient_procedure_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("procedure_code", sa.String(length=50), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("tooth_canonical", sa.SmallInteger(), nullable=True),
        sa.Column("surfaces", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("quadrant", sa.SmallInteger(), nullable=True),
        sa.Column("arch", sa.String(length=10), nullable=True),
        sa.Column("source", procedure_history_source_enum, nullable=False),
        sa.Column("claim_line_id", sa.UUID(), nullable=True),
        sa.Column("payer_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient.id"],
            ondelete="CASCADE",
            name="fk_history_tenant_patient",
        ),
        sa.ForeignKeyConstraint(
            ["claim_line_id"], ["claim_line.id"], ondelete="SET NULL", name="fk_history_claim_line"
        ),
        sa.ForeignKeyConstraint(
            ["payer_id"], ["payer.id"], ondelete="SET NULL", name="fk_history_payer"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_line_id", name="uq_history_claim_line_id"),
    )
    op.create_index(
        op.f("ix_history_patient_id"), "patient_procedure_history", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_history_procedure_code"),
        "patient_procedure_history",
        ["procedure_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_history_service_date"),
        "patient_procedure_history",
        ["service_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_history_tenant_id"), "patient_procedure_history", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    """Drop patient_procedure_history table."""
    for index in ("ix_history_tenant_id", "ix_history_service_date", "ix_history_procedure_code", "ix_history_patient_id"):
        op.drop_index(index, table_name="patient_procedure_history")
    op.drop_table("patient_procedure_history")
    procedure_history_source_enum.drop(op.get_bind(), checkfirst=True)