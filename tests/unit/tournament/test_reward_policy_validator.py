"""
Tests for tournament/reward_policy_loader.py

Missing coverage targets:
  Line 23:  get_policies_directory — dir not found → RewardPolicyError
  Lines 50-51: load_policy — JSONDecodeError
  Lines 52-53: load_policy — generic Exception on open
  Line 101:  validate_policy — missing session_attendance key
  Lines 104-105: validate_policy — session_attendance missing xp/credits
  Line 107-108: validate_policy — session_attendance XP < 0
  Lines 109-110: validate_policy — session_attendance credits < 0
  Lines 113-118: validate_policy — specializations not a list
  Lines 120-122: validate_policy — invalid specialization name
"""
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from app.services.tournament.reward_policy_loader import (
    get_policies_directory,
    load_policy,
    validate_policy,
    RewardPolicyError,
)


# ──────────────────── helpers ────────────────────


def _valid_policy():
    """Minimal policy dict that passes all validate_policy checks."""
    return {
        "policy_name": "test",
        "version": "1.0",
        "placement_rewards": {
            "1ST": {"xp": 100, "credits": 50},
            "2ND": {"xp": 75, "credits": 35},
            "3RD": {"xp": 50, "credits": 25},
            "PARTICIPANT": {"xp": 20, "credits": 10},
        },
        "participation_rewards": {
            "session_attendance": {"xp": 5, "credits": 2}
        },
    }


# ──────────────────── get_policies_directory ────────────────────


class TestGetPoliciesDirectory:

    def test_directory_not_found_raises(self):
        """Line 23: policies dir doesn't exist → RewardPolicyError."""
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(RewardPolicyError, match="not found"):
                get_policies_directory()

    def test_directory_found_returns_path(self):
        """Happy path: dir exists → returns a Path object."""
        with patch.object(Path, "exists", return_value=True):
            result = get_policies_directory()
        assert isinstance(result, Path)


# ──────────────────── load_policy ────────────────────


class TestLoadPolicy:

    def _patch_dir(self, mock_policy_path):
        """Patch get_policies_directory to return a dir whose / op returns mock_policy_path."""
        mock_dir = MagicMock(spec=Path)
        mock_dir.__truediv__ = lambda self, other: mock_policy_path
        return patch(
            "app.services.tournament.reward_policy_loader.get_policies_directory",
            return_value=mock_dir,
        )

    def test_policy_file_not_found(self):
        """Line 45: file missing → RewardPolicyError."""
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False

        with self._patch_dir(mock_path):
            with pytest.raises(RewardPolicyError, match="Policy file not found"):
                load_policy("missing_policy")

    def test_json_decode_error(self):
        """Lines 50-51: malformed JSON → RewardPolicyError with 'Invalid JSON'."""
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True

        with self._patch_dir(mock_path):
            with patch("builtins.open", mock_open(read_data="{bad json:")):
                with pytest.raises(RewardPolicyError, match="Invalid JSON"):
                    load_policy("bad_policy")

    def test_generic_exception_on_open(self):
        """Lines 52-53: IOError on open → RewardPolicyError with 'Error reading'."""
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True

        with self._patch_dir(mock_path):
            with patch("builtins.open", side_effect=IOError("disk failure")):
                with pytest.raises(RewardPolicyError, match="Error reading policy file"):
                    load_policy("broken_policy")


# ──────────────────── validate_policy ────────────────────


