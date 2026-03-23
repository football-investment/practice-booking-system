"""Add TEAM participant_type support: participant_team_ids, team_id on participations, team ranking index

Revision ID: 2026_03_23_1000
Revises: 2026_03_20_1000
Create Date: 2026-03-23 10:00:00.000000

Changes:
- sessions.participant_team_ids ARRAY(Integer)  — team-ids for TEAM format sessions
- tournament_participations.team_id FK → teams.id (ON DELETE SET NULL)
- UNIQUE INDEX uq_tournament_rankings_tournament_team_type (WHERE team_id IS NOT NULL)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '2026_03_23_1000'
down_revision = '2026_03_20_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. sessions.participant_team_ids
    op.add_column(
        'sessions',
        sa.Column(
            'participant_team_ids',
            postgresql.ARRAY(sa.Integer()),
            nullable=True,
            comment="For TEAM tournaments: list of team_ids in this session. "
                    "Mutually exclusive with participant_user_ids."
        )
    )

    # 2. tournament_participations.team_id
    op.add_column(
        'tournament_participations',
        sa.Column(
            'team_id',
            sa.Integer(),
            nullable=True,
            comment="For TEAM tournaments: which team this member's reward came from."
        )
    )
    op.create_foreign_key(
        'fk_tournament_participations_team_id',
        'tournament_participations',
        'teams',
        ['team_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        'ix_tournament_participations_team_id',
        'tournament_participations',
        ['team_id'],
        unique=False
    )

    # 3. Partial unique index for team rankings
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tournament_rankings_tournament_team_type
        ON tournament_rankings (tournament_id, team_id, participant_type)
        WHERE team_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_tournament_rankings_tournament_team_type")
    op.drop_index('ix_tournament_participations_team_id', table_name='tournament_participations')
    op.drop_constraint('fk_tournament_participations_team_id', 'tournament_participations', type_='foreignkey')
    op.drop_column('tournament_participations', 'team_id')
    op.drop_column('sessions', 'participant_team_ids')
