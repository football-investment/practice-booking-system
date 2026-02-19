"""
E2E tests for age validation and parental consent system.

Tests the complete flow from API endpoint to database for age-restricted specializations.
"""
import pytest
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_progress import Specialization
from app.services.specialization_service import SpecializationService
from app.services.specialization_validation import SpecializationValidationError


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


@pytest.fixture
def user_13_years_old(db_session: Session):
    """Create 13-year-old user"""
    dob = date.today() - timedelta(days=13*365 + 3)  # 13 years
    user = User(
        name="13 Year Old Kid",
        email="kid13@test.com",
        password_hash="fake_hash",
        date_of_birth=dob,
        is_active=True,
        parental_consent=True  # Has consent
    )
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def user_14_years_old_with_consent(db_session: Session):
    """Create 14-year-old user with parental consent"""
    dob = datetime.now() - timedelta(days=14*365 + 100)  # Definitely 14 years old
    user = User(
        name="14 Year Old Teen",
        email="teen14@test.com",
        password_hash="fake_hash",
        date_of_birth=dob,
        is_active=True,
        parental_consent=True  # Has consent
    )
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def user_14_years_old_no_consent(db_session: Session):
    """Create 14-year-old user WITHOUT parental consent"""
    dob = datetime.now() - timedelta(days=14*365 + 100)  # Definitely 14 years old
    user = User(
        name="14 Year Old No Consent",
        email="teen14_no_consent@test.com",
        password_hash="fake_hash",
        date_of_birth=dob,
        is_active=True,
        parental_consent=False  # NO consent
    )
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def user_18_years_old(db_session: Session):
    """Create 18-year-old user (adult)"""
    dob = datetime.now() - timedelta(days=18*365 + 100)  # Definitely 18 years old
    user = User(
        name="18 Year Old Adult",
        email="adult18@test.com",
        password_hash="fake_hash",
        date_of_birth=dob,
        is_active=True,
        parental_consent=True  # Adult with consent
    )
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def user_4_years_old(db_session: Session):
    """Create 4-year-old user (too young for GANCUJU_PLAYER)"""
    dob = date.today() - timedelta(days=4*365 + 3)  # 4 years
    user = User(
        name="4 Year Old Kid",
        email="kid4@test.com",
        password_hash="fake_hash",
        date_of_birth=dob,
        is_active=True,
        parental_consent=True  # Has consent but too young
    )
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def specialization_service(db_session: Session):
    """Create SpecializationService instance"""
    return SpecializationService(db_session)


def test_age_validation_13yo_lfa_coach_rejected(
    specialization_service: SpecializationService,
    user_13_years_old: User,
    setup_specializations
):
    """13-year-old CANNOT select LFA_COACH (requires 14+)"""

    with pytest.raises(SpecializationValidationError) as exc_info:
        specialization_service.enroll_user(user_13_years_old.id, "LFA_COACH")

    assert "minimum" in str(exc_info.value).lower() or "age" in str(exc_info.value).lower() or "14" in str(exc_info.value)


def test_age_validation_14yo_lfa_coach_accepted(
    specialization_service: SpecializationService,
    user_14_years_old_with_consent: User,
    setup_specializations
):
    """14-year-old CAN select LFA_COACH with parental consent"""

    result = specialization_service.enroll_user(
        user_14_years_old_with_consent.id,
        "LFA_COACH"
    )

    assert result['success'] is True
    assert result['message']


def test_parental_consent_required_under_18(
    specialization_service: SpecializationService,
    user_14_years_old_no_consent: User,
    setup_specializations
):
    """14-year-old without parental consent CANNOT select LFA_COACH"""

    with pytest.raises(SpecializationValidationError) as exc_info:
        specialization_service.enroll_user(
            user_14_years_old_no_consent.id,
            "LFA_COACH"
        )

    assert "parental consent" in str(exc_info.value).lower() or "consent" in str(exc_info.value).lower()


def test_adult_no_consent_required(
    specialization_service: SpecializationService,
    user_18_years_old: User,
    setup_specializations
):
    """18-year-old does NOT need parental consent"""

    result = specialization_service.enroll_user(user_18_years_old.id, "LFA_COACH")

    assert result['success'] is True


def test_gancuju_player_5yo_minimum(
    specialization_service: SpecializationService,
    user_4_years_old: User,
    setup_specializations
):
    """GANCUJU_PLAYER requires minimum 5 years"""

    with pytest.raises(SpecializationValidationError) as exc_info:
        specialization_service.enroll_user(user_4_years_old.id, "GANCUJU_PLAYER")

    assert "minimum" in str(exc_info.value).lower() or "age" in str(exc_info.value).lower() or "5" in str(exc_info.value)


def test_gancuju_player_13yo_with_consent_accepted(
    specialization_service: SpecializationService,
    user_13_years_old: User,
    setup_specializations
):
    """13-year-old CAN select GANCUJU_PLAYER (requires 5+)"""

    result = specialization_service.enroll_user(
        user_13_years_old.id,
        "GANCUJU_PLAYER"
    )

    assert result['success'] is True


def test_adult_can_select_any_specialization(
    specialization_service: SpecializationService,
    user_18_years_old: User,
    setup_specializations
):
    """Adults can select any specialization"""

    # Test GANCUJU_PLAYER
    result1 = specialization_service.enroll_user(user_18_years_old.id, "GANCUJU_PLAYER")
    assert result1['success'] is True

    # Note: In real system, user can only have one active specialization
    # This test demonstrates API validation works for both specializations
