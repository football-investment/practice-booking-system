"""add_uq_booking_attendance_constraint

Revision ID: 2026_03_09_1500
Revises: 2026_03_09_1400
Create Date: 2026-03-09 15:00:00.000000

Closes the DB-drift gap found during the Sprint 53+ constraint audit:

  Gap: The squashed baseline schema (2026_02_21_0859) contains:
         ALTER TABLE attendance ADD CONSTRAINT uq_booking_attendance UNIQUE (booking_id);
       but this constraint was never applied to the live database (the squash
       migration was introduced after the DB already existed, so the CREATE TABLE
       path — which includes the constraint — was never executed).

  Fix: Add the missing UNIQUE(booking_id) constraint as a proper incremental
       migration so all environments (dev, CI, production) are consistent.

Constraint design:
  UNIQUE(booking_id) — standard (non-partial) unique constraint

  PostgreSQL uniqueness semantics for NULLs:
    NULL values are never considered equal to each other in PostgreSQL's
    UNIQUE constraint logic (per SQL standard).  Multiple rows with
    booking_id IS NULL are therefore ALLOWED — correct for tournament
    sessions that have no booking.

  Combined with 2026_03_09_1400 (partial unique on NULL booking_ids),
  the two constraints together cover the full attendance uniqueness matrix:

    booking_id IS NOT NULL  →  uq_booking_attendance  (this migration)
    booking_id IS NULL      →  uq_attendance_user_session_no_booking  (prev)

Pre-migration data check (2026-03-09):
  - 83 attendance rows, 0 with NULL booking_id
  - 0 duplicate booking_id values  → safe to apply, no backfill needed

Idempotency note:
  Fresh databases (CI, new dev setups) already have this constraint via the
  squashed baseline migration (1ec11c73ea62). The upgrade() guard checks
  pg_constraint before creating, so the migration is safe to apply in both
  environments:
    - Live prod DB: constraint absent → created here ✓
    - Fresh CI DB:  constraint present (from baseline) → skipped ✓
"""
from alembic import op
from sqlalchemy import text


revision = '2026_03_09_1500'
down_revision = '2026_03_09_1400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conname='uq_booking_attendance' AND conrelid='attendance'::regclass"
        )
    ).scalar()
    if not exists:
        op.create_unique_constraint(
            'uq_booking_attendance',
            'attendance',
            ['booking_id'],
        )


def downgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conname='uq_booking_attendance' AND conrelid='attendance'::regclass"
        )
    ).scalar()
    if exists:
        op.drop_constraint('uq_booking_attendance', 'attendance', type_='unique')
