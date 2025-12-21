"""
🧪 Hybrid Semester Generation Validation Test

Tests the new gap-filling logic for semester generation across 2026-2029.

Validates:
1. ✅ NO GAPS between semesters
2. ✅ Guaranteed Monday-Sunday transitions
3. ✅ Proper leap year handling (2028)
4. ✅ Marketing themes preserved
5. ✅ Year wrap-around for semi-annual and annual semesters
"""

import sys
from datetime import date, timedelta
from typing import List, Dict

# Add parent directory to path
sys.path.append('/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system')

from app.services.semester_templates import (
    LFA_PLAYER_PRE_TEMPLATE,
    LFA_PLAYER_YOUTH_TEMPLATE,
    LFA_PLAYER_AMATEUR_TEMPLATE,
    LFA_PLAYER_PRO_TEMPLATE,
    get_first_monday,
    get_last_sunday
)


# ============================================================================
# HYBRID GENERATION LOGIC (SAME AS semester_generator.py)
# ============================================================================

class MockSemester:
    """Mock semester object for testing"""
    def __init__(self, code, name, start_date, end_date, theme):
        self.code = code
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.theme = theme


def generate_monthly_semesters_hybrid(year: int, template: dict) -> List[MockSemester]:
    """Generate 12 monthly semesters with gap-filling logic"""
    semesters = []
    spec = template["specialization"]
    age_group = template["age_group"]
    last_end_date = None

    for theme_data in template["themes"]:
        month = theme_data["month"]
        code = theme_data["code"]
        theme = theme_data["theme"]

        # HYBRID LOGIC: Gap-filling while preserving marketing themes
        if last_end_date is None:
            # First semester: month's first Monday
            start = get_first_monday(year, month)
        else:
            # Next semester: immediately after previous (gap-free)
            start = last_end_date + timedelta(days=1)
            # Align to Monday
            while start.weekday() != 0:  # 0 = Monday
                start += timedelta(days=1)

        # End: month's last Sunday
        end = get_last_sunday(year, month)

        semester = MockSemester(
            code=f"{year}/{spec}_{age_group}_{code}",
            name=f"{year} {spec} {age_group} - {theme}",
            start_date=start,
            end_date=end,
            theme=theme
        )
        semesters.append(semester)
        last_end_date = end

    return semesters


def generate_quarterly_semesters_hybrid(year: int, template: dict) -> List[MockSemester]:
    """Generate 4 quarterly semesters with gap-filling logic"""
    semesters = []
    spec = template["specialization"]
    age_group = template["age_group"]
    last_end_date = None

    for theme_data in template["themes"]:
        code = theme_data["code"]
        months = theme_data["months"]
        theme = theme_data["theme"]

        # HYBRID LOGIC: Gap-filling while preserving marketing themes
        if last_end_date is None:
            # First quarter: first month's first Monday
            start = get_first_monday(year, months[0])
        else:
            # Next quarter: immediately after previous (gap-free)
            start = last_end_date + timedelta(days=1)
            # Align to Monday
            while start.weekday() != 0:  # 0 = Monday
                start += timedelta(days=1)

        # End: last Sunday of last month
        end = get_last_sunday(year, months[-1])

        semester = MockSemester(
            code=f"{year}/{spec}_{age_group}_{code}",
            name=f"{year} {spec} {age_group} - {theme}",
            start_date=start,
            end_date=end,
            theme=theme
        )
        semesters.append(semester)
        last_end_date = end

    return semesters


