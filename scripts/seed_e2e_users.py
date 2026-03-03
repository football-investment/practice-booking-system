#!/usr/bin/env python3
"""
Seed the three users required by Cypress E2E tests.

Creates (or password-resets) exactly three accounts:
  admin@lfa.com          / AdminPass123!     → ADMIN
  grandmaster@lfa.com    / TestInstructor2026 → INSTRUCTOR
  rdias@manchestercity.com / TestPlayer2026   → STUDENT

Idempotent: existing users get their password updated to match CI credentials.
Run before Cypress tests whenever the DB is freshly migrated.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash


_USERS = [
    {
        "email":     "admin@lfa.com",
        "name":      "LFA Admin",
        "password":  "admin123",
        "role":      UserRole.ADMIN,
    },
    {
        "email":     "grandmaster@lfa.com",
        "name":      "Grand Master",
        "password":  "TestInstructor2026",
        "role":      UserRole.INSTRUCTOR,
    },
    {
        "email":     "rdias@manchestercity.com",
        "name":      "Ruben Dias",
        "password":  "TestPlayer2026",
        "role":      UserRole.STUDENT,
    },
]


def seed_e2e_users() -> bool:
    db = SessionLocal()
    try:
        for spec in _USERS:
            existing = db.query(User).filter(User.email == spec["email"]).first()
            if existing:
                existing.password_hash = get_password_hash(spec["password"])
                existing.is_active = True
                db.commit()
                print(f"✓ updated  {spec['email']} ({spec['role'].value})")
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
                print(f"✓ created  {spec['email']} ({spec['role'].value})")
        return True
    except Exception as exc:
        db.rollback()
        print(f"✗ seed_e2e_users failed: {exc}", file=sys.stderr)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding E2E test users...")
    ok = seed_e2e_users()
    sys.exit(0 if ok else 1)
