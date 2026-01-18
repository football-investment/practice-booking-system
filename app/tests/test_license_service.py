"""
Test License Service

Comprehensive tests for GānCuju™️©️ License System functionality.
Tests license creation, advancement, requirements checking, and progression tracking.
"""

from app.services.license_service import LicenseService
from app.models.license import (
    LicenseMetadata, LicenseProgression
)
from app.models.specialization import SpecializationType


# ==========================================
# BASIC OPERATIONS TESTS (5 tests)
# ==========================================

def test_get_or_create_user_license_creates_new(db_session, student_user):
    """Test creating a new user license when one doesn't exist"""
    service = LicenseService(db_session)

    # Create license for PLAYER specialization
    license = service.get_or_create_user_license(student_user.id, "PLAYER")

    assert license is not None
    assert license.user_id == student_user.id
    assert license.specialization_type == "PLAYER"
    assert license.current_level == 1
    assert license.max_achieved_level == 1
    assert license.started_at is not None


def test_get_or_create_user_license_returns_existing(db_session, student_user):
    """Test returning existing license instead of creating duplicate"""
    service = LicenseService(db_session)

    # Create first license
    license1 = service.get_or_create_user_license(student_user.id, "COACH")
    original_id = license1.id

    # Try to create again - should return same license
    license2 = service.get_or_create_user_license(student_user.id, "COACH")

    assert license2.id == original_id
    assert license1.id == license2.id


def test_get_all_license_metadata(db_session):
    """Test fetching all license metadata"""
    service = LicenseService(db_session)

    # Create test metadata for different specializations
    player_meta = LicenseMetadata(
        specialization_type="PLAYER",
        level_code="player_bamboo_student",
        level_number=1,
        title="Bronze",
        subtitle="Entry level",
        color_primary="#CD7F32",
        image_url="bronze.svg",
        advancement_criteria={"xp": 1000}
    )
    coach_meta = LicenseMetadata(
        specialization_type="COACH",
        level_code="coach_lfa_pre_assistant",
        level_number=1,
        title="D License",
        subtitle="Grassroots",
        color_primary="#808080",
        image_url="d-license.svg",
        advancement_criteria={"hours": 30}
    )
    db_session.add_all([player_meta, coach_meta])
    db_session.commit()

    # Get all metadata
    all_metadata = service.get_all_license_metadata()

    assert len(all_metadata) >= 2
    assert any(meta['specialization_type'] == 'PLAYER' for meta in all_metadata)
    assert any(meta['specialization_type'] == 'COACH' for meta in all_metadata)


def test_get_license_metadata_by_level(db_session):
    """Test fetching specific license level metadata"""
    service = LicenseService(db_session)

    # Create test metadata
    meta = LicenseMetadata(
        specialization_type="INTERNSHIP",
        level_code="intern_mid_level",
        level_number=2,
        title="Junior Developer",
        subtitle="First professional level",
        color_primary="#4169E1",
        image_url="junior.svg",
        advancement_criteria={"projects": 3}
    )
    db_session.add(meta)
    db_session.commit()

    # Fetch by level
    result = service.get_license_metadata_by_level("INTERNSHIP", 2)

    assert result is not None
    assert result['level_number'] == 2
    assert result['title'] == "Junior Developer"
    assert result['specialization_type'] == "INTERNSHIP"


def test_get_user_licenses_with_metadata(db_session, student_user):
    """Test fetching user licenses with enriched metadata"""
    service = LicenseService(db_session)

    # Create metadata for level 1 and 2
    meta1 = LicenseMetadata(
        specialization_type="PLAYER",
        level_code="player_bamboo_student",
        level_number=1,
        title="Bronze",
        subtitle="Entry level",
        color_primary="#CD7F32",
        image_url="bronze.svg",
        advancement_criteria={"xp": 1000}
    )
    meta2 = LicenseMetadata(
        specialization_type="PLAYER",
        level_code="player_morning_dew",
        level_number=2,
        title="Silver",
        subtitle="Intermediate level",
        color_primary="#C0C0C0",
        image_url="silver.svg",
        advancement_criteria={"xp": 2500}
    )
    db_session.add_all([meta1, meta2])
    db_session.commit()

    # Create user license
    license = service.get_or_create_user_license(student_user.id, "PLAYER")

    # Get licenses with metadata
    licenses = service.get_user_licenses(student_user.id)

    assert len(licenses) == 1
    assert licenses[0]['user_id'] == student_user.id
    assert licenses[0]['specialization_type'] == "PLAYER"
    assert 'current_level_metadata' in licenses[0]
    assert 'next_level_metadata' in licenses[0]
    assert licenses[0]['current_level_metadata']['title'] == "Bronze"
    assert licenses[0]['next_level_metadata']['title'] == "Silver"


# ==========================================
# LICENSE ADVANCEMENT TESTS (4 tests)
# ==========================================

