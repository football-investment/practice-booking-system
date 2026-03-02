"""add_missing_unique_constraints

Revision ID: bb4309c201b6
Revises: 2026_02_24_1200
Create Date: 2026-03-02 19:47:17.346174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb4309c201b6'
down_revision = '2026_02_24_1200'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_tournament_rankings_tournament_user_type',
        'tournament_rankings',
        ['tournament_id', 'user_id', 'participant_type']
    )
    op.create_unique_constraint(
        'uq_xp_transactions_user_semester_type',
        'xp_transactions',
        ['user_id', 'semester_id', 'transaction_type']
    )
    op.create_unique_constraint(
        'uq_skill_rewards_user_source_skill',
        'skill_rewards',
        ['user_id', 'source_type', 'source_id', 'skill_name']
    )


def downgrade() -> None:
    op.drop_constraint('uq_skill_rewards_user_source_skill', 'skill_rewards', type_='unique')
    op.drop_constraint('uq_xp_transactions_user_semester_type', 'xp_transactions', type_='unique')
    op.drop_constraint('uq_tournament_rankings_tournament_user_type', 'tournament_rankings', type_='unique')