"""
Lifecycle test suite conftest.

Overrides the root conftest base_url fixture (which returns the Streamlit URL)
with the FastAPI API URL. This prevents pytest-base-url from treating all
lifecycle tests as "destructive against a sensitive environment" (localhost:8501).

The production-flow tests (T09) write real data — they ARE destructive by design.
The base_url here tells the pytest-base-url sensitive-URL guard to evaluate
against localhost:8000 (the API), not localhost:8501 (Streamlit).
"""
import os
import sys
from pathlib import Path

# Add project root to Python path for app imports (CI compatibility)
# tests_e2e/lifecycle/conftest.py -> tests_e2e/lifecycle -> tests_e2e -> project_root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime
from app.database import SessionLocal
from app.models.user import User
from app.models.license import UserLicense
from app.core.security import get_password_hash


@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    """FastAPI backend URL — used by pytest-base-url for sensitive-URL evaluation."""
    return os.environ.get("API_URL", "http://localhost:8000")


@pytest.fixture(scope="function")
def test_players_12():
    """
    Create 12 test players with LFA_FOOTBALL_PLAYER licenses and baseline skills.
    Function-scoped to ensure test isolation. Cleanup after test completes.

    Returns: List[dict] with keys: db_id, email, password (compatible with _load_star_players format)
    """
    import uuid
    from datetime import timezone

    db = SessionLocal()
    created_player_ids = []
    created_license_ids = []
    players_data = []

    try:
        # Create 12 players with unique emails
        for i in range(12):
            uniq = uuid.uuid4().hex[:6]
            email = f"skill_test_p{i}_{uniq}@e2e.com"
            password = "testpass123"

            # Create player user
            player = User(
                email=email,
                password_hash=get_password_hash(password),
                name=f"Skill Test Player {i}",
                nickname=f"STP{i}",
                role="STUDENT",
                is_active=True,
                onboarding_completed=True,
                date_of_birth=datetime(2000, 1, 1),
                phone=f"+3620100{i:04d}"
            )
            db.add(player)
            db.flush()
            created_player_ids.append(player.id)

            # Create LFA_FOOTBALL_PLAYER license with baseline skills
            baseline_skills = {
                "finishing": {
                    "baseline": 50.0,
                    "current_level": 50.0,
                    "tournament_delta": 0.0,
                    "total_delta": 0.0,
                    "tournament_count": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                },
                "dribbling": {
                    "baseline": 50.0,
                    "current_level": 50.0,
                    "tournament_delta": 0.0,
                    "total_delta": 0.0,
                    "tournament_count": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                },
                "passing": {
                    "baseline": 50.0,
                    "current_level": 50.0,
                    "tournament_delta": 0.0,
                    "total_delta": 0.0,
                    "tournament_count": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            }
            license = UserLicense(
                user_id=player.id,
                specialization_type="LFA_FOOTBALL_PLAYER",
                is_active=True,
                started_at=datetime.now(timezone.utc),
                football_skills=baseline_skills
            )
            db.add(license)
            db.flush()
            created_license_ids.append(license.id)

            # Store player data in _load_star_players compatible format
            players_data.append({
                "db_id": player.id,
                "email": email,
                "password": password
            })

        db.commit()
        print(f"\n   🏗️  Created {len(created_player_ids)} skill progression test players")

    except Exception as exc:
        db.rollback()
        print(f"   ❌ Error creating test players: {exc}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

    # Yield player data to test
    yield players_data

    # Cleanup: Delete players and licenses after test
    db = SessionLocal()
    try:
        # Delete licenses first (foreign key constraint)
        for lic_id in created_license_ids:
            lic = db.query(UserLicense).filter(UserLicense.id == lic_id).first()
            if lic:
                db.delete(lic)

        # Delete players
        for player_id in created_player_ids:
            player = db.query(User).filter(User.id == player_id).first()
            if player:
                db.delete(player)

        db.commit()
        print(f"\n   🧹 Cleaned up {len(created_player_ids)} test players")

    except Exception as cleanup_err:
        db.rollback()
        print(f"   ⚠️  Cleanup warning: {cleanup_err}")
    finally:
        db.close()
