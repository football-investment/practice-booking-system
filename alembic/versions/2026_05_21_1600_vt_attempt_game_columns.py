"""Add gameplay columns to virtual_training_attempts

Phase 2: Color Reaction MVP — adds 5 columns required for anti-farming
validation and result display:
  duration_seconds  — total elapsed seconds from first stimulus to last click
  stimuli_count     — number of stimuli presented (used for too_few_stimuli guard)
  correct_count     — stimuli clicked within the response window
  error_count       — stimuli where the window expired before click
  min_reaction_ms   — fastest single reaction time in this attempt

Revision ID: 2026_05_21_1600
Revises:     2026_05_21_1500
Create Date: 2026-05-21 16:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_05_21_1600"
down_revision = "2026_05_21_1500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("virtual_training_attempts",
        sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column("virtual_training_attempts",
        sa.Column("stimuli_count", sa.SmallInteger(), nullable=True))
    op.add_column("virtual_training_attempts",
        sa.Column("correct_count", sa.SmallInteger(), nullable=True))
    op.add_column("virtual_training_attempts",
        sa.Column("error_count", sa.SmallInteger(), nullable=True))
    op.add_column("virtual_training_attempts",
        sa.Column("min_reaction_ms", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("virtual_training_attempts", "min_reaction_ms")
    op.drop_column("virtual_training_attempts", "error_count")
    op.drop_column("virtual_training_attempts", "correct_count")
    op.drop_column("virtual_training_attempts", "stimuli_count")
    op.drop_column("virtual_training_attempts", "duration_seconds")
