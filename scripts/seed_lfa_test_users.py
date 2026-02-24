#!/usr/bin/env python3
"""
Seed minimal @lfa-seed.hu users for CI/E2E testing

Creates 12 test users with @lfa-seed.hu emails + LFA_FOOTBALL_PLAYER licenses.
Idempotent: skips existing users.

Usage:
    DATABASE_URL="postgresql://..." python scripts/seed_lfa_test_users.py
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.user import User
from app.models.license import UserLicense
from app.core.security import get_password_hash


def create_lfa_test_users():
    """Create 12 @lfa-seed.hu test users with licenses"""

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # 12 test users for CI (minimum needed for 16-player tournament knockout)
    test_users = [
        ("player01", "Test Player 01", "STRIKER"),
        ("player02", "Test Player 02", "MIDFIELDER"),
        ("player03", "Test Player 03", "DEFENDER"),
        ("player04", "Test Player 04", "GOALKEEPER"),
        ("player05", "Test Player 05", "STRIKER"),
        ("player06", "Test Player 06", "MIDFIELDER"),
        ("player07", "Test Player 07", "DEFENDER"),
        ("player08", "Test Player 08", "STRIKER"),
        ("player09", "Test Player 09", "MIDFIELDER"),
        ("player10", "Test Player 10", "DEFENDER"),
        ("player11", "Test Player 11", "STRIKER"),
        ("player12", "Test Player 12", "MIDFIELDER"),
    ]

    # Position-based skill template (simplified)
    position_skills = {
        "STRIKER": {"finishing": 85.0, "dribbling": 80.0, "passing": 70.0},
        "MIDFIELDER": {"finishing": 65.0, "dribbling": 75.0, "passing": 85.0},
        "DEFENDER": {"finishing": 50.0, "dribbling": 60.0, "passing": 70.0},
        "GOALKEEPER": {"finishing": 40.0, "dribbling": 45.0, "passing": 60.0},
    }

    print("🌱 ═══════════════════════════════════════════════════════")
    print(f"🌱 LFA Test Users Seed  ({len(test_users)} @lfa-seed.hu users)")
    print("🌱 ═══════════════════════════════════════════════════════\n")

    created, skipped = 0, 0

    try:
        for username, full_name, position in test_users:
            email = f"{username}@lfa-seed.hu"

            # Check if user exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"   ⚠️  {email} already exists — SKIPPED")
                skipped += 1
                continue

            # Create user
            user = User(
                email=email,
                password_hash=get_password_hash("TestPass123!"),
                name=full_name,
                nickname=username,
                role="STUDENT",
                is_active=True,
                onboarding_completed=True,
                date_of_birth=datetime(2000, 1, 1),
                phone=f"+36201000{created:03d}",
            )
            db.add(user)
            db.flush()

            # Create license with baseline skills
            skills = position_skills.get(position, position_skills["MIDFIELDER"])
            now_iso = datetime.now(timezone.utc).isoformat()

            football_skills = {
                skill_key: {
                    "current_level": float(value),
                    "baseline": float(value),
                    "total_delta": 0.0,
                    "tournament_delta": 0.0,
                    "assessment_delta": 0.0,
                    "last_updated": now_iso,
                    "assessment_count": 0,
                    "tournament_count": 0,
                }
                for skill_key, value in skills.items()
            }

            license = UserLicense(
                user_id=user.id,
                specialization_type="LFA_FOOTBALL_PLAYER",
                is_active=True,
                started_at=datetime.now(timezone.utc),
                payment_verified=True,
                payment_verified_at=datetime.now(timezone.utc),
                football_skills=football_skills,
                average_motivation_score=75.0,
                motivation_last_assessed_at=datetime.now(timezone.utc),
                motivation_assessed_by=user.id,
            )
            db.add(license)
            created += 1
            print(f"   ✅ Created {email} ({position})")

        db.commit()
        print(f"\n✅ Seed complete: {created} created, {skipped} skipped")
        print("="*60)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during seed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_lfa_test_users()
