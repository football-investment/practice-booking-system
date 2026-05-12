"""
Unit tests — FIFA Classic × Instagram Square card template
==========================================================

Static assertions against app/templates/public/export/square/fifa.html.
No DB, no Playwright, no network — all tests read the template source as text.

Coverage:
  SQ-01  Hero zone is 35% (v5 — was 42% in v4; 35% gives 65% for skills)
  SQ-02  Exactly 3 .ex-skill-col divs (3-column layout)
  SQ-03  Col 1 renders skill_categories[0] (Outfield — 1st column, single cat)
  SQ-04  .ex-col-right renders skill_categories[2] (Mental — nested right panel)
  SQ-05  .ex-col-right renders both skill_categories[1] (Set Pieces) + [3] (Physical)
  SQ-06  Position badge uses primary_pos_label (not raw player.position snake_case)
  SQ-07  Secondary position chips container ex-sec-pos-chips present in HTML
  SQ-08  .ex-sec-pos-chip CSS class defined in stylesheet
  SQ-09  .ex-cat has no overflow:hidden (content layers must never clip skills)
  SQ-10  .ex-skill-rows has no overflow:hidden
  SQ-11  Animation stagger covers rows 1–19 (Outfield is longest at 19 skills)
  SQ-12  Cat animation has ≤2 nth-child selectors (3-col: max 2 cats per column)
  SQ-13  Sponsor in hero layer (.ex-hero-sponsor inside .ex-profile-col) — v8
         Sponsor NOT in skills zone (.ex-sponsor-slot removed in v8)
  SQ-14  Animated mode block is gated by {% if animated_mode %} Jinja2 block
  SQ-15  Template file exists and contains DOCTYPE declaration
  SQ-16  ex-cat--logo-host and ex-logo-slot are NOT in the HTML body (removed in v5)
  SQ-17  .ex-pos-panel-landscape class present in HTML body (v7 landscape panel)
  SQ-18  Landscape pitch SVG viewBox "0 0 105 68" (real 105m×68m geometry) — v8
         Old "0 0 100 24" aspect-squashed viewBox must be absent
  SQ-19  position_nodes Jinja2 variable referenced in SVG rendering
         Coordinate transform: cx = node.x * 105, cy = node.y * 68 (v8 real geometry)
  SQ-20  Landscape panel appears after skill_categories[3] reference
  SQ-21  Column count unchanged: still exactly 3 .ex-skill-col divs with panel added
  SQ-22  Position panel gated by {% if position_nodes %} — graceful empty state
  SQ-23  .ex-pos-svg-landscape CSS defines width and height (fills container)
  SQ-24  Position panel does NOT use .ex-cat class — immune to cat fade-slide animation
  SQ-25  .ex-col-right container present in HTML body, contains skill_categories[2]
  SQ-27  Landscape SVG has no {{ node.label }} text — no labels per user request
  SQ-28  preserveAspectRatio="xMidYMid meet" on landscape SVG — no stretch, no crop (v8)
"""
from __future__ import annotations

import pathlib
import re

import pytest

# ── Template path ──────────────────────────────────────────────────────────────

_TPL_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "app" / "templates" / "public" / "export" / "square" / "fifa.html"
)


@pytest.fixture(scope="module")
def tpl() -> str:
    return _TPL_PATH.read_text(encoding="utf-8")


# ── SQ-01: Hero zone percentage ───────────────────────────────────────────────

class TestHeroZone:
    def test_sq01_hero_flex_35_percent(self, tpl):
        """Hero must be 35%, not 42%, so skills zone gets 65% (702px at 1080px)."""
        assert "flex: 0 0 35%" in tpl

    def test_sq01_hero_not_42_percent(self, tpl):
        """Old 42% value must be gone — confirms this is v5, not v4."""
        assert "flex: 0 0 42%" not in tpl


# ── SQ-02/03/04/05: 3-column skill layout ─────────────────────────────────────

