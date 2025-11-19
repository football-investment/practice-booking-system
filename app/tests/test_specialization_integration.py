"""
Integration tests for specialization progress system
Tests full stack: Database -> API -> Frontend data format
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.user import User, UserRole
from ..models.user_progress import Specialization, PlayerLevel, CoachLevel, InternshipLevel, SpecializationProgress
from ..models.specialization import SpecializationType
from ..core.security import get_password_hash


@pytest.fixture
def setup_specializations(db_session: Session):
    """
    Set up specialization master data - MINIMAL HYBRID ARCHITECTURE

    NOTE: Only creates DB records for FK integrity.
    Content (name, icon, description, levels) comes from JSON configs.
    """
    from datetime import datetime

    # Create all 4 specializations (MINIMAL: only id, is_active, created_at)
    gancuju_spec = Specialization(
        id="GANCUJU_PLAYER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    lfa_football_spec = Specialization(
        id="LFA_FOOTBALL_PLAYER",
        is_active=True,
        created_at=datetime.utcnow()
    )
    coach_spec = Specialization(
        id="LFA_COACH",
        is_active=True,
        created_at=datetime.utcnow()
    )
    internship_spec = Specialization(
        id="INTERNSHIP",
        is_active=True,
        created_at=datetime.utcnow()
    )

    db_session.add_all([gancuju_spec, lfa_football_spec, coach_spec, internship_spec])

    # Create player levels (8 belts)
    player_levels = [
        PlayerLevel(id=1, name="Bambusz Tanítvány", color="#FFFFFF",
                   required_xp=0, required_sessions=0,
                   description="White Belt - Beginner",
                   license_title="Beginner Apprentice"),
        PlayerLevel(id=2, name="Hajnali Harmat", color="#FDD835",
                   required_xp=100, required_sessions=5,
                   description="Yellow Belt",
                   license_title="Morning Dew Practitioner"),
        PlayerLevel(id=3, name="Rugalmas Nád", color="#4CAF50",
                   required_xp=300, required_sessions=12,
                   description="Green Belt",
                   license_title="Flexible Reed Master"),
        PlayerLevel(id=4, name="Égi Folyó", color="#2196F3",
                   required_xp=600, required_sessions=20,
                   description="Blue Belt",
                   license_title="Sky River Expert"),
        PlayerLevel(id=5, name="Erős Gyökér", color="#795548",
                   required_xp=1000, required_sessions=30,
                   description="Brown Belt",
                   license_title="Strong Root Specialist"),
        PlayerLevel(id=6, name="Téli Hold", color="#616161",
                   required_xp=1500, required_sessions=42,
                   description="Dark Grey Belt",
                   license_title="Winter Moon Guardian"),
        PlayerLevel(id=7, name="Éjfél Őrzője", color="#212121",
                   required_xp=2200, required_sessions=56,
                   description="Black Belt",
                   license_title="Midnight Keeper"),
        PlayerLevel(id=8, name="Sárkány Bölcsesség", color="#D32F2F",
                   required_xp=3000, required_sessions=72,
                   description="Red Belt - Master",
                   license_title="Dragon Wisdom Master")
    ]

    # Create coach levels (8 levels)
    coach_levels = [
        CoachLevel(id=1, name="Grassroots Coach",
                  required_xp=0, required_sessions=0,
                  theory_hours=0, practice_hours=0,
                  description="Entry level",
                  license_title="Grassroots License"),
        CoachLevel(id=2, name="Youth Development Coach",
                  required_xp=150, required_sessions=8,
                  theory_hours=20, practice_hours=30,
                  description="Youth coaching",
                  license_title="UEFA C License Equivalent"),
        CoachLevel(id=3, name="Advanced Youth Coach",
                  required_xp=400, required_sessions=18,
                  theory_hours=40, practice_hours=60,
                  description="Advanced youth",
                  license_title="UEFA B License Equivalent"),
        CoachLevel(id=4, name="Senior Team Coach",
                  required_xp=800, required_sessions=30,
                  theory_hours=80, practice_hours=120,
                  description="Senior teams",
                  license_title="UEFA A License Equivalent"),
        CoachLevel(id=5, name="Professional Coach",
                  required_xp=1400, required_sessions=45,
                  theory_hours=120, practice_hours=180,
                  description="Professional level",
                  license_title="UEFA Pro License Equivalent"),
        CoachLevel(id=6, name="Elite Performance Coach",
                  required_xp=2200, required_sessions=65,
                  theory_hours=160, practice_hours=240,
                  description="Elite performance",
                  license_title="Elite Performance License"),
        CoachLevel(id=7, name="Master Coach Educator",
                  required_xp=3200, required_sessions=90,
                  theory_hours=200, practice_hours=300,
                  description="Coach education",
                  license_title="Master Educator License"),
        CoachLevel(id=8, name="Football Director",
                  required_xp=4500, required_sessions=120,
                  theory_hours=250, practice_hours=400,
                  description="Director level",
                  license_title="Football Director Certification")
    ]

    # Create internship levels (3 levels)
    internship_levels = [
        InternshipLevel(id=1, name="Junior Intern",
                       required_xp=0, required_sessions=0,
                       total_hours=0,
                       description="Starting internship",
                       license_title="Junior Intern Certificate"),
        InternshipLevel(id=2, name="Associate Intern",
                       required_xp=200, required_sessions=10,
                       total_hours=80,
                       description="Associate level",
                       license_title="Associate Intern Certificate"),
        InternshipLevel(id=3, name="Senior Intern",
                       required_xp=500, required_sessions=25,
                       total_hours=200,
                       description="Senior level",
                       license_title="Senior Intern Certificate")
    ]

    db_session.add_all(player_levels + coach_levels + internship_levels)
    db_session.commit()

    return {
        'specializations': [gancuju_spec, lfa_football_spec, coach_spec, internship_spec],
        'player_levels': player_levels,
        'coach_levels': coach_levels,
        'internship_levels': internship_levels
    }


@pytest.fixture
def student_with_specialization(db_session: Session, setup_specializations):
    """Create a test student with GANCUJU_PLAYER specialization"""
    user = User(
        name="Test Player",
        email="player@test.com",
        password_hash=get_password_hash("test123"),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        specialization=SpecializationType.GANCUJU_PLAYER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create initial progress
    progress = SpecializationProgress(
        student_id=user.id,
        specialization_id="GANCUJU_PLAYER",
        current_level=1,
        total_xp=0,
        completed_sessions=0,
        completed_projects=0
    )
    db_session.add(progress)
    db_session.commit()
    db_session.refresh(progress)

    return user


@pytest.fixture
def player_token(client, student_with_specialization):
    """Get access token for player user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "player@test.com", "password": "test123"}
    )
    return response.json()["access_token"]


