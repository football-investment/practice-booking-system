"""Add number_of_legs, track_home_away to tournament_configurations; leg_number to sessions

Revision ID: 2026_03_28_1200
Revises: 2026_03_27_1000
Create Date: 2026-03-28 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '2026_03_28_1200'
down_revision = '2026_03_27_1000'
branch_labels = None
depends_on = None


def upgrade():
    # tournament_configurations: number of legs + home/away tracking
    op.add_column(
        'tournament_configurations',
        sa.Column(
            'number_of_legs',
            sa.Integer(),
            nullable=False,
            server_default='1',
            comment='Number of legs for HEAD_TO_HEAD round robin. 1=single, 2=home+away, etc.',
        ),
    )
    op.add_column(
        'tournament_configurations',
        sa.Column(
            'track_home_away',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='If True, even legs reverse each pairing (home/away swap)',
        ),
    )
    op.create_check_constraint(
        'ck_tournament_configurations_number_of_legs_positive',
        'tournament_configurations',
        'number_of_legs >= 1',
    )

    # sessions: which leg a session belongs to (NULL for non-leg formats)
    op.add_column(
        'sessions',
        sa.Column(
            'leg_number',
            sa.SmallInteger(),
            nullable=True,
            comment='Leg number within a multi-leg round robin (1-N). NULL for knockout/swiss/INDIVIDUAL_RANKING.',
        ),
    )


def downgrade():
    op.drop_column('sessions', 'leg_number')
    op.drop_constraint(
        'ck_tournament_configurations_number_of_legs_positive',
        'tournament_configurations',
        type_='check',
    )
    op.drop_column('tournament_configurations', 'track_home_away')
    op.drop_column('tournament_configurations', 'number_of_legs')
