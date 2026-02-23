"""
Tournament Detail API Tests

Tests GET /api/v1/tournaments/{id} endpoint:
1. Valid tournament ID returns 200 with full details
2. Invalid tournament ID returns 404
3. Inactive tournament returns 404
4. Response schema validation (all required fields present)
5. Performance validation (p95 < 100ms)
"""

import pytest
import time
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.semester import Semester, SemesterStatus
from app.models.license import UserLicense
from app.core.security import get_password_hash
from app.database import get_db


@pytest.fixture
def test_student(db_session: Session):
    """Create test student for authenticated requests"""
    user = User(
        name="Test Student",
        email="tournament.detail.student@test.com",
        password_hash=get_password_hash("student123"),
        role=UserRole.STUDENT,
        is_active=True,
        credit_balance=1000,
        date_of_birth=date(2010, 1, 15)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_student_token(client, test_student):
    """Get access token for test student"""
    # Create license for student
    license = UserLicense(
        user_id=test_student.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        is_active=True,
        started_at=datetime.now(timezone.utc)
    )
    client.app.dependency_overrides[get_db]().add(license)
    client.app.dependency_overrides[get_db]().commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "tournament.detail.student@test.com", "password": "student123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def active_tournament(db_session: Session):
    """Create active tournament with all required fields"""
    tournament = Semester(
        code="DETAIL-TEST-2026",
        name="Detail Test Tournament 2026",
        specialization_type="LFA_FOOTBALL_PLAYER",
        age_group="PRO",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status="ENROLLMENT_OPEN",
        enrollment_cost=500,
        is_active=True
    )
    db_session.add(tournament)
    db_session.commit()
    db_session.refresh(tournament)
    return tournament


@pytest.fixture
def inactive_tournament(db_session: Session):
    """Create inactive tournament (is_active=False)"""
    tournament = Semester(
        code="INACTIVE-TEST-2026",
        name="Inactive Tournament 2026",
        specialization_type="LFA_FOOTBALL_PLAYER",
        age_group="PRO",
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        status=SemesterStatus.READY_FOR_ENROLLMENT,
        tournament_status="ENROLLMENT_OPEN",
        enrollment_cost=500,
        is_active=False  # Inactive
    )
    db_session.add(tournament)
    db_session.commit()
    db_session.refresh(tournament)
    return tournament


class TestTournamentDetailAPI:
    """Test suite for GET /api/v1/tournaments/{id} endpoint"""

    def test_get_tournament_detail_valid_id(
        self, client, active_tournament, test_student_token
    ):
        """Test 1: Valid tournament ID returns 200 with full details"""
        response = client.get(
            f"/api/v1/tournaments/{active_tournament.id}",
            headers={"Authorization": f"Bearer {test_student_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all fields present
        assert data["id"] == active_tournament.id
        assert data["code"] == "DETAIL-TEST-2026"
        assert data["name"] == "Detail Test Tournament 2026"
        assert data["age_group"] == "PRO"
        assert data["enrollment_cost"] == 500
        assert data["max_players"] == 16
        assert data["tournament_status"] == "ENROLLMENT_OPEN"
        assert data["semester_id"] == active_tournament.id  # Same as id

    def test_get_tournament_detail_invalid_id(self, client, test_student_token):
        """Test 2: Invalid tournament ID returns 404"""
        response = client.get(
            "/api/v1/tournaments/99999",  # Non-existent ID
            headers={"Authorization": f"Bearer {test_student_token}"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_get_tournament_detail_inactive_tournament(
        self, client, inactive_tournament, test_student_token
    ):
        """Test 3: Inactive tournament returns 404"""
        response = client.get(
            f"/api/v1/tournaments/{inactive_tournament.id}",
            headers={"Authorization": f"Bearer {test_student_token}"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_get_tournament_detail_response_schema(
        self, client, active_tournament, test_student_token
    ):
        """Test 4: Response includes all required fields"""
        response = client.get(
            f"/api/v1/tournaments/{active_tournament.id}",
            headers={"Authorization": f"Bearer {test_student_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields from TournamentDetailResponse schema
        required_fields = [
            "id",
            "code",
            "name",
            "start_date",
            "end_date",
            "age_group",
            "enrollment_cost",
            "max_players",
            "tournament_status",
            "semester_id"
        ]

        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from response"

        # Optional field (can be None)
        assert "master_instructor_id" in data

        # Verify data types
        assert isinstance(data["id"], int)
        assert isinstance(data["code"], str)
        assert isinstance(data["name"], str)
        assert isinstance(data["age_group"], str)
        assert isinstance(data["enrollment_cost"], int)
        assert isinstance(data["max_players"], int)
        assert isinstance(data["tournament_status"], str)
        assert isinstance(data["semester_id"], int)

    def test_get_tournament_detail_performance(
        self, client, active_tournament, test_student_token
    ):
        """Test 5: Performance validation (p95 < 100ms)"""
        latencies = []

        # Run 20 requests to measure p95
        for _ in range(20):
            start = time.perf_counter()
            response = client.get(
                f"/api/v1/tournaments/{active_tournament.id}",
                headers={"Authorization": f"Bearer {test_student_token}"}
            )
            end = time.perf_counter()

            assert response.status_code == 200
            latencies.append((end - start) * 1000)  # Convert to ms

        # Calculate p95
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        # Performance target: p95 < 100ms
        assert p95_latency < 100, f"p95 latency {p95_latency:.2f}ms exceeds 100ms target"
