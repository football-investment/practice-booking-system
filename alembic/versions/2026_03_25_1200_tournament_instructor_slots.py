"""Tournament instructor slots — per-event planning + check-in

Revision ID: 2026_03_25_1200
Revises: 2026_03_24_1100
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = "2026_03_25_1200"
down_revision = "2026_03_24_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tournament_instructor_slots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("semester_id", sa.Integer(),
                  sa.ForeignKey("semesters.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("instructor_id", sa.Integer(),
                  sa.ForeignKey("users.id"),
                  nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("pitch_id", sa.Integer(),
                  sa.ForeignKey("pitches.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="PLANNED"),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.Integer(),
                  sa.ForeignKey("users.id"),
                  nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    # Indexes
    op.create_index("ix_tis_semester_id",   "tournament_instructor_slots", ["semester_id"])
    op.create_index("ix_tis_instructor_id", "tournament_instructor_slots", ["instructor_id"])
    op.create_index("ix_tis_pitch_id",      "tournament_instructor_slots", ["pitch_id"])
    op.create_index("ix_tis_status",        "tournament_instructor_slots", ["status"])

    # 1 instructor = 1 slot per tournament
    op.create_unique_constraint(
        "uq_tournament_slot_instructor",
        "tournament_instructor_slots",
        ["semester_id", "instructor_id"],
    )

    # 1 field instructor per pitch per tournament (partial — only for FIELD role)
    op.execute(
        """
        CREATE UNIQUE INDEX ix_tournament_slot_pitch_unique
          ON tournament_instructor_slots (semester_id, pitch_id)
         WHERE role = 'FIELD' AND pitch_id IS NOT NULL
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_tournament_slot_pitch_unique")
    op.drop_constraint("uq_tournament_slot_instructor",
                       "tournament_instructor_slots", type_="unique")
    op.drop_index("ix_tis_status",        "tournament_instructor_slots")
    op.drop_index("ix_tis_pitch_id",      "tournament_instructor_slots")
    op.drop_index("ix_tis_instructor_id", "tournament_instructor_slots")
    op.drop_index("ix_tis_semester_id",   "tournament_instructor_slots")
    op.drop_table("tournament_instructor_slots")
