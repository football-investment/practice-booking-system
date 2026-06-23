"""Idempotent staging test user seed.

Usage:
  DATABASE_URL=postgresql://... STAGING_USER_PASSWORD=... python scripts/seed_staging_user.py

Creates (or updates) staging-smoke@lfa-staging.io via SQLAlchemy ORM so that
all model-level defaults (payment_verified, credit_balance, xp_balance, etc.)
are applied automatically without enumerating every NOT NULL column.
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

EMAIL = "staging-smoke@lfa-staging.io"
NAME = "Staging Smoke User"

# Add project root to path so `app` is importable when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User, UserRole  # noqa: E402

engine = create_engine(DATABASE_URL)
hashed = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

with Session(engine) as session:
    existing = session.query(User).filter(User.email == EMAIL).first()
    if existing:
        existing.password_hash = hashed
        session.commit()
        print(f"Updated password for existing staging user: {EMAIL}")
    else:
        user = User(
            name=NAME,
            email=EMAIL,
            password_hash=hashed,
            role=UserRole.INSTRUCTOR,
            is_active=True,
        )
        session.add(user)
        session.commit()
        print(f"Created staging user: {EMAIL} (role=INSTRUCTOR)")