class TestValidatePolicy:

    def test_valid_policy_returns_true(self):
        assert validate_policy(_valid_policy()) is True

    # ── required top-level fields ──

    def test_missing_policy_name(self):
        p = _valid_policy()
        del p["policy_name"]
        with pytest.raises(RewardPolicyError, match="Missing required field: policy_name"):
            validate_policy(p)

    def test_missing_version(self):
        p = _valid_policy()
        del p["version"]
        with pytest.raises(RewardPolicyError, match="Missing required field: version"):
            validate_policy(p)

    def test_missing_placement_rewards(self):
        p = _valid_policy()
        del p["placement_rewards"]
        with pytest.raises(RewardPolicyError, match="Missing required field"):
            validate_policy(p)

    # ── placement_rewards validation ──

    def test_missing_placement_3rd(self):
        p = _valid_policy()
        del p["placement_rewards"]["3RD"]
        with pytest.raises(RewardPolicyError, match="Missing placement reward: 3RD"):
            validate_policy(p)

    def test_placement_missing_xp_field(self):
        p = _valid_policy()
        del p["placement_rewards"]["1ST"]["xp"]
        with pytest.raises(RewardPolicyError, match="must have 'xp' and 'credits'"):
            validate_policy(p)

    def test_placement_missing_credits_field(self):
        p = _valid_policy()
        del p["placement_rewards"]["2ND"]["credits"]
        with pytest.raises(RewardPolicyError, match="must have 'xp' and 'credits'"):
            validate_policy(p)

    def test_placement_xp_negative(self):
        p = _valid_policy()
        p["placement_rewards"]["1ST"]["xp"] = -1
        with pytest.raises(RewardPolicyError, match="Invalid XP value for 1ST"):
            validate_policy(p)

    def test_placement_credits_negative(self):
        p = _valid_policy()
        p["placement_rewards"]["1ST"]["credits"] = -5
        with pytest.raises(RewardPolicyError, match="Invalid credits value for 1ST"):
            validate_policy(p)

    # ── participation_rewards / session_attendance ──

    def test_missing_session_attendance_key(self):
        """Line 101: session_attendance not present → RewardPolicyError."""
        p = _valid_policy()
        del p["participation_rewards"]["session_attendance"]
        with pytest.raises(RewardPolicyError, match="Missing participation reward: session_attendance"):
            validate_policy(p)

    def test_session_attendance_missing_xp(self):
        """Lines 104-105: session_attendance has no 'xp' key."""
        p = _valid_policy()
        del p["participation_rewards"]["session_attendance"]["xp"]
        with pytest.raises(RewardPolicyError, match="session_attendance must have"):
            validate_policy(p)

    def test_session_attendance_missing_credits(self):
        """Lines 104-105: session_attendance has no 'credits' key."""
        p = _valid_policy()
        del p["participation_rewards"]["session_attendance"]["credits"]
        with pytest.raises(RewardPolicyError, match="session_attendance must have"):
            validate_policy(p)

    def test_session_attendance_xp_negative(self):
        """Lines 107-108: session_attendance XP < 0."""
        p = _valid_policy()
        p["participation_rewards"]["session_attendance"]["xp"] = -3
        with pytest.raises(RewardPolicyError, match="Invalid XP value for session_attendance"):
            validate_policy(p)

    def test_session_attendance_credits_negative(self):
        """Lines 109-110: session_attendance credits < 0."""
        p = _valid_policy()
        p["participation_rewards"]["session_attendance"]["credits"] = -1
        with pytest.raises(RewardPolicyError, match="Invalid credits value for session_attendance"):
            validate_policy(p)

    # ── specializations ──

    def test_specializations_not_a_list(self):
        """Line 118: specializations is a string, not list → RewardPolicyError."""
        p = _valid_policy()
        p["specializations"] = "LFA_FOOTBALL_PLAYER"
        with pytest.raises(RewardPolicyError, match="specializations must be a list"):
            validate_policy(p)

    def test_specializations_dict_not_list(self):
        """Line 118: specializations is a dict → RewardPolicyError."""
        p = _valid_policy()
        p["specializations"] = {"type": "LFA_FOOTBALL_PLAYER"}
        with pytest.raises(RewardPolicyError, match="specializations must be a list"):
            validate_policy(p)

    def test_specializations_invalid_name(self):
        """Lines 120-122: unknown specialization name → RewardPolicyError."""
        p = _valid_policy()
        p["specializations"] = ["INVALID_SPEC_TYPE"]
        with pytest.raises(RewardPolicyError, match="Invalid specialization: INVALID_SPEC_TYPE"):
            validate_policy(p)

    def test_specializations_valid_list(self):
        """Lines 113-124: valid specializations → returns True."""
        p = _valid_policy()
        p["specializations"] = ["LFA_FOOTBALL_PLAYER", "GANCUJU_PLAYER"]
        assert validate_policy(p) is True

    def test_no_specializations_key_passes(self):
        """No 'specializations' key → block skipped → True."""
        p = _valid_policy()
        # specializations key not present → block at line 113 never entered
        assert "specializations" not in p
        assert validate_policy(p) is True
