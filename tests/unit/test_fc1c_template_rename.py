"""
TPL-01..TPL-06  Template file rename verification (PR-FC-1C)
SVC-01..SVC-06  Python symbol rename verification (PR-FC-1C)

TPL-01  player_card_fclassic.html exists
TPL-02  player_card_fifa.html does NOT exist
TPL-03  all 7 export buckets have fclassic.html
TPL-04  all 7 export buckets do NOT have fifa.html
TPL-05  get_design("fifa").template == "public/player_card_fclassic.html"  (alias)
TPL-06  get_design("fclassic").template == "public/player_card_fclassic.html"
TPL-07  Level C template path resolves to fclassic.html for "fclassic" input
TPL-08  Level C template path resolves to fclassic.html for "fifa" alias input
SVC-01  _FCLASSIC_COMPONENT_CONFIG exists in card_design_service
SVC-02  _FIFA_COMPONENT_CONFIG does NOT exist in card_design_service
SVC-03  FCLASSIC_CAPABILITIES is importable from card_system.registry
SVC-04  FIFA_CLASSIC_CAPABILITIES is NOT importable from card_system.registry
SVC-05  is_animated_capable("fifa", "instagram_square") aliasként True
SVC-06  is_animated_capable("fclassic", "instagram_square") True
"""
from __future__ import annotations

from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "app" / "templates"

_EXPORT_BUCKETS = ["square", "portrait", "landscape", "og", "tiktok", "story", "banner"]


# ── TPL-01/02: player_card template filename ──────────────────────────────────

class TestTPL0102PlayerCardTemplate:

    def test_tpl_01_player_card_fclassic_exists(self):
        """TPL-01: player_card_fclassic.html exists after rename."""
        assert (TEMPLATES_DIR / "public/player_card_fclassic.html").exists(), (
            "public/player_card_fclassic.html must exist"
        )

    def test_tpl_02_player_card_fifa_does_not_exist(self):
        """TPL-02: player_card_fifa.html must NOT exist after rename."""
        assert not (TEMPLATES_DIR / "public/player_card_fifa.html").exists(), (
            "public/player_card_fifa.html must be removed (renamed to fclassic)"
        )


# ── TPL-03/04: export bucket templates ───────────────────────────────────────

class TestTPL0304ExportBucketTemplates:

    def test_tpl_03_all_export_fclassic_exist(self):
        """TPL-03: all 7 export buckets have fclassic.html after rename."""
        for bucket in _EXPORT_BUCKETS:
            path = TEMPLATES_DIR / f"public/export/{bucket}/fclassic.html"
            assert path.exists(), f"public/export/{bucket}/fclassic.html must exist"

    def test_tpl_04_no_export_fifa_exists(self):
        """TPL-04: no export bucket has fifa.html after rename."""
        for bucket in _EXPORT_BUCKETS:
            path = TEMPLATES_DIR / f"public/export/{bucket}/fifa.html"
            assert not path.exists(), (
                f"public/export/{bucket}/fifa.html must be removed (renamed to fclassic)"
            )


# ── TPL-05/06/07/08: template path resolution ────────────────────────────────

