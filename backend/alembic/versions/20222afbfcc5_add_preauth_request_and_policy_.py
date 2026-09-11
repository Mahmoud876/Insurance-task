"""add_preauth_request_and_policy_verification_columns

Revision ID: 20222afbfcc5
Revises: 7ca8d6453398
Create Date: 2026-09-07 16:48:17.660798

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20222afbfcc5'
down_revision: str | Sequence[str] | None = '7ca8d6453398'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "insurance_policy",
        sa.Column("source", sa.String(length=50), nullable=True, server_default="manual"),
    )
    op.add_column("insurance_policy", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "preauth_request",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("claim_id", sa.UUID(), nullable=False),
        sa.Column("payer_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["claim_id"], ["claim.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_preauth_request_claim_id"), "preauth_request", ["claim_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_preauth_request_claim_id"), table_name="preauth_request")
    op.drop_table("preauth_request")
    op.drop_column("insurance_policy", "verified_at")
    op.drop_column("insurance_policy", "source")
