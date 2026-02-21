"""add location_type enum to locations table

Revision ID: add_location_type
Revises: 8810b2f3eea5
Create Date: 2025-12-28 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_location_type'
down_revision = '8810b2f3eea5'
branch_labels = None
depends_on = None


def upgrade():
    """Add location_type enum to locations table"""
    # Check if enum type already exists (idempotent)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'locationtype')"
    ))
    enum_exists = result.scalar()

    # Create LocationType enum if it doesn't exist
    if not enum_exists:
        locationtype_enum = postgresql.ENUM('PARTNER', 'CENTER', name='locationtype', create_type=True)
        locationtype_enum.create(conn, checkfirst=True)

    # Check if location_type column exists
    from sqlalchemy import inspect
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('locations')]

    # Add location_type column if it doesn't exist
    if 'location_type' not in existing_columns:
        # Add column as nullable first
        op.add_column('locations',
            sa.Column('location_type',
                      postgresql.ENUM('PARTNER', 'CENTER', name='locationtype', create_type=False),
                      nullable=True,
                      comment="Location capability: PARTNER (Tournament+Mini only) or CENTER (all types)"))

        # Set default value for existing rows (all existing locations become PARTNER)
        op.execute("UPDATE locations SET location_type = 'PARTNER' WHERE location_type IS NULL")

        # Make column NOT NULL after backfilling
        op.alter_column('locations', 'location_type',
                       existing_type=postgresql.ENUM('PARTNER', 'CENTER', name='locationtype'),
                       nullable=False,
                       server_default='PARTNER')


def downgrade():
    """Remove location_type from locations table"""
    # Drop the column
    op.drop_column('locations', 'location_type')

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS locationtype")
