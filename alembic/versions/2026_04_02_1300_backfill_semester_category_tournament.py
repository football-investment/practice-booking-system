"""backfill semester_category = TOURNAMENT for legacy tournament semesters

Revision ID: 2026_04_02_1300
Revises: 2026_04_02_1200
Create Date: 2026-04-02 13:00:00.000000

M-BACKFILL: semesters WHERE semester_category IS NULL AND id IN tournament_configurations
            → semester_category = 'TOURNAMENT'

The semester_category column was added as nullable (2026_03_15_1000) with the explicit
comment "Data migration (backfill from existing data) is a separate step."
This migration fulfils that note.

Logic:
  - Only NULL rows touched (existing ACADEMY_SEASON / MINI_SEASON / CAMP rows unchanged)
  - Only sets TOURNAMENT where a TournamentConfiguration row exists
    (TournamentConfiguration is created exclusively for tournament-type semesters)
  - Idempotent: on a clean DB no NULL-category tournament rows exist → UPDATE affects 0 rows

Downgrade: NULLs out the backfilled rows. Emergency pre-prod rollback only.
"""
from alembic import op

revision = '2026_04_02_1300'
down_revision = '2026_04_02_1200'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE semesters
        SET semester_category = 'TOURNAMENT'
        WHERE semester_category IS NULL
          AND id IN (SELECT semester_id FROM tournament_configurations)
    """)


def downgrade() -> None:
    # Emergency rollback only — cannot distinguish backfilled rows from manually set ones
    op.execute("""
        UPDATE semesters
        SET semester_category = NULL
        WHERE semester_category = 'TOURNAMENT'
          AND id IN (SELECT semester_id FROM tournament_configurations)
    """)
