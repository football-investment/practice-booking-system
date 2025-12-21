"""
Quick Test for LFA Player Service

CORRECTED AGE GROUP RULES (OFFICIAL):
- PRE: 6-11 years (UP category)
- YOUTH: 12-18 years (UP category)
- AMATEUR: 14+ years (Adult category, can self-enroll)
- PRO: 14+ years (Adult category, Master Instructor promotion only)

CRITICAL: 14 is the boundary - ages 14-18 can be in YOUTH OR AMATEUR/PRO

Tests:
1. Age group calculation
2. Factory pattern (get_spec_service)
3. Age group extraction
4. Cross-age-group attendance rules
5. Session-based flag validation
"""

from datetime import date, datetime
from app.services.specs import get_spec_service
from app.services.specs.session_based.lfa_player_service import LFAPlayerService


def test_age_group_calculation():
    """Test age group calculation logic"""
    print("=" * 60)
    print("TEST 1: Age Group Calculation")
    print("=" * 60)

    service = LFAPlayerService()

    # Test cases: (date_of_birth, expected_age_group)
    # NEW RULES:
    # PRE: 6-11 years (UP category)
    # YOUTH: 12-18 years (UP category) - natural group for 12-18
    # AMATEUR: 14+ years (Adult category) - default for 19+
    # PRO: 14+ years (Adult category, promotion only)
    test_cases = [
        (date(2019, 1, 1), 'PRE'),      # ~6 years old → PRE
        (date(2018, 1, 1), 'PRE'),      # ~7 years old → PRE
        (date(2015, 1, 1), 'PRE'),      # ~10 years old → PRE
        (date(2014, 1, 1), 'PRE'),      # ~11 years old → PRE
        (date(2013, 1, 1), 'YOUTH'),    # ~12 years old → YOUTH
        (date(2012, 1, 1), 'YOUTH'),    # ~13 years old → YOUTH
        (date(2011, 1, 1), 'YOUTH'),    # ~14 years old → YOUTH (can also be AMATEUR)
        (date(2010, 1, 1), 'YOUTH'),    # ~15 years old → YOUTH
        (date(2009, 1, 1), 'YOUTH'),    # ~16 years old → YOUTH
        (date(2008, 1, 1), 'YOUTH'),    # ~17 years old → YOUTH
        (date(2007, 1, 1), 'YOUTH'),    # ~18 years old → YOUTH (last year of YOUTH)
        (date(2006, 1, 1), 'AMATEUR'),  # ~19 years old → AMATEUR (adult category default)
        (date(2005, 1, 1), 'AMATEUR'),  # ~20 years old → AMATEUR
        (date(1990, 1, 1), 'AMATEUR'),  # ~35 years old → AMATEUR
    ]

    for dob, expected_group in test_cases:
        try:
            actual_group = service.calculate_age_group(dob)
            age = service.calculate_age(dob)
            status = "✅ PASS" if actual_group == expected_group else "❌ FAIL"
            print(f"{status} | Age {age} (born {dob}) → {actual_group} (expected: {expected_group})")
        except ValueError as e:
            print(f"❌ ERROR | {dob} → {e}")

    print()


def test_factory_pattern():
    """Test factory pattern for service instantiation"""
    print("=" * 60)
    print("TEST 2: Factory Pattern")
    print("=" * 60)

    test_cases = [
        ("LFA_PLAYER_PRE", "LFAPlayerService"),
        ("LFA_PLAYER_YOUTH", "LFAPlayerService"),
        ("LFA_PLAYER_AMATEUR", "LFAPlayerService"),
        ("LFA_PLAYER_PRO", "LFAPlayerService"),
    ]

    for spec_type, expected_class_name in test_cases:
        try:
            service = get_spec_service(spec_type)
            actual_class_name = service.__class__.__name__
            status = "✅ PASS" if actual_class_name == expected_class_name else "❌ FAIL"
            print(f"{status} | {spec_type} → {actual_class_name} (expected: {expected_class_name})")
        except ValueError as e:
            print(f"❌ ERROR | {spec_type} → {e}")

    # Test invalid spec
    try:
        service = get_spec_service("INVALID_SPEC")
        print(f"❌ FAIL | Should have raised ValueError for INVALID_SPEC")
    except ValueError as e:
        print(f"✅ PASS | Correctly rejected INVALID_SPEC: {e}")

    print()


