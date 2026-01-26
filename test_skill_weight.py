"""
Test Skill Weight Multiplier Functionality

Validates that skill weight multiplier correctly amplifies or reduces skill deltas.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import skill_progression_service

print("=" * 80)
print("🧪 SKILL WEIGHT MULTIPLIER TEST")
print("=" * 80)

# Test parameters
baseline = 70.0
placement_first = 1
placement_last = 10
total_players = 10
tournament_count = 1

print(f"\n📊 Test Setup:")
print(f"  Baseline: {baseline:.1f}")
print(f"  Total Players: {total_players}")
print(f"  Tournament Count: {tournament_count}")

print("\n" + "=" * 80)
print("TEST 1: Weight = 1.0 (Default/Normal Reactivity)")
print("=" * 80)

# Test weight = 1.0 (normal)
result_first_normal = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_first,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=1.0
)

result_last_normal = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_last,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=1.0
)

delta_first_normal = result_first_normal - baseline
delta_last_normal = result_last_normal - baseline

print(f"\n1st Place (weight=1.0):")
print(f"  Result: {result_first_normal:.1f}")
print(f"  Delta: {delta_first_normal:+.1f}")

print(f"\nLast Place (weight=1.0):")
print(f"  Result: {result_last_normal:.1f}")
print(f"  Delta: {delta_last_normal:+.1f}")

print("\n" + "=" * 80)
print("TEST 2: Weight = 2.0 (Double Reactivity)")
print("=" * 80)

# Test weight = 2.0 (double)
result_first_double = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_first,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=2.0
)

result_last_double = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_last,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=2.0
)

delta_first_double = result_first_double - baseline
delta_last_double = result_last_double - baseline

print(f"\n1st Place (weight=2.0):")
print(f"  Result: {result_first_double:.1f}")
print(f"  Delta: {delta_first_double:+.1f} (expected: {delta_first_normal * 2:+.1f})")
print(f"  ✅ PASS" if abs(delta_first_double - delta_first_normal * 2) < 0.1 else "  ❌ FAIL")

print(f"\nLast Place (weight=2.0):")
print(f"  Result: {result_last_double:.1f}")
print(f"  Delta: {delta_last_double:+.1f} (expected: {delta_last_normal * 2:+.1f})")
print(f"  ✅ PASS" if abs(delta_last_double - delta_last_normal * 2) < 0.1 else "  ❌ FAIL")

print("\n" + "=" * 80)
print("TEST 3: Weight = 0.5 (Half Reactivity)")
print("=" * 80)

# Test weight = 0.5 (half)
result_first_half = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_first,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=0.5
)

result_last_half = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_last,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=0.5
)

delta_first_half = result_first_half - baseline
delta_last_half = result_last_half - baseline

print(f"\n1st Place (weight=0.5):")
print(f"  Result: {result_first_half:.1f}")
print(f"  Delta: {delta_first_half:+.1f} (expected: {delta_first_normal * 0.5:+.1f})")
print(f"  ✅ PASS" if abs(delta_first_half - delta_first_normal * 0.5) < 0.1 else "  ❌ FAIL")

print(f"\nLast Place (weight=0.5):")
print(f"  Result: {result_last_half:.1f}")
print(f"  Delta: {delta_last_half:+.1f} (expected: {delta_last_normal * 0.5:+.1f})")
print(f"  ✅ PASS" if abs(delta_last_half - delta_last_normal * 0.5) < 0.1 else "  ❌ FAIL")

print("\n" + "=" * 80)
print("TEST 4: Weight = 1.5 (50% Bonus Reactivity)")
print("=" * 80)

# Test weight = 1.5
result_first_bonus = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_first,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=1.5
)

result_last_bonus = skill_progression_service.calculate_skill_value_from_placement(
    baseline=baseline,
    placement=placement_last,
    total_players=total_players,
    tournament_count=tournament_count,
    skill_weight=1.5
)

delta_first_bonus = result_first_bonus - baseline
delta_last_bonus = result_last_bonus - baseline

print(f"\n1st Place (weight=1.5):")
print(f"  Result: {result_first_bonus:.1f}")
print(f"  Delta: {delta_first_bonus:+.1f} (expected: {delta_first_normal * 1.5:+.1f})")
print(f"  ✅ PASS" if abs(delta_first_bonus - delta_first_normal * 1.5) < 0.1 else "  ❌ FAIL")

print(f"\nLast Place (weight=1.5):")
print(f"  Result: {result_last_bonus:.1f}")
print(f"  Delta: {delta_last_bonus:+.1f} (expected: {delta_last_normal * 1.5:+.1f})")
print(f"  ✅ PASS" if abs(delta_last_bonus - delta_last_normal * 1.5) < 0.1 else "  ❌ FAIL")

print("\n" + "=" * 80)
print("📊 SUMMARY TABLE")
print("=" * 80)

print("\n1st Place Results:")
print(f"{'Weight':<10} {'Result':<10} {'Delta':<10} {'Multiplier':<12}")
print("-" * 42)
print(f"{'1.0':<10} {result_first_normal:<10.1f} {delta_first_normal:<+10.1f} {'(baseline)':<12}")
print(f"{'0.5':<10} {result_first_half:<10.1f} {delta_first_half:<+10.1f} {'(0.5x)':<12}")
print(f"{'1.5':<10} {result_first_bonus:<10.1f} {delta_first_bonus:<+10.1f} {'(1.5x)':<12}")
print(f"{'2.0':<10} {result_first_double:<10.1f} {delta_first_double:<+10.1f} {'(2.0x)':<12}")

print("\nLast Place Results:")
print(f"{'Weight':<10} {'Result':<10} {'Delta':<10} {'Multiplier':<12}")
print("-" * 42)
print(f"{'1.0':<10} {result_last_normal:<10.1f} {delta_last_normal:<+10.1f} {'(baseline)':<12}")
print(f"{'0.5':<10} {result_last_half:<10.1f} {delta_last_half:<+10.1f} {'(0.5x)':<12}")
print(f"{'1.5':<10} {result_last_bonus:<10.1f} {delta_last_bonus:<+10.1f} {'(1.5x)':<12}")
print(f"{'2.0':<10} {result_last_double:<10.1f} {delta_last_double:<+10.1f} {'(2.0x)':<12}")

print("\n" + "=" * 80)
print("✅ All tests completed!")
print("=" * 80)