class TestThreeColumnLayout:
    def test_sq02_three_skill_col_divs(self, tpl):
        """Exactly 3 <div class="ex-skill-col"> present in the skills section."""
        matches = re.findall(r'class="ex-skill-col"', tpl)
        assert len(matches) == 3, f"Expected 3 ex-skill-col divs, found {len(matches)}"

    def test_sq03_col1_outfield_index_0(self, tpl):
        """Col 1 (Outfield): uses skill_categories[0]."""
        assert "skill_categories[0]" in tpl

    def test_sq04_col2_mental_index_2(self, tpl):
        """ex-col-right (right panel): uses skill_categories[2] for Mental column."""
        assert "skill_categories[2]" in tpl

    def test_sq05_col3_set_pieces_physical(self, tpl):
        """ex-col-right stacks Set Pieces [1] + Physical [3] via a for loop."""
        assert "skill_categories[1]" in tpl
        assert "skill_categories[3]" in tpl
        # Both must appear together in the right panel
        col3_start = tpl.rfind("skill_categories[1]")
        col3_end   = tpl.rfind("skill_categories[3]")
        assert col3_start > 0 and col3_end > col3_start, (
            "skill_categories[1] must appear before skill_categories[3] in right panel"
        )


# ── SQ-06/07/08: Position badge ───────────────────────────────────────────────

class TestPositionBadge:
    def test_sq06_uses_primary_pos_label(self, tpl):
        """Position badge must use primary_pos_label (human-readable), not raw player.position."""
        assert "primary_pos_label" in tpl

    def test_sq06_not_raw_player_position_in_badge(self, tpl):
        """raw {{ player.position }} must not appear inside the badge div."""
        # The badge div: search for ex-pos-badge context
        badge_idx = tpl.find('class="ex-pos-badge"')
        assert badge_idx != -1
        # The badge closing tag ends a short block; check no raw snake_case in 200 chars after
        badge_region = tpl[badge_idx: badge_idx + 300]
        assert "{{ player.position }}" not in badge_region

    def test_sq07_secondary_chips_container_in_html(self, tpl):
        """ex-sec-pos-chips container must be present in the HTML body."""
        assert 'class="ex-sec-pos-chips"' in tpl

    def test_sq08_sec_pos_chip_css_defined(self, tpl):
        """CSS class .ex-sec-pos-chip must be defined in the stylesheet."""
        assert ".ex-sec-pos-chip" in tpl

    def test_sq07_secondary_chips_gated_by_secondary_pos_labels(self, tpl):
        """Secondary chips must only render when secondary_pos_labels is defined and truthy."""
        assert "secondary_pos_labels" in tpl
        # The guard should be present
        assert "{% if secondary_pos_labels" in tpl


# ── SQ-09/10: No overflow clipping on content layers ─────────────────────────

class TestNoOverflowClipping:
    def test_sq09_ex_cat_no_overflow_hidden(self, tpl):
        """.ex-cat must not have overflow: hidden — all skills must be visible."""
        # Extract the .ex-cat CSS rule block
        cat_rule_start = tpl.find(".ex-cat {")
        assert cat_rule_start != -1
        cat_rule_end = tpl.find("}", cat_rule_start)
        cat_rule = tpl[cat_rule_start: cat_rule_end + 1]
        assert "overflow: hidden" not in cat_rule

    def test_sq10_ex_skill_rows_no_overflow_hidden(self, tpl):
        """.ex-skill-rows must not have overflow: hidden."""
        rows_rule_start = tpl.find(".ex-skill-rows {")
        assert rows_rule_start != -1
        rows_rule_end = tpl.find("}", rows_rule_start)
        rows_rule = tpl[rows_rule_start: rows_rule_end + 1]
        assert "overflow: hidden" not in rows_rule

    def test_sq10_ex_skill_col_no_overflow_hidden(self, tpl):
        """.ex-skill-col must use overflow: visible (not hidden) so content is not clipped."""
        col_rule_start = tpl.find(".ex-skill-col {")
        assert col_rule_start != -1
        col_rule_end = tpl.find("}", col_rule_start)
        col_rule = tpl[col_rule_start: col_rule_end + 1]
        assert "overflow: hidden" not in col_rule


# ── SQ-11/12: Animation stagger ───────────────────────────────────────────────

