"""p0_1_remove_deprecated_tournament_fields

Revision ID: cac420a0d9b1
Revises: 458093a51598
Create Date: 2026-01-28 21:10:14.216418

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cac420a0d9b1'
down_revision = '458093a51598'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    P0.1: Remove deprecated tournament fields
    - tournament_type (string) - replaced by tournament_type_id (FK)
    - location_city, location_venue, location_address - replaced by location_id (FK)

    Data safety verified: All fields are NULL or unused.
    """
    # Drop deprecated location fields (replaced by location_id FK)
    op.drop_column('semesters', 'location_city')
    op.drop_column('semesters', 'location_venue')
    op.drop_column('semesters', 'location_address')

    # Drop deprecated tournament_type string field (replaced by tournament_type_id FK)
    op.drop_column('semesters', 'tournament_type')


def downgrade() -> None:
    """
    Restore deprecated fields (for rollback only - will be NULL)
    """
    # Restore tournament_type string field
    op.add_column('semesters', sa.Column('tournament_type', sa.String(50), nullable=True))

    # Restore location fields
    op.add_column('semesters', sa.Column('location_address', sa.String(500), nullable=True))
    op.add_column('semesters', sa.Column('location_venue', sa.String(200), nullable=True))
    op.add_column('semesters', sa.Column('location_city', sa.String(100), nullable=True))