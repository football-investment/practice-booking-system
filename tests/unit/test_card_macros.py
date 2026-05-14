"""
tests/unit/test_card_macros.py
Unit tests for Jinja2 card macros (Phase 1 macro extraction refactor).

Tests use jinja2.Environment directly — no server or database needed.
"""
from types import SimpleNamespace

import pytest
import jinja2


# ---------------------------------------------------------------------------
# Shared Jinja2 environment + helper
# ---------------------------------------------------------------------------

TEMPLATES_DIR = "app/templates"

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    autoescape=False,
)


def _render_macro(template_path: str, macro_name: str, *args, **kwargs) -> str:
    """Load *template_path*, call *macro_name* with args/kwargs, return rendered string."""
    source = (
        "{{% from '{path}' import {macro} %}}"
        "{{{{ {macro}({positional}{keyword}) }}}}"
    ).format(
        path=template_path,
        macro=macro_name,
        positional=", ".join("arg{}".format(i) for i in range(len(args))),
        keyword=", ".join("{}=kw{}".format(k, i) for i, k in enumerate(kwargs)),
    )
    # Build the template string properly
    call_parts = []
    call_parts.extend("arg{}".format(i) for i in range(len(args)))
    call_parts.extend("{}=kw{}".format(k, i) for i, k in enumerate(kwargs))

    tmpl_src = "{{% from '{path}' import {macro} %}}{{{{ {macro}({call}) }}}}".format(
        path=template_path,
        macro=macro_name,
        call=", ".join(call_parts),
    )

    tmpl = env.from_string(tmpl_src)

    ctx = {}
    for i, v in enumerate(args):
        ctx["arg{}".format(i)] = v
    for i, k in enumerate(kwargs):
        ctx["kw{}".format(i)] = kwargs[k]

    return tmpl.render(**ctx)


def _make_skill(key: str, name_en: str) -> SimpleNamespace:
    return SimpleNamespace(key=key, name_en=name_en)


def _make_cat(key: str = "outfield", name_en: str = "Outfield", emoji: str = "⚽",
              skills=None) -> SimpleNamespace:
    if skills is None:
        skills = [_make_skill("passing", "Passing"), _make_skill("dribbling", "Dribbling")]
    return SimpleNamespace(key=key, name_en=name_en, emoji=emoji, skills=skills)


# ---------------------------------------------------------------------------
# TestExportSkillRowsMacro
# ---------------------------------------------------------------------------

class TestExportSkillRowsMacro:
    """MR_ prefix — export_skill_rows macro from macros/card_skill_row.html"""

    MACRO_PATH = "macros/card_skill_row.html"
    MACRO_NAME = "export_skill_rows"

    def _render(self, cat, skills_dict, delta_dict, **kw):
        return _render_macro(self.MACRO_PATH, self.MACRO_NAME,
                             cat, skills_dict, delta_dict, **kw)

    def test_MR_export_renders_skill_name(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {"passing": {"current_level": 75}}, {})
        assert "Passing" in html
        assert "ex-sname" in html

    def test_MR_export_renders_skill_score(self):
        cat = _make_cat(skills=[_make_skill("shooting", "Shooting")])
        html = self._render(cat, {"shooting": {"current_level": 82}}, {})
        assert "82" in html
        assert "ex-sval" in html

    def test_MR_export_positive_delta_green_bar_and_visible_up_arrow(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {"passing": {"current_level": 70}}, {"passing": 5})
        assert "#48bb78" in html
        assert "visibility:visible" in html
        assert "↑" in html

    def test_MR_export_negative_delta_red_bar_and_visible_down_arrow(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {"passing": {"current_level": 60}}, {"passing": -3})
        assert "#fc8181" in html
        assert "visibility:visible" in html
        assert "↓" in html

    def test_MR_export_zero_delta_hidden_trend_neutral_colors(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {"passing": {"current_level": 65}}, {"passing": 0})
        assert "visibility:hidden" in html
        assert "rgba(255,255,255,0.20)" in html
        assert "rgba(255,255,255,0.85)" in html

    def test_MR_export_custom_neutral_bar_and_val_colors(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(
            cat,
            {"passing": {"current_level": 65}},
            {},
            neutral_bar="rgba(255,255,255,0.18)",
            neutral_val="rgba(255,255,255,0.80)",
        )
        assert "rgba(255,255,255,0.18)" in html
        assert "rgba(255,255,255,0.80)" in html

    def test_MR_export_missing_skill_key_uses_default_50(self):
        cat = _make_cat(skills=[_make_skill("unknown_skill", "Unknown")])
        html = self._render(cat, {}, {})
        assert "50" in html

    def test_MR_export_renders_ex_skill_rows_wrapper_div(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {}, {})
        assert 'class="ex-skill-rows"' in html

    def test_MR_export_renders_ex_row_for_each_skill(self):
        skills = [_make_skill("passing", "Passing"), _make_skill("shooting", "Shooting")]
        cat = _make_cat(skills=skills)
        html = self._render(cat, {}, {})
        assert html.count('class="ex-row"') == 2


# ---------------------------------------------------------------------------
# TestCardSkillRowsMacro
# ---------------------------------------------------------------------------

class TestCardSkillRowsMacro:
    """MR_ prefix — card_skill_rows macro from macros/card_skill_row.html"""

    MACRO_PATH = "macros/card_skill_row.html"
    MACRO_NAME = "card_skill_rows"

    def _render(self, cat, skills_dict, delta_dict):
        return _render_macro(self.MACRO_PATH, self.MACRO_NAME, cat, skills_dict, delta_dict)

    def test_MR_card_renders_skill_name(self):
        cat = _make_cat(skills=[_make_skill("dribbling", "Dribbling")])
        html = self._render(cat, {"dribbling": {"current_level": 78.5}}, {})
        assert "Dribbling" in html
        assert "skill-name" in html

    def test_MR_card_renders_skill_score(self):
        cat = _make_cat(skills=[_make_skill("shooting", "Shooting")])
        html = self._render(cat, {"shooting": {"current_level": 80.0}}, {})
        assert "80.0" in html
        assert "skill-val" in html

    def test_MR_card_positive_delta_shows_up_arrow(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {"passing": {"current_level": 72}}, {"passing": 4})
        assert "#48bb78" in html
        assert "↑" in html
        # skill-up span rendered (not hidden)
        assert 'class="skill-up"' in html

    def test_MR_card_negative_delta_shows_red_down_arrow(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {"passing": {"current_level": 68}}, {"passing": -2})
        assert "#fc8181" in html
        assert "↓" in html
        assert 'color:#fc8181' in html

    def test_MR_card_zero_delta_hidden_trend_arrow(self):
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {"passing": {"current_level": 70}}, {"passing": 0})
        assert 'visibility:hidden' in html
        assert "var(--card-bar-neutral)" in html
        assert "var(--card-val-neutral)" in html

    def test_MR_card_renders_skill_row_for_each_skill(self):
        skills = [_make_skill("a", "Alpha"), _make_skill("b", "Beta"), _make_skill("c", "Gamma")]
        cat = _make_cat(skills=skills)
        html = self._render(cat, {}, {})
        assert html.count('class="skill-row"') == 3

    def test_MR_card_uses_round_1_for_score(self):
        cat = _make_cat(skills=[_make_skill("pace", "Pace")])
        html = self._render(cat, {"pace": {"current_level": 77.3}}, {})
        # round(1) → 77.3
        assert "77.3" in html

    def test_MR_card_no_wrapping_container_div(self):
        """card_skill_rows must NOT render an outer wrapper div (unlike export_skill_rows)."""
        cat = _make_cat(skills=[_make_skill("passing", "Passing")])
        html = self._render(cat, {}, {}).strip()
        assert not html.startswith('<div class="ex-skill-rows">')
        assert not html.startswith('<div class="skill-rows">')


# ---------------------------------------------------------------------------
# TestSponsorSlotMacro
# ---------------------------------------------------------------------------

class TestSponsorSlotMacro:
    """MR_ prefix — sponsor_slot macro from macros/card_sponsor_block.html"""

    MACRO_PATH = "macros/card_sponsor_block.html"
    MACRO_NAME = "sponsor_slot"

    def _render(self, sponsor_logo_url, app_logo_url):
        return _render_macro(
            self.MACRO_PATH, self.MACRO_NAME, sponsor_logo_url, app_logo_url
        )

    def test_MR_sponsor_logo_url_present_renders_sponsor_img(self):
        html = self._render("https://example.com/sponsor.png", None)
        assert 'alt="Sponsor"' in html
        assert "https://example.com/sponsor.png" in html
        assert 'class="ex-sponsor-slot-img"' in html

    def test_MR_sponsor_logo_none_app_logo_present_renders_lfa_img(self):
        html = self._render(None, "https://example.com/lfa-logo.png")
        assert 'alt="LFA"' in html
        assert "https://example.com/lfa-logo.png" in html

    def test_MR_both_none_no_img_rendered(self):
        html = self._render(None, None)
        assert "<img" not in html

    def test_MR_sponsor_logo_takes_priority_over_app_logo(self):
        html = self._render("https://sponsor.com/logo.png", "https://app.com/logo.png")
        assert 'alt="Sponsor"' in html
        assert 'alt="LFA"' not in html

    def test_MR_renders_ex_sponsor_slot_wrapper_div(self):
        html = self._render(None, None)
        assert 'class="ex-sponsor-slot"' in html


# ---------------------------------------------------------------------------
# TestExportRootVarsMacro
# ---------------------------------------------------------------------------

class TestExportRootVarsMacro:
    """MR_ prefix — export_root_vars macro from macros/card_theme_root.html"""

    MACRO_PATH = "macros/card_theme_root.html"
    MACRO_NAME = "export_root_vars"

    def _render(self, theme, **kw):
        return _render_macro(self.MACRO_PATH, self.MACRO_NAME, theme, **kw)

    def _make_theme(self):
        return SimpleNamespace(
            panel_bg="linear-gradient(155deg, #0d0d0d 0%, #1a1a2e 60%, #16213e 100%)",
            body_bg="#0f0f0f",
            accent="#00d4ff",
        )

    def test_MR_root_panel_bg_injected(self):
        html = self._render(self._make_theme())
        assert "--ex-panel-bg" in html
        assert "#0d0d0d" in html

    def test_MR_root_body_bg_injected(self):
        html = self._render(self._make_theme())
        assert "--ex-body-bg" in html
        assert "#0f0f0f" in html

    def test_MR_root_accent_injected(self):
        html = self._render(self._make_theme())
        assert "--ex-accent" in html
        assert "#00d4ff" in html

    def test_MR_root_default_cat_bg_is_005(self):
        html = self._render(self._make_theme())
        assert "rgba(255,255,255,0.05)" in html

    def test_MR_root_default_bar_bg_is_010(self):
        html = self._render(self._make_theme())
        assert "rgba(255,255,255,0.10)" in html

    def test_MR_root_custom_cat_bg_square(self):
        html = self._render(self._make_theme(), cat_bg='rgba(255,255,255,0.06)')
        assert "rgba(255,255,255,0.06)" in html

    def test_MR_root_custom_cat_bg_landscape(self):
        html = self._render(self._make_theme(), cat_bg='rgba(255,255,255,0.04)')
        assert "rgba(255,255,255,0.04)" in html

    def test_MR_root_undefined_theme_uses_defaults(self):
        html = _render_macro(self.MACRO_PATH, self.MACRO_NAME)
        assert "--ex-panel-bg" in html
        assert "#1a2744" in html
        assert "#1a202c" in html
        assert "#667eea" in html

    def test_MR_root_outputs_root_block(self):
        html = self._render(self._make_theme())
        assert ":root" in html
        assert "--ex-panel-bg" in html
        assert "--ex-body-bg" in html
        assert "--ex-accent" in html
        assert "--ex-bar-bg" in html
        assert "--ex-cat-bg" in html
