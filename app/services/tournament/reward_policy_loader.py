"""
Reward Policy Loader Service

Handles loading, validation, and management of tournament reward policies from JSON configuration files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class RewardPolicyError(Exception):
    """Exception raised for errors in reward policy loading or validation."""
    pass


def get_policies_directory() -> Path:
    """Get the path to the reward policies directory."""
    # Get the project root (where config/ directory is located)
    project_root = Path(__file__).parent.parent.parent.parent
    policies_dir = project_root / "config" / "reward_policies"

    if not policies_dir.exists():
        raise RewardPolicyError(f"Reward policies directory not found: {policies_dir}")

    return policies_dir


def load_policy(policy_name: str) -> Dict:
    """
    Load a reward policy by name from the config/reward_policies directory.

    Args:
        policy_name: Name of the policy file (without .json extension)

    Returns:
        Dictionary containing the policy configuration

    Raises:
        RewardPolicyError: If policy file not found or invalid JSON
    """
    policies_dir = get_policies_directory()
    policy_path = policies_dir / f"{policy_name}.json"

    if not policy_path.exists():
        raise RewardPolicyError(f"Policy file not found: {policy_name}.json")

    try:
        with open(policy_path, 'r', encoding='utf-8') as f:
            policy_data = json.load(f)
    except json.JSONDecodeError as e:
        raise RewardPolicyError(f"Invalid JSON in policy file {policy_name}.json: {e}")
    except Exception as e:
        raise RewardPolicyError(f"Error reading policy file {policy_name}.json: {e}")

    # Validate the policy structure
    if not validate_policy(policy_data):
        raise RewardPolicyError(f"Policy validation failed for {policy_name}.json")

    return policy_data


def validate_policy(policy_dict: Dict) -> bool:
    """
    Validate the structure and content of a reward policy.

    Args:
        policy_dict: Dictionary containing the policy data

    Returns:
        True if valid, raises RewardPolicyError if invalid

    Raises:
        RewardPolicyError: If policy structure is invalid
    """
    # Required top-level fields
    required_fields = ["policy_name", "version", "placement_rewards", "participation_rewards"]
    for field in required_fields:
        if field not in policy_dict:
            raise RewardPolicyError(f"Missing required field: {field}")

    # Validate placement_rewards structure
    placement_rewards = policy_dict.get("placement_rewards", {})
    required_placements = ["1ST", "2ND", "3RD", "PARTICIPANT"]
    for placement in required_placements:
        if placement not in placement_rewards:
            raise RewardPolicyError(f"Missing placement reward: {placement}")

        reward = placement_rewards[placement]
        if "xp" not in reward or "credits" not in reward:
            raise RewardPolicyError(f"Placement {placement} must have 'xp' and 'credits' fields")

        # Validate numeric values
        if not isinstance(reward["xp"], (int, float)) or reward["xp"] < 0:
            raise RewardPolicyError(f"Invalid XP value for {placement}: {reward['xp']}")
        if not isinstance(reward["credits"], (int, float)) or reward["credits"] < 0:
            raise RewardPolicyError(f"Invalid credits value for {placement}: {reward['credits']}")

    # Validate participation_rewards structure
    participation_rewards = policy_dict.get("participation_rewards", {})
    if "session_attendance" not in participation_rewards:
        raise RewardPolicyError("Missing participation reward: session_attendance")

    session_reward = participation_rewards["session_attendance"]
    if "xp" not in session_reward or "credits" not in session_reward:
        raise RewardPolicyError("session_attendance must have 'xp' and 'credits' fields")

    if not isinstance(session_reward["xp"], (int, float)) or session_reward["xp"] < 0:
        raise RewardPolicyError(f"Invalid XP value for session_attendance: {session_reward['xp']}")
    if not isinstance(session_reward["credits"], (int, float)) or session_reward["credits"] < 0:
        raise RewardPolicyError(f"Invalid credits value for session_attendance: {session_reward['credits']}")

    # Validate specializations if present
    if "specializations" in policy_dict:
        valid_specializations = ["LFA_FOOTBALL_PLAYER", "LFA_COACH", "INTERNSHIP", "GANCUJU_PLAYER"]
        policy_specializations = policy_dict["specializations"]

        if not isinstance(policy_specializations, list):
            raise RewardPolicyError("specializations must be a list")

        for spec in policy_specializations:
            if spec not in valid_specializations:
                raise RewardPolicyError(f"Invalid specialization: {spec}")

    return True


def get_available_policies() -> List[str]:
    """
    Get list of available policy names in the config/reward_policies directory.

    Returns:
        List of policy names (without .json extension)
    """
    policies_dir = get_policies_directory()

    policy_files = list(policies_dir.glob("*.json"))
    policy_names = [f.stem for f in policy_files]

    return sorted(policy_names)


def get_default_policy() -> Dict:
    """
    Load the default reward policy.

    Returns:
        Dictionary containing the default policy configuration

    Raises:
        RewardPolicyError: If default policy not found or invalid
    """
    return load_policy("default")


def get_policy_info(policy_name: str) -> Dict:
    """
    Get metadata about a policy without loading the full policy.

    Args:
        policy_name: Name of the policy

    Returns:
        Dictionary with policy metadata (name, version, description)
    """
    policy = load_policy(policy_name)

    return {
        "policy_name": policy.get("policy_name"),
        "version": policy.get("version"),
        "description": policy.get("description", ""),
        "applies_to_all_tournament_types": policy.get("applies_to_all_tournament_types", True)
    }
