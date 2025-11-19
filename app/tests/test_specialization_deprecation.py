"""
Unit tests for specialization deprecation system.

Tests the backward compatibility layer that maps legacy IDs (PLAYER, COACH)
to new IDs (GANCUJU_PLAYER, LFA_COACH) with deprecation warnings.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.services.specialization_service import (
    SpecializationService,
    DEPRECATED_MAPPINGS,
    DEPRECATION_DEADLINE
)
from app.models.user_progress import Specialization


@pytest.fixture
def specialization_service(db_session: Session):
    """Create a SpecializationService instance"""
    return SpecializationService(db_session)


@pytest.fixture
def setup_specializations(db_session: Session):
    """Create test specializations in DB"""
    specs = [
        Specialization(id="GANCUJU_PLAYER", is_active=True),
        Specialization(id="LFA_COACH", is_active=True),
    ]
    for spec in specs:
        db_session.add(spec)
    db_session.commit()
    yield
    # Cleanup
    db_session.query(Specialization).delete()
    db_session.commit()


def test_legacy_player_mapped_to_gancuju(
    specialization_service: SpecializationService,
    setup_specializations,
    caplog
):
    """Test PLAYER → GANCUJU_PLAYER mapping with warning"""
    import logging
    caplog.set_level(logging.WARNING)

    # Using legacy ID should work but log warning
    result = specialization_service.validate_specialization_exists("PLAYER")

    assert result is True, "Legacy PLAYER ID should be accepted"

    # Check that deprecation warning was logged
    assert any("DEPRECATED SPECIALIZATION ID" in record.message for record in caplog.records)
    assert any("PLAYER" in record.message for record in caplog.records)
    assert any("GANCUJU_PLAYER" in record.message for record in caplog.records)


def test_legacy_coach_mapped_to_lfa_coach(
    specialization_service: SpecializationService,
    setup_specializations,
    caplog
):
    """Test COACH → LFA_COACH mapping with warning"""
    import logging
    caplog.set_level(logging.WARNING)

    result = specialization_service.validate_specialization_exists("COACH")

    assert result is True, "Legacy COACH ID should be accepted"

    # Check that deprecation warning was logged
    assert any("DEPRECATED SPECIALIZATION ID" in record.message for record in caplog.records)
    assert any("COACH" in record.message for record in caplog.records)
    assert any("LFA_COACH" in record.message for record in caplog.records)


def test_after_deadline_raises_error(
    specialization_service: SpecializationService,
    setup_specializations
):
    """Test that after deadline, legacy IDs are rejected"""

    # Mock datetime to be AFTER deadline
    future_date = DEPRECATION_DEADLINE + timedelta(days=1)

    with patch('app.services.specialization_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = future_date
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            specialization_service.validate_specialization_exists("PLAYER")

        assert "no longer supported" in str(exc_info.value)
        assert "PLAYER" in str(exc_info.value)
        assert "GANCUJU_PLAYER" in str(exc_info.value)


def test_new_ids_work_without_warning(
    specialization_service: SpecializationService,
    setup_specializations,
    caplog
):
    """Test that new IDs work without deprecation warning"""
    import logging
    caplog.set_level(logging.WARNING)

    # Should work without warnings
    result = specialization_service.validate_specialization_exists("GANCUJU_PLAYER")
    assert result is True

    # No deprecation warnings should be logged
    assert not any("DEPRECATED SPECIALIZATION ID" in record.message for record in caplog.records)


def test_handle_legacy_specialization_direct(specialization_service: SpecializationService):
    """Test _handle_legacy_specialization method directly"""

    # Test legacy mapping
    assert specialization_service._handle_legacy_specialization("PLAYER") == "GANCUJU_PLAYER"
    assert specialization_service._handle_legacy_specialization("COACH") == "LFA_COACH"

    # Test pass-through for new IDs
    assert specialization_service._handle_legacy_specialization("GANCUJU_PLAYER") == "GANCUJU_PLAYER"
    assert specialization_service._handle_legacy_specialization("LFA_COACH") == "LFA_COACH"
    assert specialization_service._handle_legacy_specialization("INTERNSHIP") == "INTERNSHIP"


def test_enroll_user_with_legacy_id(
    specialization_service: SpecializationService,
    setup_specializations,
    db_session: Session,
    caplog
):
    """Test that enroll_user accepts legacy IDs with warning"""
    import logging
    from app.models.user import User

    caplog.set_level(logging.WARNING)

    # Create test user
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash="fake_hash",
        is_active=True,
        date_of_birth=datetime(2005, 1, 1),  # 20 years old
        parental_consent=False  # Adult, no consent needed
    )
    db_session.add(user)
    db_session.commit()

    # Enroll with legacy ID
    result = specialization_service.enroll_user(user.id, "PLAYER")

    assert result['success'] is True
    assert "DEPRECATED SPECIALIZATION ID" in caplog.text


def test_get_level_requirements_with_legacy_id(
    specialization_service: SpecializationService,
    setup_specializations,
    caplog
):
    """Test that get_level_requirements accepts legacy IDs with warning"""
    import logging
    caplog.set_level(logging.WARNING)

    # Get level requirements with legacy ID
    result = specialization_service.get_level_requirements("PLAYER", 1)

    # Should work (returns level data or None)
    # Check deprecation warning was logged
    assert any("DEPRECATED SPECIALIZATION ID" in record.message for record in caplog.records)
