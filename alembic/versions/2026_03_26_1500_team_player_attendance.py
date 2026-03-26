"""team player attendance and session postpone

Adds pre-tournament check-in tracking for teams and individual players,
plus match postpone reason on sessions.

Revision ID: 2026_03_26_1500
Revises: 2026_03_26_1400
Create Date: 2026-03-26 15:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_03_26_1500"
down_revision = "2026_03_26_1400"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A) Team-level check-in audit columns on existing table
    op.add_column(
        "tournament_team_enrollments",
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tournament_team_enrollments",
        sa.Column(
            "checked_in_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )

    # B) Player-level check-in table (pre-tournament, not per-session Attendance)
    op.create_table(
        "tournament_player_checkins",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tournament_id",
            sa.Integer(),
            sa.ForeignKey("semesters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=True,
        ),
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "checked_in_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.UniqueConstraint("tournament_id", "user_id", name="uq_player_checkin"),
    )
    op.create_index(
        "ix_tpc_tournament",
        "tournament_player_checkins",
        ["tournament_id"],
    )

    # C) Match postpone reason on sessions
    op.add_column(
        "sessions",
        sa.Column("postponed_reason", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "postponed_reason")
    op.drop_index("ix_tpc_tournament", table_name="tournament_player_checkins")
    op.drop_table("tournament_player_checkins")
    op.drop_column("tournament_team_enrollments", "checked_in_by_id")
    op.drop_column("tournament_team_enrollments", "checked_in_at")
