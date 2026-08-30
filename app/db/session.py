from collections.abc import Generator
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

current_tenant_id: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)

_SET_TENANT_RLS = text("SELECT set_config('app.tenant_id', :tenant_id, false)")

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def apply_tenant_rls(db: Session, tenant_id: UUID | None) -> None:
    tenant_str = str(tenant_id) if tenant_id else ""
    db.execute(
        text("SELECT set_config('app.tenant_id', :tid, false);"),
        {"tid": tenant_str},
    )


def clear_tenant_rls(db: Session) -> None:
    """Reset the session-local tenant GUC, rolling back first if the transaction aborted."""
    db.rollback()
    db.execute(_SET_TENANT_RLS, {"tenant_id": ""})


@event.listens_for(SessionLocal, "after_begin")
def set_transaction_tenant_context(session: Session, transaction: Any, connection: Any) -> None:
    tenant_id = current_tenant_id.get()
    tenant_str = str(tenant_id) if tenant_id else ""
    connection.execute(_SET_TENANT_RLS, {"tenant_id": tenant_str})


def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
