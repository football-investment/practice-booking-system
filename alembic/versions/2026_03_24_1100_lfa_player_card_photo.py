"""LFA player card photo URL column on user_licenses

Revision ID: 2026_03_24_1100
Revises: 2026_03_24_1000
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_03_24_1100"
down_revision = "2026_03_24_1000"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_licenses",
        sa.Column("player_card_photo_url", sa.String(512), nullable=True),
    )


def downgrade():
    op.drop_column("user_licenses", "player_card_photo_url")
