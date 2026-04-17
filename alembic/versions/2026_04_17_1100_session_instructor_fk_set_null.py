"""session instructor FK SET NULL

Revision ID: 2026_04_17_1100
Revises: 2026_04_17_1000
Create Date: 2026-04-17 11:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "2026_04_17_1100"
down_revision = "2026_04_17_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("sessions_instructor_id_fkey", "sessions", type_="foreignkey")
    op.create_foreign_key(
        "sessions_instructor_id_fkey",
        "sessions",
        "users",
        ["instructor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("sessions_instructor_id_fkey", "sessions", type_="foreignkey")
    op.create_foreign_key(
        "sessions_instructor_id_fkey",
        "sessions",
        "users",
        ["instructor_id"],
        ["id"],
    )
