"""add procedure and diagnosis tables

Revision ID: 7ca8d6453398
Revises: ac315f2b1dc4
Create Date: 2026-08-20 13:26:07.888097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7ca8d6453398"
down_revision: Union[str, Sequence[str], None] = "ac315f2b1dc4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Enable PostgreSQL trigram support.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ============================================================
    # Procedure codes
    # ============================================================
    op.create_table(
        "procedure_code",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("code_system", sa.Text(), nullable=False),
        sa.Column("short_desc", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),

        sa.Column(
            "requires_tooth",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "requires_surface",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "requires_quadrant",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "requires_arch",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "allowed_surfaces",
            sa.ARRAY(sa.Text()),
            nullable=True,
        ),

        sa.Column(
            "is_posterior_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_anterior_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_primary_dentition_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "typical_documentation",
            sa.ARRAY(sa.Text()),
            nullable=True,
        ),

        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),

        sa.CheckConstraint(
            "NOT (is_posterior_only AND is_anterior_only)",
            name="ck_procedure_not_both_posterior_anterior",
        ),
    )

    # Trigram index for searching procedure descriptions.
    op.execute(
        """
        CREATE INDEX idx_proc_code_trgm
        ON procedure_code
        USING gin (short_desc gin_trgm_ops)
        """
    )

    # ============================================================
    # Diagnosis codes
    # ============================================================
    op.create_table(
        "diagnosis_code",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column(
            "code_system",
            sa.Text(),
            nullable=False,
            server_default="ICD10CM",
        ),
        sa.Column("description", sa.Text(), nullable=False),

        sa.Column(
            "is_billable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
    )

    # ============================================================
    # Procedure ↔ Diagnosis compatibility
    # ============================================================
    op.create_table(
        "procedure_diagnosis_compat",
        sa.Column(
            "procedure_code",
            sa.Text(),
            sa.ForeignKey("procedure_code.code"),
            nullable=False,
        ),
        sa.Column(
            "diagnosis_code",
            sa.Text(),
            sa.ForeignKey("diagnosis_code.code"),
            nullable=False,
        ),
        sa.Column(
            "compatibility",
            sa.Text(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint(
            "procedure_code",
            "diagnosis_code",
        ),

        sa.CheckConstraint(
            "compatibility IN ('EXPECTED', 'ALLOWED', 'UNLIKELY')",
            name="ck_procedure_diagnosis_compatibility",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("procedure_diagnosis_compat")
    op.drop_table("diagnosis_code")

    op.execute(
        "DROP INDEX IF EXISTS idx_proc_code_trgm"
    )

    op.drop_table("procedure_code")

   
