"""add_defending_skill_to_lfa_player

Revision ID: 2345def67890
Revises: 574791caded6
Create Date: 2025-12-11 22:45:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2345def67890'
down_revision = '574791caded6'
branch_labels = None
depends_on = None


def upgrade():
    """Add defending_avg column to lfa_player_licenses table"""

    # Add defending_avg column
    op.add_column('lfa_player_licenses',
        sa.Column('defending_avg', sa.Numeric(5, 2), nullable=True, server_default='0')
    )

    # Add check constraint for defending_avg (0-100 range)
    op.create_check_constraint(
        'lfa_player_licenses_defending_avg_check',
        'lfa_player_licenses',
        'defending_avg >= 0 AND defending_avg <= 100'
    )

    # Drop old overall_avg computed column
    op.drop_column('lfa_player_licenses', 'overall_avg')

    # Re-create overall_avg with NEW formula including defending
    # (heading + shooting + crossing + passing + dribbling + ball_control + defending) / 7.0
    op.execute("""
        ALTER TABLE lfa_player_licenses
        ADD COLUMN overall_avg NUMERIC(5,2)
        GENERATED ALWAYS AS (
            (heading_avg + shooting_avg + crossing_avg + passing_avg + dribbling_avg + ball_control_avg + defending_avg) / 7.0
        ) STORED
    """)


def downgrade():
    """Remove defending_avg column and revert overall_avg to 6 skills"""

    # Drop new overall_avg (7 skills)
    op.drop_column('lfa_player_licenses', 'overall_avg')

    # Re-create old overall_avg (6 skills only)
    op.execute("""
        ALTER TABLE lfa_player_licenses
        ADD COLUMN overall_avg NUMERIC(5,2)
        GENERATED ALWAYS AS (
            (heading_avg + shooting_avg + crossing_avg + passing_avg + dribbling_avg + ball_control_avg) / 6.0
        ) STORED
    """)

    # Drop check constraint
    op.drop_constraint('lfa_player_licenses_defending_avg_check', 'lfa_player_licenses')

    # Drop defending_avg column
    op.drop_column('lfa_player_licenses', 'defending_avg')
