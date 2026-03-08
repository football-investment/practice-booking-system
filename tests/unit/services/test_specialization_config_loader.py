"""
Unit tests for app/services/specialization_config_loader.py
Covers: SpecializationConfigLoader, get_config_loader, load_specialization_config
Uses real config files for happy paths; tempfile for error paths.
"""
import json
import tempfile
import pytest
from pathlib import Path

from app.services.specialization_config_loader import (
    SpecializationConfigLoader,
    get_config_loader,
    load_specialization_config,
)
from app.models.specialization import SpecializationType

import app.services.specialization_config_loader as _mod

# ---------------------------------------------------------------------------
# Helpers — minimal valid config for temp-dir tests
# ---------------------------------------------------------------------------

_VALID_CFG = {
    "id": "TEST",
    "name": "Test Spec",
    "description": "Test description",
    "min_age": 10,
    "levels": [
        {"level": 1, "name": "Beginner", "xp_required": 0, "xp_max": 999},
        {"level": 2, "name": "Intermediate", "xp_required": 1000, "xp_max": 4999},
    ],
}


def _write_json(directory: Path, filename: str, data: dict) -> Path:
    path = directory / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _make_loader_with_config(cfg: dict) -> SpecializationConfigLoader:
    """Create a SpecializationConfigLoader pointing at a tempdir with gancuju_player.json."""
    tmp = tempfile.mkdtemp()
    tmp_path = Path(tmp)
    _write_json(tmp_path, "gancuju_player.json", cfg)
    loader = SpecializationConfigLoader(config_dir=tmp_path)
    return loader


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestInit:
    def test_valid_config_dir_ok(self):
        """Default config dir (real files) initialises without error."""
        loader = SpecializationConfigLoader()
        assert loader.config_dir.exists()

    def test_missing_config_dir_raises(self):
        """Non-existent config_dir → ValueError."""
        with pytest.raises(ValueError, match="not found"):
            SpecializationConfigLoader(config_dir=Path("/nonexistent/path/abc"))


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_valid_spec_returns_dict(self):
        """GANCUJU_PLAYER config loads successfully from real files."""
        loader = SpecializationConfigLoader()
        loader.clear_cache()
        cfg = loader.load_config(SpecializationType.GANCUJU_PLAYER)
        assert "id" in cfg
        assert "levels" in cfg
        assert isinstance(cfg["levels"], list)
        assert len(cfg["levels"]) > 0

    def test_missing_file_raises_file_not_found(self):
        """Config file referenced in map but not on disk → FileNotFoundError."""
        tmp = tempfile.mkdtemp()
        # Empty dir — no gancuju_player.json
        loader = SpecializationConfigLoader(config_dir=Path(tmp))
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load_config(SpecializationType.GANCUJU_PLAYER)

    def test_invalid_json_raises_value_error(self):
        """Malformed JSON in config file → ValueError."""
        tmp = tempfile.mkdtemp()
        tmp_path = Path(tmp)
        (tmp_path / "gancuju_player.json").write_text("{ broken json !!!", encoding="utf-8")
        loader = SpecializationConfigLoader(config_dir=tmp_path)
        with pytest.raises(ValueError, match="Invalid JSON"):
            loader.load_config(SpecializationType.GANCUJU_PLAYER)

    def test_missing_required_top_fields_raises(self):
        """Config missing top-level required fields (e.g. 'description') → ValueError."""
        bad_cfg = {"id": "X", "name": "X", "min_age": 5, "levels": [
            {"level": 1, "name": "L1", "xp_required": 0, "xp_max": 100}
        ]}  # no 'description'
        loader = _make_loader_with_config(bad_cfg)
        with pytest.raises(ValueError, match="missing required fields"):
            loader.load_config(SpecializationType.GANCUJU_PLAYER)

    def test_empty_levels_raises(self):
        """levels=[] → ValueError."""
        bad_cfg = dict(_VALID_CFG)
        bad_cfg["levels"] = []
        loader = _make_loader_with_config(bad_cfg)
        with pytest.raises(ValueError, match="at least one level"):
            loader.load_config(SpecializationType.GANCUJU_PLAYER)

    def test_levels_not_a_list_raises(self):
        """levels is not a list → ValueError."""
        bad_cfg = dict(_VALID_CFG)
        bad_cfg["levels"] = "not-a-list"
        loader = _make_loader_with_config(bad_cfg)
        with pytest.raises(ValueError, match="at least one level"):
            loader.load_config(SpecializationType.GANCUJU_PLAYER)

    def test_level_missing_fields_raises(self):
        """Level entry missing xp_required → ValueError."""
        bad_cfg = dict(_VALID_CFG)
        bad_cfg["levels"] = [{"level": 1, "name": "L1", "xp_max": 999}]  # no xp_required
        loader = _make_loader_with_config(bad_cfg)
        with pytest.raises(ValueError, match="missing fields"):
            loader.load_config(SpecializationType.GANCUJU_PLAYER)


