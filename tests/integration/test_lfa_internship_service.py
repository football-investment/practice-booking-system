"""
Unit Tests for LFA Internship Service

Tests the LFA Internship specialization service including:
- Factory pattern registration
- Semester-based enrollment requirements
- 5-level XP progression (8 numeric levels)
- Position selection (1-7 from 45 positions)
- Age validation (18+ years)
"""

import pytest
from app.services.specs import get_spec_service
from app.services.specs.semester_based.lfa_internship_service import LFAInternshipService


# ============================================================================
# FACTORY PATTERN TESTS
# ============================================================================

def test_factory_returns_lfa_internship_service():
    """Test that factory returns LFAInternshipService for INTERNSHIP specialization"""
    service = get_spec_service("INTERNSHIP")
    assert isinstance(service, LFAInternshipService)
    assert service.get_specialization_name() == "LFA Internship"


def test_factory_handles_internship_variants():
    """Test that factory recognizes INTERNSHIP variants"""
    variants = ["INTERNSHIP", "INTERNSHIP_JUNIOR", "INTERNSHIP_SENIOR"]

    for variant in variants:
        service = get_spec_service(variant)
        assert isinstance(service, LFAInternshipService)


# ============================================================================
# SEMESTER-BASED FLAG TESTS
# ============================================================================

def test_is_semester_based():
    """Test that LFA Internship is marked as semester-based"""
    service = LFAInternshipService()
    assert service.is_semester_based() == True
    assert service.is_session_based() == False


# ============================================================================
# LEVEL SYSTEM TESTS
# ============================================================================

def test_all_5_intern_levels():
    """Test that all 5 intern levels are defined"""
    service = LFAInternshipService()
    assert len(service.INTERN_LEVELS) == 5
    assert service.INTERN_LEVELS[0] == "INTERN_JUNIOR"
    assert service.INTERN_LEVELS[4] == "INTERN_PRINCIPAL"

    # Each level should have info
    for level in service.INTERN_LEVELS:
        info = service.get_level_info(level)
        assert 'name' in info
        assert 'semester' in info
        assert 'total_base_xp' in info
        assert info['semester'] >= 1 and info['semester'] <= 5


def test_get_next_level():
    """Test level progression sequence"""
    service = LFAInternshipService()

    # INTERN_JUNIOR → INTERN_MID_LEVEL
    next_level = service.get_next_level("INTERN_JUNIOR")
    assert next_level == "INTERN_MID_LEVEL"

    # INTERN_MID_LEVEL → INTERN_SENIOR
    next_level = service.get_next_level("INTERN_MID_LEVEL")
    assert next_level == "INTERN_SENIOR"

    # INTERN_SENIOR → INTERN_LEAD
    next_level = service.get_next_level("INTERN_SENIOR")
    assert next_level == "INTERN_LEAD"

    # INTERN_LEAD → INTERN_PRINCIPAL
    next_level = service.get_next_level("INTERN_LEAD")
    assert next_level == "INTERN_PRINCIPAL"

    # INTERN_PRINCIPAL → None (max level)
    next_level = service.get_next_level("INTERN_PRINCIPAL")
    assert next_level is None


def test_level_info():
    """Test getting level display information"""
    service = LFAInternshipService()

    # Level 1: INTERN_JUNIOR
    info = service.get_level_info("INTERN_JUNIOR")
    assert info['name'] == "INTERN JUNIOR"
    assert info['icon'] == "🔰"
    assert info['semester'] == 1
    assert info['numeric_levels'] == [1, 2]
    assert info['total_base_xp'] == 1875
    assert info['excellence_threshold'] == 92
    assert info['standard_threshold'] == 74
    assert info['conditional_threshold'] == 70

    # Level 5: INTERN_PRINCIPAL
    info = service.get_level_info("INTERN_PRINCIPAL")
    assert info['name'] == "INTERN PRINCIPAL"
    assert info['icon'] == "🚀"
    assert info['semester'] == 5
    assert info['numeric_levels'] == [8]
    assert info['total_base_xp'] == 3900
    assert info['excellence_threshold'] == 96
    assert info['standard_threshold'] == 82
    assert info['conditional_threshold'] == 78


def test_level_numeric_mapping():
    """Test that numeric levels map correctly to intern levels"""
    service = LFAInternshipService()

    level_mappings = [
        ("INTERN_JUNIOR", [1, 2]),
        ("INTERN_MID_LEVEL", [3, 4]),
        ("INTERN_SENIOR", [5, 6]),
        ("INTERN_LEAD", [7]),
        ("INTERN_PRINCIPAL", [8])
    ]

    for level_name, expected_numerics in level_mappings:
        info = service.get_level_info(level_name)
        assert info['numeric_levels'] == expected_numerics


