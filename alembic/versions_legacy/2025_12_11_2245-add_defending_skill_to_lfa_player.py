"""add_defending_skill_to_lfa_player

Revision ID: 2345def67890
Revises: 574791caded6
Create Date: 2025-12-11 22:45:00

IMPORTANT: This migration is now a NO-OP because it references a table 'lfa_player_licenses'
that was never created. This table does not exist in the schema and has no corresponding model.
The migration is likely a mistake (should have targeted 'user_licenses' instead).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2345def67890'
down_revision = '574791caded6'
branch_labels = None
depends_on = None


def upgrade():
    # NO-OP: Table 'lfa_player_licenses' does not exist and was never created
    pass


def downgrade():
    # NO-OP: Table 'lfa_player_licenses' does not exist
    pass
