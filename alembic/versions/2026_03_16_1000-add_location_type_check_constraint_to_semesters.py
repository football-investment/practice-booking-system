"""Add DB-level check constraint: Academy Season semesters require CENTER campus location

Revision ID: 2026_03_16_1000
Revises: 2026_03_15_1600
Create Date: 2026-03-16 10:00:00.000000

Business rule enforcement at the database layer:
- Academy Season specialization types (LFA_PLAYER_*_ACADEMY) can only be hosted at CENTER locations.
- PARTNER locations may only host Mini Season and Tournament types.

This constraint acts as a last line of defence against bypassing application-layer validation
(e.g. direct DB writes, future admin tools that skip LocationValidationService).

Technique: PostgreSQL CHECK constraints can invoke STABLE functions, so we create a helper
function that walks the campus → location join and returns the location_type string.
The constraint is a no-op when campus_id IS NULL (location not specified) or when
specialization_type is not an Academy type, so existing rows without a campus are unaffected.
"""

from alembic import op
import sqlalchemy as sa

# Alembic metadata
revision = "2026_03_16_1000"
down_revision = "2026_03_15_1600"
branch_labels = None
depends_on = None

# The four Academy Season specialization_type values that require a CENTER location.
_ACADEMY_TYPES = (
    "LFA_PLAYER_PRE_ACADEMY",
    "LFA_PLAYER_YOUTH_ACADEMY",
    "LFA_PLAYER_AMATEUR_ACADEMY",
    "LFA_PLAYER_PRO_ACADEMY",
)


def upgrade() -> None:
    # 1. Create a STABLE helper function that resolves location_type for a given campus_id.
    #    Using STABLE (not VOLATILE) allows PostgreSQL to cache the result within a query.
    op.execute("""
        CREATE OR REPLACE FUNCTION campus_location_type(p_campus_id INTEGER)
        RETURNS TEXT
        LANGUAGE sql
        STABLE
        AS $$
            SELECT l.location_type::text
            FROM campuses c
            JOIN locations l ON l.id = c.location_id
            WHERE c.id = p_campus_id
        $$;
    """)

    # 2. Add the CHECK constraint.
    #    Passes when ANY of these conditions hold:
    #      a) campus_id is NULL           → no location assigned, app-layer validates
    #      b) specialization_type is NULL → no type restriction applies
    #      c) specialization_type is not an Academy type → PARTNER locations are fine
    #      d) the campus's location is a CENTER
    op.execute("""
        ALTER TABLE semesters
        ADD CONSTRAINT chk_academy_season_requires_center_location
        CHECK (
            campus_id IS NULL
            OR specialization_type IS NULL
            OR specialization_type NOT IN (
                'LFA_PLAYER_PRE_ACADEMY',
                'LFA_PLAYER_YOUTH_ACADEMY',
                'LFA_PLAYER_AMATEUR_ACADEMY',
                'LFA_PLAYER_PRO_ACADEMY'
            )
            OR campus_location_type(campus_id) = 'CENTER'
        );
    """)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE semesters "
        "DROP CONSTRAINT IF EXISTS chk_academy_season_requires_center_location;"
    )
    op.execute("DROP FUNCTION IF EXISTS campus_location_type(INTEGER);")
