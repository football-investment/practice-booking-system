"""create_system_events_table

Revision ID: se001create00
Revises: e7f8a9b0c1d2
Create Date: 2026-02-17 12:00:00.000000

Creates the system_events table for structured business/security event tracking.

Architecture note:
  audit_logs  → operational/debug trail (HTTP middleware, automatic)
  system_events → deliberate business/security events written by application
                  logic; queryable by admins via the Rendszerüzenetek panel.

Rate-limiting is enforced at the service layer:
  same (user_id, event_type) combination → at most 1 record per 10 minutes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ENUM as PgENUM

# revision identifiers, used by Alembic.
revision = 'se001create00'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum type for event severity — idempotent: no-op if already exists
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE systemeventlevel AS ENUM ('INFO', 'WARNING', 'SECURITY');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        'system_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'level',
            PgENUM('INFO', 'WARNING', 'SECURITY', name='systemeventlevel', create_type=False),
            nullable=False,
        ),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('payload_json', JSONB(), nullable=True),
        sa.Column(
            'resolved',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # Individual column indexes
    op.create_index('ix_system_events_id', 'system_events', ['id'])
    op.create_index('ix_system_events_created_at', 'system_events', ['created_at'])
    op.create_index('ix_system_events_level', 'system_events', ['level'])
    op.create_index('ix_system_events_event_type', 'system_events', ['event_type'])
    op.create_index('ix_system_events_user_id', 'system_events', ['user_id'])

    # Composite index for rate-limiting queries:
    # "was there a (user_id, event_type) event in the last 10 min?"
    op.create_index(
        'ix_system_events_user_event_type_created',
        'system_events',
        ['user_id', 'event_type', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_system_events_user_event_type_created', table_name='system_events')
    op.drop_index('ix_system_events_user_id', table_name='system_events')
    op.drop_index('ix_system_events_event_type', table_name='system_events')
    op.drop_index('ix_system_events_level', table_name='system_events')
    op.drop_index('ix_system_events_created_at', table_name='system_events')
    op.drop_index('ix_system_events_id', table_name='system_events')
    op.drop_table('system_events')
    op.execute("DROP TYPE systemeventlevel")