class TestAnimationStagger:
    def test_sq11_row_stagger_covers_19_rows(self, tpl):
        """Animation row stagger must cover up to nth-child(19) for Outfield (19 skills)."""
        assert ".ex-row:nth-child(19)" in tpl

    def test_sq11_row_stagger_has_no_gaps(self, tpl):
        """Stagger must be contiguous from 1 to 19."""
        for n in range(1, 20):
            assert f".ex-row:nth-child({n})" in tpl, (
                f"Missing animation stagger for .ex-row:nth-child({n})"
            )

    def test_sq12_cat_stagger_max_two_nth_child(self, tpl):
        """Cat animation: at most 2 nth-child selectors (max 2 cats per column in 3-col layout)."""
        # Find the animated_mode block
        anim_start = tpl.find("{% if animated_mode %}")
        anim_end   = tpl.find("{% endif %}", anim_start)
        anim_block = tpl[anim_start: anim_end]
        cat_stagger = re.findall(r"\.ex-cat:nth-child\((\d+)\)", anim_block)
        indices = [int(i) for i in cat_stagger]
        assert max(indices) <= 2, (
            f"Cat stagger should not exceed nth-child(2) in 3-col layout; found {indices}"
        )
        # Old 4-category selectors (nth-child(3) and nth-child(4)) must be gone
        assert ".ex-cat:nth-child(3)" not in anim_block
        assert ".ex-cat:nth-child(4)" not in anim_block


# ── SQ-13: Sponsor placement (v8 — hero layer) ───────────────────────────────

class TestSponsorSlot:
    def test_sq13_sponsor_in_hero_layer(self, tpl):
        """v8: sponsor must use .ex-hero-sponsor class (moved to hero layer)."""
        html_body = tpl[tpl.rfind("</style>"):]
        assert 'class="ex-hero-sponsor"' in html_body

    def test_sq13_sponsor_inside_profile_col(self, tpl):
        """v8: .ex-hero-sponsor must appear inside .ex-profile-col (hero layer, not skills zone)."""
        html_body = tpl[tpl.rfind("</style>"):]
        profile_col_idx = html_body.find('class="ex-profile-col"')
        sponsor_idx = html_body.find('class="ex-hero-sponsor"', profile_col_idx)
        skill_cats_idx = html_body.find('class="ex-skill-cats"')
        assert profile_col_idx != -1
        assert sponsor_idx != -1, ".ex-hero-sponsor not found after .ex-profile-col"
        # sponsor must come before skill-cats (it's in the hero zone, above the skills zone)
        assert sponsor_idx < skill_cats_idx, (
            ".ex-hero-sponsor must be in the hero layer (before .ex-skill-cats), not in the skills zone"
        )

    def test_sq13_no_ex_sponsor_slot_in_body(self, tpl):
        """v8: old .ex-sponsor-slot class must be absent — skills zone is fully freed."""
        html_body = tpl[tpl.rfind("</style>"):]
        assert 'class="ex-sponsor-slot"' not in html_body

    def test_sq13_sponsor_gated_by_jinja2_condition(self, tpl):
        """Sponsor block must be gated — no layout break when sponsor_logo_url is absent."""
        assert "sponsor_logo_url" in tpl
        assert "{% if sponsor_logo_url" in tpl or "{% if sponsor_logo_url or" in tpl


# ── SQ-14: Animated mode gating ───────────────────────────────────────────────

class TestAnimatedModeGating:
    def test_sq14_animated_mode_jinja2_gate(self, tpl):
        """@keyframes must only be inside the {% if animated_mode %} block."""
        assert "{% if animated_mode %}" in tpl
        assert "@keyframes" in tpl
        # All @keyframes must be after the animated_mode if block
        first_keyframe = tpl.find("@keyframes")
        anim_gate      = tpl.find("{% if animated_mode %}")
        assert first_keyframe > anim_gate, (
            "@keyframes appeared before the animated_mode gate — static exports would be affected"
        )


# ── SQ-15: File integrity ─────────────────────────────────────────────────────

