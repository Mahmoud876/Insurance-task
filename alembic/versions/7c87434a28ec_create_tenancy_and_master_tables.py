"""create_tenancy_and_master_tables

Revision ID: 7c87434a28ec
Revises:
Create Date: 2026-08-15 01:39:20.253718

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c87434a28ec"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - Tenancy & Master Tables."""
    # Tenant
    op.create_table(
        "tenant",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenant_slug"), "tenant", ["slug"], unique=True)

    # App User
    op.create_table(
        "app_user",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_app_user_tenant_id"), "app_user", ["tenant_id"], unique=False)

    # Patient
    op.create_table(
        "patient",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("dob", sa.Date(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patient_tenant_id"), "patient", ["tenant_id"], unique=False)

    # Payer
    op.create_table(
        "payer",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("payer_code", sa.String(length=50), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payer_payer_code"), "payer", ["payer_code"], unique=False)
    op.create_index(op.f("ix_payer_tenant_id"), "payer", ["tenant_id"], unique=False)

    # Provider
    op.create_table(
        "provider",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("npi", sa.String(length=10), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_npi"), "provider", ["npi"], unique=False)
    op.create_index(op.f("ix_provider_tenant_id"), "provider", ["tenant_id"], unique=False)

    # Payer Plan
    op.create_table(
        "payer_plan",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("payer_id", sa.UUID(), nullable=False),
        sa.Column("plan_name", sa.String(length=255), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payer_id"], ["payer.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payer_plan_payer_id"), "payer_plan", ["payer_id"], unique=False)
    op.create_index(op.f("ix_payer_plan_tenant_id"), "payer_plan", ["tenant_id"], unique=False)

    # Insurance Policy
    op.create_table(
        "insurance_policy",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("payer_plan_id", sa.UUID(), nullable=False),
        sa.Column("policy_number", sa.String(length=100), nullable=False),
        sa.Column("group_number", sa.String(length=100), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payer_plan_id"], ["payer_plan.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_insurance_policy_patient_id"), "insurance_policy", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_insurance_policy_payer_plan_id"),
        "insurance_policy",
        ["payer_plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_insurance_policy_tenant_id"), "insurance_policy", ["tenant_id"], unique=False
    )

    # Cleanup old orm table if present
    op.execute("DROP TABLE IF EXISTS mikro_orm_migrations CASCADE;")


def downgrade() -> None:
    """Downgrade schema - Tenancy & Master Tables."""
    op.drop_index(op.f("ix_insurance_policy_tenant_id"), table_name="insurance_policy")
    op.drop_index(op.f("ix_insurance_policy_payer_plan_id"), table_name="insurance_policy")
    op.drop_index(op.f("ix_insurance_policy_patient_id"), table_name="insurance_policy")
    op.drop_table("insurance_policy")

    op.drop_index(op.f("ix_payer_plan_tenant_id"), table_name="payer_plan")
    op.drop_index(op.f("ix_payer_plan_payer_id"), table_name="payer_plan")
    op.drop_table("payer_plan")

    op.drop_index(op.f("ix_provider_tenant_id"), table_name="provider")
    op.drop_index(op.f("ix_provider_npi"), table_name="provider")
    op.drop_table("provider")

    op.drop_index(op.f("ix_payer_tenant_id"), table_name="payer")
    op.drop_index(op.f("ix_payer_payer_code"), table_name="payer")
    op.drop_table("payer")

    op.drop_index(op.f("ix_patient_tenant_id"), table_name="patient")
    op.drop_table("patient")

    op.drop_index(op.f("ix_app_user_tenant_id"), table_name="app_user")
    op.drop_table("app_user")

    op.drop_index(op.f("ix_tenant_slug"), table_name="tenant")
    op.drop_table("tenant")
