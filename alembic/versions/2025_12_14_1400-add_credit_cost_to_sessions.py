"""add credit_cost to sessions

Revision ID: 4f8c9d2e6a1b
Revises: g2h3i4j5k6l7
Create Date: 2025-12-14 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f8c9d2e6a1b'
down_revision: Union[str, None] = 'g2h3i4j5k6l7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add credit_cost field to sessions table.

    Session-level credit model: Each session has its own credit_cost.
    Benefits:
    - Flexible pricing (workshops can cost more)
    - Master instructor controls pricing per session
    - Promotional sessions possible (0 credits)
    """
    # Add credit_cost column with default value of 1
    op.add_column('sessions',
        sa.Column(
            'credit_cost',
            sa.Integer(),
            nullable=False,
            server_default='1',
            comment='Number of credits required to book this session (default: 1)'
        )
    )


def downgrade() -> None:
    """Remove credit_cost field from sessions table"""
    op.drop_column('sessions', 'credit_cost')
