"""add session semantic dimensions (event_category, participant_type, delivery_mode, reward_config)

Revision ID: 2026_03_15_1100
Revises: 2026_03_15_1000
Create Date: 2026-03-15 11:00:00.000000

M-03: event_category (TRAINING | MATCH) — replaces is_tournament_game boolean
M-04: session_participant_type (INDIVIDUAL | GROUP | TEAM)
M-05: delivery_mode (ON_SITE | VIRTUAL | HYBRID) — successor to session_type
M-06: session_reward_config (JSONB, versioned reward policy per session)

All columns are nullable — safe zero-downtime rollout.
is_tournament_game is NOT dropped here; data migration is a later step.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2026_03_15_1100'
down_revision = '2026_03_15_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # M-03: event_category
    event_cat_enum = sa.Enum('TRAINING', 'MATCH', name='event_category_type')
    event_cat_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'sessions',
        sa.Column(
            'event_category',
            sa.Enum('TRAINING', 'MATCH', name='event_category_type', create_type=False),
            nullable=True,
            comment='Event kind: TRAINING | MATCH. Supersedes is_tournament_game.',
        )
    )
    op.create_index('ix_sessions_event_category', 'sessions', ['event_category'])

    # M-04: session_participant_type
    spt_enum = sa.Enum('INDIVIDUAL', 'GROUP', 'TEAM', name='session_participant_type')
    spt_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'sessions',
        sa.Column(
            'session_participant_type',
            sa.Enum('INDIVIDUAL', 'GROUP', 'TEAM',
                    name='session_participant_type', create_type=False),
            nullable=True,
            comment='Participant organisation: INDIVIDUAL | GROUP | TEAM',
        )
    )

    # M-05: delivery_mode
    dm_enum = sa.Enum('ON_SITE', 'VIRTUAL', 'HYBRID', name='delivery_mode_type')
    dm_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'sessions',
        sa.Column(
            'delivery_mode',
            sa.Enum('ON_SITE', 'VIRTUAL', 'HYBRID',
                    name='delivery_mode_type', create_type=False),
            nullable=True,
            comment='Physical delivery: ON_SITE | VIRTUAL | HYBRID. Successor to session_type.',
        )
    )

    # M-06: session_reward_config (JSONB)
    op.add_column(
        'sessions',
        sa.Column(
            'session_reward_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Per-session reward config (versioned JSONB). '
                    'Schema v1: {"v":1,"base_xp":50,"skill_areas":[],"multipliers":{}}',
        )
    )


def downgrade() -> None:
    op.drop_column('sessions', 'session_reward_config')

    op.drop_column('sessions', 'delivery_mode')
    sa.Enum(name='delivery_mode_type').drop(op.get_bind(), checkfirst=True)

    op.drop_column('sessions', 'session_participant_type')
    sa.Enum(name='session_participant_type').drop(op.get_bind(), checkfirst=True)

    op.drop_index('ix_sessions_event_category', table_name='sessions')
    op.drop_column('sessions', 'event_category')
    sa.Enum(name='event_category_type').drop(op.get_bind(), checkfirst=True)