class TestFileIntegrity:
    def test_sq15_file_exists(self):
        """Template file must exist at expected path."""
        assert _TPL_PATH.exists(), f"Template not found: {_TPL_PATH}"

    def test_sq15_has_doctype(self, tpl):
        """Must be a complete HTML document."""
        assert "<!DOCTYPE html>" in tpl

    def test_sq15_has_ex_card_root(self, tpl):
        """Root card div with class ex-card must be present."""
        assert 'class="ex-card"' in tpl


# ── SQ-16: Removed v4 artefacts ───────────────────────────────────────────────

class TestRemovedV4Artefacts:
    def test_sq16_no_logo_host_class_in_html(self, tpl):
        """ex-cat--logo-host must not appear in HTML (v4 filler pattern removed)."""
        # Only check the HTML body part (after </style>)
        html_body = tpl[tpl.rfind("</style>"):]
        assert "ex-cat--logo-host" not in html_body

    def test_sq16_no_logo_slot_in_html(self, tpl):
        """ex-logo-slot div must not appear in HTML body (v5 has no empty filler slots)."""
        html_body = tpl[tpl.rfind("</style>"):]
        assert 'class="ex-logo-slot"' not in html_body


# ── SQ-17/18/19/20: Position landscape panel presence ────────────────────────

class TestPositionMiniPanel:
    def test_sq17_pos_panel_class_in_html(self, tpl):
        """v7 landscape panel: .ex-pos-panel-landscape div must be present in the HTML body."""
        html_body = tpl[tpl.rfind("</style>"):]
        assert 'class="ex-pos-panel-landscape"' in html_body

    def test_sq18_landscape_pitch_svg_viewbox(self, tpl):
        """v8: Landscape pitch SVG must use viewBox '0 0 105 68' (real 105m×68m pitch geometry)."""
        assert 'viewBox="0 0 105 68"' in tpl, (
            "Landscape SVG must use real pitch geometry viewBox '0 0 105 68', not the old '0 0 100 24'"
        )

    def test_sq18_old_squashed_viewbox_absent(self, tpl):
        """v8: Old aspect-squashed viewBox '0 0 100 24' must not be present."""
        assert 'viewBox="0 0 100 24"' not in tpl

    def test_sq19_position_nodes_in_svg(self, tpl):
        """SVG rendering must reference position_nodes from template context."""
        html_body = tpl[tpl.rfind("</style>"):]
        # position_nodes must be used in the for loop inside the SVG block
        assert "position_nodes" in html_body

    def test_sq19_coordinate_transform_formula(self, tpl):
        """v8: SVG must use real-geometry coordinate transform (cx=node.x*105, cy=node.y*68)."""
        html_body = tpl[tpl.rfind("</style>"):]
        assert "node.x * 105" in html_body, (
            "SVG coordinate transform must use node.x * 105 (105m pitch width), not node.x * 100"
        )
        assert "node.y * 68" in html_body, (
            "SVG coordinate transform must use node.y * 68 (68m pitch height), not node.y * 24"
        )

    def test_sq20_pos_panel_after_skill_categories_3(self, tpl):
        """Landscape panel must appear after skill_categories[3] (Physical)."""
        idx_phys  = tpl.rfind("skill_categories[3]")
        idx_panel = tpl.find('class="ex-pos-panel-landscape"')
        assert idx_phys > 0 and idx_panel > 0, "Both skill_categories[3] and ex-pos-panel-landscape must be present"
        assert idx_panel > idx_phys, (
            "ex-pos-panel-landscape must appear after skill_categories[3]"
        )


# ── SQ-21/22/23/24/25/27: Position panel structural integrity ─────────────────

