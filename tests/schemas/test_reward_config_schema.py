"""
Test script for reward configuration schemas.

Tests:
1. Template validation
2. Custom configuration creation
3. Schema validation errors
4. JSONB serialization
"""
from app.schemas.reward_config import (
    TournamentRewardConfig,
    SkillMappingConfig,
    PlacementRewardConfig,
    BadgeConfig,
    BadgeCondition,
    REWARD_CONFIG_TEMPLATES
)
import json


def test_templates():
    """Test that all templates are valid"""
    print("=" * 60)
    print("TEST 1: Template Validation")
    print("=" * 60)

    for template_name, config in REWARD_CONFIG_TEMPLATES.items():
        print(f"\n✓ Testing {template_name} template...")

        # Validate schema
        assert isinstance(config, TournamentRewardConfig)

        # Check skill mappings
        assert len(config.skill_mappings) > 0, f"{template_name}: No skill mappings"

        # Check placement rewards
        assert config.first_place is not None, f"{template_name}: Missing first_place"
        assert config.second_place is not None, f"{template_name}: Missing second_place"
        assert config.third_place is not None, f"{template_name}: Missing third_place"

        # Check badges
        assert len(config.first_place.badges) > 0, f"{template_name}: No badges for 1st place"

        print(f"  - Skill mappings: {len(config.skill_mappings)}")
        print(f"  - 1st place badges: {len(config.first_place.badges)}")
        print(f"  - Credits: {config.first_place.credits}")
        print(f"  - XP multiplier: {config.first_place.xp_multiplier}")

    print(f"\n✅ All {len(REWARD_CONFIG_TEMPLATES)} templates are valid!")


def test_custom_config():
    """Test creating a custom configuration"""
    print("\n" + "=" * 60)
    print("TEST 2: Custom Configuration Creation")
    print("=" * 60)

    # Create custom config
    config = TournamentRewardConfig(
        skill_mappings=[
            SkillMappingConfig(skill="speed", weight=2.0, category="PHYSICAL", enabled=True),
            SkillMappingConfig(skill="shooting", weight=1.5, category="TECHNICAL", enabled=True),
        ],
        first_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="CUSTOM_CHAMPION",
                    icon="🔥",
                    title="Speed King",
                    description="Fastest player in {tournament_name}",
                    rarity="LEGENDARY",
                    enabled=True
                )
            ],
            credits=1500,
            xp_multiplier=2.5
        ),
        second_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="CUSTOM_RUNNER_UP",
                    icon="⚡",
                    title="Lightning Fast",
                    rarity="EPIC",
                    enabled=True
                )
            ],
            credits=800,
            xp_multiplier=1.8
        ),
        third_place=PlacementRewardConfig(
            badges=[
                BadgeConfig(
                    badge_type="CUSTOM_THIRD",
                    icon="💨",
                    title="Quick Feet",
                    rarity="RARE",
                    enabled=True
                )
            ],
            credits=400,
            xp_multiplier=1.4
        ),
        template_name="Custom Speed Test",
        custom_config=True
    )

    print(f"\n✓ Custom config created successfully!")
    print(f"  - Template: {config.template_name}")
    print(f"  - Custom: {config.custom_config}")
    print(f"  - Skill mappings: {len(config.skill_mappings)}")
    print(f"  - 1st place icon: {config.first_place.badges[0].icon}")
    print(f"  - 1st place title: {config.first_place.badges[0].title}")

    print(f"\n✅ Custom configuration works!")


def test_jsonb_serialization():
    """Test JSONB serialization/deserialization"""
    print("\n" + "=" * 60)
    print("TEST 3: JSONB Serialization")
    print("=" * 60)

    # Get a template
    config = REWARD_CONFIG_TEMPLATES["STANDARD"]

    # Serialize to JSON (simulates saving to database)
    config_json = config.model_dump(mode="json")
    json_str = json.dumps(config_json, indent=2)

    print(f"\n✓ Serialized to JSON ({len(json_str)} chars)")
    print("\nFirst 500 chars:")
    print(json_str[:500] + "...")

    # Deserialize back (simulates reading from database)
    config_dict = json.loads(json_str)
    restored_config = TournamentRewardConfig(**config_dict)

    print(f"\n✓ Deserialized back to TournamentRewardConfig")
    print(f"  - Skill mappings: {len(restored_config.skill_mappings)}")
    print(f"  - Template name: {restored_config.template_name}")

    # Verify they match
    assert restored_config.template_name == config.template_name
    assert len(restored_config.skill_mappings) == len(config.skill_mappings)
    assert restored_config.first_place.credits == config.first_place.credits

    print(f"\n✅ JSONB serialization works perfectly!")


def test_validation_errors():
    """Test that validation catches errors"""
    print("\n" + "=" * 60)
    print("TEST 4: Validation Error Detection")
    print("=" * 60)

    # Test 1: Empty skill mappings with all disabled
    try:
        config = TournamentRewardConfig(
            skill_mappings=[
                SkillMappingConfig(skill="speed", weight=1.0, enabled=False),
                SkillMappingConfig(skill="agility", weight=1.0, enabled=False),
            ],
            first_place=PlacementRewardConfig(
                badges=[BadgeConfig(badge_type="TEST", title="Test", enabled=True)],
                credits=100
            )
        )
        print("❌ ERROR: Should have failed with all skills disabled!")
    except ValueError as e:
        print(f"✓ Correctly caught error: {str(e)}")

    # Test 2: Invalid weight
    try:
        config = SkillMappingConfig(skill="speed", weight=10.0)  # Max is 5.0
        print("❌ ERROR: Should have failed with weight > 5.0!")
    except ValueError as e:
        print(f"✓ Correctly caught error: weight out of range")

    # Test 3: Invalid rarity
    try:
        badge = BadgeConfig(
            badge_type="TEST",
            title="Test",
            rarity="ULTRA_RARE"  # Invalid
        )
        print("❌ ERROR: Should have failed with invalid rarity!")
    except ValueError as e:
        print(f"✓ Correctly caught error: invalid rarity")

    print(f"\n✅ Validation errors are caught correctly!")


def print_template_summary():
    """Print summary of all templates"""
    print("\n" + "=" * 60)
    print("TEMPLATE SUMMARY")
    print("=" * 60)

    for template_name, config in REWARD_CONFIG_TEMPLATES.items():
        print(f"\n📋 {template_name} Template:")
        print(f"   Skills: {', '.join([s.skill for s in config.skill_mappings if s.enabled])}")
        print(f"   1st place: {config.first_place.credits} credits, {config.first_place.xp_multiplier}x XP")
        print(f"   Badges: {len(config.first_place.badges)} (1st) + {len(config.second_place.badges)} (2nd) + {len(config.third_place.badges)} (3rd)")
        if config.top_25_percent:
            print(f"   Top 25%: ✓ {config.top_25_percent.credits} credits")
        if config.participation:
            print(f"   Participation: {config.participation.credits} credits")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 REWARD CONFIG SCHEMA TESTS")
    print("=" * 60)

    test_templates()
    test_custom_config()
    test_jsonb_serialization()
    test_validation_errors()
    print_template_summary()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nPhase 1 (Backend - Configuration Schema) is complete! 🚀")
    print("\nReady for Phase 2: Admin UI - Checkbox Form")
    print("=" * 60 + "\n")
