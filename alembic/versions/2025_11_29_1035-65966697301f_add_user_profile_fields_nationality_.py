"""add_user_profile_fields_nationality_gender_location

Revision ID: 65966697301f
Revises: create_semester_enrollments
Create Date: 2025-11-29 10:35:35.556344

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '65966697301f'
down_revision = 'create_semester_enrollments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new profile fields to users table
    op.add_column('users', sa.Column('nationality', sa.String(), nullable=True, comment="User's nationality (e.g., Hungarian, American)"))
    op.add_column('users', sa.Column('gender', sa.String(), nullable=True, comment="User's gender (Male, Female, Other, Prefer not to say)"))
    op.add_column('users', sa.Column('current_location', sa.String(), nullable=True, comment="User's current location (e.g., Budapest, Hungary)"))


def downgrade() -> None:
    # Remove the new profile fields
    op.drop_column('users', 'current_location')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'nationality')