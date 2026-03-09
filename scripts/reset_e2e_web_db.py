#!/usr/bin/env python3
"""
Web E2E DB Reset — Sprint 55

Truncates E2E-specific tables and re-seeds baseline for Cypress web tests
(FastAPI Jinja2, localhost:8000).  Idempotent per scenario.

Usage:
    python scripts/reset_e2e_web_db.py --scenario baseline
    python scripts/reset_e2e_web_db.py --scenario student_no_dob
    python scripts/reset_e2e_web_db.py --scenario student_with_credits
    python scripts/reset_e2e_web_db.py --scenario session_ready

Scenarios:
    baseline             admin + instructor + student (DOB set) + semester
    student_no_dob       baseline users but fresh student has no DOB
    student_with_credits baseline + student.credit_balance = 200
    session_ready        student_with_credits + 1 on_site + 1 hybrid session
"""

import sys
import os
import argparse
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.models.session import Session as SessionModel, SessionType
from app.models.booking import Booking
from app.models.attendance import Attendance
from app.models.quiz import QuizAttempt
from app.models.credit_transaction import CreditTransaction
from app.models.semester_enrollment import SemesterEnrollment
from app.core.security import get_password_hash

TZ = ZoneInfo("Europe/Budapest")

# ── Baseline credentials ───────────────────────────────────────────────────────

_BASELINE_USERS = [
    {
        "email":    "admin@lfa.com",
        "name":     "LFA Admin",
        "password": "admin123",
        "role":     UserRole.ADMIN,
        "dob":      date(1985, 6, 15),
    },
    {
        "email":    "grandmaster@lfa.com",
        "name":     "Grand Master",
        "password": "TestInstructor2026",
        "role":     UserRole.INSTRUCTOR,
        "dob":      date(1980, 3, 20),
    },
    {
        "email":    "rdias@manchestercity.com",
        "name":     "Ruben Dias",
        "password": "TestPlayer2026",
        "role":     UserRole.STUDENT,
        "dob":      date(1998, 5, 14),
    },
]

_FRESH_STUDENT = {
    "email":    "fresh.e2e@lfa.com",
    "name":     "Fresh E2E Student",
    "password": "FreshE2E2026",
    "role":     UserRole.STUDENT,
    "dob":      None,   # intentionally missing — age_verification flow
}

# Seeded with is_active=False in every scenario → used by AUTH-07
_INACTIVE_STUDENT = {
    "email":    "inactive.e2e@lfa.com",
    "name":     "Inactive E2E Student",
    "password": "InactiveE2E2026",
    "role":     UserRole.STUDENT,
    "dob":      date(2000, 1, 1),
}

_SEMESTER_CODE = "E2E-CI-2026"
_SEMESTER_NAME = "E2E CI Test Semester"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate_transactional_data(db) -> None:
    """Remove all transactional E2E data (bookings, attendance, quiz attempts, etc.)."""
    db.query(QuizAttempt).delete(synchronize_session=False)
    db.query(Attendance).delete(synchronize_session=False)
    db.query(Booking).delete(synchronize_session=False)
    db.query(CreditTransaction).delete(synchronize_session=False)
    db.query(SemesterEnrollment).filter(
        SemesterEnrollment.user_id.in_(
            db.query(User.id).filter(User.email.in_(
                [u["email"] for u in _BASELINE_USERS]
                + [_FRESH_STUDENT["email"], _INACTIVE_STUDENT["email"]]
            ))
        )
    ).delete(synchronize_session=False)
    db.query(SessionModel).filter(
        SessionModel.title.like("E2E%")
    ).delete(synchronize_session=False)
    db.commit()


