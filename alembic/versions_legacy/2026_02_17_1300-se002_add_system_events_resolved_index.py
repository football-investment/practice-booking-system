"""add_system_events_resolved_index

Revision ID: se002residx00
Revises: se001create00
Create Date: 2026-02-17 13:00:00.000000

Performance guard for the Rendszerüzenetek admin panel.

The most common query pattern is:
    WHERE resolved = FALSE ORDER BY created_at DESC LIMIT 50

Also adds:
  - ix_system_events_resolved (single col)
  - ix_system_events_resolved_created (composite for paginated query)
  - ix_system_events_open_created (partial index: resolved=false only)
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'se002residx00'
down_revision = 'se001create00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_system_events_resolved', 'system_events', ['resolved'])

    op.create_index(
        'ix_system_events_resolved_created',
        'system_events',
        ['resolved', 'created_at'],
    )

    op.create_index(
        'ix_system_events_open_created',
        'system_events',
        ['created_at'],
        postgresql_where='resolved = false',
    )


def downgrade() -> None:
    op.drop_index('ix_system_events_open_created', table_name='system_events')
    op.drop_index('ix_system_events_resolved_created', table_name='system_events')
    op.drop_index('ix_system_events_resolved', table_name='system_events')
