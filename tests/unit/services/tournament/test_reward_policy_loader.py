"""
Unit tests for reward policy loader service
"""
import pytest
import json
from pathlib import Path

from app.services.tournament.reward_policy_loader import (
    load_policy,
    validate_policy,
    get_available_policies,
    get_default_policy,
    get_policy_info,
    RewardPolicyError,
    get_policies_directory
)


class TestRewardPolicyLoader:
    """Test reward policy loading and validation"""

    def test_get_policies_directory(self):
        """Get policies directory returns valid path"""
        policies_dir = get_policies_directory()

        assert policies_dir.exists()
        assert policies_dir.is_dir()
        assert policies_dir.name == "reward_policies"

    def test_load_default_policy(self):
        """Load default policy successfully"""
        policy = load_policy("default")

        assert policy is not None
        assert policy["policy_name"] == "default"
        assert policy["version"] == "1.0.0"
        assert "placement_rewards" in policy
        assert "participation_rewards" in policy

    def test_load_nonexistent_policy(self):
        """Loading nonexistent policy raises error"""
        with pytest.raises(RewardPolicyError, match="Policy file not found"):
            load_policy("nonexistent_policy")

    def test_validate_default_policy(self):
        """Default policy passes validation"""
        policy = load_policy("default")
        assert validate_policy(policy) is True

    def test_validate_policy_missing_required_field(self):
        """Validation fails when required field is missing"""
        invalid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            # Missing placement_rewards and participation_rewards
        }

        with pytest.raises(RewardPolicyError, match="Missing required field"):
            validate_policy(invalid_policy)

    def test_validate_policy_missing_placement_reward(self):
        """Validation fails when required placement reward is missing"""
        invalid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            "placement_rewards": {
                "1ST": {"xp": 500, "credits": 100},
                "2ND": {"xp": 300, "credits": 50},
                # Missing 3RD and PARTICIPANT
            },
            "participation_rewards": {
                "session_attendance": {"xp": 10, "credits": 0}
            }
        }

        with pytest.raises(RewardPolicyError, match="Missing placement reward"):
            validate_policy(invalid_policy)

    def test_validate_policy_invalid_xp_value(self):
        """Validation fails when XP value is invalid"""
        invalid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            "placement_rewards": {
                "1ST": {"xp": -100, "credits": 100},  # Negative XP
                "2ND": {"xp": 300, "credits": 50},
                "3RD": {"xp": 200, "credits": 25},
                "PARTICIPANT": {"xp": 50, "credits": 0}
            },
            "participation_rewards": {
                "session_attendance": {"xp": 10, "credits": 0}
            }
        }

        with pytest.raises(RewardPolicyError, match="Invalid XP value"):
            validate_policy(invalid_policy)

    def test_validate_policy_invalid_credits_value(self):
        """Validation fails when credits value is invalid"""
        invalid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            "placement_rewards": {
                "1ST": {"xp": 500, "credits": -50},  # Negative credits
                "2ND": {"xp": 300, "credits": 50},
                "3RD": {"xp": 200, "credits": 25},
                "PARTICIPANT": {"xp": 50, "credits": 0}
            },
            "participation_rewards": {
                "session_attendance": {"xp": 10, "credits": 0}
            }
        }

        with pytest.raises(RewardPolicyError, match="Invalid credits value"):
            validate_policy(invalid_policy)

    def test_validate_policy_missing_xp_field(self):
        """Validation fails when placement reward missing xp field"""
        invalid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            "placement_rewards": {
                "1ST": {"credits": 100},  # Missing xp
                "2ND": {"xp": 300, "credits": 50},
                "3RD": {"xp": 200, "credits": 25},
                "PARTICIPANT": {"xp": 50, "credits": 0}
            },
            "participation_rewards": {
                "session_attendance": {"xp": 10, "credits": 0}
            }
        }

        with pytest.raises(RewardPolicyError, match="must have 'xp' and 'credits' fields"):
            validate_policy(invalid_policy)

    def test_validate_policy_missing_session_attendance(self):
        """Validation fails when session_attendance is missing"""
        invalid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            "placement_rewards": {
                "1ST": {"xp": 500, "credits": 100},
                "2ND": {"xp": 300, "credits": 50},
                "3RD": {"xp": 200, "credits": 25},
                "PARTICIPANT": {"xp": 50, "credits": 0}
            },
            "participation_rewards": {}  # Missing session_attendance
        }

        with pytest.raises(RewardPolicyError, match="Missing participation reward: session_attendance"):
            validate_policy(invalid_policy)

    def test_validate_policy_invalid_specialization(self):
        """Validation fails when invalid specialization is provided"""
        invalid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            "placement_rewards": {
                "1ST": {"xp": 500, "credits": 100},
                "2ND": {"xp": 300, "credits": 50},
                "3RD": {"xp": 200, "credits": 25},
                "PARTICIPANT": {"xp": 50, "credits": 0}
            },
            "participation_rewards": {
                "session_attendance": {"xp": 10, "credits": 0}
            },
            "specializations": ["LFA_FOOTBALL_PLAYER", "INVALID_SPEC"]  # Invalid specialization
        }

        with pytest.raises(RewardPolicyError, match="Invalid specialization"):
            validate_policy(invalid_policy)

    def test_validate_policy_valid_specializations(self):
        """Validation succeeds with valid specializations"""
        valid_policy = {
            "policy_name": "test",
            "version": "1.0.0",
            "placement_rewards": {
                "1ST": {"xp": 500, "credits": 100},
                "2ND": {"xp": 300, "credits": 50},
                "3RD": {"xp": 200, "credits": 25},
                "PARTICIPANT": {"xp": 50, "credits": 0}
            },
            "participation_rewards": {
                "session_attendance": {"xp": 10, "credits": 0}
            },
            "specializations": ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"]
        }

        assert validate_policy(valid_policy) is True

    def test_get_available_policies(self):
        """Get list of available policies"""
        policies = get_available_policies()

        assert isinstance(policies, list)
        assert "default" in policies
        assert len(policies) >= 1

    def test_get_default_policy(self):
        """Get default policy directly"""
        policy = get_default_policy()

        assert policy["policy_name"] == "default"
        assert policy["version"] == "1.0.0"

    def test_get_policy_info(self):
        """Get policy metadata"""
        info = get_policy_info("default")

        assert info["policy_name"] == "default"
        assert info["version"] == "1.0.0"
        assert "description" in info
        assert info["applies_to_all_tournament_types"] is True

    def test_default_policy_exact_values(self):
        """Verify default policy has exact user-specified values"""
        policy = load_policy("default")

        # Placement rewards
        assert policy["placement_rewards"]["1ST"]["xp"] == 500
        assert policy["placement_rewards"]["1ST"]["credits"] == 100

        assert policy["placement_rewards"]["2ND"]["xp"] == 300
        assert policy["placement_rewards"]["2ND"]["credits"] == 50

        assert policy["placement_rewards"]["3RD"]["xp"] == 200
        assert policy["placement_rewards"]["3RD"]["credits"] == 25

        assert policy["placement_rewards"]["PARTICIPANT"]["xp"] == 50
        assert policy["placement_rewards"]["PARTICIPANT"]["credits"] == 0

        # Participation rewards
        assert policy["participation_rewards"]["session_attendance"]["xp"] == 10
        assert policy["participation_rewards"]["session_attendance"]["credits"] == 0

    def test_default_policy_specializations(self):
        """Verify default policy has all 4 specializations"""
        policy = load_policy("default")

        specializations = policy["specializations"]
        assert len(specializations) == 4
        assert "LFA_FOOTBALL_PLAYER" in specializations
        assert "LFA_COACH" in specializations
        assert "INTERNSHIP" in specializations
        assert "GANCUJU_PLAYER" in specializations

        # Verify NO invalid specializations
        assert "LFA_PLAYER_YOUTH" not in specializations
        assert "LFA_PLAYER_PRO" not in specializations