class TestPositionPanelIntegrity:
    def test_sq21_column_count_unchanged(self, tpl):
        """Adding landscape panel must not change column count — still exactly 3 ex-skill-col divs."""
        matches = re.findall(r'class="ex-skill-col"', tpl)
        assert len(matches) == 3, (
            f"Landscape panel must not add a 4th column; found {len(matches)} ex-skill-col divs"
        )

    def test_sq22_pos_panel_gated_by_position_nodes(self, tpl):
        """Landscape panel must be inside {% if position_nodes %} guard — graceful when no pos set."""
        assert "{% if position_nodes %}" in tpl
        panel_idx = tpl.find('class="ex-pos-panel-landscape"')
        gate_idx  = tpl.rfind("{% if position_nodes %}", 0, panel_idx)
        assert gate_idx != -1, "ex-pos-panel-landscape must be inside a {% if position_nodes %} block"

    def test_sq23_pos_svg_explicit_dimensions(self, tpl):
        """.ex-pos-svg-landscape must define width and height — fills container, no auto-stretch."""
        svg_rule_start = tpl.find(".ex-pos-svg-landscape {")
        assert svg_rule_start != -1, ".ex-pos-svg-landscape CSS rule must be defined"
        svg_rule_end = tpl.find("}", svg_rule_start)
        svg_rule = tpl[svg_rule_start: svg_rule_end + 1]
        assert "width:" in svg_rule
        assert "height:" in svg_rule

    def test_sq24_pos_panel_not_ex_cat(self, tpl):
        """Landscape panel must NOT use .ex-cat class — immune to cat fade-slide animation."""
        html_body = tpl[tpl.rfind("</style>"):]
        assert 'class="ex-pos-panel-landscape"' in html_body
        assert 'class="ex-cat ex-pos-panel-landscape"' not in html_body
        assert 'class="ex-pos-panel-landscape ex-cat"' not in html_body

    def test_sq24_pos_panel_animated_mode_self_contained(self, tpl):
        """In animated_mode block, .ex-pos-panel-landscape gets its own animation rule."""
        anim_start = tpl.find("{% if animated_mode %}")
        anim_end   = tpl.find("{% endif %}", anim_start)
        anim_block = tpl[anim_start: anim_end]
        assert ".ex-pos-panel-landscape" in anim_block
        pos_panel_anim = anim_block.find(".ex-pos-panel-landscape {")
        ex_cat_anim    = anim_block.find(".ex-cat {")
        assert pos_panel_anim != ex_cat_anim, (
            ".ex-pos-panel-landscape and .ex-cat must have separate animation rules"
        )

    def test_sq25_ex_col_right_container_in_html(self, tpl):
        """v7: .ex-col-right container must be present in HTML body and wrap skill_categories[2]."""
        html_body = tpl[tpl.rfind("</style>"):]
        assert 'class="ex-col-right"' in html_body
        col_right_idx = html_body.find('class="ex-col-right"')
        cat2_idx      = html_body.find("skill_categories[2]", col_right_idx)
        assert cat2_idx > col_right_idx, (
            "skill_categories[2] (Mental) must appear inside .ex-col-right"
        )

    def test_sq27_no_node_label_in_landscape_svg(self, tpl):
        """Landscape SVG must not render node.label text — position name is in the hero badge."""
        html_body = tpl[tpl.rfind("</style>"):]
        panel_start = html_body.find('class="ex-pos-panel-landscape"')
        panel_end   = html_body.find("{% endif %}", panel_start)
        assert panel_start > 0 and panel_end > panel_start
        svg_block = html_body[panel_start:panel_end]
        assert "node.label" not in svg_block, (
            "Landscape SVG must not render node.label — no text labels per design spec"
        )


# ── SQ-28: preserveAspectRatio — v8 undistorted render ───────────────────────

class TestAspectRatioIntegrity:
    def test_sq28_preserve_aspect_ratio_meet(self, tpl):
        """v8: landscape SVG must declare preserveAspectRatio='xMidYMid meet' — no stretch, no crop."""
        html_body = tpl[tpl.rfind("</style>"):]
        panel_start = html_body.find('class="ex-pos-panel-landscape"')
        panel_end   = html_body.find("{% endif %}", panel_start)
        svg_block   = html_body[panel_start:panel_end]
        assert 'preserveAspectRatio="xMidYMid meet"' in svg_block, (
            "Landscape SVG must use preserveAspectRatio='xMidYMid meet' to prevent horizontal stretch"
        )

    def test_sq28_no_stretch_viewbox(self, tpl):
        """v8: old 100:24 squashed viewBox (artificially flat) must be absent."""
        assert 'viewBox="0 0 100 24"' not in tpl