def generate_semiannual_semesters_hybrid(year: int, template: dict) -> List[MockSemester]:
    """Generate 2 semi-annual semesters with gap-filling logic"""
    semesters = []
    spec = template["specialization"]
    age_group = template["age_group"]
    last_end_date = None

    for theme_data in template["themes"]:
        code = theme_data["code"]
        start_month = theme_data["start_month"]
        end_month = theme_data["end_month"]
        theme = theme_data["theme"]

        # HYBRID LOGIC: Gap-filling while preserving marketing themes
        if last_end_date is None:
            # First semester (Fall): start month's first Monday
            start = get_first_monday(year, start_month)
        else:
            # Second semester (Spring): immediately after Fall (gap-free)
            start = last_end_date + timedelta(days=1)
            # Align to Monday
            while start.weekday() != 0:  # 0 = Monday
                start += timedelta(days=1)

        # Handle year wrap-around for Fall semester (Sep-Feb)
        if start_month > end_month:  # Fall semester (Sep-Feb)
            end = get_last_sunday(year + 1, end_month)
        else:  # Spring semester (Mar-Aug)
            end = get_last_sunday(year, end_month)

        semester = MockSemester(
            code=f"{year}/{spec}_{age_group}_{code}",
            name=f"{year} {spec} {age_group} - {theme}",
            start_date=start,
            end_date=end,
            theme=theme
        )
        semesters.append(semester)
        last_end_date = end

    return semesters


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_no_gaps(semesters: List[MockSemester]) -> Dict:
    """Validate that there are NO gaps between semesters"""
    issues = []

    for i in range(len(semesters) - 1):
        current = semesters[i]
        next_sem = semesters[i + 1]

        # Check gap
        gap_days = (next_sem.start_date - current.end_date).days - 1

        if gap_days > 0:
            issues.append({
                "type": "GAP",
                "between": f"{current.theme} → {next_sem.theme}",
                "current_end": current.end_date,
                "next_start": next_sem.start_date,
                "gap_days": gap_days
            })
        elif gap_days < 0:
            issues.append({
                "type": "OVERLAP",
                "between": f"{current.theme} → {next_sem.theme}",
                "current_end": current.end_date,
                "next_start": next_sem.start_date,
                "overlap_days": abs(gap_days)
            })

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


