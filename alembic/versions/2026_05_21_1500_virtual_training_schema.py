"""Add virtual_training_games and virtual_training_attempts tables

Phase 1: inactive game presets only — no active user routes.
Provides the data model foundation for the Virtual Training mini-game system.

Tables:
  virtual_training_games    — game preset catalogue (is_active=False by default)
  virtual_training_attempts — per-user attempt records with XP + skill deltas

Revision ID: 2026_05_21_1500
Revises:     2026_05_21_1400
Create Date: 2026-05-21 15:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "2026_05_21_1500"
down_revision = "2026_05_21_1400"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "virtual_training_games",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("game_type", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("base_xp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_daily_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("skill_targets", JSONB(), nullable=False, server_default="{}"),
        sa.Column("config", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_vt_games_code", "virtual_training_games", ["code"], unique=True)

    op.create_table(
        "virtual_training_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "game_id",
            sa.Integer(),
            sa.ForeignKey("virtual_training_games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("invalid_reason", sa.String(100), nullable=True),
        sa.Column("score_raw", sa.Float(), nullable=True),
        sa.Column("score_normalized", sa.Float(), nullable=True),
        sa.Column("avg_reaction_ms", sa.Float(), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skill_deltas", JSONB(), nullable=False, server_default="{}"),
        sa.Column("attempt_index_today", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.UniqueConstraint("idempotency_key", name="uq_vt_attempts_idempotency_key"),
    )
    op.create_index("ix_vt_attempts_user_id", "virtual_training_attempts", ["user_id"])
    op.create_index("ix_vt_attempts_game_id", "virtual_training_attempts", ["game_id"])
    op.create_index(
        "ix_vt_attempts_user_game_started",
        "virtual_training_attempts",
        ["user_id", "game_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_table("virtual_training_attempts")
    op.drop_table("virtual_training_games")
