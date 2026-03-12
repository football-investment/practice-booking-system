"""drop_location_venue

Drop the deprecated Location.venue column.
All venue data now lives in the Campus model (campus.venue).

Revision ID: 2026_03_12_1200
Revises: 2026_03_12_1100
Create Date: 2026-03-12 12:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_03_12_1200'
down_revision = '2026_03_12_1100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('locations', 'venue')


def downgrade() -> None:
    op.add_column(
        'locations',
        sa.Column('venue', sa.String(200), nullable=True,
                  comment='DEPRECATED: Restored by downgrade. Use Campus.venue instead.')
    )
