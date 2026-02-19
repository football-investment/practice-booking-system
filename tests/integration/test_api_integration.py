"""
Simple Integration Test for Spec Services API

Tests that the new spec services are properly integrated into the API layer.
"""

import pytest
from app.api.helpers.spec_validation import check_specialization_type


def test_check_specialization_type_lfa_player():
    """Test that LFA_PLAYER is recognized as session_based"""
    is_valid, service_type = check_specialization_type("LFA_PLAYER")
    assert is_valid == True
    assert service_type == "session_based"


def test_check_specialization_type_gancuju():
    """Test that GANCUJU_PLAYER is recognized as semester_based"""
    is_valid, service_type = check_specialization_type("GANCUJU_PLAYER")
    assert is_valid == True
    assert service_type == "semester_based"


def test_check_specialization_type_coach():
    """Test that LFA_COACH is recognized as semester_based"""
    is_valid, service_type = check_specialization_type("LFA_COACH")
    assert is_valid == True
    assert service_type == "semester_based"


def test_check_specialization_type_internship():
    """Test that INTERNSHIP is recognized as semester_based"""
    is_valid, service_type = check_specialization_type("INTERNSHIP")
    assert is_valid == True
    assert service_type == "semester_based"


def test_check_specialization_type_with_suffix():
    """Test that suffixed spec types are also recognized"""
    # LFA_PLAYER with age group suffix
    is_valid, service_type = check_specialization_type("LFA_PLAYER_PRE")
    assert is_valid == True
    assert service_type == "session_based"

    is_valid, service_type = check_specialization_type("LFA_PLAYER_YOUTH")
    assert is_valid == True
    assert service_type == "session_based"


def test_check_specialization_type_invalid():
    """Test that invalid spec types are rejected"""
    is_valid, service_type = check_specialization_type("INVALID_SPEC")
    assert is_valid == False
    assert service_type == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
