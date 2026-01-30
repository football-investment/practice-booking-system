"""
E2E Test Fixtures - Deterministic Test Data Layer

This module provides DETERMINISTIC fixtures for E2E testing.
All credentials are fixed (not timestamp-based) for reproducibility.

Key principles:
- API-first: Create data via endpoints, not direct DB manipulation
- Deterministic: Fixed emails like tournament_player_1@test.local
- Self-contained: Each test cleans up its own data
- Realistic: Mirrors production user flows

Pattern: fixture creates → test uses → fixture cleans up
"""

import pytest
import requests
from typing import Dict, Any, Generator
from datetime import date, timedelta, datetime
import os
import time

import psycopg2

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ============================================================================
# DETERMINISTIC CREDENTIALS (Priority 2 Requirement)
# ============================================================================

ADMIN_CREDENTIALS = {
    "email": "admin@lfa.com",
    "password": "admin123"
}

INSTRUCTOR_CREDENTIALS = {
    "email": "tournament_instructor@example.com",
    "password": "Instructor123!",
    "name": "Tournament Instructor",
    "role": "instructor",
    "date_of_birth": "1985-06-15T00:00:00"
}

PLAYER_CREDENTIALS = [
    {
        "email": "tournament_player_1@example.com",
        "password": "Player123!",
        "name": "Player One",
        "role": "student",
        "date_of_birth": "2005-01-15T00:00:00",
        "specialization": "LFA_FOOTBALL_PLAYER"
    },
    {
        "email": "tournament_player_2@example.com",
        "password": "Player123!",
        "name": "Player Two",
        "role": "student",
        "date_of_birth": "2005-02-20T00:00:00",
        "specialization": "LFA_FOOTBALL_PLAYER"
    },
    {
        "email": "tournament_player_3@example.com",
        "password": "Player123!",
        "name": "Player Three",
        "role": "student",
        "date_of_birth": "2005-03-25T00:00:00",
        "specialization": "LFA_FOOTBALL_PLAYER"
    },
    {
        "email": "tournament_player_4@example.com",
        "password": "Player123!",
        "name": "Player Four",
        "role": "student",
        "date_of_birth": "2005-04-10T00:00:00",
        "specialization": "LFA_FOOTBALL_PLAYER"
    },
    {
        "email": "tournament_player_5@example.com",
        "password": "Player123!",
        "name": "Player Five",
        "role": "student",
        "date_of_birth": "2005-05-18T00:00:00",
        "specialization": "LFA_FOOTBALL_PLAYER"
    }
]


# ============================================================================
# HELPER FUNCTIONS FOR API CALLS
# ============================================================================

def get_admin_token() -> str:
    """Get admin authentication token."""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json=ADMIN_CREDENTIALS
    )
    response.raise_for_status()
    return response.json()["access_token"]


