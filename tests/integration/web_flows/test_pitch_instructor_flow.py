"""
Pitch Instructor Flow Integration Tests — FLOW-01 through FLOW-04

FLOW-01  Admin direct assign → instructor accepts → session.instructor_id updated
FLOW-02  Master uniqueness: second direct assign with is_master=True → 409
FLOW-03  Instructor declines a PENDING assignment → status=DECLINED
FLOW-04  GET /campuses/{id}/pitches lists pitches; GET /pitches/{id}/eligible-instructors works

All tests run against the real DB in a SAVEPOINT-isolated transaction (auto-rollback).
"""
import uuid
import pytest
from datetime import datetime, date, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import event

from app.main import app
from app.database import engine, get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.campus import Campus
from app.models.location import Location
from app.models.pitch import Pitch
from app.models.pitch_instructor_assignment import (
    PitchInstructorAssignment,
    PitchAssignmentStatus,
)
from app.models.session import Session as SessionModel, SessionType
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.core.security import get_password_hash


# ─────────────────────────────────────────────────────────────────────────────
# DB fixture (SAVEPOINT isolated)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def test_db():
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSession()
    connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, txn):
        if txn.nested and not txn._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


# ─────────────────────────────────────────────────────────────────────────────
# Helper factories
# ─────────────────────────────────────────────────────────────────────────────

