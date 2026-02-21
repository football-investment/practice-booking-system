"""create_campuses_table

Revision ID: a1b2c3d4e5f6
Revises: e0b638299ddb
Create Date: 2025-12-18 18:00:00.000000

Campus model - specific facility/venue within a location.

Hierarchy:
- Location = City level (Budapest, Budaörs)
- Campus = Venue within city (Buda Campus, Pest Campus, Main Field)

Business Logic:
- Instructor is bound to a LOCATION (city)
- Instructor can teach at ANY campus within that location
- Instructor CANNOT teach at different locations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create campuses table
    op.create_table(
        'campuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False, comment='Foreign key to locations table (city level)'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Campus name (e.g., "Buda Campus", "Main Field")'),
        sa.Column('venue', sa.String(length=200), nullable=True, comment='Venue/facility name'),
        sa.Column('address', sa.String(length=500), nullable=True, comment='Full street address'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Additional notes about the campus'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether this campus is currently active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign key with cascade delete
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),

        # Unique constraint: campus name must be unique within a location
        sa.UniqueConstraint('location_id', 'name', name='uix_location_campus_name')
    )

    # Create indexes for common queries
    op.create_index('ix_campuses_location_id', 'campuses', ['location_id'])
    op.create_index('ix_campuses_is_active', 'campuses', ['is_active'])
    op.create_index('ix_campuses_name', 'campuses', ['name'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_campuses_name', table_name='campuses')
    op.drop_index('ix_campuses_is_active', table_name='campuses')
    op.drop_index('ix_campuses_location_id', table_name='campuses')

    # Drop table
    op.drop_table('campuses')