def poll_tournament_status(
    token: str,
    tournament_id: int,
    expected_status: str,
    timeout_seconds: float = 10.0,
    poll_interval_seconds: float = 0.5
) -> bool:
    """
    Poll tournament status until it reaches expected value or timeout.

    This handles race conditions where DB commits may not be immediately visible.
    Mirrors real frontend behavior where UI polls for status updates.

    Args:
        token: Admin auth token
        tournament_id: Tournament ID to poll
        expected_status: Expected status value (e.g., "SEEKING_INSTRUCTOR")
        timeout_seconds: Maximum time to wait (default: 10 seconds)
        poll_interval_seconds: Time between polls (default: 0.5 seconds)

    Returns:
        True if status reached expected value, False if timeout

    Example:
        if poll_tournament_status(admin_token, tournament_id, "SEEKING_INSTRUCTOR"):
            print("Status confirmed!")
    """
    start_time = time.time()
    attempts = 0

    while time.time() - start_time < timeout_seconds:
        attempts += 1

        try:
            # Use status-history endpoint since GET /tournaments/{id} doesn't exist
            response = requests.get(
                f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/status-history",
                headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                history_data = response.json()
                current_status = history_data.get("current_status")

                if current_status == expected_status:
                    print(f"    ✅ Status confirmed: {expected_status} (after {attempts} attempts, {time.time() - start_time:.2f}s)")
                    return True

                print(f"    ⏳ Polling... Current: {current_status}, Expected: {expected_status} (attempt {attempts})")

        except Exception as e:
            print(f"    ⚠️  Poll attempt {attempts} failed: {e}")

        time.sleep(poll_interval_seconds)

    print(f"    ❌ Timeout: Status did not reach {expected_status} after {timeout_seconds}s ({attempts} attempts)")
    return False


def create_user_via_api(token: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a user via admin API.

    Args:
        token: Admin auth token
        user_data: User creation data (email, name, password, role, etc.)

    Returns:
        User object with id, email, and original password field added
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json=user_data
    )

    if response.status_code == 400 and "already exists" in response.text:
        # User already exists - try to login
        login_response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]}
        )

        if login_response.status_code == 200:
            user_token = login_response.json()["access_token"]
            # Get user profile
            profile_response = requests.get(
                f"{API_BASE_URL}/api/v1/users/me",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            profile_response.raise_for_status()
            user = profile_response.json()
            user["password"] = user_data["password"]  # Add password for test use
            return user
        elif login_response.status_code == 400 and "Inactive user" in login_response.text:
            # User exists but is inactive - need to reactivate it
            print(f"⚠️  User {user_data['email']} exists but is inactive. Attempting to reactivate...")

            # Get all users via admin API and find the inactive user
            users_response = requests.get(
                f"{API_BASE_URL}/api/v1/users",
                headers={"Authorization": f"Bearer {token}"}
            )

            if users_response.status_code == 200:
                users_data = users_response.json()
                users_list = users_data.get("users", [])
                inactive_user = next((u for u in users_list if u.get("email") == user_data["email"]), None)

                if inactive_user:
                    # Reactivate the user by updating it
                    update_data = {
                        "is_active": True,
                        "name": user_data.get("name"),
                        "role": user_data.get("role")
                    }

                    reactivate_response = requests.patch(
                        f"{API_BASE_URL}/api/v1/users/{inactive_user['id']}",
                        headers={"Authorization": f"Bearer {token}"},
                        json=update_data
                    )

                    if reactivate_response.status_code == 200:
                        print(f"✅ Reactivated user {user_data['email']}")
                        user = reactivate_response.json()
                        user["password"] = user_data["password"]  # Add password for test use
                        return user
                    else:
                        print(f"❌ Reactivation failed: {reactivate_response.status_code} {reactivate_response.text}")

    response.raise_for_status()
    user = response.json()
    user["password"] = user_data["password"]  # Add password for test use
    return user


def delete_user_via_api(token: str, user_id: int) -> None:
    """Delete a user via admin API."""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Ignore 404 - user might already be deleted
        if response.status_code not in [200, 204, 404]:
            print(f"Warning: Failed to delete user {user_id}: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Warning: Exception deleting user {user_id}: {e}")


def create_tournament_via_api(
    token: str,
    name: str = None,
    specialization_type: str = "LFA_FOOTBALL_PLAYER",
    start_date: date = None,
    end_date: date = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a tournament via the new lifecycle API.

    Args:
        token: Admin auth token
        name: Tournament name (auto-generated if None)
        specialization_type: Tournament type
        start_date: Start date (tomorrow if None)
        end_date: End date (next week if None)
        **kwargs: Additional tournament fields

    Returns:
        Tournament creation response
    """
    if start_date is None:
        start_date = date.today() + timedelta(days=1)
    if end_date is None:
        end_date = date.today() + timedelta(days=7)
    if name is None:
        # Add microsecond timestamp to ensure uniqueness
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        name = f"Test Tournament {timestamp}"

    tournament_data = {
        "name": name,
        "specialization_type": specialization_type,
        "age_group": kwargs.get("age_group", "YOUTH"),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "description": kwargs.get("description", "E2E test tournament")
    }
    tournament_data.update(kwargs)

    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments",
        headers={"Authorization": f"Bearer {token}"},
        json=tournament_data
    )
    response.raise_for_status()
    return response.json()


def delete_tournament_via_api(token: str, tournament_id: int) -> None:
    """Delete a tournament via API (if endpoint exists)."""
    try:
        # Note: DELETE endpoint may not exist yet in Cycle 1
        response = requests.delete(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code not in [200, 204, 404, 405]:
            print(f"Warning: Failed to delete tournament {tournament_id}: {response.status_code}")
    except Exception as e:
        print(f"Warning: Exception deleting tournament {tournament_id}: {e}")


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def admin_token() -> str:
    """
    Admin authentication token (session scope - reused across tests).

    Returns:
        JWT token for admin@lfa.com
    """
    return get_admin_token()


@pytest.fixture(scope="function")
def test_instructor(admin_token: str) -> Generator[Dict[str, Any], None, None]:
    """
    Create deterministic instructor user with:
    - Fixed email: tournament_instructor@example.com
    - Role: INSTRUCTOR
    - Active LFA_COACH license
    - Onboarding completed

    Returns:
        User dict with id, email, password, name, role

    Cleanup:
        Deletes user after test
    """
    instructor = create_user_via_api(admin_token, INSTRUCTOR_CREDENTIALS)

    # Add LFA_COACH license via direct DB insert (E2E test workaround)
    # This is acceptable in E2E tests as we need deterministic setup
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()
    try:
        # Check if license already exists
        cur.execute("""
            SELECT id FROM user_licenses
            WHERE user_id = %s AND specialization_type = 'LFA_COACH'
        """, (instructor["id"],))
        existing = cur.fetchone()

        if existing:
            # Update existing license
            cur.execute("""
                UPDATE user_licenses
                SET is_active = true, payment_verified = true, onboarding_completed = true, payment_verified_at = NOW()
                WHERE user_id = %s AND specialization_type = 'LFA_COACH'
            """, (instructor["id"],))
            print(f"✅ LFA_COACH license updated for instructor {instructor['email']}")
        else:
            # Insert new license with all required fields
            cur.execute("""
                INSERT INTO user_licenses (
                    user_id, specialization_type, current_level, max_achieved_level,
                    started_at, is_active, payment_verified, onboarding_completed,
                    payment_verified_at, renewal_cost, credit_balance, credit_purchased
                )
                VALUES (%s, 'LFA_COACH', 1, 1, NOW(), true, true, true, NOW(), 0, 0, 0)
            """, (instructor["id"],))
            print(f"✅ LFA_COACH license created for instructor {instructor['email']}")

        conn.commit()
    except Exception as e:
        print(f"⚠️  Warning: Failed to create LFA_COACH license: {e}")
    finally:
        cur.close()
        conn.close()

    yield instructor
    delete_user_via_api(admin_token, instructor["id"])


@pytest.fixture(scope="function")
def test_players(admin_token: str) -> Generator[list[Dict[str, Any]], None, None]:
    """
    Create 5 deterministic player users with:
    - Fixed emails: tournament_player_1@test.local to tournament_player_5@test.local
    - Role: STUDENT
    - Specialization: LFA_FOOTBALL_PLAYER
    - Active LFA_FOOTBALL_PLAYER license
    - 1000 credits for enrollments

    Returns:
        List of 5 user dicts

    Cleanup:
        Deletes all players after test
    """
    players = []
    for player_creds in PLAYER_CREDENTIALS:
        player = create_user_via_api(admin_token, player_creds)

        # Add LFA_FOOTBALL_PLAYER license + credits via direct DB insert
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        cur = conn.cursor()
        try:
            # Check if license already exists
            cur.execute("""
                SELECT id FROM user_licenses
                WHERE user_id = %s AND specialization_type = 'LFA_FOOTBALL_PLAYER'
            """, (player["id"],))
            existing = cur.fetchone()

            if existing:
                # Update existing license
                cur.execute("""
                    UPDATE user_licenses
                    SET is_active = true, payment_verified = true, onboarding_completed = true, payment_verified_at = NOW()
                    WHERE user_id = %s AND specialization_type = 'LFA_FOOTBALL_PLAYER'
                """, (player["id"],))
                print(f"✅ LFA_FOOTBALL_PLAYER license updated for player {player['email']}")
            else:
                # Insert new license
                cur.execute("""
                    INSERT INTO user_licenses (
                        user_id, specialization_type, current_level, max_achieved_level,
                        started_at, is_active, payment_verified, onboarding_completed,
                        payment_verified_at, renewal_cost, credit_balance, credit_purchased
                    )
                    VALUES (%s, 'LFA_FOOTBALL_PLAYER', 1, 1, NOW(), true, true, true, NOW(), 0, 0, 0)
                """, (player["id"],))
                print(f"✅ LFA_FOOTBALL_PLAYER license created for player {player['email']}")

            # Give player 1000 credits for tournament enrollment
            cur.execute("""
                UPDATE users
                SET credit_balance = 1000
                WHERE id = %s
            """, (player["id"],))
            print(f"✅ 1000 credits added to player {player['email']}")

            conn.commit()
        except Exception as e:
            print(f"⚠️  Warning: Failed to set up player {player['email']}: {e}")
        finally:
            cur.close()
            conn.close()

        players.append(player)

    yield players

    for player in players:
        delete_user_via_api(admin_token, player["id"])


@pytest.fixture(scope="function")
def create_tournament(admin_token: str):
    """
    Tournament factory fixture (function scope).

    Usage:
        def test_something(create_tournament):
            tournament = create_tournament(
                name="My Test Tournament",
                specialization_type="LFA_FOOTBALL_PLAYER",
                start_date=date.today() + timedelta(days=3)
            )
            assert tournament["status"] == "DRAFT"

    Returns:
        Factory function that creates tournaments and tracks them for cleanup
    """
    created_tournaments = []

    def _create(**kwargs) -> Dict[str, Any]:
        tournament = create_tournament_via_api(admin_token, **kwargs)
        created_tournaments.append(tournament["tournament_id"])
        return tournament

    yield _create

    # Cleanup all created tournaments
    for tournament_id in created_tournaments:
        delete_tournament_via_api(admin_token, tournament_id)


@pytest.fixture(scope="function")
def tournament_in_draft(create_tournament) -> Dict[str, Any]:
    """
    Quick fixture: Tournament in DRAFT status.

    Returns:
        Tournament response dict
    """
    return create_tournament(name="Draft Tournament")


@pytest.fixture(scope="function")
def tournament_with_instructor(
    create_tournament,
    test_instructor: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quick fixture: Tournament with instructor assigned (READY_FOR_ENROLLMENT status).

    Note: In Cycle 1, tournaments start in DRAFT. This fixture will need updating
    in Cycle 2 to properly transition through the instructor assignment flow.

    Returns:
        Dict with 'tournament' and 'instructor' keys
    """
    tournament = create_tournament(name="Tournament with Instructor")

    # TODO: In Cycle 2, add instructor assignment flow here
    # For now, just return tournament in DRAFT status

    return {
        "tournament": tournament,
        "instructor": test_instructor
    }


@pytest.fixture(scope="function")
def complete_tournament_setup(
    create_tournament,
    test_instructor: Dict[str, Any],
    test_players: list[Dict[str, Any]]
) -> Generator[Dict[str, Any], None, None]:
    """
    Complete tournament setup for integration testing:
    - Tournament created
    - Instructor assigned (TODO: Cycle 2)
    - Players enrolled (TODO: Cycle 2)
    - Sessions created (TODO: Cycle 2)

    Returns:
        Dict with tournament, instructor, players keys
    """
    tournament = create_tournament(name="Complete Tournament Setup")

    # TODO: In Cycle 2+, add:
    # - Instructor assignment + acceptance
    # - Session creation
    # - Player enrollment
    # - Status transitions

    yield {
        "tournament": tournament,
        "instructor": test_instructor,
        "players": test_players
    }

    # Cleanup handled by individual fixtures
