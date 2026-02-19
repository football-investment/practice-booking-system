"""add_recommended_locked_flags_to_game_presets

Revision ID: 458093a51598
Revises: f5c8522cfe5e
Create Date: 2026-01-28 20:45:46.370579

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '458093a51598'
down_revision = 'f5c8522cfe5e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_recommended and is_locked columns to game_presets
    op.add_column('game_presets', sa.Column('is_recommended', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('game_presets', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'))

    # Create indexes for performance
    op.create_index('ix_game_presets_recommended', 'game_presets', ['is_recommended'])
    op.create_index('ix_game_presets_locked', 'game_presets', ['is_locked'])

    # Mark GanFootvolley as recommended (most balanced preset)
    op.execute("""
        UPDATE game_presets
        SET is_recommended = true
        WHERE code = 'gan_footvolley'
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_game_presets_locked', table_name='game_presets')
    op.drop_index('ix_game_presets_recommended', table_name='game_presets')

    # Drop columns
    op.drop_column('game_presets', 'is_locked')
    op.drop_column('game_presets', 'is_recommended')