"""Add academy_id_color to user_licenses

Revision ID: 2026_06_09_1100
Revises:     2026_06_09_1000
Create Date: 2026-06-09

Adds a dedicated column to store the active Academy ID card colour for each
LFA Football Player licence.  This column belongs exclusively to the
Academy ID colour system (card_type_id='academy_id') and is independent of
the Player Card / Welcome Card / Challenge Card theme/colour fields.

Default 'official' covers all existing rows without a backfill step.
"""

import sqlalchemy as sa
from alembic import op

revision      = "2026_06_09_1100"
down_revision = "2026_06_09_1000"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "user_licenses",
        sa.Column(
            "academy_id_color",
            sa.String(50),
            nullable=False,
            server_default="official",
            comment="Active Academy ID card colour (academy_id colour family). "
                    "Independent of Player/Welcome/Challenge card theme fields.",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_licenses", "academy_id_color")
