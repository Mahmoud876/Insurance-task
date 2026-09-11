"""add_ruleset_versioning_and_active_unique_index

Revision ID: 6a4360bde94e
Revises: 20222afbfcc5
Create Date: 2026-09-07 17:41:28.443340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a4360bde94e'
down_revision: Union[str, Sequence[str], None] = '20222afbfcc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ruleset_version",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("rules_payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False, server_default="system"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "uix_tenant_active_ruleset",
        "ruleset_version",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uix_tenant_active_ruleset",
        table_name="ruleset_version",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_table("ruleset_version")