def test_advance_license_success(db_session, student_user, admin_user):
    """Test successful license advancement"""
    service = LicenseService(db_session)

    # Create metadata for levels 1, 2, 3
    level_codes = ["coach_lfa_pre_assistant", "coach_lfa_pre_head", "coach_lfa_youth_assistant"]
    for idx, level in enumerate(range(1, 4), 0):
        meta = LicenseMetadata(
            specialization_type="COACH",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"hours": level * 30}
        )
        db_session.add(meta)
    db_session.commit()

    # Create user license
    license = service.get_or_create_user_license(student_user.id, "COACH")
    assert license.current_level == 1

    # Advance to level 2
    result = service.advance_license(
        user_id=student_user.id,
        specialization="COACH",
        target_level=2,
        advanced_by=admin_user.id,
        reason="Completed requirements",
        requirements_met="30 hours of training"
    )

    assert result['success'] is True
    assert result['license']['current_level'] == 2
    assert result['license']['max_achieved_level'] == 2
    assert 'progression' in result
    assert result['progression']['from_level'] == 1
    assert result['progression']['to_level'] == 2


def test_advance_license_validation_failure(db_session, student_user, admin_user):
    """Test license advancement fails when validation fails"""
    service = LicenseService(db_session)

    # Create metadata for only 2 levels
    level_codes = ["player_bamboo_student", "player_morning_dew"]
    for idx, level in enumerate(range(1, 3), 0):
        meta = LicenseMetadata(
            specialization_type="PLAYER",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"xp": level * 1000}
        )
        db_session.add(meta)
    db_session.commit()

    # Create user license at level 1
    license = service.get_or_create_user_license(student_user.id, "PLAYER")

    # Try to advance to level 10 (exceeds max level)
    result = service.advance_license(
        user_id=student_user.id,
        specialization="PLAYER",
        target_level=10,
        advanced_by=admin_user.id,
        reason="Test"
    )

    assert result['success'] is False
    assert 'message' in result
    assert result['license']['current_level'] == 1  # Should remain at level 1


def test_advance_license_progression_history(db_session, student_user, admin_user):
    """Test that license advancements are recorded in progression history"""
    service = LicenseService(db_session)

    # Create metadata for 4 levels
    level_codes = ["intern_junior", "intern_mid_level", "intern_senior", "intern_lead"]
    for idx, level in enumerate(range(1, 5), 0):
        meta = LicenseMetadata(
            specialization_type="INTERNSHIP",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"projects": level}
        )
        db_session.add(meta)
    db_session.commit()

    # Create license and advance multiple times
    license = service.get_or_create_user_license(student_user.id, "INTERNSHIP")

    service.advance_license(student_user.id, "INTERNSHIP", 2, admin_user.id, "First advancement")
    service.advance_license(student_user.id, "INTERNSHIP", 3, admin_user.id, "Second advancement")

    # Check progression history
    progressions = db_session.query(LicenseProgression).filter(
        LicenseProgression.user_license_id == license.id
    ).all()

    assert len(progressions) == 2
    assert progressions[0].from_level == 1
    assert progressions[0].to_level == 2
    assert progressions[1].from_level == 2
    assert progressions[1].to_level == 3


def test_advance_license_updates_max_achieved_level(db_session, student_user, admin_user):
    """Test that max_achieved_level tracks highest level reached"""
    service = LicenseService(db_session)

    # Create metadata for 3 levels
    level_codes = ["coach_lfa_pre_assistant", "coach_lfa_pre_head", "coach_lfa_youth_assistant"]
    for idx, level in enumerate(range(1, 4), 0):
        meta = LicenseMetadata(
            specialization_type="COACH",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"hours": level * 20}
        )
        db_session.add(meta)
    db_session.commit()

    # Create license
    license = service.get_or_create_user_license(student_user.id, "COACH")

    # Advance to level 2, then to level 3 (can only advance one level at a time)
    service.advance_license(student_user.id, "COACH", 2, admin_user.id, "Advance to 2")
    result = service.advance_license(student_user.id, "COACH", 3, admin_user.id, "Advance to 3")

    assert result['license']['current_level'] == 3
    assert result['license']['max_achieved_level'] == 3


# ==========================================
# DASHBOARD & PROGRESSION PATH TESTS (3 tests)
# ==========================================

def test_get_specialization_progression_path(db_session):
    """Test fetching complete progression path for a specialization"""
    service = LicenseService(db_session)

    # Create complete progression path for PLAYER
    levels = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]
    level_codes = ["player_bamboo_student", "player_morning_dew", "player_flexible_reed", "player_sky_river", "player_strong_root"]
    for idx, level_name in enumerate(levels, start=1):
        meta = LicenseMetadata(
            specialization_type="PLAYER",
            level_code=level_codes[idx-1],
            level_number=idx,
            title=level_name,
            subtitle=f"{level_name} level description",
            color_primary=f"#00000{idx}",
            image_url=f"{level_name.lower()}.svg",
            advancement_criteria={"xp": idx * 1000}
        )
        db_session.add(meta)
    db_session.commit()

    # Get progression path
    path = service.get_specialization_progression_path("PLAYER")

    assert len(path) == 5
    assert path[0]['title'] == "Bronze"
    assert path[4]['title'] == "Diamond"
    assert all('advancement_criteria' in level for level in path)