# ============================================================================
# XP SYSTEM TESTS
# ============================================================================

def test_xp_base_values_by_semester():
    """Test that base XP values are defined for all 5 semesters"""
    service = LFAInternshipService()

    assert len(service.XP_SCALING) == 5

    # Semester 1 (JUNIOR)
    assert service.XP_SCALING[1] == {'hybrid': 100, 'onsite': 75, 'virtual': 50}

    # Semester 5 (PRINCIPAL)
    assert service.XP_SCALING[5] == {'hybrid': 200, 'onsite': 150, 'virtual': 100}


def test_xp_scaling_increases():
    """Test that XP scales up with each semester (+25%)"""
    service = LFAInternshipService()

    # Check HYBRID scaling
    assert service.XP_SCALING[1]['hybrid'] == 100
    assert service.XP_SCALING[2]['hybrid'] == 125  # +25%
    assert service.XP_SCALING[3]['hybrid'] == 150  # +25%
    assert service.XP_SCALING[4]['hybrid'] == 175  # +25%
    assert service.XP_SCALING[5]['hybrid'] == 200  # +25%


def test_total_base_xp_increases():
    """Test that total base XP increases with each semester"""
    service = LFAInternshipService()

    xp_values = [
        ("INTERN_JUNIOR", 1875),
        ("INTERN_MID_LEVEL", 2370),
        ("INTERN_SENIOR", 2860),
        ("INTERN_LEAD", 3385),
        ("INTERN_PRINCIPAL", 3900)
    ]

    for level, expected_xp in xp_values:
        info = service.get_level_info(level)
        assert info['total_base_xp'] == expected_xp


def test_thresholds_get_stricter():
    """Test that XP thresholds increase with each semester"""
    service = LFAInternshipService()

    # Excellence thresholds: 92 → 93 → 94 → 95 → 96
    assert service.LEVEL_INFO['INTERN_JUNIOR']['excellence_threshold'] == 92
    assert service.LEVEL_INFO['INTERN_MID_LEVEL']['excellence_threshold'] == 93
    assert service.LEVEL_INFO['INTERN_SENIOR']['excellence_threshold'] == 94
    assert service.LEVEL_INFO['INTERN_LEAD']['excellence_threshold'] == 95
    assert service.LEVEL_INFO['INTERN_PRINCIPAL']['excellence_threshold'] == 96

    # Conditional thresholds: 70 → 72 → 74 → 76 → 78
    assert service.LEVEL_INFO['INTERN_JUNIOR']['conditional_threshold'] == 70
    assert service.LEVEL_INFO['INTERN_MID_LEVEL']['conditional_threshold'] == 72
    assert service.LEVEL_INFO['INTERN_SENIOR']['conditional_threshold'] == 74
    assert service.LEVEL_INFO['INTERN_LEAD']['conditional_threshold'] == 76
    assert service.LEVEL_INFO['INTERN_PRINCIPAL']['conditional_threshold'] == 78


def test_uv_max_xp():
    """Test UV (makeup) max XP by semester"""
    service = LFAInternshipService()

    assert len(service.UV_MAX_XP) == 5
    assert service.UV_MAX_XP[1] == 300  # 16% of 1,875
    assert service.UV_MAX_XP[2] == 380  # 16% of 2,370
    assert service.UV_MAX_XP[3] == 400  # 14% of 2,860
    assert service.UV_MAX_XP[4] == 480  # 14% of 3,385
    assert service.UV_MAX_XP[5] == 540  # 14% of 3,900


# ============================================================================
# POSITION SYSTEM TESTS
# ============================================================================

def test_all_30_positions_available():
    """Test that all 30 internship positions are available"""
    service = LFAInternshipService()

    total_positions = service.get_position_count()
    assert total_positions == 30


def test_positions_grouped_by_department():
    """Test that positions are grouped into 6 departments"""
    service = LFAInternshipService()

    positions = service.get_all_positions()
    assert len(positions) == 6  # 6 departments

    # Check department names
    assert 'Administrative' in positions
    assert 'Facility Management' in positions
    assert 'Commercial' in positions
    assert 'Communications' in positions
    assert 'Academy' in positions
    assert 'International' in positions


