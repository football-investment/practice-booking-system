"""add_nda_fields_to_users

Revision ID: 9d6cb6c21651
Revises: competency_system
Create Date: 2025-10-12 11:51:09.609468

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d6cb6c21651'
down_revision = 'competency_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add NDA fields to users table
    op.add_column('users', sa.Column('nda_accepted', sa.Boolean(), nullable=False, server_default='false', comment='Whether student has accepted the NDA'))
    op.add_column('users', sa.Column('nda_accepted_at', sa.DateTime(), nullable=True, comment='Timestamp when NDA was accepted'))
    op.add_column('users', sa.Column('nda_ip_address', sa.String(), nullable=True, comment='IP address from which NDA was accepted'))


def downgrade() -> None:
    # Remove NDA fields from users table
    op.drop_column('users', 'nda_ip_address')
    op.drop_column('users', 'nda_accepted_at')
    op.drop_column('users', 'nda_accepted')