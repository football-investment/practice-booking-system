"""
Migration rollback tests — Sprint 53+ attendance constraint migrations

Covers two migrations:
  2026_03_09_1400  uq_attendance_user_session_no_booking  (partial unique, NULL booking)
  2026_03_09_1500  uq_booking_attendance                  (unique on non-NULL booking_id)

Design principles
─────────────────
* All downgrade calls use EXPLICIT revision targets (never "-1").
  This makes tests stable regardless of how many migrations are added later.
* An autouse fixture calls `upgrade head` after each test so the DB is
  always left at the current head — even if a test body raises an exception.
* Tests are schema-level (DDL) and NOT SAVEPOINT-isolated. Run explicitly:

    pytest tests/integration/test_migration_rollback.py -v

Dependency: `alembic upgrade head` must have been run before this suite executes.
"""
import pytest
from sqlalchemy import text
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from app.database import engine


# ── Revision constants ────────────────────────────────────────────────────────

REV_BASE     = "2026_03_02_2115"   # revision before 1400 (down_revision of 1400)
REV_1400     = "2026_03_09_1400"   # partial unique index (NULL booking)
REV_1500     = "2026_03_09_1500"   # uq_booking_attendance (non-NULL booking)

INDEX_1400   = "uq_attendance_user_session_no_booking"
CONSTRAINT_1500 = "uq_booking_attendance"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg() -> Config:
    return Config("alembic.ini")


def _current_revision() -> str | None:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def _index_exists(name: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM pg_indexes WHERE tablename='attendance' AND indexname=:n"),
            {"n": name},
        ).fetchone()
    return row is not None


def _constraint_exists(name: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM pg_constraint "
                "WHERE conname=:n AND conrelid='attendance'::regclass"
            ),
            {"n": name},
        ).fetchone()
    return row is not None


# ── Shared fixture ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def restore_to_head():
    """Always restore DB to head after each test (schema cleanup)."""
    yield
    command.upgrade(_cfg(), "head")


# ── Class 1: migration 2026_03_09_1400 ───────────────────────────────────────

class TestMigration1400PartialUniqueIndex:
    """Round-trip tests for uq_attendance_user_session_no_booking."""

    def test_precondition_index_exists(self):
        """Index must be present when tests start (requires upgrade head first)."""
        assert _index_exists(INDEX_1400), (
            f"'{INDEX_1400}' not found. Run 'alembic upgrade head' before this suite."
        )

    def test_downgrade_to_base_removes_index(self):
        """Explicit downgrade to REV_BASE drops uq_attendance_user_session_no_booking."""
        command.downgrade(_cfg(), REV_BASE)
        assert not _index_exists(INDEX_1400)

    def test_downgrade_to_base_sets_correct_revision(self):
        command.downgrade(_cfg(), REV_BASE)
        assert _current_revision() == REV_BASE

    def test_downgrade_to_rev1400_keeps_index_removes_constraint(self):
        """Downgrade only to 1400 (drops 1500 constraint) — 1400 index survives."""
        command.downgrade(_cfg(), REV_1400)
        assert _index_exists(INDEX_1400), "1400 index must survive downgrade to 1400"
        assert not _constraint_exists(CONSTRAINT_1500), "1500 constraint must be gone"

    def test_round_trip_restores_index(self):
        """Downgrade to REV_BASE then upgrade head → index is back."""
        command.downgrade(_cfg(), REV_BASE)
        assert not _index_exists(INDEX_1400)
        command.upgrade(_cfg(), "head")
        assert _index_exists(INDEX_1400)

    def test_index_definition_is_partial_and_unique(self):
        """Recreated index must be UNIQUE and scoped to booking_id IS NULL."""
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT indexdef FROM pg_indexes WHERE tablename='attendance' AND indexname=:n"),
                {"n": INDEX_1400},
            ).fetchone()
        assert row is not None
        d = row[0].lower()
        assert "unique" in d
        assert "booking_id is null" in d
        assert "user_id" in d
        assert "session_id" in d

    def test_pk_and_fk_survive_downgrade_to_base(self):
        """Core attendance constraints must not be affected by rollback."""
        command.downgrade(_cfg(), REV_BASE)
        assert _constraint_exists("attendance_pkey")
        assert _constraint_exists("attendance_booking_id_fkey")


# ── Class 2: migration 2026_03_09_1500 ───────────────────────────────────────

class TestMigration1500BookingAttendanceUnique:
    """Round-trip tests for uq_booking_attendance UNIQUE(booking_id)."""

    def test_precondition_constraint_exists(self):
        """Constraint must be present at head (requires upgrade head first)."""
        assert _constraint_exists(CONSTRAINT_1500), (
            f"'{CONSTRAINT_1500}' not found. Run 'alembic upgrade head' first."
        )
        assert _current_revision() == REV_1500

    def test_downgrade_to_rev1400_removes_constraint(self):
        """downgrade 1400 drops uq_booking_attendance; partial index survives."""
        command.downgrade(_cfg(), REV_1400)
        assert not _constraint_exists(CONSTRAINT_1500)
        assert _index_exists(INDEX_1400), "partial index must survive downgrade to 1400"

    def test_downgrade_to_rev1400_sets_correct_revision(self):
        command.downgrade(_cfg(), REV_1400)
        assert _current_revision() == REV_1400

    def test_round_trip_restores_constraint(self):
        """Downgrade to REV_1400 then upgrade head → constraint is back."""
        command.downgrade(_cfg(), REV_1400)
        assert not _constraint_exists(CONSTRAINT_1500)
        command.upgrade(_cfg(), "head")
        assert _constraint_exists(CONSTRAINT_1500)
        assert _current_revision() == REV_1500

    def test_constraint_allows_multiple_null_booking_ids(self):
        """PostgreSQL UNIQUE ignores NULL values — multiple NULL booking_ids
        must NOT raise an IntegrityError (tournament sessions use NULL booking_id)."""
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT COUNT(*) FROM pg_constraint "
                    "WHERE conname=:n AND contype='u' AND conrelid='attendance'::regclass"
                ),
                {"n": CONSTRAINT_1500},
            ).fetchone()
        assert row[0] == 1, "uq_booking_attendance must be a UNIQUE constraint (contype='u')"

    def test_pk_fk_and_1400_index_survive_downgrade(self):
        """Downgrade of 1500 must not affect any pre-existing constraints."""
        command.downgrade(_cfg(), REV_1400)
        assert _constraint_exists("attendance_pkey")
        assert _constraint_exists("attendance_booking_id_fkey")
        assert _index_exists(INDEX_1400)

    def test_double_upgrade_idempotent(self):
        """upgrade head twice is safe (second is a no-op)."""
        command.upgrade(_cfg(), "head")
        command.upgrade(_cfg(), "head")
        assert _constraint_exists(CONSTRAINT_1500)
        assert _current_revision() == REV_1500
