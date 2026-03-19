"""game_config_preset_fk_restrict

Update game_configurations.game_preset_id FK: SET NULL → RESTRICT.
This prevents accidental deletion of game presets that are in use.

NOTE: NOT NULL enforcement deferred to Phase 4 (auto-preset assignment not yet
implemented in create_tournament_semester). game_preset_id remains nullable.

Revision ID: 2026_03_18_1800
Revises: 2026_03_16_1000
Create Date: 2026-03-18 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '2026_03_18_1800'
down_revision = '2026_03_16_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
