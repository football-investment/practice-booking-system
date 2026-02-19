"""standardize_tournament_phase_enum

Phase 2.1: Enum Standardization
- Normalize legacy string values to canonical TournamentPhase enum values
- Create PostgreSQL enum type
- Convert tournament_phase column from VARCHAR to ENUM

Revision ID: 41b554a1284c
Revises: 015a0596cf1d
Create Date: 2026-02-07 11:56:50.735303

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '41b554a1284c'
down_revision = '015a0596cf1d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Standardize tournament_phase to use canonical TournamentPhase enum values.

    Current database state (from production data analysis):
    - GROUP_STAGE (1269 rows) - canonical ✅
    - Group Stage (930 rows) - legacy → GROUP_STAGE
    - INDIVIDUAL_RANKING (623 rows) - canonical ✅
    - KNOCKOUT (78 rows) - canonical ✅
    - Knockout (400 rows) - legacy → KNOCKOUT
    - Knockout Stage (296 rows) - legacy → KNOCKOUT
    - League - Round Robin (2577 rows) - legacy → GROUP_STAGE

    Total: 6,173 sessions to normalize
    """

    # Step 1: Normalize legacy string values to canonical enum values
    print("Phase 2.1 Migration: Normalizing tournament_phase values...")

    # Mapping: legacy value → canonical TournamentPhase enum value
    op.execute("""
        UPDATE sessions
        SET tournament_phase = CASE tournament_phase
            -- GROUP_STAGE normalizations
            WHEN 'Group Stage' THEN 'GROUP_STAGE'
            WHEN 'League - Round Robin' THEN 'GROUP_STAGE'

            -- KNOCKOUT normalizations
            WHEN 'Knockout' THEN 'KNOCKOUT'
            WHEN 'Knockout Stage' THEN 'KNOCKOUT'

            -- Already canonical values (no change)
            WHEN 'GROUP_STAGE' THEN 'GROUP_STAGE'
            WHEN 'KNOCKOUT' THEN 'KNOCKOUT'
            WHEN 'INDIVIDUAL_RANKING' THEN 'INDIVIDUAL_RANKING'
            WHEN 'FINALS' THEN 'FINALS'
            WHEN 'PLACEMENT' THEN 'PLACEMENT'
            WHEN 'SWISS' THEN 'SWISS'

            ELSE tournament_phase  -- Preserve any unknown values (for safety)
        END
        WHERE tournament_phase IS NOT NULL;
    """)

    print("✅ Normalized all legacy tournament_phase values")

    # Step 2: Create PostgreSQL enum type
    print("Creating tournament_phase_enum type...")

    tournament_phase_enum = postgresql.ENUM(
        'GROUP_STAGE',
        'KNOCKOUT',
        'FINALS',
        'PLACEMENT',
        'INDIVIDUAL_RANKING',
        'SWISS',
        name='tournament_phase_enum',
        create_type=True
    )
    tournament_phase_enum.create(op.get_bind(), checkfirst=True)

    print("✅ Created tournament_phase_enum PostgreSQL type")

    # Step 3: Convert column from VARCHAR to ENUM
    print("Converting tournament_phase column to enum type...")

    # Use ALTER TYPE for safe conversion
    op.execute("""
        ALTER TABLE sessions
        ALTER COLUMN tournament_phase TYPE tournament_phase_enum
        USING tournament_phase::tournament_phase_enum;
    """)

    print("✅ Converted tournament_phase to enum type")
    print("✅ Phase 2.1 Migration complete!")


def downgrade() -> None:
    """
    Rollback: Convert enum back to VARCHAR and restore legacy values.

    Note: This preserves canonical enum values as VARCHAR strings.
    Legacy format restoration is NOT performed to avoid data loss.
    """

    print("Phase 2.1 Migration Rollback: Converting tournament_phase back to VARCHAR...")

    # Step 1: Convert enum column back to VARCHAR
    op.execute("""
        ALTER TABLE sessions
        ALTER COLUMN tournament_phase TYPE VARCHAR(50)
        USING tournament_phase::text;
    """)

    print("✅ Converted tournament_phase back to VARCHAR")

    # Step 2: Drop PostgreSQL enum type
    print("Dropping tournament_phase_enum type...")

    tournament_phase_enum = postgresql.ENUM(
        'GROUP_STAGE',
        'KNOCKOUT',
        'FINALS',
        'PLACEMENT',
        'INDIVIDUAL_RANKING',
        'SWISS',
        name='tournament_phase_enum'
    )
    tournament_phase_enum.drop(op.get_bind(), checkfirst=True)

    print("✅ Dropped tournament_phase_enum type")
    print("⚠️  Note: Legacy format values (e.g., 'Group Stage') were NOT restored")
    print("✅ Phase 2.1 Migration rollback complete!")