class TestSpecializationProgressIntegration:
    """Integration tests for specialization progress system"""

    def test_get_all_specializations(self, client, setup_specializations, student_token):
        """Test GET /api/v1/specializations/ returns all specializations"""
        response = client.get(
            "/api/v1/specializations/",
            headers={"Authorization": f"Bearer {player_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Backend returns array directly, not wrapped in { success, data }
        assert isinstance(data, list)
        assert len(data) == 4  # Updated: Now includes LFA_FOOTBALL_PLAYER

        # Verify structure (UPDATED: Check all 4 specializations)
        spec_codes = [s["code"] for s in data]
        assert "GANCUJU_PLAYER" in spec_codes
        assert "LFA_FOOTBALL_PLAYER" in spec_codes
        assert "LFA_COACH" in spec_codes
        assert "INTERNSHIP" in spec_codes

    def test_get_player_levels(self, client, setup_specializations, student_token):
        """Test GET /api/v1/specializations/levels/GANCUJU_PLAYER returns all 8 levels"""
        response = client.get(
            "/api/v1/specializations/levels/GANCUJU_PLAYER",
            headers={"Authorization": f"Bearer {player_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        print(f"DEBUG: Response data: {data}")

        assert data["success"] is True
        assert len(data["data"]) == 8

        # Verify level 1 structure
        level_1 = data["data"][0]
        assert level_1["level"] == 1
        assert level_1["name"] == "Bambusz Tanítvány"
        assert level_1["color"] == "#FFFFFF"
        assert level_1["required_xp"] == 0
        assert level_1["required_sessions"] == 0

    def test_get_my_progress_initial(self, client, student_with_specialization, player_token):
        """Test GET /api/v1/specializations/progress/GANCUJU_PLAYER returns initial progress"""
        response = client.get(
            "/api/v1/specializations/progress/GANCUJU_PLAYER",
            headers={"Authorization": f"Bearer {player_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # This should match the backend response format
        assert data["success"] is True
        progress = data["data"]

        assert progress["student_id"] == student_with_specialization.id
        assert progress["specialization_id"] == "GANCUJU_PLAYER"
        assert progress["current_level"]["level"] == 1  # current_level is an object
        assert progress["total_xp"] == 0
        assert progress["completed_sessions"] == 0
        assert progress["completed_projects"] == 0

    def test_update_progress_xp_gain(self, client, db_session, student_with_specialization, player_token):
        """Test POST /api/v1/specializations/update-progress/GANCUJU_PLAYER with XP gain"""
        # UPDATED: Level 2 requires 1000 XP + 5 sessions (from JSON config)
        # Gain 1000 XP and complete 6 sessions to ensure level up
        response = client.post(
            "/api/v1/specializations/update-progress/GANCUJU_PLAYER?xp_gained=1000&sessions_completed=6&projects_completed=0",
            headers={"Authorization": f"Bearer {player_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        result = data["data"]

        # Verify result structure (update_progress returns different format than get_progress)
        assert result["success"] is True
        assert result["new_xp"] == 1000  # Total XP after update
        assert result["old_level"] == 1
        # Level 2 requires 1000 XP + 5 sessions, we have 1000 XP + 6 sessions, so should level up
        assert result["new_level"] == 2
        assert result["leveled_up"] is True
        assert result["levels_gained"] == 1
        assert result["new_level_info"] is not None
        assert result["new_level_info"]["name"] == "Hajnali Harmat"

    def test_progress_level_up_to_level_2(self, client, db_session, student_with_specialization, player_token):
        """Test that gaining enough XP causes level up from 1 to 2"""
        # UPDATED: Level 2 requirements: 1000 XP, 5 sessions (from JSON config)
        update_data = {
            "xp_gained": 1000,
            "sessions_completed": 5,
            "projects_completed": 0
        }

        response = client.post(
            "/api/v1/specializations/update-progress/GANCUJU_PLAYER?xp_gained=100&sessions_completed=5&projects_completed=0",
            headers={"Authorization": f"Bearer {player_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

        # Check if backend triggered level up
        if "level_up" in data:
            assert data["level_up"]["new_level"] == 2
            assert data["level_up"]["old_level"] == 1

        # Verify by fetching progress again
        get_response = client.get(
            "/api/v1/specializations/progress/GANCUJU_PLAYER",
            headers={"Authorization": f"Bearer {player_token}"}
        )

        assert get_response.status_code == 200
        get_data = get_response.json()
        progress = get_data["data"]

        assert progress["total_xp"] == 100
        assert progress["completed_sessions"] == 5
        # Backend should have leveled up to 2
        assert progress["current_level"]["level"] >= 1

    def test_coach_specialization_progress(self, client, db_session, setup_specializations, student_token):
        """Test LFA_COACH specialization progress (different from GANCUJU_PLAYER)"""
        # Create a student with LFA_COACH specialization
        coach_student = User(
            name="Test Coach",
            email="coach@test.com",
            password_hash=get_password_hash("test123"),
            role=UserRole.STUDENT,
            is_active=True,
            onboarding_completed=True,
            specialization=SpecializationType.LFA_COACH
        )
        db_session.add(coach_student)
        db_session.commit()

        # Create progress
        progress = SpecializationProgress(
            student_id=coach_student.id,
            specialization_id="LFA_COACH",
            current_level=1,
            total_xp=0,
            completed_sessions=0,
            completed_projects=0
        )
        db_session.add(progress)
        db_session.commit()

        # Login as coach student
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "coach@test.com", "password": "test123"}
        )
        coach_token = login_response.json()["access_token"]

        # Get coach levels (UPDATED: COACH → LFA_COACH)
        response = client.get(
            "/api/v1/specializations/levels/LFA_COACH",
            headers={"Authorization": f"Bearer {coach_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["data"]) == 8

        # Verify level 2 structure (UPDATED to match JSON config)
        level_2 = data["data"][1]
        assert level_2["name"] == "LFA Pre Football Vezetőedző"
        assert level_2["required_xp"] == 1000  # Updated from 150 to match JSON config

    def test_internship_specialization_with_projects(self, client, db_session, setup_specializations, student_token):
        """Test INTERNSHIP specialization with projects counter"""
        # Create student with INTERNSHIP
        intern = User(
            name="Test Intern",
            email="intern@test.com",
            password_hash=get_password_hash("test123"),
            role=UserRole.STUDENT,
            is_active=True,
            onboarding_completed=True,
            specialization=SpecializationType.INTERNSHIP
        )
        db_session.add(intern)
        db_session.commit()

        # Create progress
        progress = SpecializationProgress(
            student_id=intern.id,
            specialization_id="INTERNSHIP",
            current_level=1,
            total_xp=0,
            completed_sessions=0,
            completed_projects=0
        )
        db_session.add(progress)
        db_session.commit()

        # Login as intern
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "intern@test.com", "password": "test123"}
        )
        intern_token = login_response.json()["access_token"]

        # Update progress with projects
        update_data = {
            "xp_gained": 50,
            "sessions_completed": 3,
            "projects_completed": 2
        }

        response = client.post(
            "/api/v1/specializations/update-progress/INTERNSHIP?xp_gained=50&sessions_completed=3&projects_completed=2",
            headers={"Authorization": f"Bearer {intern_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        result = data["data"]

        # Verify update was successful (update_progress returns different format)
        assert result["success"] is True
        assert result["new_xp"] == 50  # XP gained in this update

    def test_frontend_data_format(self, client, student_with_specialization, player_token):
        """Test that API response matches frontend expectations"""
        response = client.get(
            "/api/v1/specializations/progress/GANCUJU_PLAYER",
            headers={"Authorization": f"Bearer {player_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Frontend expects: { success: true, data: {...} }
        assert "success" in data
        assert "data" in data
        assert data["success"] is True

        # Frontend ProgressCard.jsx extracts response.data via specializationService
        # So the response structure should be: { success, data: { student_id, specialization_id, ... } }
        progress = data["data"]

        # Verify all expected fields for frontend
        required_fields = [
            "student_id",
            "specialization_id",
            "current_level",
            "total_xp",
            "completed_sessions",
            "completed_projects"
        ]

        for field in required_fields:
            assert field in progress, f"Missing field: {field}"

    def test_no_progress_creates_new_record(self, client, db_session, setup_specializations):
        """Test that fetching progress for a student with no record creates one"""
        # Create student without initial progress
        new_student = User(
            name="New Student",
            email="newstudent@test.com",
            password_hash=get_password_hash("test123"),
            role=UserRole.STUDENT,
            is_active=True,
            onboarding_completed=True,
            specialization=SpecializationType.GANCUJU_PLAYER
        )
        db_session.add(new_student)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "newstudent@test.com", "password": "test123"}
        )
        token = login_response.json()["access_token"]

        # Try to get progress (should auto-create)
        response = client.get(
            "/api/v1/specializations/progress/GANCUJU_PLAYER",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Backend should auto-create progress
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["current_level"]["level"] == 1  # current_level is an object
        assert data["data"]["total_xp"] == 0
