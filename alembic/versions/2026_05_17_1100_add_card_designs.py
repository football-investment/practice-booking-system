"""Add card_designs table with seed data for the 7 launch designs.

Revision ID: 2026_05_17_1100
Revises:     2026_05_17_1000
Create Date: 2026-05-17 11:00:00.000000

Self-contained — zero app imports.  All seed values are inlined below.

Seed strategy (ON CONFLICT DO NOTHING):
  Idempotent; re-running upgrade on a DB that already has the rows is safe.
  The 7 designs match the DESIGNS dict in card_design_service.py exactly.

Export coverage at seed time (2026-05-17):
  - fifa:        all 6 buckets (square/portrait/story/tiktok/landscape/banner)
  - pulse:       square only  (export/square/pulse.html exists)
  - compact, showcase, compact_bg, showcase_bg, atlas: no export templates yet

Animated export at seed time:
  - fifa  × instagram_square:  animated (replaces hardcoded ANIMATED_EXPORT_CAPABLE entry)
  - pulse × instagram_square:  animated (replaces hardcoded ANIMATED_EXPORT_CAPABLE entry)

archetype_id is NULL for all rows — will be populated in CS-4a.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "2026_05_17_1100"
down_revision = "2026_05_17_1000"
branch_labels = None
depends_on = None

_NOW = datetime(2026, 5, 17, 11, 0, 0, tzinfo=timezone.utc)

_ALL_BUCKETS = ["square", "portrait", "story", "tiktok", "landscape", "banner"]
_SQ_ONLY     = ["square"]
_NO_BUCKETS  = []

_FIFA_ANIMATED  = ["instagram_square"]
_PULSE_ANIMATED = ["instagram_square"]
_NO_ANIMATED    = []

# ── Seed rows ─────────────────────────────────────────────────────────────────
# (id, label, description, is_premium, credit_cost, sort_order,
#  browser_template, supported_export_buckets, animated_platforms)
_SEED: list[tuple] = [
    (
        "fifa",
        "FIFA Classic",
        "The original LFA player card with full skill breakdown and event history.",
        False, 0, 0,
        "public/player_card_fifa.html",
        _ALL_BUCKETS,
        _FIFA_ANIMATED,
    ),
    (
        "compact",
        "Compact",
        "Mobile-first card designed for sharing. Shows category averages at a glance.",
        True, 300, 1,
        "public/player_card_compact.html",
        _NO_BUCKETS,
        _NO_ANIMATED,
    ),
    (
        "compact_bg",
        "Compact + BG",
        "Compact layout with a custom background image behind your player photo.",
        True, 400, 2,
        "public/player_card_compact_bg.html",
        _NO_BUCKETS,
        _NO_ANIMATED,
    ),
    (
        "showcase",
        "Showcase",
        "Premium landscape trading card with category highlights and recent events strip.",
        True, 500, 3,
        "public/player_card_showcase.html",
        _NO_BUCKETS,
        _NO_ANIMATED,
    ),
    (
        "showcase_bg",
        "Showcase + BG",
        "Showcase layout with a custom background image behind your player photo.",
        True, 600, 4,
        "public/player_card_showcase_bg.html",
        _NO_BUCKETS,
        _NO_ANIMATED,
    ),
    (
        "atlas",
        "Atlas",
        "Modern vertical card with hero section, stat strip, and three-tab layout including player profile.",
        True, 400, 5,
        "public/player_card_atlas.html",
        _NO_BUCKETS,
        _NO_ANIMATED,
    ),
    (
        "pulse",
        "Pulse",
        "Radar skill chart with animated OVR ring, pulse effects, and HUD aesthetic.",
        True, 600, 6,
        "public/player_card_pulse.html",
        _SQ_ONLY,
        _PULSE_ANIMATED,
    ),
]


def upgrade() -> None:
    op.create_table(
        "card_designs",
        sa.Column("id",          sa.String(50),  primary_key=True),
        sa.Column("label",       sa.String(80),  nullable=False),
        sa.Column("description", sa.Text(),       nullable=False, server_default=""),
        sa.Column("is_premium",  sa.Boolean(),   nullable=False, server_default=sa.text("false")),
        sa.Column("credit_cost", sa.Integer(),   nullable=False, server_default=sa.text("0")),
        sa.Column("is_active",   sa.Boolean(),   nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order",  sa.Integer(),   nullable=False, server_default=sa.text("0")),
        sa.Column("archetype_id",       sa.String(50),  nullable=True),
        sa.Column("browser_template",   sa.String(300), nullable=False),
        sa.Column("supported_export_buckets",
                  sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("animated_platforms",
                  sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    conn = op.get_bind()
    for row in _SEED:
        (
            id_, label, description, is_premium, credit_cost, sort_order,
            browser_template, supported_export_buckets, animated_platforms,
        ) = row
        conn.execute(
            sa.text(
                """
                INSERT INTO card_designs (
                    id, label, description, is_premium, credit_cost, sort_order,
                    archetype_id, browser_template,
                    supported_export_buckets, animated_platforms,
                    is_active, created_at, updated_at
                ) VALUES (
                    :id, :label, :description, :is_premium, :credit_cost, :sort_order,
                    NULL, :browser_template,
                    CAST(:supported_export_buckets AS jsonb),
                    CAST(:animated_platforms AS jsonb),
                    true, :now, :now
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id":                       id_,
                "label":                    label,
                "description":              description,
                "is_premium":               is_premium,
                "credit_cost":              credit_cost,
                "sort_order":               sort_order,
                "browser_template":         browser_template,
                "supported_export_buckets": json.dumps(supported_export_buckets),
                "animated_platforms":       json.dumps(animated_platforms),
                "now":                      _NOW,
            },
        )


def downgrade() -> None:
    op.drop_table("card_designs")
