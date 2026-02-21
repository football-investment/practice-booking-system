"""create_locations_table

Revision ID: 67aa5bfdad3c
Revises: 3f9a1b2c5d6e
Create Date: 2025-12-13 10:20:42.350459

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67aa5bfdad3c'
down_revision = '3f9a1b2c5d6e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('venue', sa.String(length=200), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_locations_id'), 'locations', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_locations_id'), table_name='locations')
    op.drop_table('locations')