class TestTPL0508TemplatePathResolution:

    def test_tpl_05_get_design_fifa_template_is_fclassic(self):
        """TPL-05: get_design('fifa').template == 'public/player_card_fclassic.html' (alias)."""
        from app.services.card_design_service import get_design
        d = get_design("fifa")
        assert d.template == "public/player_card_fclassic.html", (
            f"get_design('fifa').template must be 'public/player_card_fclassic.html', "
            f"got {d.template!r}"
        )

    def test_tpl_06_get_design_fclassic_template_is_fclassic(self):
        """TPL-06: get_design('fclassic').template == 'public/player_card_fclassic.html'."""
        from app.services.card_design_service import get_design
        d = get_design("fclassic")
        assert d.template == "public/player_card_fclassic.html", (
            f"get_design('fclassic').template must be 'public/player_card_fclassic.html', "
            f"got {d.template!r}"
        )

    def test_tpl_07_level_c_path_for_fclassic_resolves_to_fclassic_html(self):
        """TPL-07: Level C path for 'fclassic' variant_id → fclassic.html per bucket."""
        from app.services.card_design_service import resolve_design_id
        for bucket in _EXPORT_BUCKETS:
            canonical = resolve_design_id("fclassic")
            path = f"public/export/{bucket}/{canonical}.html"
            assert "fclassic" in path, (
                f"Level C path for 'fclassic' must contain 'fclassic': {path}"
            )
            assert "fifa" not in path, (
                f"Level C path for 'fclassic' must not contain 'fifa': {path}"
            )

    def test_tpl_08_level_c_path_for_fifa_alias_resolves_to_fclassic_html(self):
        """TPL-08: Level C path for 'fifa' alias → resolves to fclassic.html per bucket."""
        from app.services.card_design_service import resolve_design_id
        for bucket in _EXPORT_BUCKETS:
            canonical = resolve_design_id("fifa")  # alias → "fclassic"
            path = f"public/export/{bucket}/{canonical}.html"
            assert "fclassic" in path, (
                f"Level C path for 'fifa' alias must resolve to 'fclassic': {path}"
            )
            assert "fifa" not in path, (
                f"Level C path for 'fifa' alias must not contain 'fifa': {path}"
            )


# ── SVC-01/02: _FCLASSIC_COMPONENT_CONFIG ────────────────────────────────────

class TestSVC0102ComponentConfig:

    def test_svc_01_fclassic_component_config_exists(self):
        """SVC-01: _FCLASSIC_COMPONENT_CONFIG exists in card_design_service."""
        import app.services.card_design_service as svc
        assert hasattr(svc, "_FCLASSIC_COMPONENT_CONFIG"), (
            "_FCLASSIC_COMPONENT_CONFIG must exist in card_design_service"
        )
        assert isinstance(svc._FCLASSIC_COMPONENT_CONFIG, dict)

    def test_svc_02_fifa_component_config_removed(self):
        """SVC-02: _FIFA_COMPONENT_CONFIG must NOT exist in card_design_service."""
        import app.services.card_design_service as svc
        assert not hasattr(svc, "_FIFA_COMPONENT_CONFIG"), (
            "_FIFA_COMPONENT_CONFIG must be removed (renamed to _FCLASSIC_COMPONENT_CONFIG)"
        )


# ── SVC-03/04: FCLASSIC_CAPABILITIES ─────────────────────────────────────────

class TestSVC0304Capabilities:

    def test_svc_03_fclassic_capabilities_importable(self):
        """SVC-03: FCLASSIC_CAPABILITIES is importable from card_system.registry."""
        from app.services.card_system.registry import FCLASSIC_CAPABILITIES
        assert FCLASSIC_CAPABILITIES is not None
        assert FCLASSIC_CAPABILITIES.animated_mode is True

    def test_svc_04_fifa_classic_capabilities_not_importable(self):
        """SVC-04: FIFA_CLASSIC_CAPABILITIES must NOT exist in card_system.registry."""
        import app.services.card_system.registry as registry
        assert not hasattr(registry, "FIFA_CLASSIC_CAPABILITIES"), (
            "FIFA_CLASSIC_CAPABILITIES must be removed (renamed to FCLASSIC_CAPABILITIES)"
        )


# ── SVC-05/06: is_animated_capable alias ─────────────────────────────────────

class TestSVC0506AnimatedCapable:

    def test_svc_05_is_animated_capable_fifa_alias_true(self):
        """SVC-05: is_animated_capable('fifa', 'instagram_square') aliasként True."""
        from app.services.card_constants import is_animated_capable
        assert is_animated_capable("fifa", "instagram_square") is True

    def test_svc_06_is_animated_capable_fclassic_true(self):
        """SVC-06: is_animated_capable('fclassic', 'instagram_square') True."""
        from app.services.card_constants import is_animated_capable
        assert is_animated_capable("fclassic", "instagram_square") is True
