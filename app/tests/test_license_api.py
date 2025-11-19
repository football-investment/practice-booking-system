"""
Test License API Endpoints

Comprehensive tests for GānCuju™️©️ License System API endpoints.
Tests authentication, authorization, data retrieval, and license advancement workflows.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.license import LicenseMetadata, UserLicense
from app.models.user import User, UserRole
from app.models.specialization import SpecializationType


# ==========================================
# PUBLIC METADATA ENDPOINTS (2 tests)
# ==========================================

def test_get_license_metadata_public(client: TestClient, db_session: Session):
    """Test getting license metadata without authentication"""
    # Create test metadata
    meta = LicenseMetadata(
        specialization_type="PLAYER",
        level_code="player_bamboo_student",
        level_number=1,
        title="Bamboo Student",
        subtitle="Entry level",
        color_primary="#F8F8FF",
        image_url="bamboo.svg",
        advancement_criteria={"xp": 1000}
    )
    db_session.add(meta)
    db_session.commit()

    # Get metadata (no auth required)
    response = client.get("/api/v1/licenses/metadata")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(m['specialization_type'] == 'PLAYER' for m in data)


def test_get_license_metadata_by_specialization(client: TestClient, db_session: Session):
    """Test getting metadata for specific specialization"""
    # Create test metadata for COACH
    meta = LicenseMetadata(
        specialization_type="COACH",
        level_code="coach_lfa_pre_assistant",
        level_number=1,
        title="Pre-Assistant",
        subtitle="Grassroots level",
        color_primary="#808080",
        image_url="coach1.svg",
        advancement_criteria={"hours": 30}
    )
    db_session.add(meta)
    db_session.commit()

    # Get COACH metadata
    response = client.get("/api/v1/licenses/metadata/COACH")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(m['specialization_type'] == 'COACH' for m in data)


# ==========================================
# USER LICENSE ACCESS TESTS (2 tests)
# ==========================================

def test_get_my_licenses_requires_auth(client: TestClient):
    """Test that getting user licenses requires authentication"""
    response = client.get("/api/v1/licenses/my-licenses")

    # FastAPI returns 403 for missing authentication
    assert response.status_code in [401, 403]


def test_get_my_licenses_success(client: TestClient, db_session: Session, student_user: User, student_token: str):
    """Test getting user's licenses with authentication"""
    # Create test metadata
    meta = LicenseMetadata(
        specialization_type="PLAYER",
        level_code="player_bamboo_student",
        level_number=1,
        title="Bamboo Student",
        subtitle="Entry level",
        color_primary="#F8F8FF",
        image_url="bamboo.svg",
        advancement_criteria={"xp": 1000}
    )
    db_session.add(meta)
    db_session.commit()

    # Create user license
    license = UserLicense(
        user_id=student_user.id,
        specialization_type="PLAYER",
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(license)
    db_session.commit()

    # Get user's licenses
    response = client.get(
        "/api/v1/licenses/my-licenses",
        headers={"Authorization": f"Bearer {student_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['specialization_type'] == "PLAYER"
    assert data[0]['current_level'] == 1


# ==========================================
# LICENSE DASHBOARD TESTS (1 test)
# ==========================================

def test_get_license_dashboard(client: TestClient, db_session: Session, student_user: User, student_token: str):
    """Test getting comprehensive license dashboard"""
    # Create test metadata
    meta = LicenseMetadata(
        specialization_type="INTERNSHIP",
        level_code="intern_junior",
        level_number=1,
        title="Junior Intern",
        subtitle="Entry level",
        color_primary="#4CAF50",
        image_url="intern.svg",
        advancement_criteria={"projects": 1}
    )
    db_session.add(meta)
    db_session.commit()

    # Create user license
    student_user.specialization = SpecializationType.INTERNSHIP
    db_session.commit()

    license = UserLicense(
        user_id=student_user.id,
        specialization_type="INTERNSHIP",
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(license)
    db_session.commit()

    # Get dashboard
    response = client.get(
        "/api/v1/licenses/dashboard",
        headers={"Authorization": f"Bearer {student_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert 'user' in data
    assert 'licenses' in data
    assert 'available_specializations' in data
    assert 'overall_progress' in data
    assert data['user']['id'] == student_user.id


# ==========================================
# LICENSE ADVANCEMENT WORKFLOW TESTS (3 tests)
# ==========================================

def test_advance_license_missing_fields(client: TestClient, student_token: str):
    """Test that license advancement requires all fields"""
    response = client.post(
        "/api/v1/licenses/advance",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"specialization": "PLAYER"}  # Missing target_level
    )

    assert response.status_code == 400
    # FastAPI structured error response may contain the message in different fields
    data = response.json()
    response_str = str(data)
    assert "Missing required field" in response_str or "target_level" in response_str


def test_advance_license_success(client: TestClient, db_session: Session, student_user: User, student_token: str):
    """Test successful license advancement"""
    # Create metadata for levels 1 and 2
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
    license = UserLicense(
        user_id=student_user.id,
        specialization_type="PLAYER",
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(license)
    db_session.commit()

    # Advance to level 2
    response = client.post(
        "/api/v1/licenses/advance",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "specialization": "PLAYER",
            "target_level": 2,
            "reason": "Completed requirements"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['license']['current_level'] == 2
    assert data['license']['max_achieved_level'] == 2


def test_advance_license_validation_failure(client: TestClient, db_session: Session, student_user: User, student_token: str):
    """Test that license advancement validates properly"""
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

    # Create user license at level 1
    license = UserLicense(
        user_id=student_user.id,
        specialization_type="COACH",
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(license)
    db_session.commit()

    # Try to advance to level 10 (exceeds max level)
    response = client.post(
        "/api/v1/licenses/advance",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "specialization": "COACH",
            "target_level": 10,
            "reason": "Test invalid advancement"
        }
    )

    assert response.status_code == 200  # Returns 200 with success: false
    data = response.json()
    assert data['success'] is False
    assert 'message' in data


# ==========================================
# REQUIREMENTS CHECK TESTS (1 test)
# ==========================================

def test_check_advancement_requirements(client: TestClient, db_session: Session, student_user: User, student_token: str):
    """Test checking advancement requirements"""
    # Create metadata
    level_codes = ["intern_junior", "intern_mid_level"]
    for idx, level in enumerate(range(1, 3), 0):
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

    # Create user license
    license = UserLicense(
        user_id=student_user.id,
        specialization_type="INTERNSHIP",
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.now(timezone.utc)
    )
    db_session.add(license)
    db_session.commit()

    # Check requirements for level 2
    response = client.get(
        "/api/v1/licenses/requirements/INTERNSHIP/2",
        headers={"Authorization": f"Bearer {student_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['current_level'] == 1
    assert data['target_level'] == 2
    assert 'requirements' in data
    assert 'target_metadata' in data


# ==========================================
# MARKETING CONTENT TEST (1 test)
# ==========================================

def test_get_marketing_content(client: TestClient, db_session: Session):
    """Test getting marketing content for specialization"""
    # Create metadata with marketing content
    meta = LicenseMetadata(
        specialization_type="PLAYER",
        level_code="player_bamboo_student",
        level_number=1,
        title="Bamboo Student",
        subtitle="The first lessons in flexibility",
        color_primary="#F8F8FF",
        marketing_narrative="Begin your journey with the ancient art of Cuju",
        cultural_context="Inspired by 4000 years of tradition",
        image_url="bamboo.svg",
        advancement_criteria={"xp": 1000}
    )
    db_session.add(meta)
    db_session.commit()

    # Get marketing content (no auth required)
    response = client.get("/api/v1/licenses/marketing/PLAYER?level=1")

    assert response.status_code == 200
    data = response.json()
    assert data['title'] == "Bamboo Student"
    assert data['subtitle'] == "The first lessons in flexibility"
    assert 'marketing_narrative' in data
    assert 'cultural_context' in data
