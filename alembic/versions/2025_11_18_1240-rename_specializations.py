"""rename_specializations

Revision ID: rename_specializations
Revises: add_parental_consent
Create Date: 2025-11-18 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'rename_specializations'
down_revision = 'add_parental_consent'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Rename specializations to match LFA Education Center curriculum:
    - PLAYER → GANCUJU_PLAYER (4000-year Chinese Cuju martial arts style)
    - COACH → LFA_COACH (LFA's own coaching system, NOT UEFA/FIFA)
    - Add new specialization: LFA_FOOTBALL_PLAYER (age-group based football player)
    - INTERNSHIP remains unchanged (startup/business program)

    This migration updates existing user records and enum type.

    CORRECTED: Create new enum FIRST, then update data, then swap enum types.
    """

    # Step 1: Create new enum type with updated values
    # PostgreSQL requires creating a new enum type with the new values
    op.execute("""
        CREATE TYPE specializationtype_new AS ENUM (
            'GANCUJU_PLAYER',
            'LFA_FOOTBALL_PLAYER',
            'LFA_COACH',
            'INTERNSHIP',
            'PLAYER',
            'COACH'
        )
    """)

    # Step 2: Alter column to use new enum type (this converts existing data)
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN specialization TYPE specializationtype_new
        USING specialization::text::specializationtype_new
    """)

    # Step 3: Now update existing user records with new names
    # PLAYER → GANCUJU_PLAYER
    op.execute("""
        UPDATE users
        SET specialization = 'GANCUJU_PLAYER'
        WHERE specialization = 'PLAYER'
    """)

    # COACH → LFA_COACH
    op.execute("""
        UPDATE users
        SET specialization = 'LFA_COACH'
        WHERE specialization = 'COACH'
    """)

    # Step 4: Convert sessions and projects tables to use new enum BEFORE dropping old one
    connection = op.get_bind()

    # Check and update sessions table
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'sessions'
            AND column_name = 'target_specialization'
        )
    """))
    session_column_exists = result.scalar()

    if session_column_exists:
        # Convert sessions.target_specialization to new enum type
        op.execute("""
            ALTER TABLE sessions
            ALTER COLUMN target_specialization TYPE specializationtype_new
            USING target_specialization::text::specializationtype_new
        """)

        # Update the values
        op.execute("""
            UPDATE sessions
            SET target_specialization = 'GANCUJU_PLAYER'
            WHERE target_specialization = 'PLAYER'
        """)

        op.execute("""
            UPDATE sessions
            SET target_specialization = 'LFA_COACH'
            WHERE target_specialization = 'COACH'
        """)

    # Check and update projects table
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'projects'
            AND column_name = 'target_specialization'
        )
    """))
    project_column_exists = result.scalar()

    if project_column_exists:
        # Convert projects.target_specialization to new enum type
        op.execute("""
            ALTER TABLE projects
            ALTER COLUMN target_specialization TYPE specializationtype_new
            USING target_specialization::text::specializationtype_new
        """)

        # Update the values
        op.execute("""
            UPDATE projects
            SET target_specialization = 'GANCUJU_PLAYER'
            WHERE target_specialization = 'PLAYER'
        """)

        op.execute("""
            UPDATE projects
            SET target_specialization = 'LFA_COACH'
            WHERE target_specialization = 'COACH'
        """)

    # Step 5: NOW we can safely drop old enum type and rename new one
    op.execute("DROP TYPE specializationtype")
    op.execute("ALTER TYPE specializationtype_new RENAME TO specializationtype")

    # Update user_progress specialization if exists
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'user_progress'
            AND column_name = 'specialization'
        )
    """))
    column_exists = result.scalar()

    if column_exists:
        op.execute("""
            UPDATE user_progress
            SET specialization = 'GANCUJU_PLAYER'
            WHERE specialization = 'PLAYER'
        """)

        op.execute("""
            UPDATE user_progress
            SET specialization = 'LFA_COACH'
            WHERE specialization = 'COACH'
        """)

    # Update licenses specialization_type if exists
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'licenses'
            AND column_name = 'specialization_type'
        )
    """))
    column_exists = result.scalar()

    if column_exists:
        op.execute("""
            UPDATE licenses
            SET specialization_type = 'GANCUJU_PLAYER'
            WHERE specialization_type = 'PLAYER'
        """)

        op.execute("""
            UPDATE licenses
            SET specialization_type = 'LFA_COACH'
            WHERE specialization_type = 'COACH'
        """)


def downgrade() -> None:
    """
    Revert specialization names to old values.
    Note: LFA_FOOTBALL_PLAYER records will be lost (set to NULL).
    """

    # Step 1: Update existing records back to old names
    # GANCUJU_PLAYER → PLAYER
    op.execute("""
        UPDATE users
        SET specialization = 'PLAYER'
        WHERE specialization = 'GANCUJU_PLAYER'
    """)

    # LFA_COACH → COACH
    op.execute("""
        UPDATE users
        SET specialization = 'COACH'
        WHERE specialization = 'LFA_COACH'
    """)

    # LFA_FOOTBALL_PLAYER → NULL (no equivalent in old system)
    op.execute("""
        UPDATE users
        SET specialization = NULL
        WHERE specialization = 'LFA_FOOTBALL_PLAYER'
    """)

    # Step 2: Recreate enum with old values
    op.execute("""
        CREATE TYPE specializationtype_old AS ENUM (
            'PLAYER',
            'COACH',
            'INTERNSHIP'
        )
    """)

    op.execute("""
        ALTER TABLE users
        ALTER COLUMN specialization TYPE specializationtype_old
        USING specialization::text::specializationtype_old
    """)

    op.execute("DROP TYPE specializationtype")
    op.execute("ALTER TYPE specializationtype_old RENAME TO specializationtype")

    # Revert other tables (sessions, projects, user_progress, licenses) similarly
    connection = op.get_bind()

    # Sessions
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'sessions'
            AND column_name = 'target_specialization'
        )
    """))
    if result.scalar():
        op.execute("UPDATE sessions SET target_specialization = 'PLAYER' WHERE target_specialization = 'GANCUJU_PLAYER'")
        op.execute("UPDATE sessions SET target_specialization = 'COACH' WHERE target_specialization = 'LFA_COACH'")
        op.execute("UPDATE sessions SET target_specialization = NULL WHERE target_specialization = 'LFA_FOOTBALL_PLAYER'")

    # Projects
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'projects'
            AND column_name = 'target_specialization'
        )
    """))
    if result.scalar():
        op.execute("UPDATE projects SET target_specialization = 'PLAYER' WHERE target_specialization = 'GANCUJU_PLAYER'")
        op.execute("UPDATE projects SET target_specialization = 'COACH' WHERE target_specialization = 'LFA_COACH'")
        op.execute("UPDATE projects SET target_specialization = NULL WHERE target_specialization = 'LFA_FOOTBALL_PLAYER'")

    # User Progress
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'user_progress'
            AND column_name = 'specialization'
        )
    """))
    if result.scalar():
        op.execute("UPDATE user_progress SET specialization = 'PLAYER' WHERE specialization = 'GANCUJU_PLAYER'")
        op.execute("UPDATE user_progress SET specialization = 'COACH' WHERE specialization = 'LFA_COACH'")
        op.execute("UPDATE user_progress SET specialization = NULL WHERE specialization = 'LFA_FOOTBALL_PLAYER'")

    # Licenses
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'licenses'
            AND column_name = 'specialization_type'
        )
    """))
    if result.scalar():
        op.execute("UPDATE licenses SET specialization_type = 'PLAYER' WHERE specialization_type = 'GANCUJU_PLAYER'")
        op.execute("UPDATE licenses SET specialization_type = 'COACH' WHERE specialization_type = 'LFA_COACH'")
        op.execute("UPDATE licenses SET specialization_type = NULL WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'")