def _make_user(db: Session, role: UserRole = UserRole.INSTRUCTOR) -> User:
    u = User(
        email=f"pitch-test+{uuid.uuid4().hex[:8]}@lfa.com",
        name=f"Pitch Test User {uuid.uuid4().hex[:4]}",
        password_hash=get_password_hash("Test1234!"),
        role=role,
        is_active=True,
        onboarding_completed=True,
        credit_balance=0,
        payment_verified=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_location(db: Session) -> Location:
    loc = Location(
        name=f"Test City {uuid.uuid4().hex[:4]}",
        city="TestCity",
        country="HU",
        is_active=True,
    )
    db.add(loc)
    db.flush()
    return loc


def _make_campus(db: Session, location: Location) -> Campus:
    campus = Campus(
        location_id=location.id,
        name=f"Test Campus {uuid.uuid4().hex[:4]}",
        is_active=True,
    )
    db.add(campus)
    db.flush()
    return campus


def _make_pitch(db: Session, campus: Campus, pitch_number: int = 1) -> Pitch:
    pitch = Pitch(
        campus_id=campus.id,
        pitch_number=pitch_number,
        name=f"Pálya {pitch_number}",
        capacity=2,
        is_active=True,
    )
    db.add(pitch)
    db.flush()
    return pitch


def _make_semester(db: Session) -> Semester:
    sem = Semester(
        code=f"PITCH-{uuid.uuid4().hex[:8].upper()}",
        name="Pitch Test Semester",
        semester_category=SemesterCategory.TOURNAMENT,
        status=SemesterStatus.ONGOING,
        enrollment_cost=0,
        specialization_type="LFA_FOOTBALL_PLAYER",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        age_group="YOUTH",
    )
    db.add(sem)
    db.flush()
    return sem


def _make_session(db: Session, semester: Semester, pitch: Pitch) -> SessionModel:
    s = SessionModel(
        title="Test Session",
        date_start=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
        date_end=datetime(2026, 4, 1, 11, 0, tzinfo=timezone.utc),
        session_type=SessionType.on_site,
        semester_id=semester.id,
        pitch_id=pitch.id,
        instructor_id=None,
    )
    db.add(s)
    db.flush()
    return s


def _client_for(test_db: Session, current_user: User) -> TestClient:
    """Create a TestClient with the given user injected as the authenticated user."""
    def _override_db():
        yield test_db

    def _override_user():
        return current_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return TestClient(app, raise_server_exceptions=True)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW-01: Admin direct assign → instructor accepts → session.instructor_id updated
# ─────────────────────────────────────────────────────────────────────────────

def test_FLOW_01_direct_assign_accept_updates_sessions(test_db: Session):
    admin = _make_user(test_db, role=UserRole.ADMIN)
    instructor = _make_user(test_db, role=UserRole.INSTRUCTOR)
    location = _make_location(test_db)
    campus = _make_campus(test_db, location)
    pitch = _make_pitch(test_db, campus)
    semester = _make_semester(test_db)
    session = _make_session(test_db, semester, pitch)

    assert session.instructor_id is None

    # Step 1: Admin assigns instructor (DIRECT, is_master=True)
    client = _client_for(test_db, admin)
    resp = client.post(
        f"/api/v1/pitches/{pitch.id}/assign-instructor",
        json={
            "instructor_id": instructor.id,
            "semester_id": semester.id,
            "is_master": True,
        },
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["is_master"] is True
    assignment_id = data["id"]

    # Step 2: Instructor accepts
    client2 = _client_for(test_db, instructor)
    resp2 = client2.post(
        f"/api/v1/pitch-assignments/{assignment_id}/accept",
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert data2["status"] == "ACTIVE"
    assert data2["sessions_updated"] == 1

    # Step 3: Verify session.instructor_id was updated in DB
    test_db.refresh(session)
    assert session.instructor_id == instructor.id

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# FLOW-02: Master uniqueness — second assign with is_master=True → 409
# ─────────────────────────────────────────────────────────────────────────────

def test_FLOW_02_master_uniqueness_409(test_db: Session):
    admin = _make_user(test_db, role=UserRole.ADMIN)
    instructor_a = _make_user(test_db, role=UserRole.INSTRUCTOR)
    instructor_b = _make_user(test_db, role=UserRole.INSTRUCTOR)
    location = _make_location(test_db)
    campus = _make_campus(test_db, location)
    pitch = _make_pitch(test_db, campus)
    semester = _make_semester(test_db)

    # Manually insert an ACTIVE master assignment for instructor_a
    existing = PitchInstructorAssignment(
        pitch_id=pitch.id,
        instructor_id=instructor_a.id,
        semester_id=semester.id,
        is_master=True,
        assignment_type="DIRECT",
        status="ACTIVE",
        assigned_by=admin.id,
    )
    test_db.add(existing)
    test_db.flush()

    # Attempt to assign instructor_b as master on the same pitch/semester
    client = _client_for(test_db, admin)
    resp = client.post(
        f"/api/v1/pitches/{pitch.id}/assign-instructor",
        json={
            "instructor_id": instructor_b.id,
            "semester_id": semester.id,
            "is_master": True,
        },
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp.status_code == 409, resp.text
    body = resp.json()
    # Custom exception handler wraps under body["error"]["message"]
    error_obj = body.get("error") or body
    error_text = (error_obj.get("message") or error_obj.get("detail") or "").lower()
    assert "active master" in error_text, f"Unexpected response: {body}"

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# FLOW-03: Instructor declines assignment → status=DECLINED
# ─────────────────────────────────────────────────────────────────────────────

def test_FLOW_03_decline_assignment(test_db: Session):
    admin = _make_user(test_db, role=UserRole.ADMIN)
    instructor = _make_user(test_db, role=UserRole.INSTRUCTOR)
    location = _make_location(test_db)
    campus = _make_campus(test_db, location)
    pitch = _make_pitch(test_db, campus)
    semester = _make_semester(test_db)

    # Admin assigns
    client_admin = _client_for(test_db, admin)
    resp = client_admin.post(
        f"/api/v1/pitches/{pitch.id}/assign-instructor",
        json={"instructor_id": instructor.id, "semester_id": semester.id, "is_master": False},
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp.status_code == 200
    assignment_id = resp.json()["id"]

    # Instructor declines
    client_inst = _client_for(test_db, instructor)
    resp2 = client_inst.post(
        f"/api/v1/pitch-assignments/{assignment_id}/decline",
        json={"reason": "Nem érek rá"},
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp2.status_code == 200, resp2.text
    data = resp2.json()
    assert data["status"] == "DECLINED"

    # Verify in DB
    assignment = test_db.query(PitchInstructorAssignment).filter(
        PitchInstructorAssignment.id == assignment_id
    ).first()
    assert assignment.status == "DECLINED"
    assert "Nem érek rá" in assignment.notes

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# FLOW-04: GET /campuses/{id}/pitches and GET /pitches/{id}/eligible-instructors
# ─────────────────────────────────────────────────────────────────────────────

def test_FLOW_04_list_pitches_and_eligible_instructors(test_db: Session):
    admin = _make_user(test_db, role=UserRole.ADMIN)
    instructor = _make_user(test_db, role=UserRole.INSTRUCTOR)
    location = _make_location(test_db)
    campus = _make_campus(test_db, location)
    pitch_1 = _make_pitch(test_db, campus, pitch_number=1)
    pitch_2 = _make_pitch(test_db, campus, pitch_number=2)

    client = _client_for(test_db, admin)

    # List pitches for campus
    resp = client.get(
        f"/api/v1/campuses/{campus.id}/pitches",
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp.status_code == 200, resp.text
    pitches = resp.json()
    pitch_ids = [p["id"] for p in pitches]
    assert pitch_1.id in pitch_ids
    assert pitch_2.id in pitch_ids
    assert len(pitches) == 2

    # List eligible instructors for pitch_1
    resp2 = client.get(
        f"/api/v1/pitches/{pitch_1.id}/eligible-instructors",
        headers={"Authorization": "Bearer test-csrf-bypass"},
    )
    assert resp2.status_code == 200, resp2.text
    eligible = resp2.json()
    eligible_ids = [u["id"] for u in eligible]
    assert instructor.id in eligible_ids

    app.dependency_overrides.clear()
