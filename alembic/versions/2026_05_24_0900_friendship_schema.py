"""Add friendships table and social notification types

Creates the minimal social graph (Friendship model) required for
friend-gated features such as Virtual Training challenges.

Tables:
  friendships — directed friendship rows (requester → addressee)

Enum extensions:
  notificationtype — adds FRIEND_REQUEST_RECEIVED, FRIEND_REQUEST_ACCEPTED

Revision ID: 2026_05_24_0900
Revises:     2026_05_22_1100
Create Date: 2026-05-24 09:00:00
"""
import sqlalchemy as sa
from alembic import op

revision      = "2026_05_24_0900"
down_revision = "2026_05_22_1100"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── 1. Extend notificationtype enum ──────────────────────────────────────
    # PostgreSQL stores Python enum member NAMEs (uppercase).
    # ADD VALUE IF NOT EXISTS is safe and idempotent.
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'FRIEND_REQUEST_RECEIVED'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'FRIEND_REQUEST_ACCEPTED'")

    # ── 2. Create friendshipstatus enum ──────────────────────────────────────
    friendshipstatus = sa.Enum(
        "pending", "accepted", "declined", "blocked",
        name="friendshipstatus",
    )
    friendshipstatus.create(op.get_bind(), checkfirst=True)

    # ── 3. Create friendships table ──────────────────────────────────────────
    op.create_table(
        "friendships",
        sa.Column("id",           sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("addressee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("status", sa.Enum("pending", "accepted", "declined", "blocked",
                                    name="friendshipstatus", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
        sa.CheckConstraint("requester_id != addressee_id", name="ck_no_self_friendship"),
    )
    op.create_index("ix_friendships_requester_id", "friendships", ["requester_id"])
    op.create_index("ix_friendships_addressee_id", "friendships", ["addressee_id"])
    op.create_index("ix_friendships_status",       "friendships", ["status"])


def downgrade() -> None:
    op.drop_index("ix_friendships_status",       table_name="friendships")
    op.drop_index("ix_friendships_addressee_id", table_name="friendships")
    op.drop_index("ix_friendships_requester_id", table_name="friendships")
    op.drop_table("friendships")
    # Cannot remove enum values from PostgreSQL without recreating the type —
    # leave notificationtype values in place on downgrade.
    sa.Enum(name="friendshipstatus").drop(op.get_bind(), checkfirst=True)