def test_department_position_counts():
    """Test position counts per department"""
    service = LFAInternshipService()

    positions = service.get_all_positions()

    assert len(positions['Administrative']) == 6
    assert len(positions['Facility Management']) == 6
    assert len(positions['Commercial']) == 7
    assert len(positions['Communications']) == 5
    assert len(positions['Academy']) == 3
    assert len(positions['International']) == 3


def test_validate_position_selection_success():
    """Test valid position selection (1-7 positions)"""
    service = LFAInternshipService()

    # 1 position - valid
    is_valid, msg = service.validate_position_selection(['LFA Sports Director'])
    assert is_valid == True

    # 7 positions - valid (maximum)
    positions = [
        'LFA Sports Director',
        'LFA Digital Marketing Manager',
        'LFA Facility Manager',
        'LFA Retail Manager',
        'LFA Press Officer',
        'LFA Talent Scout',
        'LFA Regional Director'
    ]
    is_valid, msg = service.validate_position_selection(positions)
    assert is_valid == True
    assert "7 position" in msg


def test_validate_position_selection_failures():
    """Test invalid position selections"""
    service = LFAInternshipService()

    # 0 positions - invalid
    is_valid, msg = service.validate_position_selection([])
    assert is_valid == False
    assert "At least 1" in msg

    # 8 positions - invalid (too many)
    positions = [
        'LFA Sports Director',
        'LFA Digital Marketing Manager',
        'LFA Facility Manager',
        'LFA Retail Manager',
        'LFA Press Officer',
        'LFA Talent Scout',
        'LFA Regional Director',
        'LFA Social Media Manager'
    ]
    is_valid, msg = service.validate_position_selection(positions)
    assert is_valid == False
    assert "Maximum 7" in msg

    # Duplicates - invalid
    positions = ['LFA Sports Director', 'LFA Sports Director']
    is_valid, msg = service.validate_position_selection(positions)
    assert is_valid == False
    assert "Duplicate" in msg

    # Invalid position - invalid
    positions = ['Invalid Position Name']
    is_valid, msg = service.validate_position_selection(positions)
    assert is_valid == False
    assert "Invalid position" in msg


# ============================================================================
# AGE VALIDATION TESTS
# ============================================================================

def test_minimum_age_constant():
    """Test that minimum age for LFA Internship is 18 years"""
    service = LFAInternshipService()
    assert service.MINIMUM_AGE == 18


# ============================================================================
# SESSION TYPE XP CALCULATION
# ============================================================================

def test_calculate_session_xp():
    """Test XP calculation for different session types"""
    service = LFAInternshipService()

    # Semester 1, HYBRID, PRESENT
    xp = service.calculate_session_xp('HYBRID', 1, 'PRESENT')
    assert xp == 100

    # Semester 1, ONSITE, PRESENT
    xp = service.calculate_session_xp('ONSITE', 1, 'PRESENT')
    assert xp == 75

    # Semester 1, VIRTUAL, PRESENT
    xp = service.calculate_session_xp('VIRTUAL', 1, 'PRESENT')
    assert xp == 50

    # Semester 5, HYBRID, PRESENT (highest XP)
    xp = service.calculate_session_xp('HYBRID', 5, 'PRESENT')
    assert xp == 200

    # ABSENT - no XP
    xp = service.calculate_session_xp('HYBRID', 1, 'ABSENT')
    assert xp == 0


def test_invalid_level():
    """Test handling of invalid level"""
    service = LFAInternshipService()

    with pytest.raises(ValueError, match="Invalid level"):
        service.get_next_level("INVALID_LEVEL")


def test_unknown_level_info():
    """Test that unknown level returns default info"""
    service = LFAInternshipService()

    info = service.get_level_info("UNKNOWN_LEVEL")
    assert info['name'] == "Unknown"
    assert info['icon'] == "❓"
    assert info['semester'] == 0


# ============================================================================
# LEVEL FOCUS AREAS
# ============================================================================

def test_level_focus_areas():
    """Test that each level has a clear focus area"""
    service = LFAInternshipService()

    focus_areas = [
        ("INTERN_JUNIOR", "Foundation & Culture"),
        ("INTERN_MID_LEVEL", "Core Skills & Development"),
        ("INTERN_SENIOR", "Mastery & Strategy"),
        ("INTERN_LEAD", "Leadership & Team Management"),
        ("INTERN_PRINCIPAL", "Executive & Co-Founder Ready")
    ]

    for level, expected_focus in focus_areas:
        info = service.get_level_info(level)
        assert info['focus'] == expected_focus


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
