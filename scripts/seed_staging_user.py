"""Idempotent staging test user seed.

Usage (single user):
  DATABASE_URL=... STAGING_USER_PASSWORD=... python scripts/seed_staging_user.py

Override email/role/name via env vars:
  DATABASE_URL=... STAGING_USER_PASSWORD=... STAGING_USER_EMAIL=player@lfa-staging.io \
      STAGING_USER_ROLE=STUDENT STAGING_USER_NAME="Staging Player" python scripts/seed_staging_user.py

The password is read from STAGING_USER_PASSWORD — never hardcoded.
"""

import os
import sys

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DATABASE_URL = os.environ.get("DATABASE_URL")
PASSWORD = os.environ.get("STAGING_USER_PASSWORD")

if not DATABASE_URL or not PASSWORD:
    print("ERROR: Set DATABASE_URL and STAGING_USER_PASSWORD environment variables.")
    sys.exit(1)

EMAIL = os.environ.get("STAGING_USER_EMAIL", "staging-instructor@lfa-staging.io")
NAME = os.environ.get("STAGING_USER_NAME", "Staging Instructor")
ROLE_STR = os.environ.get("STAGING_USER_ROLE", "INSTRUCTOR").upper()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User, UserRole  # noqa: E402

try:
    role = UserRole[ROLE_STR]
except KeyError:
    valid = ", ".join(r.name for r in UserRole)
    print(f"ERROR: Invalid role '{ROLE_STR}'. Valid: {valid}")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
hashed = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

with Session(engine) as session:
    existing = session.query(User).filter(User.email == EMAIL).first()
    if existing:
        existing.password_hash = hashed
        existing.role = role
        existing.name = NAME
        session.commit()
        print(f"Updated staging user: {EMAIL} (role={role.name}, id={existing.id})")
    else:
        user = User(
            name=NAME,
            email=EMAIL,
            password_hash=hashed,
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()
        print(f"Created staging user: {EMAIL} (role={role.name}, id={user.id})")
