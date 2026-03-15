import logging
import time

from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# Production-ready connection pool configuration
# For 100+ concurrent users, we need larger pool
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Base pool size (was: 5 default)
    max_overflow=30,       # Extra connections beyond pool_size (total: 50)
    pool_pre_ping=True,    # Verify connections before use (prevents stale connections)
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo_pool=False        # Set to True for debugging pool issues
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ── Slow-query monitoring ──────────────────────────────────────────────────────
# Queries slower than this threshold are logged to ``app.slow_query`` with
# the current request_id for easy correlation in production log aggregators.
_SLOW_QUERY_THRESHOLD_MS: float = 200.0
_sq_logger = logging.getLogger("app.slow_query")


@sa_event.listens_for(engine, "before_cursor_execute")
def _sq_before_execute(conn, cursor, statement, params, context, executemany):
    conn.info.setdefault("_sq_start", []).append(time.perf_counter())


@sa_event.listens_for(engine, "after_cursor_execute")
def _sq_after_execute(conn, cursor, statement, params, context, executemany):
    elapsed_ms = (time.perf_counter() - conn.info["_sq_start"].pop()) * 1000
    if elapsed_ms >= _SLOW_QUERY_THRESHOLD_MS:
        # Deferred imports to avoid circular dependency at module load time
        from app.core.structured_log import log_warn
        from app.core.request_context import get_request_id
        rid = get_request_id()
        extra = {"request_id": rid} if rid else {}
        log_warn(
            _sq_logger,
            "slow_query",
            duration_ms=round(elapsed_ms, 1),
            statement=statement[:200],
            **extra,
        )


# ── end slow-query monitoring ──────────────────────────────────────────────────


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database():
    """Create all database tables"""
    # Import all models to ensure they are registered with Base
    Base.metadata.create_all(bind=engine)