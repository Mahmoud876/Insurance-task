"""enable_tenant_rls

Revision ID: ccbc6d418c41
Revises: ac315f2b1dc4
Create Date: 2026-08-20 05:03:06.655439

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ccbc6d418c41"
down_revision: str | Sequence[str] | None = "ac315f2b1dc4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = [
    "app_user",
    "patient",
    "provider",
    "payer",
    "payer_plan",
    "insurance_policy",
    "claim",
    "claim_line",
    "claim_attachment",
    "audit_event",
]


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_tenant_id()
        RETURNS uuid
        LANGUAGE plpgsql
        STABLE
        AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.tenant_id', true), '')::uuid;
        EXCEPTION WHEN invalid_text_representation THEN
            RETURN NULL;
        END;
        $$;
        """
    )
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_policy ON {table};")

        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation_policy ON {table}
                FOR ALL
                USING (
                    tenant_id = app_current_tenant_id()
                )
                WITH CHECK (
                    tenant_id = app_current_tenant_id()
                );
            """
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP FUNCTION IF EXISTS app_current_tenant_id() CASCADE;")
