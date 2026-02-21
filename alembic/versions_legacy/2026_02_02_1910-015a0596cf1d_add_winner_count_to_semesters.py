"""add_winner_count_to_semesters

Revision ID: 015a0596cf1d
Revises: 2c77e5ab056f
Create Date: 2026-02-02 19:10:39.661626

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015a0596cf1d'
down_revision = '2c77e5ab056f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add winner_count column to semesters table for INDIVIDUAL_RANKING tournaments
    op.add_column('semesters', sa.Column('winner_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove winner_count column
    op.drop_column('semesters', 'winner_count')