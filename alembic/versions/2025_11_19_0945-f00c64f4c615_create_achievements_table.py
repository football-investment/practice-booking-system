"""create_achievements_table

Revision ID: f00c64f4c615
Revises: 27e3f401dc7f
Create Date: 2025-11-19 09:45:40.509727

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f00c64f4c615'
down_revision = '27e3f401dc7f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create achievements table
    op.create_table(
        'achievements',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(10), nullable=True),
        sa.Column('xp_reward', sa.Integer(), server_default='0'),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('requirements', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )

    # Create indexes for performance
    op.create_index('ix_achievements_code', 'achievements', ['code'])
    op.create_index('ix_achievements_category', 'achievements', ['category'])
    op.create_index('ix_achievements_is_active', 'achievements', ['is_active'])

    # Add achievement_id column to user_achievements table
    op.add_column('user_achievements', sa.Column('achievement_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_user_achievements_achievement_id',
        'user_achievements', 'achievements',
        ['achievement_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_user_achievements_achievement_id', 'user_achievements', ['achievement_id'])


def downgrade() -> None:
    op.drop_index('ix_user_achievements_achievement_id', table_name='user_achievements')
    op.drop_constraint('fk_user_achievements_achievement_id', 'user_achievements', type_='foreignkey')
    op.drop_column('user_achievements', 'achievement_id')
    op.drop_index('ix_achievements_is_active', table_name='achievements')
    op.drop_index('ix_achievements_category', table_name='achievements')
    op.drop_index('ix_achievements_code', table_name='achievements')
    op.drop_table('achievements')