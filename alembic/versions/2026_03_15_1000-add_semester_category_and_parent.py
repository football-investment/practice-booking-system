"""add semester_category and parent_semester_id to semesters

Revision ID: 2026_03_15_1000
Revises: 2026_03_13_1500
Create Date: 2026-03-15 10:00:00.000000

M-01: Adds semester_category enum column (ACADEMY_SEASON | MINI_SEASON | TOURNAMENT | CAMP)
M-02: Adds parent_semester_id self-referential FK (nullable, for nested programs)

All new columns are nullable — safe zero-downtime rollout.
Data migration (backfill from existing data) is a separate step.
"""
from alembic import op
import sqlalchemy as sa

revision = '2026_03_15_1000'
down_revision = '2026_03_13_1500'
branch_labels = None
depends_on = None

# Enum name used in PostgreSQL
_ENUM_NAME = 'semester_category_type'
_ENUM_VALUES = ('ACADEMY_SEASON', 'MINI_SEASON', 'TOURNAMENT', 'CAMP')


def upgrade() -> None:
    # M-01: Create enum type and add column
    semester_category_enum = sa.Enum(*_ENUM_VALUES, name=_ENUM_NAME)
    semester_category_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'semesters',
        sa.Column(
            'semester_category',
            sa.Enum(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
            nullable=True,
            comment='Program category: ACADEMY_SEASON | MINI_SEASON | TOURNAMENT | CAMP',
        )
    )
    op.create_index(
        'ix_semesters_semester_category',
        'semesters',
        ['semester_category'],
    )

    # M-02: Add self-referential parent FK
    op.add_column(
        'semesters',
        sa.Column(
            'parent_semester_id',
            sa.Integer(),
            sa.ForeignKey('semesters.id', ondelete='SET NULL'),
            nullable=True,
            comment='Parent semester for nested programs (access-control gate)',
        )
    )
    op.create_index(
        'ix_semesters_parent_semester_id',
        'semesters',
        ['parent_semester_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_semesters_parent_semester_id', table_name='semesters')
    op.drop_column('semesters', 'parent_semester_id')

    op.drop_index('ix_semesters_semester_category', table_name='semesters')
    op.drop_column('semesters', 'semester_category')

    sa.Enum(name=_ENUM_NAME).drop(op.get_bind(), checkfirst=True)
