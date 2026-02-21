"""add_unique_constraint_tournament_rankings

Revision ID: 69606094ea87
Revises: 831da85c3ff5
Create Date: 2026-02-01 19:57:06.042104

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '69606094ea87'
down_revision = '831da85c3ff5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add unique constraint to tournament_rankings table.

    Prevents DUAL FINALIZATION PATH bug where both sandbox and production
    write rankings for the same (tournament_id, user_id, participant_type),
    creating duplicate rows with conflicting data.

    Critical fix for Tournament 227 bug where 16 rankings existed for 8 players.
    """
    # Step 1: Delete existing duplicates (keep lowest id for each unique key)
    op.execute("""
        DELETE FROM tournament_rankings a
        USING tournament_rankings b
        WHERE a.id > b.id
        AND a.tournament_id = b.tournament_id
        AND a.user_id = b.user_id
        AND a.participant_type = b.participant_type;
    """)

    # Step 2: Add unique constraint
    op.create_unique_constraint(
        'uq_tournament_rankings_tournament_user_type',
        'tournament_rankings',
        ['tournament_id', 'user_id', 'participant_type']
    )


def downgrade() -> None:
    """Remove unique constraint"""
    op.drop_constraint(
        'uq_tournament_rankings_tournament_user_type',
        'tournament_rankings',
        type_='unique'
    )