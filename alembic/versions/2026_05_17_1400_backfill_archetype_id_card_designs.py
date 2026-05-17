"""CS-6: Backfill archetype_id for existing card_designs rows.

Revision ID: 2026_05_17_1400
Revises:     2026_05_17_1300
Create Date: 2026-05-17 14:00:00.000000

archetype_id was introduced as a nullable column in the original card_designs
migration (2026_05_17_1100) with intent to populate in CS-4a / CS-6.

CS-6 A-model semantic:
  archetype_id identifies the driver family for component_config-backed
  (driver-eligible) exports only.  File-based exports are unaffected.

Backfill targets:
  fifa         → "column"  (portrait+story driver-eligible via column_driver.html;
                             square/tiktok/landscape/banner remain file-based)
  classic_lite → "column"  (portrait+story driver-eligible; pure column-archetype)
  pulse        → "pulse"   (square driver-eligible via pulse_driver.html)

Designs with no component_config (compact, compact_bg, showcase, showcase_bg,
atlas) remain NULL — they are fully file-based and need no archetype driver.
"""
from alembic import op

# revision identifiers
revision        = "2026_05_17_1400"
down_revision   = "2026_05_17_1300"
branch_labels   = None
depends_on      = None


def upgrade() -> None:
    op.execute("""
        UPDATE card_designs
           SET archetype_id = 'column'
         WHERE id IN ('fifa', 'classic_lite')
    """)
    op.execute("""
        UPDATE card_designs
           SET archetype_id = 'pulse'
         WHERE id = 'pulse'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE card_designs
           SET archetype_id = NULL
         WHERE id IN ('fifa', 'classic_lite', 'pulse')
    """)
