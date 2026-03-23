"""Add unique constraint on user_licenses(user_id, specialization_type)

Prevents duplicate licenses for the same user+specialization pair.
Before adding the constraint, removes any existing duplicates (keeping oldest id).

Revision ID: 2026_03_20_1000
Revises: 2026_03_18_1800
Create Date: 2026-03-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '2026_03_20_1000'
down_revision = '2026_03_18_1800'
branch_labels = None
depends_on = None


def upgrade():
    # Remove any existing duplicates — keep the oldest license (lowest id)
    op.execute("""
        DELETE FROM user_licenses
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM user_licenses
            GROUP BY user_id, specialization_type
        )
    """)

    op.create_unique_constraint(
        'uq_user_license_spec',
        'user_licenses',
        ['user_id', 'specialization_type']
    )


def downgrade():
    op.drop_constraint('uq_user_license_spec', 'user_licenses', type_='unique')
