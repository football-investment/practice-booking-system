"""create_match_structures_and_match_results

Creates the match_structures and match_results tables defined in
app/models/match_structure.py.

These tables were present in the ORM models but never migrated to the DB.
The missing migration caused BUG-TC01: when test_campus_scope_guard_integration.py
imported app.main, the MatchStructure.session backref was registered on the Session
SQLAlchemy mapper. Subsequent Session deletions triggered a SELECT on the
non-existent match_structures table, raising UndefinedTable and failing
test_core.py::TestDeleteTournament cascade tests.

Revision ID: 2026_03_02_2115
Revises: bb4309c201b6
Create Date: 2026-03-02 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_03_02_2115'
down_revision = 'bb4309c201b6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create match_structures and match_results tables.

    Schema derived directly from app/models/match_structure.py ORM definitions.
    Uses PostgreSQL native ENUM types for match_format and scoring_type.
    """

    # ========================================================================
    # Step 1: Create PostgreSQL ENUM types
    # ========================================================================
    op.execute("""
        CREATE TYPE matchformat AS ENUM (
            'INDIVIDUAL_RANKING',
            'HEAD_TO_HEAD',
            'TEAM_MATCH',
            'TIME_BASED',
            'SKILL_RATING'
        )
    """)

    op.execute("""
        CREATE TYPE scoringtype AS ENUM (
            'PLACEMENT',
            'WIN_LOSS',
            'SCORE_BASED',
            'TIME_BASED',
            'SKILL_RATING'
        )
    """)

    # ========================================================================
    # Step 2: Create match_structures table
    # ========================================================================
    # One MatchStructure per Session (unique FK).
    # CASCADE DELETE: when a Session is deleted, its MatchStructure is removed.
    op.execute("""
        CREATE TABLE match_structures (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
            match_format matchformat NOT NULL,
            scoring_type scoringtype NOT NULL,
            structure_config JSONB
        )
    """)

    op.execute("""
        CREATE INDEX ix_match_structures_id ON match_structures (id)
    """)

    # ========================================================================
    # Step 3: Create match_results table
    # ========================================================================
    # Each MatchResult belongs to a MatchStructure.
    # CASCADE DELETE: when a MatchStructure is deleted, its MatchResults go too.
    op.execute("""
        CREATE TABLE match_results (
            id SERIAL PRIMARY KEY,
            match_structure_id INTEGER NOT NULL REFERENCES match_structures(id) ON DELETE CASCADE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            team_identifier VARCHAR(50),
            performance_data JSONB NOT NULL,
            derived_rank INTEGER,
            recorded_at VARCHAR DEFAULT NOW()::TEXT
        )
    """)

    op.execute("""
        CREATE INDEX ix_match_results_id ON match_results (id)
    """)


def downgrade():
    """
    Drop match_results, match_structures tables and their ENUM types.
    """
    op.execute("DROP TABLE IF EXISTS match_results")
    op.execute("DROP TABLE IF EXISTS match_structures")
    op.execute("DROP TYPE IF EXISTS scoringtype")
    op.execute("DROP TYPE IF EXISTS matchformat")
