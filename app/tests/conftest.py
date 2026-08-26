import os
from collections.abc import Generator
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.db.models.claim import Claim, ClaimStatus
from app.db.models.patient import Patient
from app.db.models.provider import Provider
from app.db.session import apply_tenant_rls

load_dotenv()

_ENSURE_RLS_ROLE = text(
    """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'test_rls_role') THEN
            CREATE ROLE test_rls_role NOLOGIN NOSUPERUSER NOBYPASSRLS;
        END IF;
    END $$;
    GRANT USAGE ON SCHEMA public TO test_rls_role;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO test_rls_role;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO test_rls_role;
    GRANT test_rls_role TO CURRENT_USER;
    """
)


def ensure_rls_role(connection) -> None:
    """Create a non-superuser role so FORCE/ENABLE RLS is actually evaluated."""
    connection.execute(_ENSURE_RLS_ROLE)


def assume_rls_role(connection) -> None:
    """Switch to the non-superuser role for the rest of the current transaction."""
    connection.execute(text("SET LOCAL ROLE test_rls_role"))


def enable_row_security(db_session: Session) -> None:
    db_session.execute(text("SET row_security = ON;"))


def apply_test_tenant_context(db_session: Session, tenant_id: UUID | None) -> None:
    """Apply tenant RLS context in tests (superuser connections require row_security)."""
    enable_row_security(db_session)
    apply_tenant_rls(db_session, tenant_id)


def seed_patient_and_provider(db_session: Session, tenant_id: UUID) -> tuple[Patient, Provider]:
    apply_tenant_rls(db_session, tenant_id)
    patient = Patient(
        id=uuid4(),
        tenant_id=tenant_id,
        first_name="Test",
        last_name="Patient",
        dob=date(1990, 1, 1),
    )
    provider = Provider(
        id=uuid4(),
        tenant_id=tenant_id,
        npi="1234567890",
        first_name="Dr",
        last_name="Test",
    )
    db_session.add_all([patient, provider])
    db_session.flush()
    return patient, provider


def make_test_claim(
    db_session: Session,
    tenant_id: UUID,
    *,
    claim_id: UUID | None = None,
    status: ClaimStatus = ClaimStatus.DRAFT,
    total_amount: Decimal | float = Decimal("100.00"),
) -> Claim:
    patient, provider = seed_patient_and_provider(db_session, tenant_id)
    claim = Claim(
        id=claim_id or uuid4(),
        tenant_id=tenant_id,
        patient_id=patient.id,
        provider_id=provider.id,
        status=status,
        total_amount=Decimal(str(total_amount)),
    )
    db_session.add(claim)
    return claim


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:5433/postgres",
    )


@pytest.fixture(scope="session")
def db_engine(database_url: str):
    engine = create_engine(database_url)
    config = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)

    with engine.begin() as connection:
        # Recreate from Alembic so RLS policies are present. SQLAlchemy
        # create_all would leave tables without policies, and a no-op
        # upgrade on an already-stamped DB would not restore them.
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO CURRENT_USER"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        ensure_rls_role(connection)

    yield engine

    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE claim_line, claim_attachment, claim, audit_event, "
                "insurance_policy, payer_plan, payer, provider, patient, app_user, tenant "
                "CASCADE"
            )
        )
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    with Session(db_engine) as session:
        yield session
        session.rollback()