def test_get_user_license_dashboard(db_session, student_user):
    """Test fetching comprehensive license dashboard data"""
    service = LicenseService(db_session)

    # Create metadata for COACH
    level_codes = ["coach_lfa_pre_assistant", "coach_lfa_pre_head"]
    for idx, level in enumerate(range(1, 3), 0):
        meta = LicenseMetadata(
            specialization_type="COACH",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"hours": level * 25}
        )
        db_session.add(meta)
    db_session.commit()

    # Create user license
    student_user.specialization = SpecializationType.LFA_COACH
    db_session.commit()
    license = service.get_or_create_user_license(student_user.id, "COACH")

    # Get dashboard
    dashboard = service.get_user_license_dashboard(student_user.id)

    assert 'user' in dashboard
    assert dashboard['user']['id'] == student_user.id
    assert 'licenses' in dashboard
    assert len(dashboard['licenses']) == 1
    assert 'available_specializations' in dashboard
    assert 'overall_progress' in dashboard


def test_get_recent_license_activity(db_session, student_user, admin_user):
    """Test fetching recent license progression activity"""
    service = LicenseService(db_session)

    # Create metadata
    level_codes = ["intern_junior", "intern_mid_level", "intern_senior"]
    for idx, level in enumerate(range(1, 4), 0):
        meta = LicenseMetadata(
            specialization_type="INTERNSHIP",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"projects": level}
        )
        db_session.add(meta)
    db_session.commit()

    # Create license and multiple progressions
    license = service.get_or_create_user_license(student_user.id, "INTERNSHIP")
    service.advance_license(student_user.id, "INTERNSHIP", 2, admin_user.id, "First")
    service.advance_license(student_user.id, "INTERNSHIP", 3, admin_user.id, "Second")

    # Get dashboard which includes recent activity
    dashboard = service.get_user_license_dashboard(student_user.id)

    assert 'recent_activity' in dashboard
    activity = dashboard['recent_activity']
    assert len(activity) == 2
    assert activity[0]['specialization'] == "INTERNSHIP"  # Most recent first


# ==========================================
# REQUIREMENTS CHECKING TESTS (3 tests)
# ==========================================

def test_get_license_requirements_check_valid(db_session, student_user):
    """Test checking requirements for valid advancement"""
    service = LicenseService(db_session)

    # Create metadata
    level_codes = ["player_bamboo_student", "player_morning_dew"]
    for idx, level in enumerate(range(1, 3), 0):
        meta = LicenseMetadata(
            specialization_type="PLAYER",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"xp": level * 1000, "sessions": level * 5}
        )
        db_session.add(meta)
    db_session.commit()

    # Create user license
    license = service.get_or_create_user_license(student_user.id, "PLAYER")

    # Check requirements for level 2
    check = service.get_license_requirements_check(student_user.id, "PLAYER", 2)

    assert check is not None
    assert 'error' not in check
    assert check['current_level'] == 1
    assert check['target_level'] == 2
    assert 'requirements' in check
    assert 'target_metadata' in check


def test_get_license_requirements_check_invalid_level(db_session, student_user):
    """Test checking requirements for non-existent level"""
    service = LicenseService(db_session)

    # Create metadata for only 2 levels
    level_codes = ["coach_lfa_pre_assistant", "coach_lfa_pre_head"]
    for idx, level in enumerate(range(1, 3), 0):
        meta = LicenseMetadata(
            specialization_type="COACH",
            level_code=level_codes[idx],
            level_number=level,
            title=f"Level {level}",
            subtitle=f"Description {level}",
            color_primary="#000000",
            image_url=f"level{level}.svg",
            advancement_criteria={"hours": level * 30}
        )
        db_session.add(meta)
    db_session.commit()

    # Create user license
    license = service.get_or_create_user_license(student_user.id, "COACH")

    # Check requirements for level 99 (doesn't exist)
    check = service.get_license_requirements_check(student_user.id, "COACH", 99)

    assert 'error' in check
    assert check['error'] == "Target level not found"


def test_get_marketing_content(db_session):
    """Test fetching marketing content for license levels"""
    service = LicenseService(db_session)

    # Create metadata with marketing content
    meta = LicenseMetadata(
        specialization_type="INTERNSHIP",
        level_code="intern_junior",
        level_number=1,
        title="Intern",
        subtitle="Start your IT career journey",
        color_primary="#4CAF50",
        image_url="intern.svg",
        advancement_criteria={"projects": 1}
    )
    db_session.add(meta)
    db_session.commit()

    # Get marketing content for specific level
    content = service.get_marketing_content("INTERNSHIP", level=1)

    assert content is not None
    assert content['title'] == "Intern"
    assert content['subtitle'] == "Start your IT career journey"

    # Get marketing content for all levels
    all_content = service.get_marketing_content("INTERNSHIP")

    assert 'specialization' in all_content
    assert 'levels' in all_content
    assert len(all_content['levels']) == 1
