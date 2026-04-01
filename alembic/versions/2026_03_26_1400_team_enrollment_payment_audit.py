"""team enrollment payment audit fields

Revision ID: 2026_03_26_1400
Revises: 2026_03_25_1200
Create Date: 2026-03-26 14:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_03_26_1400"
down_revision = "2026_03_25_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tournament_team_enrollments",
        sa.Column("payment_verified_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "tournament_team_enrollments",
        sa.Column("payment_verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tournament_team_enrollments", "payment_verified_at")
    op.drop_column("tournament_team_enrollments", "payment_verified_by")
