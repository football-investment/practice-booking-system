"""users.secondary_nationality — optional dual citizenship field

Revision ID: 2026_05_10_1000
Revises: 2026_05_05_1000
Create Date: 2026-05-10 10:00:00.000000

Domain: players may hold dual citizenship; secondary_nationality stores the
        second ISO 3166-1 alpha-2 code. Primary nationality remains in
        users.nationality. Secondary is always NULL for existing rows.
"""
from alembic import op
import sqlalchemy as sa

revision = '2026_05_10_1000'
down_revision = '2026_05_05_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'secondary_nationality',
            sa.String(),
            nullable=True,
            comment='Optional second nationality ISO 3166-1 alpha-2 code (e.g. BR for Brazil).',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'secondary_nationality')
