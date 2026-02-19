"""enrollment_concurrency_guards

Revision ID: eb01concurr00
Revises: se002residx00
Create Date: 2026-02-18 10:00:00.000000

Phase B enrollment concurrency hardening:

B-01 — Partial unique index on (user_id, semester_id) WHERE is_active = TRUE
    Prevents RACE-02: two concurrent POST /enroll for the same player+tournament
    both passing the application-layer duplicate check and then both INSERTing.
    The partial index makes the second INSERT raise IntegrityError, which the
    endpoint catches and returns HTTP 409.

    NOTE: The existing constraint uq_semester_enrollments_user_semester_license
    includes user_license_id and therefore allows a player to have two active
    enrollment rows with different licenses (unintended for tournament use).
    This new partial unique covers (user_id, semester_id) alone while active.

B-04 — CHECK constraint credit_balance >= 0 on users table
    Defense-in-depth for RACE-03 (credit double-spend). Even if the atomic
    SQL UPDATE in the application layer fails to catch a concurrent drain,
    the DB-level CHECK constraint will reject any UPDATE that would make
    credit_balance negative, rolling back the transaction and raising
    IntegrityError before persisting bad data.

Audit ref: docs/features/ENROLLMENT_CONCURRENCY_AUDIT_2026-02-18.md
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb01concurr00'
down_revision = 'se002residx00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # B-01: Partial unique index — prevents duplicate active enrollments
    # -------------------------------------------------------------------------
    # Partial unique: only one active enrollment per (user, tournament).
    # Cancelled rows (is_active=FALSE) are excluded so a player can re-enroll
    # after cancellation (new row is created; old cancelled row remains).
    op.create_index(
        'uq_active_enrollment',
        'semester_enrollments',
        ['user_id', 'semester_id'],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # -------------------------------------------------------------------------
    # B-04: CHECK constraint — credit_balance floor at 0
    # -------------------------------------------------------------------------
    # Defense-in-depth: even with the atomic SQL UPDATE in enroll.py, this
    # constraint ensures no UPDATE can persist a negative credit_balance.
    op.create_check_constraint(
        'chk_credit_balance_non_negative',
        'users',
        'credit_balance >= 0',
    )


def downgrade() -> None:
    op.drop_constraint('chk_credit_balance_non_negative', 'users', type_='check')
    op.drop_index('uq_active_enrollment', table_name='semester_enrollments')
