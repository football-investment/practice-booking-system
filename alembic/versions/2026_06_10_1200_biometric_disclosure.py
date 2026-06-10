"""biometric disclosure table — PR-7A user tájékoztató modal

Revision ID: 2026_06_10_1200
Revises: 2026_06_10_1100
Create Date: 2026-06-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision    = "2026_06_10_1200"
down_revision = "2026_06_10_1100"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "user_biometric_disclosures",
        sa.Column("id",                 sa.Integer(),     nullable=False),
        sa.Column("user_id",            sa.Integer(),     nullable=False),
        sa.Column("disclosure_version", sa.String(20),   nullable=False),
        sa.Column("accepted_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("acceptance_ip",      sa.String(45),   nullable=True),
        sa.Column("revoked_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason",  sa.String(200),  nullable=True),
        sa.Column("is_active",          sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("created_at",         sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            ondelete="CASCADE",
        ),
    )

    # Standard lookup index on user_id
    op.create_index(
        "ix_user_biometric_disclosures_user_id",
        "user_biometric_disclosures",
        ["user_id"],
    )

    # Partial unique: only one active disclosure per user at any time.
    # Prevents duplicate active acceptances; allows multiple historical rows.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_user_biometric_disclosures_active
        ON user_biometric_disclosures (user_id)
        WHERE is_active = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_user_biometric_disclosures_active")
    op.drop_index("ix_user_biometric_disclosures_user_id",
                  table_name="user_biometric_disclosures")
    op.drop_table("user_biometric_disclosures")