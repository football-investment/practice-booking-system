"""Rename FIFA Classic display label to FClassic Player (PR-FC-1A).

Updates the public-facing label for the legacy 'fifa' design from
'FIFA Classic' to 'FClassic Player'.  The design_id PK ('fifa') is
intentionally unchanged — that migration is deferred to PR-FC-1B.

Revision ID: 2026_05_30_1200
Revises:     2026_05_29_1200
"""
from alembic import op

revision = "2026_05_30_1200"
down_revision = "2026_05_29_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE card_designs SET label = 'FClassic Player' WHERE id = 'fifa'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE card_designs SET label = 'FIFA Classic' WHERE id = 'fifa'"
    )
