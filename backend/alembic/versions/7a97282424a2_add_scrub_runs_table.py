"""add_scrub_runs_table

Revision ID: 7a97282424a2
Revises: ff0157cd3766
Create Date: 2026-09-13 16:45:35.098520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a97282424a2'
down_revision: Union[str, Sequence[str], None] = 'ff0157cd3766'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scrub_runs table tracking every executed scrub per claim."""
    op.create_table(
        "scrub_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claim.id", name="fk_scrub_runs_claim_id"),
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        sa.Column("ruleset_versions", postgresql.JSONB(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("is_truncated", postgresql.JSONB(), nullable=False, server_default=sa.text("'false'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Index(
            "uq_scrub_runs_claim_hash_engine",
            "claim_id",
            "input_hash",
            "engine_version",
            unique=True,
        ),
    )
    op.create_index("ix_scrub_runs_claim_id", "scrub_runs", ["claim_id"])


def downgrade() -> None:
    """Drop scrub_runs table."""
    op.drop_index("ix_scrub_runs_claim_id", table_name="scrub_runs")
    op.drop_table("scrub_runs")
