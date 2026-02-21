"""add_license_issued_at_column

Revision ID: 9f961b92c5f3
Revises: add_tournament_game_fields
Create Date: 2026-01-02 09:27:06.197316

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f961b92c5f3'
down_revision = 'add_tournament_game_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add issued_at column (officially issued date, can differ from created_at)
    op.add_column('user_licenses', sa.Column('issued_at', sa.DateTime(), nullable=True))

    # 2. Set default values for existing records: issued_at = started_at (earliest known date)
    op.execute("""
        UPDATE user_licenses
        SET issued_at = started_at
        WHERE issued_at IS NULL
    """)

    # 3. Set Grand Master's official issuance date to 2014-01-01 for ALL licenses
    op.execute("""
        UPDATE user_licenses
        SET issued_at = '2014-01-01 00:00:00'
        WHERE user_id = 3
    """)

    # 4. Set expires_at based on annual renewal (January 31st deadline)
    # Current year (2026): expires_at should be 2026-01-31 (TESTING - expires THIS month!)
    op.execute("""
        UPDATE user_licenses
        SET expires_at = '2026-01-31 23:59:59'
        WHERE user_id = 3
          AND is_active = true
          AND (expires_at IS NULL OR expires_at < CURRENT_DATE)
    """)

    # 5. Create index for expiration queries
    op.create_index('idx_user_licenses_issued_at', 'user_licenses', ['issued_at'])


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_user_licenses_issued_at', table_name='user_licenses')

    # Drop issued_at column
    op.drop_column('user_licenses', 'issued_at')