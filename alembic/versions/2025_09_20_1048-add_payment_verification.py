"""Add payment verification field

Revision ID: add_payment_verification
Revises: 87081a834645
Create Date: 2025-09-20 10:48:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_payment_verification'
down_revision = '87081a834645'
branch_labels = None
depends_on = None

def upgrade():
    """Add payment_verified field to users table"""
    # Add payment_verified column as nullable first
    op.add_column('users', sa.Column('payment_verified', sa.Boolean(), nullable=True))
    
    # Set default value for existing records
    op.execute("UPDATE users SET payment_verified = false WHERE payment_verified IS NULL")
    
    # Now make it non-nullable
    op.alter_column('users', 'payment_verified', nullable=False)
    
    # Add payment_verified_at timestamp for audit trail
    op.add_column('users', sa.Column('payment_verified_at', sa.DateTime(), nullable=True))
    
    # Add payment_verified_by for admin tracking
    op.add_column('users', sa.Column('payment_verified_by', sa.Integer(), nullable=True))
    
    # Add foreign key constraint for payment_verified_by
    op.create_foreign_key(
        'fk_users_payment_verified_by',
        'users', 'users',
        ['payment_verified_by'], ['id']
    )

def downgrade():
    """Remove payment verification fields"""
    op.drop_constraint('fk_users_payment_verified_by', 'users', type_='foreignkey')
    op.drop_column('users', 'payment_verified_by')
    op.drop_column('users', 'payment_verified_at')
    op.drop_column('users', 'payment_verified')