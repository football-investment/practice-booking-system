"""create event_reward_logs table

Revision ID: 2026_03_15_1200
Revises: 2026_03_15_1100
Create Date: 2026-03-15 12:00:00.000000

M-07: Creates the event_reward_logs table — universal reward tracking per (user, session).

Decoupled from LicenseProgression (structural level changes).
One row per (user_id, session_id); later an upsert strategy will be enforced at service layer.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2026_03_15_1200'
down_revision = '2026_03_15_1100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'event_reward_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'session_id',
            sa.Integer(),
            sa.ForeignKey('sessions.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'xp_earned',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Total XP credited to user for this session',
        ),
        sa.Column(
            'points_earned',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Skill/ranking points earned (separate ledger from XP)',
        ),
        sa.Column(
            'skill_areas_affected',
            postgresql.ARRAY(sa.String()),
            nullable=True,
            comment="Skill area codes impacted (e.g. ['dribbling', 'passing'])",
        ),
        sa.Column(
            'multiplier_applied',
            sa.Float(),
            nullable=False,
            server_default='1.0',
            comment='Final multiplier used (streak, tier, attendance bonus, etc.)',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table('event_reward_logs')
