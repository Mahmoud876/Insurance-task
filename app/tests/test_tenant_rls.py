import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from app.tests.conftest import assume_rls_role, ensure_rls_role

_SET_TENANT_RLS = text("SELECT set_config('app.tenant_id', :tenant_id, true)")


def _set_tenant_context(conn, tenant_id: str | None) -> None:
    conn.execute(_SET_TENANT_RLS, {"tenant_id": tenant_id or ""})
    assume_rls_role(conn)


@pytest.fixture(scope="module")
def alembic_cfg():
    ini_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
    config = Config(ini_path)
    config.set_main_option(
        "sqlalchemy.url",
        os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5433/postgres",
        ),
    )
    return config


@pytest.fixture(autouse=True)
def clean_database(alembic_cfg):
    admin_url = alembic_cfg.get_main_option("sqlalchemy.url")
    admin_engine = create_engine(admin_url)
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE claim_line, claim_attachment, claim, audit_event, "
                "insurance_policy, payer_plan, payer, provider, patient, app_user, tenant "
                "CASCADE"
            )
        )
    admin_engine.dispose()


@pytest.fixture
def setup_tenants(db_engine):
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()
    now = datetime.now(UTC)

    with db_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tenant (id, name, slug, created_at, updated_at) "
                "VALUES (:id_a, 'Tenant A', 'tenant-a', :now, :now), "
                "       (:id_b, 'Tenant B', 'tenant-b', :now, :now)"
            ),
            {"id_a": tenant_a_id, "id_b": tenant_b_id, "now": now},
        )

    return tenant_a_id, tenant_b_id


@pytest.mark.parametrize("invalid_setting", [None, "", "invalid-uuid-string"])
def test_rls_fail_closed_on_missing_or_invalid_context(db_engine, setup_tenants, invalid_setting):
    tenant_a_id, _ = setup_tenants
    patient_id = uuid4()
    now = datetime.now(UTC)

    # Insert a row under Tenant A context
    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_a_id))
        conn.execute(
            text(
                "INSERT INTO patient (id, tenant_id, first_name, last_name, dob, created_at, updated_at) "
                "VALUES (:id, :tenant_id, 'John', 'Doe', '1990-01-01', :now, :now)"
            ),
            {"id": patient_id, "tenant_id": tenant_a_id, "now": now},
        )

        # Query with missing or malformed context as a non-superuser.
        # postgres bypasses RLS even when FORCE ROW LEVEL SECURITY is on.
        with db_engine.begin() as conn:
            _set_tenant_context(conn, invalid_setting)

            result = conn.execute(text("SELECT COUNT(*) FROM patient")).scalar()
            assert result == 0


def test_rls_select_isolation(db_engine, setup_tenants):
    tenant_a_id, tenant_b_id = setup_tenants
    now = datetime.now(UTC)

    # Seed Patient for Tenant A in its own transaction
    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_a_id))
        conn.execute(
            text(
                "INSERT INTO patient (id, tenant_id, first_name, last_name, dob, created_at, updated_at) "
                "VALUES (:id, :tenant_id, 'Alice', 'A', '1992-02-02', :now, :now)"
            ),
            {"id": uuid4(), "tenant_id": tenant_a_id, "now": now},
        )

    # Seed Patient for Tenant B in a separate transaction
    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_b_id))
        conn.execute(
            text(
                "INSERT INTO patient (id, tenant_id, first_name, last_name, dob, created_at, updated_at) "
                "VALUES (:id, :tenant_id, 'Bob', 'B', '1993-03-03', :now, :now)"
            ),
            {"id": uuid4(), "tenant_id": tenant_b_id, "now": now},
        )

    # Query as Tenant A in a fresh transaction
    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_a_id))
        patients = conn.execute(text("SELECT first_name FROM patient")).scalars().all()

        assert "Alice" in patients
        assert "Bob" not in patients


def test_rls_insert_with_check_violation(db_engine, setup_tenants):
    tenant_a_id, tenant_b_id = setup_tenants
    now = datetime.now(UTC)

    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_a_id))

        # Attempting to insert Tenant B's ID while active context is Tenant A
        with pytest.raises(DBAPIError) as exc_info:
            conn.execute(
                text(
                    "INSERT INTO patient (id, tenant_id, first_name, last_name, dob, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, 'Malicious', 'User', '1995-05-05', :now, :now)"
                ),
                {"id": uuid4(), "tenant_id": tenant_b_id, "now": now},
            )

        assert "new row violates row-level security policy" in str(exc_info.value).lower()


def test_rls_update_and_delete_isolation(db_engine, setup_tenants):
    tenant_a_id, tenant_b_id = setup_tenants
    patient_b_id = uuid4()
    now = datetime.now(UTC)

    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_b_id))
        conn.execute(
            text(
                "INSERT INTO patient (id, tenant_id, first_name, last_name, dob, created_at, updated_at) "
                "VALUES (:id, :tenant_id, 'Charlie', 'B', '1994-04-04', :now, :now)"
            ),
            {"id": patient_b_id, "tenant_id": tenant_b_id, "now": now},
        )

    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_a_id))
        result_update = conn.execute(
            text("UPDATE patient SET first_name = 'Hacked' WHERE id = :id"),
            {"id": patient_b_id},
        )
        assert result_update.rowcount == 0

    with db_engine.begin() as conn:
        _set_tenant_context(conn, str(tenant_a_id))
        result_delete = conn.execute(
            text("DELETE FROM patient WHERE id = :id"),
            {"id": patient_b_id},
        )
        assert result_delete.rowcount == 0


def test_rls_migration_upgrade_downgrade_cycle(alembic_cfg, db_engine):
    command.downgrade(alembic_cfg, "ac315f2b1dc4")
    command.upgrade(alembic_cfg, "ccbc6d418c41")

    with db_engine.connect() as conn:
        policies = (
            conn.execute(text("SELECT policyname FROM pg_policies WHERE tablename = 'patient'"))
            .scalars()
            .all()
        )
        assert "patient_tenant_isolation_policy" in policies

    command.downgrade(alembic_cfg, "ac315f2b1dc4")

    with db_engine.connect() as conn:
        policies = (
            conn.execute(text("SELECT policyname FROM pg_policies WHERE tablename = 'patient'"))
            .scalars()
            .all()
        )
        assert "patient_tenant_isolation_policy" not in policies

    command.upgrade(alembic_cfg, "head")
    with db_engine.begin() as conn:
        ensure_rls_role(conn)
