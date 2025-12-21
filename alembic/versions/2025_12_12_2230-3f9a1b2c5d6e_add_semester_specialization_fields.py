"""Add specialization and age_group fields to semesters

Revision ID: 3f9a1b2c5d6e
Revises: 2345def67890
Create Date: 2025-12-12 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f9a1b2c5d6e'
down_revision = '2345def67890'
branch_labels = None
depends_on = None


def upgrade():
    # Add specialization_type column
    op.add_column('semesters', sa.Column(
        'specialization_type',
        sa.String(50),
        nullable=True,
        comment='Specialization type (e.g., LFA_PLAYER_PRE, GANCUJU_PLAYER_YOUTH)'
    ))

    # Add age_group column
    op.add_column('semesters', sa.Column(
        'age_group',
        sa.String(20),
        nullable=True,
        comment='Age group (PRE, YOUTH, AMATEUR, PRO)'
    ))

    # Add theme column
    op.add_column('semesters', sa.Column(
        'theme',
        sa.String(200),
        nullable=True,
        comment='Marketing theme (e.g., "New Year Challenge", "Q1", "Fall")'
    ))

    # Add focus_description column
    op.add_column('semesters', sa.Column(
        'focus_description',
        sa.String(500),
        nullable=True,
        comment='Focus description (e.g., "Újévi fogadalmak, friss kezdés")'
    ))

    # Create index on specialization_type + age_group for faster queries
    op.create_index(
        'ix_semesters_spec_age',
        'semesters',
        ['specialization_type', 'age_group']
    )


def downgrade():
    op.drop_index('ix_semesters_spec_age', table_name='semesters')
    op.drop_column('semesters', 'focus_description')
    op.drop_column('semesters', 'theme')
    op.drop_column('semesters', 'age_group')
    op.drop_column('semesters', 'specialization_type')
