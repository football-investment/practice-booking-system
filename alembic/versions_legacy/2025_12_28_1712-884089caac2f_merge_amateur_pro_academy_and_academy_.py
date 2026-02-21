"""merge amateur_pro_academy and academy_spec_types

Revision ID: 884089caac2f
Revises: add_academy_spec_types, add_amateur_pro_academy_types
Create Date: 2025-12-28 17:12:44.755054

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '884089caac2f'
down_revision = ('add_academy_spec_types', 'add_amateur_pro_academy_types')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass