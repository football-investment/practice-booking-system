"""add_unique_constraint_skill_rewards

Revision ID: d73137711dd5
Revises: 8e84e34793ac
Create Date: 2026-02-01 20:12:36.977652

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd73137711dd5'
down_revision = '8e84e34793ac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add unique constraint to skill_rewards table.

    Prevents DUAL PATH bug where multiple services (RewardDistributor,
    FootballSkillService) write skill rewards for the same source,
    creating duplicate skill points.

    Business Invariant: One skill reward per (user, source_type, source_id, skill_name).
    Example: Session 123 can only award "Passing" skill points to User 5 ONCE.
    """
    # Step 1: Delete existing duplicates (keep lowest id for each unique key)
    op.execute("""
        DELETE FROM skill_rewards a
        USING skill_rewards b
        WHERE a.id > b.id
        AND a.user_id = b.user_id
        AND a.source_type = b.source_type
        AND a.source_id = b.source_id
        AND a.skill_name = b.skill_name;
    """)

    # Step 2: Add unique constraint
    op.create_unique_constraint(
        'uq_skill_rewards_user_source_skill',
        'skill_rewards',
        ['user_id', 'source_type', 'source_id', 'skill_name']
    )


def downgrade() -> None:
    """Remove unique constraint"""
    op.drop_constraint(
        'uq_skill_rewards_user_source_skill',
        'skill_rewards',
        type_='unique'
    )