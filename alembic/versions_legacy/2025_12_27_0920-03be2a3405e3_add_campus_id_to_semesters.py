"""add_campus_id_to_semesters

Revision ID: 03be2a3405e3
Revises: 35f1375883f8
Create Date: 2025-12-27 09:20:32.675983

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03be2a3405e3'
down_revision = '35f1375883f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add campus_id column to semesters table
    op.add_column('semesters',
        sa.Column('campus_id', sa.Integer(), nullable=True,
                 comment='FK to campuses table - more specific than location_id')
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_semesters_campus',
        'semesters', 'campuses',
        ['campus_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for performance
    op.create_index(
        'ix_semesters_campus_id',
        'semesters',
        ['campus_id']
    )


def downgrade() -> None:
    op.drop_index('ix_semesters_campus_id', table_name='semesters')
    op.drop_constraint('fk_semesters_campus', 'semesters', type_='foreignkey')
    op.drop_column('semesters', 'campus_id')