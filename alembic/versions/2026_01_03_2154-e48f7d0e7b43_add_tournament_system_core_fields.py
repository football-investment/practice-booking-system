"""add_tournament_system_core_fields

Revision ID: e48f7d0e7b43
Revises: 775ecc8293d0
Create Date: 2026-01-03 21:54:32.679362

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e48f7d0e7b43'
down_revision = '775ecc8293d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tournament type and participant type columns to semesters
    op.add_column('semesters', sa.Column('tournament_type', sa.String(50), nullable=True))
    op.add_column('semesters', sa.Column('participant_type', sa.String(50), nullable=True, server_default='INDIVIDUAL'))
    op.add_column('semesters', sa.Column('is_multi_day', sa.Boolean(), nullable=True, server_default='false'))

    # Backfill existing tournaments
    op.execute("""
        UPDATE semesters
        SET tournament_type = 'LEAGUE',
            participant_type = 'INDIVIDUAL',
            is_multi_day = false
        WHERE code LIKE 'TOURN-%'
    """)

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), nullable=True),
        sa.Column('captain_user_id', sa.Integer(), nullable=True),
        sa.Column('specialization_type', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['captain_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_teams_code', 'teams', ['code'])

    # Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_members_team_user')
    )
    op.create_index('ix_team_members_team_id', 'team_members', ['team_id'])
    op.create_index('ix_team_members_user_id', 'team_members', ['user_id'])

    # Create tournament_team_enrollments table
    op.create_table(
        'tournament_team_enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('enrollment_date', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('payment_verified', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('semester_id', 'team_id', name='uq_tournament_team_enrollment')
    )
    op.create_index('ix_tournament_team_enrollments_semester', 'tournament_team_enrollments', ['semester_id'])
    op.create_index('ix_tournament_team_enrollments_team', 'tournament_team_enrollments', ['team_id'])

    # Create tournament_rankings table
    op.create_table(
        'tournament_rankings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('participant_type', sa.String(50), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('points', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('wins', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('losses', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('draws', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tournament_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'user_id', name='uq_tournament_rankings_user'),
        sa.UniqueConstraint('tournament_id', 'team_id', name='uq_tournament_rankings_team')
    )
    op.create_index('ix_tournament_rankings_tournament', 'tournament_rankings', ['tournament_id'])
    op.create_index('ix_tournament_rankings_rank', 'tournament_rankings', ['tournament_id', 'rank'])

    # Create tournament_stats table
    op.create_table(
        'tournament_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('total_participants', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_teams', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_matches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completed_matches', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_revenue', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_attendance_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tournament_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id')
    )
    op.create_index('ix_tournament_stats_tournament', 'tournament_stats', ['tournament_id'])

    # Create tournament_rewards table
    op.create_table(
        'tournament_rewards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.String(20), nullable=False),
        sa.Column('xp_amount', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('credits_reward', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('badge_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tournament_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tournament_id', 'position', name='uq_tournament_rewards')
    )
    op.create_index('ix_tournament_rewards_tournament', 'tournament_rewards', ['tournament_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_tournament_rewards_tournament', 'tournament_rewards')
    op.drop_table('tournament_rewards')

    op.drop_index('ix_tournament_stats_tournament', 'tournament_stats')
    op.drop_table('tournament_stats')

    op.drop_index('ix_tournament_rankings_rank', 'tournament_rankings')
    op.drop_index('ix_tournament_rankings_tournament', 'tournament_rankings')
    op.drop_table('tournament_rankings')

    op.drop_index('ix_tournament_team_enrollments_team', 'tournament_team_enrollments')
    op.drop_index('ix_tournament_team_enrollments_semester', 'tournament_team_enrollments')
    op.drop_table('tournament_team_enrollments')

    op.drop_index('ix_team_members_user_id', 'team_members')
    op.drop_index('ix_team_members_team_id', 'team_members')
    op.drop_table('team_members')

    op.drop_index('ix_teams_code', 'teams')
    op.drop_table('teams')

    # Remove columns from semesters
    op.drop_column('semesters', 'is_multi_day')
    op.drop_column('semesters', 'participant_type')
    op.drop_column('semesters', 'tournament_type')