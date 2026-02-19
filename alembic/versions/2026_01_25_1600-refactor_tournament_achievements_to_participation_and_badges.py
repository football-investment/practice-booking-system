"""refactor_tournament_achievements_to_participation_and_badges

Revision ID: 2026_01_25_1600
Revises: 2026_01_25_1500
Create Date: 2026-01-25 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_01_25_1600'
down_revision = '2026_01_25_1500'
branch_labels = None
depends_on = None


def upgrade():
    """
    Refactor tournament achievement system:
    1. Rename tournament_achievements → tournament_participations (skill/XP tracking)
    2. Create tournament_badges table (visual achievements with icons, titles, descriptions)
    """

    # 1. Rename tournament_achievements to tournament_participations
    op.rename_table('tournament_achievements', 'tournament_participations')

    # Rename indexes
    op.execute('ALTER INDEX ix_tournament_achievements_user_id RENAME TO ix_tournament_participations_user_id')
    op.execute('ALTER INDEX ix_tournament_achievements_semester_id RENAME TO ix_tournament_participations_semester_id')
    op.execute('ALTER INDEX uq_user_semester_achievement RENAME TO uq_user_semester_participation')

    # Rename constraints
    op.execute('ALTER TABLE tournament_participations RENAME CONSTRAINT tournament_achievements_pkey TO tournament_participations_pkey')
    op.execute('ALTER TABLE tournament_participations RENAME CONSTRAINT tournament_achievements_user_id_fkey TO tournament_participations_user_id_fkey')
    op.execute('ALTER TABLE tournament_participations RENAME CONSTRAINT tournament_achievements_semester_id_fkey TO tournament_participations_semester_id_fkey')

    # Rename sequence
    op.execute('ALTER SEQUENCE tournament_achievements_id_seq RENAME TO tournament_participations_id_seq')

    # 2. Create tournament_badges table for visual achievements
    op.create_table(
        'tournament_badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('badge_type', sa.String(length=50), nullable=False),
        sa.Column('badge_category', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=10), nullable=True),
        sa.Column('rarity', sa.String(length=20), server_default='COMMON', nullable=False),
        sa.Column('badge_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('earned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tournament_badges_user_id', 'tournament_badges', ['user_id'])
    op.create_index('ix_tournament_badges_semester_id', 'tournament_badges', ['semester_id'])
    op.create_index('ix_tournament_badges_badge_type', 'tournament_badges', ['badge_type'])
    op.create_index('ix_tournament_badges_badge_category', 'tournament_badges', ['badge_category'])


def downgrade():
    """
    Reverse the refactoring.
    """
    # Drop tournament_badges table
    op.drop_table('tournament_badges')

    # Rename tournament_participations back to tournament_achievements
    op.execute('ALTER SEQUENCE tournament_participations_id_seq RENAME TO tournament_achievements_id_seq')
    op.execute('ALTER TABLE tournament_participations RENAME CONSTRAINT uq_user_semester_participation TO uq_user_semester_achievement')
    op.execute('ALTER TABLE tournament_participations RENAME CONSTRAINT tournament_participations_semester_id_fkey TO tournament_achievements_semester_id_fkey')
    op.execute('ALTER TABLE tournament_participations RENAME CONSTRAINT tournament_participations_user_id_fkey TO tournament_achievements_user_id_fkey')
    op.execute('ALTER TABLE tournament_participations RENAME CONSTRAINT tournament_participations_pkey TO tournament_achievements_pkey')
    op.execute('ALTER INDEX uq_user_semester_participation RENAME TO uq_user_semester_achievement')
    op.execute('ALTER INDEX ix_tournament_participations_semester_id RENAME TO ix_tournament_achievements_semester_id')
    op.execute('ALTER INDEX ix_tournament_participations_user_id RENAME TO ix_tournament_achievements_user_id')
    op.rename_table('tournament_participations', 'tournament_achievements')
