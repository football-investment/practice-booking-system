"""game_config_preset_not_null

Phase 4 enforcement: game_configurations.game_preset_id → NOT NULL.

Pre-condition: ALL game_configuration rows must already have game_preset_id set.
If any NULL rows remain, the upgrade() guard raises ValueError and blocks.
Run scripts/migrate_assign_outfield_preset.py before this migration.

Revision ID: 2026_03_18_1800
Revises: 2026_03_16_1000
Create Date: 2026-03-18 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = '2026_03_18_1800'
down_revision = '2026_03_16_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Guard: block migration if any NULL preset IDs remain ─────────────────
    null_count = conn.execute(
        text(
            "SELECT count(*) FROM game_configurations "
            "WHERE game_preset_id IS NULL"
        )
    ).scalar()

    if null_count > 0:
        raise ValueError(
            f"Migration blocked: {null_count} game_configuration row(s) still have "
            "game_preset_id IS NULL. "
            "Run scripts/migrate_assign_outfield_preset.py first, then re-run alembic upgrade."
        )

    # ── Apply NOT NULL constraint ─────────────────────────────────────────────
    op.alter_column(
        'game_configurations',
        'game_preset_id',
        nullable=False,
        existing_type=sa.Integer(),
        existing_nullable=True,
    )

    # ── Update FK: SET NULL → RESTRICT (preset in use cannot be deleted) ──────
    op.drop_constraint(
        'game_configurations_game_preset_id_fkey',
        'game_configurations',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'game_configurations_game_preset_id_fkey',
        'game_configurations',
        'game_presets',
        ['game_preset_id'],
        ['id'],
        ondelete='RESTRICT',
    )


def downgrade() -> None:
    # Revert FK to SET NULL
    op.drop_constraint(
        'game_configurations_game_preset_id_fkey',
        'game_configurations',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'game_configurations_game_preset_id_fkey',
        'game_configurations',
        'game_presets',
        ['game_preset_id'],
        ['id'],
        ondelete='SET NULL',
    )
    # Revert to nullable
    op.alter_column(
        'game_configurations',
        'game_preset_id',
        nullable=True,
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
