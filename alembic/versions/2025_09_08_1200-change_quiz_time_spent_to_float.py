"""Change quiz time_spent_minutes to float

Revision ID: change_quiz_time_spent_to_float
Revises: 52d803f6d8dc
Create Date: 2025-09-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_quiz_time_spent_to_float'
down_revision = '52d803f6d8dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change time_spent_minutes column from Integer to Float in quiz_attempts table
    op.alter_column('quiz_attempts', 'time_spent_minutes',
                   existing_type=sa.Integer(),
                   type_=sa.Float(),
                   existing_nullable=True)


def downgrade() -> None:
    # Revert time_spent_minutes column back to Integer
    op.alter_column('quiz_attempts', 'time_spent_minutes',
                   existing_type=sa.Float(),
                   type_=sa.Integer(),
                   existing_nullable=True)