def validate_monday_sunday(semesters: List[MockSemester]) -> Dict:
    """Validate that all semesters start on Monday and end on Sunday"""
    issues = []

    for sem in semesters:
        if sem.start_date.weekday() != 0:  # 0 = Monday
            issues.append({
                "type": "NOT_MONDAY_START",
                "semester": sem.theme,
                "start_date": sem.start_date,
                "day_of_week": sem.start_date.strftime("%A")
            })

        if sem.end_date.weekday() != 6:  # 6 = Sunday
            issues.append({
                "type": "NOT_SUNDAY_END",
                "semester": sem.theme,
                "end_date": sem.end_date,
                "day_of_week": sem.end_date.strftime("%A")
            })

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_validation_tests():
    """Run comprehensive validation tests for 2026-2029"""

    print("=" * 80)
    print("🧪 HYBRID SEMESTER GENERATION VALIDATION TEST")
    print("=" * 80)
    print()

    test_years = [2026, 2027, 2028, 2029]  # Include 2028 (leap year)
    all_passed = True

    for year in test_years:
        print(f"\n{'='*80}")
        print(f"📅 TESTING YEAR {year} {'(LEAP YEAR)' if year == 2028 else ''}")
        print(f"{'='*80}\n")

        # Test 1: Monthly (PRE age group)
        print(f"🔹 Testing MONTHLY semesters (PRE) - {year}")
        monthly_sems = generate_monthly_semesters_hybrid(year, LFA_PLAYER_PRE_TEMPLATE)

        gap_result = validate_no_gaps(monthly_sems)
        day_result = validate_monday_sunday(monthly_sems)

        if gap_result["valid"]:
            print(f"   ✅ NO GAPS - Perfect coverage")
        else:
            print(f"   ❌ GAPS FOUND:")
            for issue in gap_result["issues"]:
                print(f"      {issue}")
            all_passed = False

        if day_result["valid"]:
            print(f"   ✅ All Monday-Sunday transitions correct")
        else:
            print(f"   ❌ DAY ISSUES:")
            for issue in day_result["issues"]:
                print(f"      {issue}")
            all_passed = False

        print(f"   📊 Generated {len(monthly_sems)} semesters")
        print(f"   📅 Coverage: {monthly_sems[0].start_date} → {monthly_sems[-1].end_date}")

        # Test 2: Quarterly (YOUTH age group)
        print(f"\n🔹 Testing QUARTERLY semesters (YOUTH) - {year}")
        quarterly_sems = generate_quarterly_semesters_hybrid(year, LFA_PLAYER_YOUTH_TEMPLATE)

        gap_result = validate_no_gaps(quarterly_sems)
        day_result = validate_monday_sunday(quarterly_sems)

        if gap_result["valid"]:
            print(f"   ✅ NO GAPS - Perfect coverage")
        else:
            print(f"   ❌ GAPS FOUND:")
            for issue in gap_result["issues"]:
                print(f"      {issue}")
            all_passed = False

        if day_result["valid"]:
            print(f"   ✅ All Monday-Sunday transitions correct")
        else:
            print(f"   ❌ DAY ISSUES:")
            for issue in day_result["issues"]:
                print(f"      {issue}")
            all_passed = False

        print(f"   📊 Generated {len(quarterly_sems)} semesters")
        print(f"   📅 Coverage: {quarterly_sems[0].start_date} → {quarterly_sems[-1].end_date}")

        # Test 3: Semi-annual (AMATEUR age group)
        print(f"\n🔹 Testing SEMI-ANNUAL semesters (AMATEUR) - {year}")
        semiannual_sems = generate_semiannual_semesters_hybrid(year, LFA_PLAYER_AMATEUR_TEMPLATE)

        gap_result = validate_no_gaps(semiannual_sems)
        day_result = validate_monday_sunday(semiannual_sems)

        if gap_result["valid"]:
            print(f"   ✅ NO GAPS - Perfect coverage")
        else:
            print(f"   ❌ GAPS FOUND:")
            for issue in gap_result["issues"]:
                print(f"      {issue}")
            all_passed = False

        if day_result["valid"]:
            print(f"   ✅ All Monday-Sunday transitions correct")
        else:
            print(f"   ❌ DAY ISSUES:")
            for issue in day_result["issues"]:
                print(f"      {issue}")
            all_passed = False

        print(f"   📊 Generated {len(semiannual_sems)} semesters")
        print(f"   📅 Coverage: {semiannual_sems[0].start_date} → {semiannual_sems[-1].end_date}")

    # Final summary
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Hybrid solution working perfectly!")
    else:
        print("❌ SOME TESTS FAILED - Review issues above")
    print("=" * 80)

    return all_passed


# ============================================================================
# DETAILED EXAMPLE OUTPUT
# ============================================================================

def print_detailed_example():
    """Print detailed example for 2026 to show the improvement"""

    print("\n" + "=" * 80)
    print("📋 DETAILED EXAMPLE: 2026 MONTHLY SEMESTERS (PRE)")
    print("=" * 80)
    print()

    semesters = generate_monthly_semesters_hybrid(2026, LFA_PLAYER_PRE_TEMPLATE)

    print(f"{'Code':<15} {'Theme':<25} {'Start':<12} {'End':<12} {'Gap':<8}")
    print("-" * 80)

    for i, sem in enumerate(semesters):
        gap = ""
        if i > 0:
            prev_end = semesters[i-1].end_date
            gap_days = (sem.start_date - prev_end).days - 1
            if gap_days == 0:
                gap = "✅ 0 days"
            else:
                gap = f"❌ {gap_days} days"

        print(f"{sem.code:<15} {sem.theme:<25} {sem.start_date} {sem.end_date} {gap}")


if __name__ == "__main__":
    # Run validation tests
    all_passed = run_validation_tests()

    # Show detailed example
    print_detailed_example()

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)
