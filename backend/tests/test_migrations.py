import os

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


@pytest.fixture(scope="module")
def alembic_cfg():
    """Builds Alembic Config instance pointing to alembic.ini."""
    ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    config = Config(ini_path)
    config.set_main_option(
        "sqlalchemy.url",
        os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@127.0.0.1:5433/postgres",
        ),
    )
    return config


def test_migration_upgrade_downgrade_cycle(alembic_cfg):
    """Verifies upgrade head -> downgrade -1 -> upgrade head lifecycle."""
    command.upgrade(alembic_cfg, "head")

    db_url = alembic_cfg.get_main_option("sqlalchemy.url")
    engine = create_engine(db_url)
    inspector = inspect(engine)

    assert "tenant" in inspector.get_table_names()
    assert "insurance_policy" in inspector.get_table_names()
    assert "procedure_code" in inspector.get_table_names()

    command.downgrade(alembic_cfg, "-1")

    inspector = inspect(engine)
    assert "procedure_code" not in inspector.get_table_names()

    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)
    assert "procedure_code" in inspector.get_table_names()
