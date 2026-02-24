"""add skill assessment lifecycle

Revision ID: 2026_02_24_1200
Revises: 2026_02_21_2100
Create Date: 2026-02-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_02_24_1200'
down_revision = '2026_02_21_2100'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add skill assessment lifecycle state machine.

    Implements production-grade skill assessment lifecycle with:
    - Explicit state definition (NOT_ASSESSED, ASSESSED, VALIDATED, ARCHIVED)
    - DB-level integrity constraint (CHECK constraint)
    - Validation tracking (optional validation per business rule)
    - Archive tracking (manual archive on new assessment creation)
    - State transition audit trail
    - UniqueConstraint for active assessments (1 per skill)

    Policy Decisions (approved 2026-02-24):
    - Validation: Optional (business rule determines requirement)
    - Archive: Manual only (triggered by new assessment creation)
    - DISPUTED state: Phase 2 (not included in this migration)
    """

    # ========================================================================
    # Step 1: Add status column with default 'ASSESSED'
    # ========================================================================
    op.execute("""
        ALTER TABLE football_skill_assessments
        ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ASSESSED'
    """)

    # ========================================================================
    # Step 2: Add CHECK constraint for valid status values
    # ========================================================================
    # Phase 1: 4 states (NOT_ASSESSED, ASSESSED, VALIDATED, ARCHIVED)
    # Phase 2 will add DISPUTED via ALTER constraint
    op.execute("""
        ALTER TABLE football_skill_assessments
        ADD CONSTRAINT ck_skill_assessment_status
        CHECK (status IN ('NOT_ASSESSED', 'ASSESSED', 'VALIDATED', 'ARCHIVED'))
    """)

    # ========================================================================
    # Step 3: Add validation tracking columns (nullable — optional validation)
    # ========================================================================
    op.execute("""
        ALTER TABLE football_skill_assessments
        ADD COLUMN IF NOT EXISTS validated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS requires_validation BOOLEAN NOT NULL DEFAULT FALSE
    """)

    # ========================================================================
    # Step 4: Add archive tracking columns
    # ========================================================================
    op.execute("""
        ALTER TABLE football_skill_assessments
        ADD COLUMN IF NOT EXISTS archived_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS archived_reason TEXT
    """)

    # ========================================================================
    # Step 5: Add state transition audit columns
    # ========================================================================
    op.execute("""
        ALTER TABLE football_skill_assessments
        ADD COLUMN IF NOT EXISTS previous_status VARCHAR(20),
        ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS status_changed_by INTEGER REFERENCES users(id) ON DELETE SET NULL
    """)

    # ========================================================================
    # Step 6: Create indexes for common query patterns
    # ========================================================================

    # Index: status queries (filter by status)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_skill_assessments_status
        ON football_skill_assessments(status)
    """)

    # Index: user + skill + status (most common query pattern)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_skill_assessments_user_skill_status
        ON football_skill_assessments(user_license_id, skill_name, status)
    """)

    # Index: requires_validation flag (for admin validation queue)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_skill_assessments_requires_validation
        ON football_skill_assessments(requires_validation)
        WHERE requires_validation = TRUE AND status = 'ASSESSED'
    """)

    # ========================================================================
    # Step 7: Create partial unique index for active assessments
    # ========================================================================
    # Business Rule: Only 1 active (ASSESSED or VALIDATED) assessment per skill
    # This prevents race conditions during concurrent assessment creation
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_skill_assessment_active
        ON football_skill_assessments(user_license_id, skill_name)
        WHERE status IN ('ASSESSED', 'VALIDATED')
    """)

    # ========================================================================
    # Step 8: Backfill existing data
    # ========================================================================

    # 8a. Set status to 'ASSESSED' for all existing assessments
    op.execute("""
        UPDATE football_skill_assessments
        SET status = 'ASSESSED',
            status_changed_at = assessed_at,
            status_changed_by = assessed_by
        WHERE status IS NULL OR status = ''
    """)

    # 8b. Mark old assessments as VALIDATED (grace period)
    # Business rule: Assessments older than 30 days assumed valid (no validation required)
    op.execute("""
        UPDATE football_skill_assessments
        SET status = 'VALIDATED',
            validated_at = assessed_at,
            validated_by = assessed_by,
            status_changed_at = assessed_at
        WHERE assessed_at < NOW() - INTERVAL '30 days'
          AND status = 'ASSESSED'
    """)

    # 8c. Set requires_validation based on current state
    # Default: no validation required (can be updated by business logic later)
    op.execute("""
        UPDATE football_skill_assessments
        SET requires_validation = FALSE
        WHERE requires_validation IS NULL
    """)

    # ========================================================================
    # Step 9: Add comment documentation
    # ========================================================================
    op.execute("""
        COMMENT ON COLUMN football_skill_assessments.status IS
        'Lifecycle state: NOT_ASSESSED, ASSESSED, VALIDATED, ARCHIVED. Enforced by CHECK constraint.'
    """)

    op.execute("""
        COMMENT ON COLUMN football_skill_assessments.requires_validation IS
        'Business rule flag: TRUE if this assessment requires admin validation before use. Determined at creation time based on license level, instructor tenure, and skill category.'
    """)

    op.execute("""
        COMMENT ON INDEX uq_skill_assessment_active IS
        'Ensures only 1 active (ASSESSED or VALIDATED) assessment per (user_license_id, skill_name). Prevents duplicate assessments during concurrent creation.'
    """)


def downgrade():
    """
    Remove skill assessment lifecycle state machine.

    WARNING: This will drop all lifecycle tracking data (status, validation, archive history).
    Only use for rollback during development/testing.
    """

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS uq_skill_assessment_active")
    op.execute("DROP INDEX IF EXISTS ix_skill_assessments_requires_validation")
    op.execute("DROP INDEX IF EXISTS ix_skill_assessments_user_skill_status")
    op.execute("DROP INDEX IF EXISTS ix_skill_assessments_status")

    # Drop CHECK constraint
    op.execute("ALTER TABLE football_skill_assessments DROP CONSTRAINT IF EXISTS ck_skill_assessment_status")

    # Drop columns (reverse order of creation)
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS status_changed_by")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS status_changed_at")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS previous_status")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS archived_reason")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS archived_by")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS requires_validation")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS validated_at")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS validated_by")
    op.execute("ALTER TABLE football_skill_assessments DROP COLUMN IF EXISTS status")
