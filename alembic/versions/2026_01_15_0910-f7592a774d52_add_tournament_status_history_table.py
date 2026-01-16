"""add_tournament_status_history_table

Revision ID: f7592a774d52
Revises: f222a15fc815
Create Date: 2026-01-15 09:10:07.876974

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f7592a774d52'
down_revision = 'f222a15fc815'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create tournament_status_history table for audit logging
    """
    op.create_table(
        'tournament_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.String(length=50), nullable=False),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tournament_id'], ['semesters.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_tournament_status_history_id'),
        'tournament_status_history',
        ['id'],
        unique=False
    )
    op.create_index(
        op.f('ix_tournament_status_history_tournament_id'),
        'tournament_status_history',
        ['tournament_id'],
        unique=False
    )


def downgrade() -> None:
    """
    Drop tournament_status_history table
    """
    op.drop_index(op.f('ix_tournament_status_history_tournament_id'), table_name='tournament_status_history')
    op.drop_index(op.f('ix_tournament_status_history_id'), table_name='tournament_status_history')
    op.drop_table('tournament_status_history')