def test_age_group_extraction():
    """Test extracting age group from specialization_type"""
    print("=" * 60)
    print("TEST 3: Age Group Extraction")
    print("=" * 60)

    service = LFAPlayerService()

    test_cases = [
        ("LFA_PLAYER_PRE", "PRE"),
        ("LFA_PLAYER_YOUTH", "YOUTH"),
        ("LFA_PLAYER_AMATEUR", "AMATEUR"),
        ("LFA_PLAYER_PRO", "PRO"),
        ("LFA_COACH", None),  # Not LFA_PLAYER
        ("INVALID", None),
    ]

    for spec_type, expected_group in test_cases:
        actual_group = service.get_age_group_from_specialization(spec_type)
        status = "✅ PASS" if actual_group == expected_group else "❌ FAIL"
        print(f"{status} | {spec_type} → {actual_group} (expected: {expected_group})")

    print()


def test_cross_age_group_attendance():
    """Test cross-age-group session attendance rules"""
    print("=" * 60)
    print("TEST 4: Cross-Age-Group Attendance")
    print("=" * 60)

    service = LFAPlayerService()

    # Test cases: (user_age_group, session_age_group, expected_allowed)
    test_cases = [
        ('PRE', 'PRE', True),        # Same group
        ('PRE', 'YOUTH', True),      # PRE can attend YOUTH
        ('PRE', 'AMATEUR', False),   # PRE cannot attend AMATEUR
        ('PRE', 'PRO', False),       # PRE cannot attend PRO

        ('YOUTH', 'PRE', True),      # YOUTH can attend PRE
        ('YOUTH', 'YOUTH', True),    # Same group
        ('YOUTH', 'AMATEUR', True),  # YOUTH can attend AMATEUR
        ('YOUTH', 'PRO', False),     # YOUTH cannot attend PRO

        ('AMATEUR', 'PRE', False),   # AMATEUR cannot attend PRE
        ('AMATEUR', 'YOUTH', True),  # AMATEUR can attend YOUTH
        ('AMATEUR', 'AMATEUR', True),# Same group
        ('AMATEUR', 'PRO', False),   # AMATEUR cannot attend PRO

        ('PRO', 'PRE', False),       # PRO cannot attend PRE
        ('PRO', 'YOUTH', False),     # PRO cannot attend YOUTH
        ('PRO', 'AMATEUR', False),   # PRO cannot attend AMATEUR
        ('PRO', 'PRO', True),        # Same group
    ]

    for user_group, session_group, expected_allowed in test_cases:
        can_attend, reason = service.can_attend_age_group_session(user_group, session_group)
        status = "✅ PASS" if can_attend == expected_allowed else "❌ FAIL"
        allowed_text = "✓ Allowed" if can_attend else "✗ Not allowed"
        print(f"{status} | {user_group} → {session_group}: {allowed_text} (expected: {expected_allowed})")
        if can_attend != expected_allowed:
            print(f"       Reason: {reason}")

    print()


def test_session_based_flag():
    """Test that LFA Player is correctly marked as session-based"""
    print("=" * 60)
    print("TEST 5: Session-Based Flag")
    print("=" * 60)

    service = LFAPlayerService()

    is_session = service.is_session_based()
    is_semester = service.is_semester_based()

    print(f"{'✅ PASS' if is_session else '❌ FAIL'} | is_session_based() = {is_session} (expected: True)")
    print(f"{'✅ PASS' if not is_semester else '❌ FAIL'} | is_semester_based() = {is_semester} (expected: False)")
    print(f"Specialization name: {service.get_specialization_name()}")

    print()


if __name__ == "__main__":
    print("\n" + "🧪 " * 30)
    print("LFA PLAYER SERVICE - UNIT TESTS")
    print("🧪 " * 30 + "\n")

    test_age_group_calculation()
    test_factory_pattern()
    test_age_group_extraction()
    test_cross_age_group_attendance()
    test_session_based_flag()

    print("=" * 60)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 60)
