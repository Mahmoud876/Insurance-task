"""add_claim_daily_metrics_table

Revision ID: ff0157cd3766
Revises: 6a4360bde94e
Create Date: 2026-09-07 17:47:51.562888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff0157cd3766'
down_revision: Union[str, Sequence[str], None] = '6a4360bde94e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "claim_daily_metrics",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("total_claims", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_claims", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flagged_claims", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("autofixed_claims", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_value_cents", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("metrics_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "tenant_id", name="uq_daily_metrics_date_tenant"),
    )
    op.create_index(op.f("ix_claim_daily_metrics_date"), "claim_daily_metrics", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_claim_daily_metrics_date"), table_name="claim_daily_metrics")
    op.drop_table("claim_daily_metrics")
