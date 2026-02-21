"""merge session groups and master hiring

Revision ID: 35f1375883f8
Revises: 2025_12_25_1900, 2025_12_25_2000
Create Date: 2025-12-25 20:02:51.432558

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35f1375883f8'
down_revision = ('2025_12_25_1900', '2025_12_25_2000')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass