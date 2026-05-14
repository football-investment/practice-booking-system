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
        assert "var(--ex-text-secondary)" in html
        assert "var(--ex-text-strong)" in html

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


# ---------------------------------------------------------------------------
# TestExportRootVarsDarkLight  (Phase 2b — arctic / light-theme token system)
# ---------------------------------------------------------------------------

class TestExportRootVarsDarkLight:
    """MR_ prefix — light/dark text token behaviour in export_root_vars."""

    MACRO_PATH = "macros/card_theme_root.html"
    MACRO_NAME = "export_root_vars"

    def _dark_theme(self):
        return SimpleNamespace(
            panel_bg="linear-gradient(155deg, #0d0d0d 0%, #1a1a2e 60%, #16213e 100%)",
            body_bg="#0f0f0f",
            accent="#00d4ff",
            is_light_body_bg=False,
        )

    def _light_theme(self):
        """Simulates arctic: near-white body_bg, is_light_body_bg=True."""
        return SimpleNamespace(
            panel_bg="linear-gradient(155deg, #1a2744 0%, #2a3a5c 60%, #1e3a4a 100%)",
            body_bg="#f7fafc",
            accent="#4299e1",
            is_light_body_bg=True,
        )

    def _render(self, theme, **kw):
        return _render_macro(self.MACRO_PATH, self.MACRO_NAME, theme, **kw)

    # -- dark theme emits white text tokens -----------------------------------

    def test_MR_dark_theme_emits_white_text_strong(self):
        html = self._render(self._dark_theme())
        assert "rgba(255,255,255,0.85)" in html

    def test_MR_dark_theme_emits_white_text_body(self):
        html = self._render(self._dark_theme())
        assert "rgba(255,255,255,0.72)" in html

    def test_MR_dark_theme_emits_white_text_secondary(self):
        html = self._render(self._dark_theme())
        assert "rgba(255,255,255,0.48)" in html

    def test_MR_dark_theme_emits_white_text_muted(self):
        html = self._render(self._dark_theme())
        assert "rgba(255,255,255,0.30)" in html

    def test_MR_dark_theme_preserves_white_bar_bg(self):
        html = self._render(self._dark_theme())
        assert "rgba(255,255,255,0.10)" in html

    # -- light theme emits dark text tokens -----------------------------------

    def test_MR_light_theme_emits_dark_text_strong(self):
        html = self._render(self._light_theme())
        assert "rgba(0,0,0,0.87)" in html

    def test_MR_light_theme_emits_dark_text_body(self):
        html = self._render(self._light_theme())
        assert "rgba(0,0,0,0.75)" in html

    def test_MR_light_theme_emits_dark_text_secondary(self):
        html = self._render(self._light_theme())
        assert "rgba(0,0,0,0.55)" in html

    def test_MR_light_theme_emits_dark_text_muted(self):
        html = self._render(self._light_theme())
        assert "rgba(0,0,0,0.38)" in html

    def test_MR_light_theme_emits_dark_bar_bg(self):
        html = self._render(self._light_theme())
        assert "rgba(0,0,0,0.08)" in html

    def test_MR_light_theme_emits_dark_cat_bg(self):
        html = self._render(self._light_theme())
        assert "rgba(0,0,0,0.06)" in html

    def test_MR_light_theme_ignores_platform_cat_bg_param(self):
        """Platform cat_bg param is ignored for light themes — dark value used."""
        html = self._render(self._light_theme(), cat_bg='rgba(255,255,255,0.06)')
        assert "rgba(0,0,0,0.06)" in html
        assert "--ex-cat-bg:         rgba(0,0,0,0.06)" in html

    def test_MR_light_theme_no_white_text_tokens_emitted(self):
        """Light theme must not emit any of the dark-theme white text token values."""
        html = self._render(self._light_theme())
        assert "--ex-text-strong:    rgba(255,255,255" not in html
        assert "--ex-text-body:      rgba(255,255,255" not in html
        assert "--ex-text-secondary: rgba(255,255,255" not in html
        assert "--ex-text-muted:     rgba(255,255,255" not in html

    # -- skill row macro uses CSS vars ----------------------------------------

    def test_MR_skill_row_neutral_val_is_css_var(self):
        """export_skill_rows zero-delta neutral_val must be var(--ex-text-strong)."""
        import os, app as _app_pkg
        tpl_dir = os.path.join(os.path.dirname(_app_pkg.__file__), "templates")
        with open(os.path.join(tpl_dir, "macros/card_skill_row.html")) as f:
            src = f.read()
        assert "neutral_val='var(--ex-text-strong)'" in src

    def test_MR_skill_row_neutral_bar_is_css_var(self):
        """export_skill_rows zero-delta neutral_bar must be var(--ex-text-secondary)."""
        import os, app as _app_pkg
        tpl_dir = os.path.join(os.path.dirname(_app_pkg.__file__), "templates")
        with open(os.path.join(tpl_dir, "macros/card_skill_row.html")) as f:
            src = f.read()
        assert "neutral_bar='var(--ex-text-secondary)'" in src

    # -- template CSS: no hardcoded white RGBA for tokenised body classes ------

    def test_MR_template_square_no_hardcoded_white_text_color_in_tokenised_classes(self):
        """Verify text color (not border/background) is tokenised in body-section classes."""
        import os, app as _app_pkg, re
        tpl_dir = os.path.join(os.path.dirname(_app_pkg.__file__), "templates")
        with open(os.path.join(tpl_dir, "public/export/square/fifa.html")) as f:
            src = f.read()
        tokenised = [".ex-skills-title", ".ex-cat-name", ".ex-sname",
                     ".ex-pos-panel-title", ".ex-pos-primary-label", ".ex-pos-secondary-label"]
        for cls in tokenised:
            block = re.search(rf'{re.escape(cls)}\s*{{([^}}]+)}}', src)
            if block:
                # Only check the `color:` property, not borders/backgrounds
                color_lines = [l for l in block.group(1).splitlines()
                               if re.search(r'\bcolor:', l) and 'border' not in l]
                for line in color_lines:
                    assert "rgba(255,255,255" not in line, \
                        f"Hardcoded white RGBA in `color:` property of {cls} in square template: {line.strip()}"

    def test_MR_template_story_no_hardcoded_white_text_color_in_tokenised_classes(self):
        import os, app as _app_pkg, re
        tpl_dir = os.path.join(os.path.dirname(_app_pkg.__file__), "templates")
        with open(os.path.join(tpl_dir, "public/export/story/fifa.html")) as f:
            src = f.read()
        for cls in [".ex-skills-title", ".ex-cat-name", ".ex-sname"]:
            block = re.search(rf'{re.escape(cls)}\s*{{([^}}]+)}}', src)
            if block:
                color_lines = [l for l in block.group(1).splitlines()
                               if re.search(r'\bcolor:', l) and 'border' not in l]
                for line in color_lines:
                    assert "rgba(255,255,255" not in line, \
                        f"Hardcoded white RGBA in `color:` property of {cls} in story template: {line.strip()}"
