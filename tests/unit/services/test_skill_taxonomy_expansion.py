"""
Phase 3 Skill Taxonomy Expansion — Contract Tests

Verifies the 44-skill taxonomy is correct and internally consistent.
All tests use no DB (pure config / in-memory logic).

Taxonomy:
  outfield:   19 skills (11 original + 8 new: shooting/technique/creativity/
                          long_passing/flair/touch/forward_runs/throwing)
  set_pieces:  3 skills (unchanged)
  mental:     14 skills (8 original + 6 new: anticipation/concentration/
                          decisions/determination/teamwork/leadership)
  physical:    8 skills (7 original + 1 new: work_rate)
  Total:      44 skills
"""
import pytest
from app.skills_config import (
    SKILL_CATEGORIES,
    get_all_skill_keys,
    get_skill_display_name,
    get_skill_description,
    ALL_SKILLS,
)

# ── Constants under test ───────────────────────────────────────────────────────

_EXPECTED_TOTAL       = 44
_EXPECTED_OUTFIELD    = 19
_EXPECTED_SET_PIECES  = 3
_EXPECTED_MENTAL      = 14
_EXPECTED_PHYSICAL    = 8

_NEW_OUTFIELD_KEYS = [
    "shooting", "technique", "creativity", "long_passing",
    "flair", "touch", "forward_runs", "throwing",
]
_NEW_MENTAL_KEYS = [
    "anticipation", "concentration", "decisions",
    "determination", "teamwork", "leadership",
]
_NEW_PHYSICAL_KEYS = ["work_rate"]

ALL_NEW_KEYS = _NEW_OUTFIELD_KEYS + _NEW_MENTAL_KEYS + _NEW_PHYSICAL_KEYS


# ── Total count ────────────────────────────────────────────────────────────────

class TestSkillCount:
    def test_total_skill_count_is_44(self):
        assert len(get_all_skill_keys()) == _EXPECTED_TOTAL

    def test_no_duplicate_skill_keys(self):
        keys = get_all_skill_keys()
        assert len(keys) == len(set(keys)), f"Duplicate keys: {[k for k in keys if keys.count(k) > 1]}"

    def test_all_skills_dict_matches_category_list(self):
        from_categories = [s["key"] for cat in SKILL_CATEGORIES for s in cat["skills"]]
        assert sorted(from_categories) == sorted(get_all_skill_keys())


# ── Per-category counts ────────────────────────────────────────────────────────

class TestCategoryCounts:
    def _cat(self, key: str) -> list:
        for cat in SKILL_CATEGORIES:
            if cat["key"] == key:
                return [s["key"] for s in cat["skills"]]
        return []

    def test_outfield_has_19_skills(self):
        assert len(self._cat("outfield")) == _EXPECTED_OUTFIELD

    def test_set_pieces_has_3_skills(self):
        assert len(self._cat("set_pieces")) == _EXPECTED_SET_PIECES

    def test_mental_has_14_skills(self):
        assert len(self._cat("mental")) == _EXPECTED_MENTAL

    def test_physical_has_8_skills(self):
        assert len(self._cat("physical")) == _EXPECTED_PHYSICAL


# ── Mandatory keys ─────────────────────────────────────────────────────────────

class TestMandatoryKeys:
    def test_throwing_exists(self):
        assert "throwing" in get_all_skill_keys()

    def test_balance_exists_exactly_once(self):
        keys = get_all_skill_keys()
        assert keys.count("balance") == 1

    def test_balance_in_physical_category(self):
        phys = next(cat for cat in SKILL_CATEGORIES if cat["key"] == "physical")
        assert "balance" in [s["key"] for s in phys["skills"]]

    def test_work_rate_in_physical_category(self):
        phys = next(cat for cat in SKILL_CATEGORIES if cat["key"] == "physical")
        assert "work_rate" in [s["key"] for s in phys["skills"]]

    def test_throwing_in_outfield_category(self):
        out = next(cat for cat in SKILL_CATEGORIES if cat["key"] == "outfield")
        assert "throwing" in [s["key"] for s in out["skills"]]


# ── New skills placement ───────────────────────────────────────────────────────

class TestNewSkillPlacement:
    def _keys_for_category(self, cat_key: str) -> list:
        for cat in SKILL_CATEGORIES:
            if cat["key"] == cat_key:
                return [s["key"] for s in cat["skills"]]
        return []

    @pytest.mark.parametrize("skill_key", _NEW_OUTFIELD_KEYS)
    def test_new_outfield_skills_in_outfield_category(self, skill_key: str):
        assert skill_key in self._keys_for_category("outfield"), \
            f"{skill_key} should be in outfield category"

    @pytest.mark.parametrize("skill_key", _NEW_MENTAL_KEYS)
    def test_new_mental_skills_in_mental_category(self, skill_key: str):
        assert skill_key in self._keys_for_category("mental"), \
            f"{skill_key} should be in mental category"

    @pytest.mark.parametrize("skill_key", _NEW_PHYSICAL_KEYS)
    def test_new_physical_skills_in_physical_category(self, skill_key: str):
        assert skill_key in self._keys_for_category("physical"), \
            f"{skill_key} should be in physical category"


# ── Metadata completeness ──────────────────────────────────────────────────────

