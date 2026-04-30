"""Add right_foot_score and left_foot_score to user_licenses.

Revision ID: 2026_04_30_1000
Revises: 2026_04_29_1000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "2026_04_30_1000"
down_revision = "2026_04_29_1000"
branch_labels = None
depends_on = None

_TABLE = "user_licenses"
_NEW_COLUMNS = [
    ("right_foot_score", sa.Column("right_foot_score", sa.Float, nullable=True)),
    ("left_foot_score",  sa.Column("left_foot_score",  sa.Float, nullable=True)),
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns(_TABLE)}
    for col_name, col_def in _NEW_COLUMNS:
        if col_name not in existing:
            op.add_column(_TABLE, col_def)


def downgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in inspect(bind).get_columns(_TABLE)}
    for col_name, _ in reversed(_NEW_COLUMNS):
        if col_name in existing:
            op.drop_column(_TABLE, col_name)
