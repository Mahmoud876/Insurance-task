"""add_claim_board_fields

Revision ID: d4e8f2a1b7c9
Revises: ccbc6d418c41
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e8f2a1b7c9"
down_revision: str | Sequence[str] | None = "ccbc6d418c41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "claim",
        sa.Column("claim_number", sa.String(length=100), nullable=True),
    )
    op.add_column("claim", sa.Column("payer_id", sa.UUID(), nullable=True))
    op.add_column("claim", sa.Column("policy_id", sa.UUID(), nullable=True))
    op.add_column("claim", sa.Column("service_date_from", sa.Date(), nullable=True))
    op.add_column("claim", sa.Column("service_date_to", sa.Date(), nullable=True))
    op.add_column(
        "claim",
        sa.Column("readiness_score", sa.SmallInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "claim",
        sa.Column(
            "findings_summary",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.execute("UPDATE claim SET claim_number = id::text WHERE claim_number IS NULL")
    op.execute("UPDATE claim SET service_date_from = CURRENT_DATE WHERE service_date_from IS NULL")
    op.execute("UPDATE claim SET service_date_to = service_date_from WHERE service_date_to IS NULL")
    op.alter_column("claim", "claim_number", nullable=False)
    op.alter_column("claim", "service_date_from", nullable=False)
    op.alter_column("claim", "service_date_to", nullable=False)
    op.create_foreign_key(
        "fk_claim_payer",
        "claim",
        "payer",
        ["payer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_claim_policy",
        "claim",
        "insurance_policy",
        ["policy_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_claim_tenant_claim_number", "claim", ["tenant_id", "claim_number"]
    )
    op.create_index("idx_claim_board_cursor", "claim", ["tenant_id", "updated_at", "id"])
    op.create_index("idx_claim_board_status", "claim", ["tenant_id", "status", "updated_at", "id"])


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_claim_board_status;")
    op.execute("DROP INDEX IF EXISTS idx_claim_board_cursor;")
    op.execute("ALTER TABLE claim DROP CONSTRAINT IF EXISTS uq_claim_tenant_claim_number;")
    op.execute("ALTER TABLE claim DROP CONSTRAINT IF EXISTS fk_claim_policy;")
    op.execute("ALTER TABLE claim DROP CONSTRAINT IF EXISTS fk_claim_payer;")
    op.execute("ALTER TABLE claim DROP COLUMN IF EXISTS payer_id;")
    op.execute("ALTER TABLE claim DROP COLUMN IF EXISTS findings_summary;")
    op.execute("ALTER TABLE claim DROP COLUMN IF EXISTS readiness_score;")
    op.execute("ALTER TABLE claim DROP COLUMN IF EXISTS service_date_to;")
    op.execute("ALTER TABLE claim DROP COLUMN IF EXISTS service_date_from;")
    op.execute("ALTER TABLE claim DROP COLUMN IF EXISTS policy_id;")
    op.execute("ALTER TABLE claim DROP COLUMN IF EXISTS claim_number;")
