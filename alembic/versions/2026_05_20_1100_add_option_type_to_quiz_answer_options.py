"""Add option_type column to quiz_answer_options

Introduces a string-backed discriminator column with three values:
  FIXED           — all 375 legacy options (default)
  CORRECT_VARIANT — one of several correct phrasings for a question
  DISTRACTOR      — member of a wrong-answer pool; runtime selects 3

All existing rows receive server_default='FIXED', preserving full backward
compatibility with the existing adaptive-learning session logic.

Revision ID: 2026_05_20_1100
Revises:     2026_05_20_1000
Create Date: 2026-05-20 11:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_05_20_1100"
down_revision = "2026_05_20_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quiz_answer_options",
        sa.Column(
            "option_type",
            sa.String(20),
            nullable=False,
            server_default="FIXED",
        ),
    )


def downgrade() -> None:
    op.drop_column("quiz_answer_options", "option_type")
