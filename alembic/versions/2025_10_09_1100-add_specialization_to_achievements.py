"""Add specialization_id to user_achievements

Revision ID: add_spec_achievements
Revises: spec_level_system
Create Date: 2025-10-09 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_spec_achievements'
down_revision = 'spec_level_system'
branch_labels = None
depends_on = None


def upgrade():
    # Add specialization_id column to user_achievements (nullable for general achievements)
    op.add_column('user_achievements',
        sa.Column('specialization_id', sa.String(50), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_user_achievement_specialization',
        'user_achievements', 'specializations',
        ['specialization_id'], ['id']
    )

    # Add index for faster queries
    op.create_index(
        'ix_user_achievements_specialization_id',
        'user_achievements',
        ['specialization_id']
    )


def downgrade():
    op.drop_index('ix_user_achievements_specialization_id', table_name='user_achievements')
    op.drop_constraint('fk_user_achievement_specialization', 'user_achievements', type_='foreignkey')
    op.drop_column('user_achievements', 'specialization_id')
