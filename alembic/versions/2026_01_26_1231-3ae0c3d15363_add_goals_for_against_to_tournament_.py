"""add_goals_for_against_to_tournament_rankings

Revision ID: 3ae0c3d15363
Revises: 777c4e7a6618
Create Date: 2026-01-26 12:31:00.686235

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3ae0c3d15363'
down_revision = '777c4e7a6618'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add goals_for and goals_against columns to tournament_rankings table
    op.add_column('tournament_rankings', sa.Column('goals_for', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('tournament_rankings', sa.Column('goals_against', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    # Remove goals_for and goals_against columns
    op.drop_column('tournament_rankings', 'goals_against')
    op.drop_column('tournament_rankings', 'goals_for')