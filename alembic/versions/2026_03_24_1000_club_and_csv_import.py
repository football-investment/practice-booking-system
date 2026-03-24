"""Club entity + teams.club_id/age_group_label + csv_import_logs

Revision ID: 2026_03_24_1000
Revises: 2026_03_24_0900
Create Date: 2026-03-24 10:00:00.000000

Changes:
- CREATE TABLE clubs (id, name, code, city, country, contact_email, is_active, created_at, created_by)
- UNIQUE INDEX uq_clubs_code ON clubs(code)
- ALTER TABLE teams ADD COLUMN club_id INT REFERENCES clubs(id)
- ALTER TABLE teams ADD COLUMN age_group_label VARCHAR(20)
- CREATE INDEX ix_teams_club_id ON teams(club_id)
- CREATE TABLE csv_import_logs
"""
from alembic import op
import sqlalchemy as sa


revision = "2026_03_24_1000"
down_revision = "2026_03_24_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── clubs table ──────────────────────────────────────────────────────────
    op.create_table(
        "clubs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("country", sa.String(50), nullable=True),
        sa.Column("contact_email", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_clubs_code"),
    )
    op.create_index("ix_clubs_id", "clubs", ["id"])

    # ── teams — add club_id + age_group_label ─────────────────────────────
    op.add_column("teams", sa.Column("club_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_teams_club_id", "teams", "clubs", ["club_id"], ["id"]
    )
    op.create_index("ix_teams_club_id", "teams", ["club_id"])

    op.add_column("teams", sa.Column("age_group_label", sa.String(20), nullable=True))

    # ── csv_import_logs table ─────────────────────────────────────────────
    op.create_table(
        "csv_import_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("club_id", sa.Integer(), sa.ForeignKey("clubs.id"), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("total_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_updated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_skipped", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("errors", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'DONE'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_csv_import_logs_id", "csv_import_logs", ["id"])
    op.create_index("ix_csv_import_logs_club_id", "csv_import_logs", ["club_id"])


def downgrade() -> None:
    op.drop_index("ix_csv_import_logs_club_id", table_name="csv_import_logs")
    op.drop_index("ix_csv_import_logs_id", table_name="csv_import_logs")
    op.drop_table("csv_import_logs")

    op.drop_index("ix_teams_club_id", table_name="teams")
    op.drop_constraint("fk_teams_club_id", "teams", type_="foreignkey")
    op.drop_column("teams", "age_group_label")
    op.drop_column("teams", "club_id")

    op.drop_index("ix_clubs_id", table_name="clubs")
    op.drop_table("clubs")
