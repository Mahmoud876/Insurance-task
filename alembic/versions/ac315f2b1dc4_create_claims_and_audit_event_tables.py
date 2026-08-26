"""create_claims_and_audit_event_tables

Revision ID: ac315f2b1dc4
Revises: 7c87434a28ec
Create Date: 2026-08-15 01:56:10.082799

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "ac315f2b1dc4"
down_revision: str | Sequence[str] | None = "7c87434a28ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
claim_status_enum = sa.Enum(
    "DRAFT",
    "SCRUBBED",
    "SUBMITTED",
    "ACCEPTED",
    "REJECTED",
    "PAID",
    name="claim_status",
)


def upgrade() -> None:
    """Upgrade schema - Claims & Audit Logs."""
    # Audit Event
    op.create_table(
        "audit_event",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["app_user.tenant_id", "app_user.id"],
            ondelete="SET NULL",
            name="fk_audit_event_tenant_user",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_event_action"), "audit_event", ["action"], unique=False)
    op.create_index(op.f("ix_audit_event_tenant_id"), "audit_event", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_audit_event_user_id"), "audit_event", ["user_id"], unique=False)

    # Claim
    op.create_table(
        "claim",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("provider_id", sa.UUID(), nullable=False),
        sa.Column("status", claim_status_enum, nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "patient_id"],
            ["patient.tenant_id", "patient.id"],
            ondelete="RESTRICT",
            name="fk_claim_tenant_patient",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "provider_id"],
            ["provider.tenant_id", "provider.id"],
            ondelete="RESTRICT",
            name="fk_claim_tenant_provider",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_claim_tenant_id"),
    )
    op.create_index(op.f("ix_claim_patient_id"), "claim", ["patient_id"], unique=False)
    op.create_index(op.f("ix_claim_provider_id"), "claim", ["provider_id"], unique=False)
    op.create_index(op.f("ix_claim_status"), "claim", ["status"], unique=False)
    op.create_index(op.f("ix_claim_tenant_id"), "claim", ["tenant_id"], unique=False)

    # Claim Attachment
    op.create_table(
        "claim_attachment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("claim_id", sa.UUID(), nullable=False),
        sa.Column("file_key", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["claim.tenant_id", "claim.id"],
            ondelete="CASCADE",
            name="fk_claim_attachment_tenant_claim",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_claim_attachment_claim_id"), "claim_attachment", ["claim_id"], unique=False
    )
    op.create_index(
        op.f("ix_claim_attachment_tenant_id"), "claim_attachment", ["tenant_id"], unique=False
    )

    # Claim Line
    op.create_table(
        "claim_line",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("claim_id", sa.UUID(), nullable=False),
        sa.Column("procedure_code", sa.String(length=50), nullable=False),
        sa.Column("tooth_number", sa.String(length=10), nullable=True),
        sa.Column("surface", sa.String(length=20), nullable=True),
        sa.Column("charge_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["claim.tenant_id", "claim.id"],
            ondelete="CASCADE",
            name="fk_claim_line_tenant_claim",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claim_line_claim_id"), "claim_line", ["claim_id"], unique=False)
    op.create_index(op.f("ix_claim_line_tenant_id"), "claim_line", ["tenant_id"], unique=False)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_event_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_event is append-only. UPDATE and DELETE operations are prohibited.';
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_prevent_audit_modification
        BEFORE UPDATE OR DELETE ON audit_event
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_modification();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_modification ON audit_event;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_event_modification();")

    op.drop_index(op.f("ix_claim_line_tenant_id"), table_name="claim_line")
    op.drop_index(op.f("ix_claim_line_claim_id"), table_name="claim_line")
    op.drop_table("claim_line")

    op.drop_index(op.f("ix_claim_attachment_tenant_id"), table_name="claim_attachment")
    op.drop_index(op.f("ix_claim_attachment_claim_id"), table_name="claim_attachment")
    op.drop_table("claim_attachment")

    op.drop_index(op.f("ix_claim_tenant_id"), table_name="claim")
    op.drop_index(op.f("ix_claim_status"), table_name="claim")
    op.drop_index(op.f("ix_claim_provider_id"), table_name="claim")
    op.drop_index(op.f("ix_claim_patient_id"), table_name="claim")
    op.drop_table("claim")

    op.drop_index(op.f("ix_audit_event_user_id"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_tenant_id"), table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_action"), table_name="audit_event")
    op.drop_table("audit_event")

    bind = op.get_bind()
    claim_status_enum.drop(bind, checkfirst=True)