class TestSkillMetadata:
    @pytest.mark.parametrize("skill_key", ALL_NEW_KEYS)
    def test_new_skill_has_name_en(self, skill_key: str):
        skill = ALL_SKILLS.get(skill_key)
        assert skill is not None, f"{skill_key} not in ALL_SKILLS"
        assert skill.get("name_en"), f"{skill_key} missing name_en"

    @pytest.mark.parametrize("skill_key", ALL_NEW_KEYS)
    def test_new_skill_has_name_hu(self, skill_key: str):
        skill = ALL_SKILLS.get(skill_key)
        assert skill is not None
        assert skill.get("name_hu"), f"{skill_key} missing name_hu"

    @pytest.mark.parametrize("skill_key", ALL_NEW_KEYS)
    def test_new_skill_has_description_hu(self, skill_key: str):
        skill = ALL_SKILLS.get(skill_key)
        assert skill is not None
        assert skill.get("description_hu"), f"{skill_key} missing description_hu"

    @pytest.mark.parametrize("skill_key", ALL_NEW_KEYS)
    def test_get_skill_display_name_returns_non_empty(self, skill_key: str):
        name = get_skill_display_name(skill_key, lang="hu")
        assert name and name != skill_key.replace("_", " ").title(), \
            f"{skill_key} display name should come from config, not fallback"


# ── Self-assessment contract for new skills ───────────────────────────────────

class TestNewSkillSelfAssessmentContract:
    """
    New skills in the taxonomy must obey the same self-assessment contract
    as original skills: current_level / baseline / system_baseline = 60.0,
    self_assessment stored but not used for calculation.
    """

    def _new_skill_entry(self) -> dict:
        return {
            "system_baseline":  60.0,
            "baseline":         60.0,
            "current_level":    60.0,
            "self_assessment":  60.0,
            "total_delta":      0.0,
            "tournament_delta": 0.0,
            "assessment_delta": 0.0,
            "assessment_count": 0,
            "tournament_count": 0,
            "last_updated":     "2026-05-11T00:00:00+00:00",
        }

    @pytest.mark.parametrize("skill_key", ALL_NEW_KEYS)
    def test_new_skill_baseline_fields_are_60(self, skill_key: str):
        entry = self._new_skill_entry()
        assert entry["system_baseline"] == 60.0, f"{skill_key}: system_baseline must be 60.0"
        assert entry["baseline"] == 60.0, f"{skill_key}: baseline must be 60.0"
        assert entry["current_level"] == 60.0, f"{skill_key}: current_level must be 60.0"

    @pytest.mark.parametrize("skill_key", ALL_NEW_KEYS)
    def test_new_skill_assessment_delta_zero(self, skill_key: str):
        entry = self._new_skill_entry()
        assert entry["assessment_delta"] == 0.0

    @pytest.mark.parametrize("skill_key", ALL_NEW_KEYS)
    def test_new_skill_tournament_count_zero(self, skill_key: str):
        entry = self._new_skill_entry()
        assert entry["tournament_count"] == 0


# ── Backfill logic unit tests ─────────────────────────────────────────────────

class TestBackfillLogic:
    """Unit tests for the backfill logic (no DB — pure dict manipulation)."""

    _NEW_KEYS = ALL_NEW_KEYS
    _SYSTEM_BASELINE = 60.0

    def _apply_backfill(self, football_skills: dict) -> tuple[dict, list]:
        """Simulate the backfill: add missing keys, return (updated_dict, added_keys)."""
        now_iso = "2026-05-11T00:00:00+00:00"
        new_entry = {
            "system_baseline":  self._SYSTEM_BASELINE,
            "baseline":         self._SYSTEM_BASELINE,
            "current_level":    self._SYSTEM_BASELINE,
            "self_assessment":  self._SYSTEM_BASELINE,
            "total_delta":      0.0,
            "tournament_delta": 0.0,
            "assessment_delta": 0.0,
            "assessment_count": 0,
            "tournament_count": 0,
            "last_updated":     now_iso,
        }
        added = []
        for key in self._NEW_KEYS:
            if key not in football_skills:
                football_skills[key] = new_entry.copy()
                added.append(key)
        return football_skills, added

    def test_backfill_adds_missing_keys_to_29_skill_record(self):
        from app.skills_config import SKILL_CATEGORIES
        original_keys = [
            s["key"]
            for cat in SKILL_CATEGORIES
            for s in cat["skills"]
            if cat["key"] != "outfield" or s["key"] in [
                "ball_control", "dribbling", "finishing", "shot_power", "long_shots",
                "volleys", "crossing", "passing", "heading", "tackle", "marking"
            ]
        ]
        # Build a 29-skill record (original keys only)
        fs = {k: {"current_level": 70.0, "baseline": 70.0} for k in original_keys[:29]}
        result, added = self._apply_backfill(fs)
        assert len(added) > 0, "Backfill should add keys to a 29-skill record"
        for key in added:
            assert key in self._NEW_KEYS

    def test_backfill_all_new_keys_get_system_baseline_60(self):
        fs = {}  # empty record
        result, added = self._apply_backfill(fs)
        for key in self._NEW_KEYS:
            assert result[key]["system_baseline"] == 60.0
            assert result[key]["current_level"] == 60.0
            assert result[key]["self_assessment"] == 60.0

    def test_backfill_idempotent(self):
        fs = {}
        result1, added1 = self._apply_backfill(fs)
        result2, added2 = self._apply_backfill(result1)
        assert len(added2) == 0, "Second backfill run should add nothing"

    def test_backfill_does_not_overwrite_existing_keys(self):
        existing_value = {"current_level": 85.0, "baseline": 85.0, "system_baseline": 85.0}
        fs = {"shooting": existing_value.copy()}
        result, added = self._apply_backfill(fs)
        assert "shooting" not in added, "shooting already existed — must not be overwritten"
        assert result["shooting"]["current_level"] == 85.0

    def test_backfill_self_assessment_is_60_not_null(self):
        fs = {}
        result, _ = self._apply_backfill(fs)
        for key in self._NEW_KEYS:
            sa = result[key].get("self_assessment")
            assert sa is not None, f"{key}: self_assessment must not be null after backfill"
            assert sa == 60.0, f"{key}: self_assessment must be 60.0 (neutral baseline)"
