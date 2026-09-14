import re
import time
from collections.abc import Generator
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.core.telemetry import (
    DCS_DB_ACTIVE_CONNECTIONS,
    DCS_DB_MAX_CONNECTIONS,
    DCS_DB_QUERY_DURATION_SECONDS,
)

current_tenant_id: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)

_SET_TENANT_RLS = text("SELECT set_config('app.tenant_id', :tenant_id, false)")

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_QUERY_TABLE = re.compile(r"\b(?:INTO|UPDATE|FROM|TABLE)\s+(\w+)", re.IGNORECASE)


def _repository_label(statement: str) -> str:
    match = _QUERY_TABLE.search(statement)
    return match.group(1) if match else "other"


def _wire_db_observability(target_engine: Any) -> None:
    """Expose pool occupancy and per-query duration to Prometheus."""
    pool = target_engine.pool
    max_overflow = int(getattr(pool, "_max_overflow", 10) or 10)
    DCS_DB_MAX_CONNECTIONS.set(pool.size() + max_overflow if max_overflow >= 0 else pool.size())

    @event.listens_for(target_engine, "checkout")
    def _on_checkout(_conn: Any, _record: Any, _proxy: Any) -> None:
        DCS_DB_ACTIVE_CONNECTIONS.inc()

    @event.listens_for(target_engine, "checkin")
    def _on_checkin(_conn: Any, _record: Any) -> None:
        DCS_DB_ACTIVE_CONNECTIONS.dec()

    query_starts: dict[int, float] = {}

    @event.listens_for(target_engine, "before_cursor_execute")
    def _before_cursor_execute(
        conn: Any, _cursor: Any, _statement: str, _params: Any, _context: Any, _executemany: bool
    ) -> None:
        query_starts[id(conn)] = time.perf_counter()

    @event.listens_for(target_engine, "after_cursor_execute")
    def _after_cursor_execute(
        conn: Any, _cursor: Any, statement: str, _params: Any, _context: Any, _executemany: bool
    ) -> None:
        start = query_starts.pop(id(conn), None)
        if start is not None:
            DCS_DB_QUERY_DURATION_SECONDS.labels(repository=_repository_label(statement)).observe(
                time.perf_counter() - start
            )


_wire_db_observability(engine)


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
