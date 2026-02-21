"""Add registration form fields: first_name, last_name, phone_required, address fields

Revision ID: 775ecc8293d0
Revises: 9f961b92c5f3
Create Date: 2026-01-03 15:34:26.773883

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '775ecc8293d0'
down_revision = '9f961b92c5f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new required fields for registration
    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True, comment='User first name (given name)'))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True, comment='User last name (family name)'))

    # Address fields for invoicing and registration
    op.add_column('users', sa.Column('street_address', sa.String(), nullable=True, comment='Street address (e.g., Main Street 123)'))
    op.add_column('users', sa.Column('city', sa.String(), nullable=True, comment='City name'))
    op.add_column('users', sa.Column('postal_code', sa.String(), nullable=True, comment='Postal/ZIP code'))
    op.add_column('users', sa.Column('country', sa.String(), nullable=True, comment='Country name'))

    # Note: phone field already exists in users table (line 28 in user.py)
    # Note: nickname field already exists in users table (line 22 in user.py)


def downgrade() -> None:
    # Remove registration form fields
    op.drop_column('users', 'country')
    op.drop_column('users', 'postal_code')
    op.drop_column('users', 'city')
    op.drop_column('users', 'street_address')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')