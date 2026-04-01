"""Add team_enrollment_cost to tournament_configurations + team_invites table

Revision ID: 2026_03_23_1100
Revises: 2026_03_23_1000
Create Date: 2026-03-23 11:00:00.000000

Changes:
- tournament_configurations.team_enrollment_cost INTEGER NOT NULL DEFAULT 0
- CREATE TABLE team_invites (id, team_id, invited_user_id, invited_by_id, status, created_at, responded_at)
- UNIQUE INDEX uq_team_invite_pending (team_id, invited_user_id) WHERE status = 'PENDING'
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '2026_03_23_1100'
down_revision = '2026_03_23_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add team_enrollment_cost to tournament_configurations
    op.add_column(
        'tournament_configurations',
        sa.Column(
            'team_enrollment_cost',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Credits deducted from captain when creating a team for this tournament. 0 = free.'
        )
    )

    # 2. Create team_invites table
    op.create_table(
        'team_invites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('team_id', sa.Integer(),
                  sa.ForeignKey('teams.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('invited_user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('invited_by_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_team_invites_team_id', 'team_invites', ['team_id'])
    op.create_index('ix_team_invites_invited_user_id', 'team_invites', ['invited_user_id'])

    # Partial unique index: only one PENDING invite per (team, user) pair
    op.execute(
        """
        CREATE UNIQUE INDEX uq_team_invite_pending
        ON team_invites (team_id, invited_user_id)
        WHERE status = 'PENDING'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_team_invite_pending")
    op.drop_index('ix_team_invites_invited_user_id', table_name='team_invites')
    op.drop_index('ix_team_invites_team_id', table_name='team_invites')
    op.drop_table('team_invites')
    op.drop_column('tournament_configurations', 'team_enrollment_cost')
