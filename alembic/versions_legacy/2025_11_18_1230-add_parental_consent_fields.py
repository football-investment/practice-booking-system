"""add_parental_consent_fields

Revision ID: add_parental_consent
Revises: f1934c4aa75e
Create Date: 2025-11-18 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_parental_consent'
down_revision = 'f1934c4aa75e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add parental consent fields to users table.
    Required for LFA_COACH specialization for users under 18 years old.
    """
    # Add parental_consent boolean field (default False)
    op.add_column('users', sa.Column(
        'parental_consent',
        sa.Boolean,
        nullable=False,
        default=False,
        server_default='false',
        comment='Whether parental consent has been given (required for users under 18 in LFA_COACH)'
    ))

    # Add parental_consent_at timestamp field
    op.add_column('users', sa.Column(
        'parental_consent_at',
        sa.DateTime,
        nullable=True,
        comment='Timestamp when parental consent was given'
    ))

    # Add parental_consent_by field (parent/guardian name)
    op.add_column('users', sa.Column(
        'parental_consent_by',
        sa.String,
        nullable=True,
        comment='Name of parent/guardian who gave consent'
    ))


def downgrade() -> None:
    """
    Remove parental consent fields from users table.
    """
    op.drop_column('users', 'parental_consent_by')
    op.drop_column('users', 'parental_consent_at')
    op.drop_column('users', 'parental_consent')