# ---------------------------------------------------------------------------
# get_level_config
# ---------------------------------------------------------------------------

class TestGetLevelConfig:
    def setup_method(self):
        self.loader = _make_loader_with_config(_VALID_CFG)

    def test_found_returns_dict(self):
        cfg = self.loader.get_level_config(SpecializationType.GANCUJU_PLAYER, 1)
        assert cfg is not None
        assert cfg["level"] == 1
        assert cfg["name"] == "Beginner"

    def test_not_found_returns_none(self):
        cfg = self.loader.get_level_config(SpecializationType.GANCUJU_PLAYER, 999)
        assert cfg is None

    def test_second_level_found(self):
        cfg = self.loader.get_level_config(SpecializationType.GANCUJU_PLAYER, 2)
        assert cfg is not None
        assert cfg["level"] == 2


# ---------------------------------------------------------------------------
# get_xp_range
# ---------------------------------------------------------------------------

class TestGetXpRange:
    def setup_method(self):
        self.loader = _make_loader_with_config(_VALID_CFG)

    def test_valid_level_returns_tuple(self):
        lo, hi = self.loader.get_xp_range(SpecializationType.GANCUJU_PLAYER, 1)
        assert lo == 0
        assert hi == 999

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.loader.get_xp_range(SpecializationType.GANCUJU_PLAYER, 999)


# ---------------------------------------------------------------------------
# get_max_level
# ---------------------------------------------------------------------------

class TestGetMaxLevel:
    def test_returns_max_int(self):
        loader = _make_loader_with_config(_VALID_CFG)
        assert loader.get_max_level(SpecializationType.GANCUJU_PLAYER) == 2

    def test_real_config_max_level(self):
        loader = SpecializationConfigLoader()
        loader.clear_cache()
        max_lvl = loader.get_max_level(SpecializationType.GANCUJU_PLAYER)
        assert isinstance(max_lvl, int)
        assert max_lvl >= 1


# ---------------------------------------------------------------------------
# get_level_name
# ---------------------------------------------------------------------------

class TestGetLevelName:
    def setup_method(self):
        # Config with name_en on level 1, no name_en on level 2
        cfg = dict(_VALID_CFG)
        cfg["levels"] = [
            {"level": 1, "name": "Kezdő", "name_en": "Beginner", "xp_required": 0, "xp_max": 999},
            {"level": 2, "name": "Közepes", "xp_required": 1000, "xp_max": 4999},
        ]
        self.loader = _make_loader_with_config(cfg)

    def test_level_not_found_returns_placeholder(self):
        name = self.loader.get_level_name(SpecializationType.GANCUJU_PLAYER, 999)
        assert name == "Level 999"

    def test_english_false_returns_default_name(self):
        name = self.loader.get_level_name(SpecializationType.GANCUJU_PLAYER, 1, english=False)
        assert name == "Kezdő"

    def test_english_true_with_name_en(self):
        name = self.loader.get_level_name(SpecializationType.GANCUJU_PLAYER, 1, english=True)
        assert name == "Beginner"

    def test_english_true_without_name_en_fallback(self):
        """Level 2 has no name_en → falls back to name."""
        name = self.loader.get_level_name(SpecializationType.GANCUJU_PLAYER, 2, english=True)
        assert name == "Közepes"


# ---------------------------------------------------------------------------
# get_level_requirements
# ---------------------------------------------------------------------------

