"""Add al_import_logs table

Records each admin import operation with per-file outcome details.

Revision ID: 2026_05_20_1200
Revises:     2026_05_20_1100
Create Date: 2026-05-20 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_05_20_1200"
down_revision = "2026_05_20_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "al_import_logs",
        sa.Column("id",                sa.Integer(),    nullable=False),
        sa.Column("operator_id",       sa.Integer(),    nullable=True),
        sa.Column("spec",              sa.String(64),   nullable=False),
        sa.Column("status",            sa.String(20),   nullable=False),
        sa.Column("completed_at",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("files_submitted",   sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("files_ok",          sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("files_skipped",     sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("files_error",       sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("quizzes_created",   sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("questions_created", sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("options_fixed",     sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("options_variant",   sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("options_distractor",sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("details_json",      sa.Text(),       nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_al_import_logs_id", "al_import_logs", ["id"], unique=False)
    op.create_index("ix_al_import_logs_spec", "al_import_logs", ["spec"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_al_import_logs_spec", table_name="al_import_logs")
    op.drop_index("ix_al_import_logs_id",   table_name="al_import_logs")
    op.drop_table("al_import_logs")
