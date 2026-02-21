"""add_postal_code_to_locations

Revision ID: ff330f866c45
Revises: 67aa5bfdad3c
Create Date: 2025-12-13 10:30:56.015784

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff330f866c45'
down_revision = '67aa5bfdad3c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('locations', sa.Column('postal_code', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('locations', 'postal_code')