def _upsert_user(db, spec: dict, credit_balance: int = 0,
                 clear_dob: bool = False, is_active: bool = True,
                 onboarding_completed: bool = False) -> User:
    existing = db.query(User).filter(User.email == spec["email"]).first()
    dob = None if clear_dob else spec.get("dob")
    dob_dt = datetime(dob.year, dob.month, dob.day) if dob else None

    if existing:
        existing.password_hash = get_password_hash(spec["password"])
        existing.is_active = is_active
        existing.credit_balance = credit_balance
        existing.date_of_birth = dob_dt
        existing.onboarding_completed = onboarding_completed
        db.commit()
        return existing
    else:
        user = User(
            name=spec["name"],
            email=spec["email"],
            password_hash=get_password_hash(spec["password"]),
            role=spec["role"],
            is_active=is_active,
            credit_balance=credit_balance,
            date_of_birth=dob_dt,
            onboarding_completed=onboarding_completed,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def _upsert_semester(db) -> Semester:
    today = date.today()
    sem = db.query(Semester).filter(Semester.code == _SEMESTER_CODE).first()
    if sem:
        sem.start_date = today - timedelta(days=180)
        sem.end_date   = today + timedelta(days=180)
        db.commit()
    else:
        sem = Semester(
            code=_SEMESTER_CODE,
            name=_SEMESTER_NAME,
            start_date=today - timedelta(days=180),
            end_date=today + timedelta(days=180),
        )
        db.add(sem)
        db.commit()
        db.refresh(sem)
    return sem


def _create_sessions(db, semester: Semester, instructor: User) -> list[SessionModel]:
    """Create 1 on_site + 1 hybrid session for instructor."""
    now = datetime.now(TZ).replace(tzinfo=None)
    sessions = []

    on_site = SessionModel(
        title="E2E On-Site Session",
        description="Auto-created for Cypress web E2E",
        date_start=now + timedelta(days=1),
        date_end=now + timedelta(days=1, hours=1),
        session_type=SessionType.on_site,
        capacity=20,
        location="E2E Test Field",
        semester_id=semester.id,
        instructor_id=instructor.id,
        session_status="scheduled",
        quiz_unlocked=False,
    )
    db.add(on_site)

    hybrid = SessionModel(
        title="E2E Hybrid Session",
        description="Auto-created for Cypress web E2E (hybrid with quiz)",
        date_start=now + timedelta(days=2),
        date_end=now + timedelta(days=2, hours=1),
        session_type=SessionType.hybrid,
        capacity=20,
        location="E2E Test Field",
        semester_id=semester.id,
        instructor_id=instructor.id,
        session_status="scheduled",
        quiz_unlocked=False,
    )
    db.add(hybrid)

    db.commit()
    db.refresh(on_site)
    db.refresh(hybrid)
    sessions = [on_site, hybrid]
    return sessions


# ── Scenario runners ──────────────────────────────────────────────────────────

def scenario_baseline(db) -> list[str]:
    _truncate_transactional_data(db)
    lines = []
    for spec in _BASELINE_USERS:
        u = _upsert_user(db, spec, credit_balance=0)
        lines.append(f"  upserted user {spec['email']} ({spec['role'].value})")
    _upsert_user(db, _INACTIVE_STUDENT, credit_balance=0, is_active=False)
    lines.append(f"  upserted inactive user {_INACTIVE_STUDENT['email']}")
    _upsert_semester(db)
    lines.append(f"  upserted semester {_SEMESTER_CODE}")
    return lines


def scenario_student_no_dob(db) -> list[str]:
    lines = scenario_baseline(db)
    u = _upsert_user(db, _FRESH_STUDENT, credit_balance=50, clear_dob=True)
    lines.append(f"  upserted fresh student {_FRESH_STUDENT['email']} (no DOB)")
    return lines


def scenario_student_with_credits(db) -> list[str]:
    _truncate_transactional_data(db)
    lines = []
    for spec in _BASELINE_USERS:
        credit = 200 if spec["role"] == UserRole.STUDENT else 0
        u = _upsert_user(db, spec, credit_balance=credit)
        lines.append(f"  upserted user {spec['email']} credit_balance={credit}")
    u = _upsert_user(db, _FRESH_STUDENT, credit_balance=200, clear_dob=True)
    lines.append(f"  upserted fresh student {_FRESH_STUDENT['email']} credit_balance=200")
    _upsert_semester(db)
    lines.append(f"  upserted semester {_SEMESTER_CODE}")
    return lines


def scenario_session_ready(db) -> list[str]:
    lines = scenario_student_with_credits(db)
    # Mark the E2E student as onboarding_completed so /sessions and /calendar are accessible
    student_spec = next(s for s in _BASELINE_USERS if s["role"] == UserRole.STUDENT)
    _upsert_user(db, student_spec, credit_balance=200, onboarding_completed=True)
    lines.append(f"  set onboarding_completed=True for {student_spec['email']}")
    semester = db.query(Semester).filter(Semester.code == _SEMESTER_CODE).first()
    instructor = db.query(User).filter(User.email == "grandmaster@lfa.com").first()
    sessions = _create_sessions(db, semester, instructor)
    for s in sessions:
        lines.append(f"  created session id={s.id} '{s.title}' ({s.session_type.value})")
    return lines


# ── Entry point ───────────────────────────────────────────────────────────────

_SCENARIOS = {
    "baseline":             scenario_baseline,
    "student_no_dob":       scenario_student_no_dob,
    "student_with_credits": scenario_student_with_credits,
    "session_ready":        scenario_session_ready,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset E2E web test database")
    parser.add_argument("--scenario", choices=list(_SCENARIOS.keys()),
                        default="baseline", help="DB scenario to seed")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print(f"reset_e2e_web_db — scenario: {args.scenario}")
        lines = _SCENARIOS[args.scenario](db)
        for line in lines:
            print(line)
        print(f"Done ({len(lines)} operations).")
    except Exception as exc:
        db.rollback()
        print(f"✗ reset_e2e_web_db failed: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
