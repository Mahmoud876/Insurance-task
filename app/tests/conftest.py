import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.main import app

# testcontainers.postgres is a "community module" within the main
# testcontainers package — there is no testcontainers.community namespace.
from testcontainers.postgres import PostgresContainer

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def test_database_url(postgres_container):
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session", autouse=True)
def run_migrations(test_database_url):
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url
    try:
        alembic_config = Config(str(ALEMBIC_INI))
        command.upgrade(alembic_config, "head")
        yield
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url


@pytest.fixture(scope="session")
def engine(test_database_url, run_migrations):
    eng = create_engine(test_database_url)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.execute(text(
            """
            TRUNCATE TABLE
                claim_line,
                claim,
                patient,
                provider,
                tenant
            CASCADE
            """
        ))
        db.commit()
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
