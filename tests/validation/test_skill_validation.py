"""
Test: Skill Selection Validation

Validates that:
1. Configs with NO enabled skills are REJECTED
2. Configs with at least 1 enabled skill are ACCEPTED
3. Templates start with all skills DISABLED by default
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.schemas.reward_config import (
    TournamentRewardConfig,
    SkillMappingConfig,
    PlacementRewardConfig,
    REWARD_CONFIG_TEMPLATES
)

print("=" * 80)
print("🔒 Skill Selection Validation Test")
print("=" * 80)

# ============================================================================
# TEST 1: Config with NO enabled skills should FAIL validation
# ============================================================================
print("\n📝 TEST 1: Config with NO enabled skills...")

config_no_skills = TournamentRewardConfig(
    skill_mappings=[
        SkillMappingConfig(skill="speed", weight=1.0, category="PHYSICAL", enabled=False),
        SkillMappingConfig(skill="agility", weight=1.0, category="PHYSICAL", enabled=False),
    ],
    first_place=PlacementRewardConfig(credits=100, xp_multiplier=1.5),
    template_name="TEST_NO_SKILLS",
    custom_config=True
)

is_valid, error_msg = config_no_skills.validate_enabled_skills()

if not is_valid:
    print(f"   ✅ PASS - Config rejected as expected: {error_msg}")
else:
    print(f"   ❌ FAIL - Config should have been rejected but wasn't!")
    sys.exit(1)

# ============================================================================
# TEST 2: Config with 1 enabled skill should PASS validation
# ============================================================================
print("\n📝 TEST 2: Config with 1 enabled skill...")

config_one_skill = TournamentRewardConfig(
    skill_mappings=[
        SkillMappingConfig(skill="speed", weight=1.0, category="PHYSICAL", enabled=True),  # ✅ enabled
        SkillMappingConfig(skill="agility", weight=1.0, category="PHYSICAL", enabled=False),
    ],
    first_place=PlacementRewardConfig(credits=100, xp_multiplier=1.5),
    template_name="TEST_ONE_SKILL",
    custom_config=True
)

is_valid, error_msg = config_one_skill.validate_enabled_skills()

if is_valid:
    print(f"   ✅ PASS - Config accepted with 1 enabled skill")
else:
    print(f"   ❌ FAIL - Config should have been accepted: {error_msg}")
    sys.exit(1)

# ============================================================================
# TEST 3: Config with multiple enabled skills should PASS validation
# ============================================================================
print("\n📝 TEST 3: Config with multiple enabled skills...")

config_multi_skills = TournamentRewardConfig(
    skill_mappings=[
        SkillMappingConfig(skill="speed", weight=2.0, category="PHYSICAL", enabled=True),
        SkillMappingConfig(skill="agility", weight=1.5, category="PHYSICAL", enabled=True),
        SkillMappingConfig(skill="stamina", weight=1.0, category="PHYSICAL", enabled=False),
    ],
    first_place=PlacementRewardConfig(credits=100, xp_multiplier=1.5),
    template_name="TEST_MULTI_SKILLS",
    custom_config=True
)

is_valid, error_msg = config_multi_skills.validate_enabled_skills()

if is_valid:
    enabled_count = len(config_multi_skills.enabled_skills)
    print(f"   ✅ PASS - Config accepted with {enabled_count} enabled skills")
else:
    print(f"   ❌ FAIL - Config should have been accepted: {error_msg}")
    sys.exit(1)

# ============================================================================
# TEST 4: Verify templates have ALL skills DISABLED by default
# ============================================================================
print("\n📝 TEST 4: Verify templates have all skills disabled by default...")

all_disabled = True

for template_name, template_config in REWARD_CONFIG_TEMPLATES.items():
    enabled_count = len(template_config.enabled_skills)
    total_count = len(template_config.skill_mappings)

    print(f"\n   Template: {template_name}")
    print(f"      Total skills: {total_count}")
    print(f"      Enabled skills: {enabled_count}")

    if enabled_count > 0:
        all_disabled = False
        print(f"      ❌ FAIL - Template should have all skills disabled by default!")
        print(f"      Enabled skills:")
        for skill in template_config.enabled_skills:
            print(f"         - {skill.skill} (weight: {skill.weight})")
    else:
        print(f"      ✅ PASS - All skills disabled by default")

if not all_disabled:
    print("\n❌ TEST 4 FAILED - Some templates have skills enabled by default")
    sys.exit(1)

# ============================================================================
# TEST 5: Verify enabled_skills property works correctly
# ============================================================================
print("\n📝 TEST 5: Verify enabled_skills property...")

test_config = TournamentRewardConfig(
    skill_mappings=[
        SkillMappingConfig(skill="speed", weight=1.0, enabled=True),
        SkillMappingConfig(skill="agility", weight=1.0, enabled=False),
        SkillMappingConfig(skill="stamina", weight=1.0, enabled=True),
        SkillMappingConfig(skill="strength", weight=1.0, enabled=False),
    ],
    first_place=PlacementRewardConfig(credits=100, xp_multiplier=1.5)
)

enabled = test_config.enabled_skills
enabled_names = [skill.skill for skill in enabled]

expected_enabled = ["speed", "stamina"]

if set(enabled_names) == set(expected_enabled):
    print(f"   ✅ PASS - enabled_skills property returns correct skills: {enabled_names}")
else:
    print(f"   ❌ FAIL - enabled_skills property incorrect")
    print(f"      Expected: {expected_enabled}")
    print(f"      Got: {enabled_names}")
    sys.exit(1)

# ============================================================================
# TEST 6: Empty skill_mappings list should FAIL validation
# ============================================================================
print("\n📝 TEST 6: Empty skill_mappings list...")

config_empty = TournamentRewardConfig(
    skill_mappings=[],  # Empty list
    first_place=PlacementRewardConfig(credits=100, xp_multiplier=1.5),
    template_name="TEST_EMPTY",
    custom_config=True
)

is_valid, error_msg = config_empty.validate_enabled_skills()

if not is_valid:
    print(f"   ✅ PASS - Empty skill list rejected: {error_msg}")
else:
    print(f"   ❌ FAIL - Empty skill list should be rejected")
    sys.exit(1)

# ============================================================================
# Final Summary
# ============================================================================
print("\n" + "=" * 80)
print("📊 Validation Test Summary")
print("=" * 80)
print("✅ TEST 1: Config with NO enabled skills - REJECTED ✅")
print("✅ TEST 2: Config with 1 enabled skill - ACCEPTED ✅")
print("✅ TEST 3: Config with multiple enabled skills - ACCEPTED ✅")
print("✅ TEST 4: Templates have all skills DISABLED by default ✅")
print("✅ TEST 5: enabled_skills property works correctly ✅")
print("✅ TEST 6: Empty skill_mappings list - REJECTED ✅")
print("\n🎉 All validation tests PASSED!")
print("=" * 80)