class TestGetLevelRequirements:
    def setup_method(self):
        cfg = dict(_VALID_CFG)
        cfg["levels"] = [
            {
                "level": 1, "name": "L1", "xp_required": 0, "xp_max": 999,
                "requirements": {"theory_hours": 5, "practice_hours": 20},
            },
            {"level": 2, "name": "L2", "xp_required": 1000, "xp_max": 4999},
        ]
        self.loader = _make_loader_with_config(cfg)

    def test_with_requirements(self):
        reqs = self.loader.get_level_requirements(SpecializationType.GANCUJU_PLAYER, 1)
        assert reqs == {"theory_hours": 5, "practice_hours": 20}

    def test_level_not_found_returns_empty_dict(self):
        reqs = self.loader.get_level_requirements(SpecializationType.GANCUJU_PLAYER, 999)
        assert reqs == {}

    def test_level_with_no_requirements_key(self):
        """Level 2 has no 'requirements' key → empty dict."""
        reqs = self.loader.get_level_requirements(SpecializationType.GANCUJU_PLAYER, 2)
        assert reqs == {}


# ---------------------------------------------------------------------------
# get_age_groups
# ---------------------------------------------------------------------------

class TestGetAgeGroups:
    def test_no_age_groups_returns_empty_list(self):
        loader = _make_loader_with_config(_VALID_CFG)  # no age_groups
        result = loader.get_age_groups(SpecializationType.GANCUJU_PLAYER)
        assert result == []

    def test_with_age_groups(self):
        cfg = dict(_VALID_CFG)
        cfg["age_groups"] = [{"name": "PRE", "min_age": 5, "max_age": 10}]
        loader = _make_loader_with_config(cfg)
        result = loader.get_age_groups(SpecializationType.GANCUJU_PLAYER)
        assert len(result) == 1
        assert result[0]["name"] == "PRE"

    def test_real_lfa_player_has_age_groups(self):
        """LFA_FOOTBALL_PLAYER should define age_groups in real config."""
        loader = SpecializationConfigLoader()
        loader.clear_cache()
        result = loader.get_age_groups(SpecializationType.LFA_FOOTBALL_PLAYER)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# get_display_info
# ---------------------------------------------------------------------------

class TestGetDisplayInfo:
    def test_returns_expected_keys(self):
        loader = _make_loader_with_config(_VALID_CFG)
        info = loader.get_display_info(SpecializationType.GANCUJU_PLAYER)
        assert "id" in info
        assert "name" in info
        assert "description" in info
        assert "min_age" in info
        assert info["id"] == "TEST"
        assert info["min_age"] == 10

    def test_missing_optional_fields_return_none(self):
        loader = _make_loader_with_config(_VALID_CFG)  # no icon, no color_theme
        info = loader.get_display_info(SpecializationType.GANCUJU_PLAYER)
        assert info["icon"] is None
        assert info["color_theme"] is None


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------

class TestClearCache:
    def test_clear_cache_works(self):
        """clear_cache() does not raise and allows re-loading config."""
        loader = _make_loader_with_config(_VALID_CFG)
        loader.load_config(SpecializationType.GANCUJU_PLAYER)  # populate cache
        loader.clear_cache()
        # Should re-load without error
        cfg = loader.load_config(SpecializationType.GANCUJU_PLAYER)
        assert cfg is not None


# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------

class TestModuleFunctions:
    def test_get_config_loader_singleton(self):
        """get_config_loader() returns the same instance on repeated calls."""
        _mod._loader_instance = None
        l1 = get_config_loader()
        l2 = get_config_loader()
        assert l1 is l2
        _mod._loader_instance = None  # cleanup

    def test_get_config_loader_creates_instance(self):
        _mod._loader_instance = None
        loader = get_config_loader()
        assert isinstance(loader, SpecializationConfigLoader)
        _mod._loader_instance = None  # cleanup

    def test_load_specialization_config_convenience(self):
        """load_specialization_config() wraps get_config_loader().load_config()."""
        _mod._loader_instance = None
        cfg = load_specialization_config(SpecializationType.GANCUJU_PLAYER)
        assert "id" in cfg
        assert "levels" in cfg
        _mod._loader_instance = None  # cleanup
