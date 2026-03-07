#!/usr/bin/env python3
"""
CI E2E Environment Initializer — single source of truth for E2E baseline data.

Run by cypress-tests.yml BEFORE starting the backend.  Idempotent: safe to
re-run on an already-seeded DB (updates passwords / semester dates in place).

────────────────────────────────────────────────────────────────────────────
REQUIRED BASELINE
────────────────────────────────────────────────────────────────────────────

Users (3):
  ┌──────────────────────────────┬────────────────────┬──────────────┐
  │ email                        │ password           │ role         │
  ├──────────────────────────────┼────────────────────┼──────────────┤
  │ admin@lfa.com                │ admin123           │ ADMIN        │
  │ grandmaster@lfa.com          │ TestInstructor2026 │ INSTRUCTOR   │
  │ rdias@manchestercity.com     │ TestPlayer2026     │ STUDENT      │
  └──────────────────────────────┴────────────────────┴──────────────┘
  Cypress env vars (cypress-tests.yml) must mirror this table exactly.

Semesters (1):
  ┌────────────────┬──────────────────────────┬──────────────────────────────┐
  │ code           │ start_date               │ end_date                     │
  ├────────────────┼──────────────────────────┼──────────────────────────────┤
  │ E2E-CI-2026    │ today − 180 days         │ today + 180 days             │
  └────────────────┴──────────────────────────┴──────────────────────────────┘
  Purpose: SessionCreate.semester_id is required; the CI DB starts empty.
  The rolling ±180-day window ensures session dates (e.g. "7 days from now")
  always fall inside the semester boundary check in the backend.

────────────────────────────────────────────────────────────────────────────
HOW TO UPDATE
────────────────────────────────────────────────────────────────────────────
Add or change baseline records in _USERS / _SEMESTERS below, then keep the
corresponding Cypress env vars in .github/workflows/cypress-tests.yml in sync.
"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.semester import Semester
from app.core.security import get_password_hash


# ── Baseline specification ────────────────────────────────────────────────────

_USERS = [
    {
        "email":    "admin@lfa.com",
        "name":     "LFA Admin",
        "password": "admin123",
        "role":     UserRole.ADMIN,
    },
    {
        "email":    "grandmaster@lfa.com",
        "name":     "Grand Master",
        "password": "TestInstructor2026",
        "role":     UserRole.INSTRUCTOR,
    },
    {
        "email":    "rdias@manchestercity.com",
        "name":     "Ruben Dias",
        "password": "TestPlayer2026",
        "role":     UserRole.STUDENT,
    },
]

_SEMESTERS = [
    {
        "code": "E2E-CI-2026",
        "name": "E2E CI Test Semester",
        # start/end derived at runtime so the window is always current
    },
]


# ── Seed logic ────────────────────────────────────────────────────────────────

def _seed(db) -> list[str]:
    """Seed all baseline records.  Returns list of human-readable status lines."""
    lines = []

    # Users
    for spec in _USERS:
        existing = db.query(User).filter(User.email == spec["email"]).first()
        if existing:
            existing.password_hash = get_password_hash(spec["password"])
            existing.is_active = True
            db.commit()
            lines.append(f"  updated  user     {spec['email']} ({spec['role'].value})")
        else:
            user = User(
                name=spec["name"],
                email=spec["email"],
                password_hash=get_password_hash(spec["password"]),
                role=spec["role"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            lines.append(f"  created  user     {spec['email']} ({spec['role'].value})")

    # Semesters
    today = date.today()
    for spec in _SEMESTERS:
        sem = db.query(Semester).filter(Semester.code == spec["code"]).first()
        if sem:
            sem.start_date = today - timedelta(days=180)
            sem.end_date   = today + timedelta(days=180)
            db.commit()
            lines.append(
                f"  updated  semester {spec['code']} "
                f"({today - timedelta(days=180)} → {today + timedelta(days=180)})"
            )
        else:
            sem = Semester(
                code=spec["code"],
                name=spec["name"],
                start_date=today - timedelta(days=180),
                end_date=today + timedelta(days=180),
            )
            db.add(sem)
            db.commit()
            lines.append(
                f"  created  semester {spec['code']} "
                f"({today - timedelta(days=180)} → {today + timedelta(days=180)})"
            )

    return lines


def init_e2e_environment() -> bool:
    """Idempotently seed the E2E baseline.  Returns True on success."""
    db = SessionLocal()
    try:
        print("E2E baseline initialization:")
        lines = _seed(db)
        for line in lines:
            print(line)
        print(f"Done — {len(_USERS)} user(s), {len(_SEMESTERS)} semester(s) ready.")
        return True
    except Exception as exc:
        db.rollback()
        print(f"✗ init_e2e_environment failed: {exc}", file=sys.stderr)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    ok = init_e2e_environment()
    sys.exit(0 if ok else 1)
