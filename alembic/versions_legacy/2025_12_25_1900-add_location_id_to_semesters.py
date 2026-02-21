"""add location_id to semesters

Revision ID: 2025_12_25_1900
Revises: 2025_12_23_1900, add_semester_status
Create Date: 2025-12-25 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_12_25_1900'
down_revision = ('2025_12_23_1900', 'add_semester_status')  # Merge migration
branch_labels = None
depends_on = None


def upgrade():
    # Add location_id column to semesters table
    op.add_column('semesters',
        sa.Column('location_id', sa.Integer(), nullable=True,
                 comment='FK to locations table - replaces location_city/venue/address')
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_semesters_location',
        'semesters', 'locations',
        ['location_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for performance
    op.create_index(
        'ix_semesters_location_id',
        'semesters',
        ['location_id']
    )

    # Migrate existing data: Match location_city to locations.city
    # Budapest → location_id=1, Budaörs → location_id=2
    op.execute("""
        UPDATE semesters s
        SET location_id = l.id
        FROM locations l
        WHERE s.location_city = l.city
    """)


def downgrade():
    op.drop_index('ix_semesters_location_id', table_name='semesters')
    op.drop_constraint('fk_semesters_location', 'semesters', type_='foreignkey')
    op.drop_column('semesters', 'location_id')
