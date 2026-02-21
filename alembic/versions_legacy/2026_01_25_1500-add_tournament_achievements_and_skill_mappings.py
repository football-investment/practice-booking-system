"""add_tournament_achievements_and_skill_mappings

Revision ID: 2026_01_25_1500
Revises: 2026_01_25_1230
Create Date: 2026-01-25 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_01_25_1500'
down_revision = '2026_01_25_1230'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create tables for tournament achievement and skill integration system:
    1. tournament_skill_mappings: Maps tournaments to skills they develop
    2. tournament_achievements: Tracks player achievements in tournaments
    3. skill_point_conversion_rates: Defines XP conversion rates per skill category
    """

    # 1. Create tournament_skill_mappings table
    op.create_table(
        'tournament_skill_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('skill_name', sa.String(length=100), nullable=False),
        sa.Column('skill_category', sa.String(length=50), nullable=True),
        sa.Column('weight', sa.Numeric(precision=3, scale=2), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tournament_skill_mappings_semester_id', 'tournament_skill_mappings', ['semester_id'])

    # 2. Create tournament_achievements table
    op.create_table(
        'tournament_achievements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('placement', sa.Integer(), nullable=True),
        sa.Column('skill_points_awarded', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('xp_awarded', sa.Integer(), nullable=False),
        sa.Column('credits_awarded', sa.Integer(), nullable=False),
        sa.Column('achieved_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'semester_id', name='uq_user_semester_achievement')
    )
    op.create_index('ix_tournament_achievements_user_id', 'tournament_achievements', ['user_id'])
    op.create_index('ix_tournament_achievements_semester_id', 'tournament_achievements', ['semester_id'])

    # 3. Create skill_point_conversion_rates table
    op.create_table(
        'skill_point_conversion_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('skill_category', sa.String(length=50), nullable=False),
        sa.Column('xp_per_point', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('skill_category', name='uq_skill_category')
    )

    # Insert default conversion rates
    op.execute("""
        INSERT INTO skill_point_conversion_rates (skill_category, xp_per_point) VALUES
        ('Technical', 10),
        ('Tactical', 10),
        ('Physical', 8),
        ('Mental', 12),
        ('football_skill', 10)
    """)


def downgrade():
    """
    Drop all tournament achievement tables.
    """
    op.drop_table('skill_point_conversion_rates')
    op.drop_table('tournament_achievements')
    op.drop_table('tournament_skill_mappings')
