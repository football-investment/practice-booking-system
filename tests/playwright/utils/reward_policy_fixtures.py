"""
Reward Policy E2E Test Fixtures

Creates multi-user test environment for reward policy testing:
- 1 admin
- 5 players (different age groups)
- Tournament with multiple games/sessions
- Rankings and results
"""

import requests
import pytest
from typing import Dict, Any, List, Generator
from datetime import datetime, timedelta
import os


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ============================================================================
# Multi-User Creation Helpers
# ============================================================================

def create_admin_token() -> str:
    """Get admin authentication token."""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_instructor_user(token: str) -> Dict[str, Any]:
    """
    Create instructor user with LFA_COACH license.

    Returns:
        Dict with instructor details including email, password, id, token
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

    instructor_data = {
        "email": f"tournament_instructor_{timestamp}@test.com",
        "name": f"Tournament Instructor {timestamp}",
        "password": "InstructorPass123!",
        "role": "instructor",  # ✅ lowercase role value
        "date_of_birth": "1985-01-01T00:00:00",
        "specialization": "LFA_COACH"
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json=instructor_data
    )
    if response.status_code != 200:
        print(f"❌ Failed to create instructor: {response.status_code}")
        print(f"Response: {response.json()}")
    response.raise_for_status()

    instructor = response.json()
    instructor["password"] = instructor_data["password"]

    # ✅ CRITICAL FIX: Directly insert LFA_COACH license via database
    import psycopg2
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # 1. Activate user
    cur.execute(
        "UPDATE users SET is_active = true WHERE id = %s",
        (instructor['id'],)
    )

    # 2. Insert LFA_COACH license (required for instructor assignment validation)
    cur.execute(
        """
        INSERT INTO user_licenses (
            user_id,
            specialization_type,
            current_level,
            max_achieved_level,
            started_at,
            payment_verified,
            is_active,
            onboarding_completed,
            payment_verified_at,
            renewal_cost,
            credit_balance,
            credit_purchased
        )
        VALUES (%s, 'LFA_COACH', 1, 1, NOW(), true, true, true, NOW(), 0, 0, 0)
        RETURNING id
        """,
        (instructor['id'],)
    )
    license_id = cur.fetchone()[0]
    instructor["license_id"] = license_id

    conn.commit()
    cur.close()
    conn.close()

    # Get instructor token for API calls
    login_response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"email": instructor["email"], "password": instructor["password"]}
    )
    instructor["token"] = login_response.json()["access_token"]

    return instructor


def instructor_accepts_assignment(instructor_token: str, tournament_id: int) -> Dict[str, Any]:
    """
    Instructor accepts tournament assignment via API (works for both scenarios).

    Uses: POST /api/v1/tournaments/{id}/instructor-assignment/accept

    Actions:
    - Updates semester.master_instructor_id
    - Updates semester.status → READY_FOR_ENROLLMENT
    - Updates all sessions.instructor_id

    Returns:
        API response with tournament details
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-assignment/accept",
        headers={"Authorization": f"Bearer {instructor_token}"}
    )
    response.raise_for_status()
    return response.json()


def instructor_applies_to_tournament(
    instructor_token: str,
    tournament_id: int,
    application_message: str = "I would like to lead this tournament"
) -> Dict[str, Any]:
    """
    SCENARIO 2: Instructor applies to tournament.

    Uses: POST /api/v1/tournaments/{id}/instructor-applications

    Actions:
    - Creates InstructorAssignmentRequest with status PENDING
    - Records application_message

    Returns:
        Application details with application_id
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications",
        headers={"Authorization": f"Bearer {instructor_token}"},
        json={"application_message": application_message}
    )
    response.raise_for_status()
    return response.json()


def admin_approves_instructor_application(
    admin_token: str,
    tournament_id: int,
    application_id: int,
    response_message: str = "Application approved"
) -> Dict[str, Any]:
    """
    SCENARIO 2: Admin approves instructor application.

    Uses: POST /api/v1/tournaments/{id}/instructor-applications/{id}/approve

    Actions:
    - Updates application status to ACCEPTED
    - Records responded_at timestamp
    - Records optional response_message

    Note: After approval, instructor must still call instructor_accepts_assignment()

    Returns:
        Approval details
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{application_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"response_message": response_message}
    )
    response.raise_for_status()
    return response.json()


def admin_directly_assigns_instructor(
    admin_token: str,
    tournament_id: int,
    instructor_id: int,
    assignment_message: str = "You have been selected to lead this tournament"
) -> Dict[str, Any]:
    """
    SCENARIO 1: Admin directly assigns instructor without application workflow.

    Uses: POST /api/v1/tournaments/{id}/direct-assign-instructor

    Actions:
    - Creates InstructorAssignmentRequest with status ACCEPTED immediately
    - Records assignment_message from admin

    Note: After direct assignment, instructor must still call instructor_accepts_assignment()

    Returns:
        Assignment details with assignment_id
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/direct-assign-instructor",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "instructor_id": instructor_id,
            "assignment_message": assignment_message
        }
    )
    response.raise_for_status()
    return response.json()


def admin_declines_instructor_application(
    admin_token: str,
    tournament_id: int,
    application_id: int,
    decline_message: str = "Thank you for applying. We selected another candidate."
) -> Dict[str, Any]:
    """
    Admin declines instructor application.

    Uses: POST /api/v1/tournaments/{id}/instructor-applications/{id}/decline

    Actions:
    - Updates application status to DECLINED
    - Records declined_at timestamp
    - Records optional decline_message

    Returns:
        Decline confirmation
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{application_id}/decline",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"decline_message": decline_message}
    )
    response.raise_for_status()
    return response.json()


def create_multiple_instructors(admin_token: str, count: int = 4) -> List[Dict[str, Any]]:
    """
    Create multiple instructor users with LFA_COACH licenses.

    Args:
        admin_token: Admin auth token
        count: Number of instructors to create (default: 4)

    Returns:
        List of instructor dicts with email, password, id, token
    """
    instructors = []
    for i in range(count):
        instructor = create_instructor_user(admin_token)
        instructor["index"] = i + 1
        instructors.append(instructor)
        print(f"     ✅ Instructor {i+1}/{count}: {instructor['email']}")

    return instructors


def create_first_team_players(admin_token: str, count: int = 3) -> List[Dict[str, Any]]:
    """
    Create First Team players with @f1rstteamfc.hu email addresses.

    Business Rule: First Team players have emails ending with @f1rstteamfc.hu

    Args:
        admin_token: Admin auth token
        count: Number of First Team players to create (default: 3)

    Returns:
        List of player dicts with email, password, id, token
    """
    import psycopg2
    players = []

    for i in range(count):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        player_data = {
            "email": f"player{i+1}.{timestamp}@f1rstteamfc.hu",  # First Team email pattern
            "name": f"First Team Player {i+1}",
            "password": "TestPass123!",  # Standard test password for enrollment compatibility
            "role": "student",
            "date_of_birth": "2000-01-01T00:00:00",
            "specialization": "LFA_PLAYER"
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=player_data
        )
        response.raise_for_status()

        player = response.json()
        player["password"] = player_data["password"]

        # Activate user via database
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_active = true, credits = 1000 WHERE id = %s", (player['id'],))
        conn.commit()
        cur.close()
        conn.close()

        # Get player token
        login_response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": player["email"], "password": player["password"]}
        )
        player["token"] = login_response.json()["access_token"]

        players.append(player)
        print(f"     ✅ First Team Player {i+1}/{count}: {player['email']}")

    return players


def create_coupon(admin_token: str, code: str, credits: int, max_uses: int = None) -> Dict[str, Any]:
    """
    Create a coupon that awards credits to users.

    Args:
        admin_token: Admin auth token
        code: Coupon code (will be uppercased)
        credits: Amount of credits to award
        max_uses: Maximum number of times coupon can be used (None = unlimited)

    Returns:
        Coupon details
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/admin/coupons",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "code": code.upper(),
            "type": "credits",
            "discount_value": credits,
            "description": f"Bonus {credits} credits",
            "is_active": True,
            "expires_at": None,
            "max_uses": max_uses
        }
    )
    response.raise_for_status()
    return response.json()


def apply_coupon(user_token: str, code: str) -> Dict[str, Any]:
    """
    Apply a coupon code to user's account.

    Args:
        user_token: User auth token
        code: Coupon code to apply

    Returns:
        Application result with credits awarded and new balance
    """
    response = requests.post(
        f"{API_BASE_URL}/api/v1/coupons/apply",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"code": code}
    )
    response.raise_for_status()
    return response.json()


def admin_assigns_instructor(admin_token: str, tournament_id: int, instructor_id: int) -> Dict[str, Any]:
    """
    DEPRECATED: Use admin_directly_assigns_instructor() instead.

    Admin directly assigns instructor to tournament (old PATCH method).

    Note: Even with admin assignment, instructor MUST still call accept API
    to properly set master_instructor_id and session instructor_ids.

    Returns:
        Tournament update response
    """
    response = requests.patch(
        f"{API_BASE_URL}/api/v1/semesters/{tournament_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"master_instructor_id": instructor_id}
    )
    response.raise_for_status()
    return response.json()


def create_attendance_records(
    admin_token: str,
    tournament_id: int,
    player_ids: List[int]
) -> Dict[str, Any]:
    """
    Create attendance records for tournament sessions.

    Required for production validation: distribute_rewards() checks attendance_count > 0.

    Args:
        admin_token: Admin auth token
        tournament_id: Tournament (semester) ID
        player_ids: List of player user IDs to mark as PRESENT

    Returns:
        Dict with attendance count created
    """
    import psycopg2
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # Get all sessions for this tournament
    cur.execute(
        "SELECT id FROM sessions WHERE semester_id = %s ORDER BY date_start",
        (tournament_id,)
    )
    session_ids = [row[0] for row in cur.fetchall()]

    attendance_count = 0

    # Mark all players as PRESENT in first session (minimum requirement)
    # In production, instructor would mark attendance for ALL sessions
    if session_ids:
        first_session_id = session_ids[0]
        for player_id in player_ids:
            # First, get or create booking for this session
            cur.execute(
                """
                SELECT id FROM bookings
                WHERE session_id = %s AND user_id = %s
                LIMIT 1
                """,
                (first_session_id, player_id)
            )
            booking_row = cur.fetchone()

            if booking_row:
                booking_id = booking_row[0]
                # Insert attendance record (status must be lowercase: 'present')
                cur.execute(
                    """
                    INSERT INTO attendance (session_id, user_id, booking_id, status, check_in_time)
                    VALUES (%s, %s, %s, 'present', NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    (first_session_id, player_id, booking_id)
                )
                attendance_count += 1

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Attendance records created", "count": attendance_count, "sessions": len(session_ids)}


def create_player_users(token: str, count: int = 5, age_group: str = "AMATEUR") -> List[Dict[str, Any]]:
    """
    Create multiple player users with different characteristics.

    Args:
        token: Admin auth token
        count: Number of players (default 5)
        age_group: Age group for tournament (PRE, YOUTH, AMATEUR, PRO)

    Returns:
        List of player dicts with email, password, id, initial_xp, initial_credits
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    players = []

    for i in range(count):
        player_data = {
            "email": f"tournament_player_{timestamp}_{i}@test.com",
            "name": f"Tournament Player {i+1}",
            "password": "TestPass123!",
            "role": "student",  # ✅ FIXED: lowercase role value
            "date_of_birth": "2000-01-01T00:00:00",  # ✅ FIXED: ISO datetime format
            "specialization": "LFA_FOOTBALL_PLAYER"
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json=player_data
        )
        response.raise_for_status()

        user = response.json()
        user["password"] = player_data["password"]

        # Get current XP and credits for validation later
        user_detail_response = requests.get(
            f"{API_BASE_URL}/api/v1/users/{user['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        user_detail = user_detail_response.json()
        user["initial_xp"] = user_detail.get("total_xp", 0)
        user["initial_credits"] = user_detail.get("credit_balance", 0)

        # ✅ CRITICAL FIX: Directly insert license via database
        # Bypass API complexity and create license + user_license records directly
        import psycopg2
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        cur = conn.cursor()

        # 1. Activate user and give 1000 credits
        cur.execute(
            "UPDATE users SET is_active = true, credit_balance = 1000 WHERE id = %s",
            (user['id'],)
        )

        # 2. Insert user_licenses record (required for enrollment validation)
        cur.execute(
            """
            INSERT INTO user_licenses (
                user_id, specialization_type, current_level, max_achieved_level,
                started_at, payment_verified, payment_verified_at, is_active,
                onboarding_completed, renewal_cost, credit_balance, credit_purchased,
                created_at, updated_at
            )
            VALUES (%s, 'LFA_FOOTBALL_PLAYER', 1, 1, NOW(), TRUE, NOW(), TRUE, TRUE, 1000, 0, 0, NOW(), NOW())
            RETURNING id
            """,
            (user['id'],)
        )
        license_id = cur.fetchone()[0]
        user["license_id"] = license_id

        conn.commit()
        cur.close()
        conn.close()
        user["initial_credits"] = 1000

        # Login to get token for UI access
        login_response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={
                "email": player_data["email"],
                "password": player_data["password"]
            }
        )
        if login_response.status_code == 200:
            login_data = login_response.json()
            user["token"] = login_data["access_token"]
        else:
            raise Exception(f"Failed to login player {player_data['email']}: {login_response.text}")

        players.append(user)

    return players


def create_tournament_via_api(
    token: str,
    name: str,
    reward_policy_name: str = "default",
    age_group: str = "AMATEUR"
) -> Dict[str, Any]:
    """
    Create tournament with reward policy via API.

    Uses the POST /api/v1/tournaments/generate endpoint.
    """
    import random

    # Try multiple dates to avoid conflicts
    for attempt in range(10):
        today = datetime.now().date()
        # Use far future date with random offset
        future_days = random.randint(100, 365)  # 100-365 days in future
        future_date = today + timedelta(days=future_days)

        tournament_data = {
            "date": future_date.isoformat(),
            "name": name,
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": age_group,
            "reward_policy_name": reward_policy_name,
            "sessions": [
                {"time": "10:00", "title": "Morning Game", "duration_minutes": 90, "capacity": 20},
                {"time": "14:00", "title": "Afternoon Game", "duration_minutes": 90, "capacity": 20},
                {"time": "18:00", "title": "Evening Finals", "duration_minutes": 90, "capacity": 16}
            ],
            "campus_id": 1,  # Assume campus 1 exists
            "location_id": 1,  # Assume location 1 exists
            "auto_book_students": False
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/generate",
            headers={"Authorization": f"Bearer {token}"},
            json=tournament_data
        )

        if response.status_code == 201 or response.status_code == 200:
            return response.json()
        elif response.status_code == 409:
            # Conflict - try next date
            continue
        else:
            response.raise_for_status()

    # If all attempts failed, raise the last error
    response.raise_for_status()
    return {}


def enroll_players_in_tournament(
    token: str,
    tournament_id: int,
    player_ids: List[int]
) -> List[Dict[str, Any]]:
    """Enroll multiple players in tournament."""
    enrollments = []

    for player_id in player_ids:
        # Get player token
        player_response = requests.get(
            f"{API_BASE_URL}/api/v1/users/{player_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        player = player_response.json()

        # Login as player to get their token
        login_response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": player["email"], "password": "TestPass123!"}
        )
        player_token = login_response.json()["access_token"]

        # Enroll in tournament
        enroll_response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/enroll",
            headers={"Authorization": f"Bearer {player_token}"}
        )
        enroll_response.raise_for_status()
        enrollments.append(enroll_response.json())

    return enrollments


def set_tournament_rankings(
    token: str,
    tournament_id: int,
    rankings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Set final tournament rankings via direct database insertion.

    Args:
        rankings: List of {"user_id": int, "placement": str, "points": int, "wins": int, "draws": int, "losses": int}
                  placement values: "1ST", "2ND", "3RD", "PARTICIPANT"
    """
    import psycopg2
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # Map placement to rank number
    placement_to_rank = {"1ST": 1, "2ND": 2, "3RD": 3, "PARTICIPANT": 4}

    for ranking in rankings:
        rank = placement_to_rank.get(ranking["placement"], 999)
        cur.execute(
            """
            INSERT INTO tournament_rankings (tournament_id, user_id, participant_type, rank, points, wins, draws, losses)
            VALUES (%s, %s, 'INDIVIDUAL', %s, %s, %s, %s, %s)
            """,
            (
                tournament_id,
                ranking["user_id"],
                rank,
                ranking["points"],
                ranking["wins"],
                ranking["draws"],
                ranking["losses"]
            )
        )

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Rankings set successfully", "count": len(rankings)}


def mark_tournament_completed(token: str, tournament_id: int):
    """Mark tournament as COMPLETED."""
    # WORKAROUND: SemesterUpdate schema doesn't include tournament_status field,
    # so we update via direct SQL to set both status and tournament_status
    import psycopg2
    conn = psycopg2.connect(
        dbname="lfa_intern_system",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute(
        "UPDATE semesters SET status = 'COMPLETED', tournament_status = 'COMPLETED' WHERE id = %s",
        (tournament_id,)
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Tournament marked as COMPLETED"}


def distribute_rewards(token: str, tournament_id: int) -> Dict[str, Any]:
    """Trigger reward distribution."""
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/distribute-rewards",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "E2E test reward distribution"}
    )
    response.raise_for_status()
    return response.json()


def get_user_current_stats(token: str, user_id: int) -> Dict[str, Any]:
    """Get user's current XP and credits."""
    response = requests.get(
        f"{API_BASE_URL}/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    user = response.json()
    return {
        "user_id": user_id,
        "email": user["email"],
        "total_xp": user.get("total_xp", 0),
        "credit_balance": user.get("credit_balance", 0)
    }


def cleanup_user(token: str, user_id: int):
    """Delete test user."""
    try:
        requests.delete(
            f"{API_BASE_URL}/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup user {user_id}: {e}")


def cleanup_tournament(token: str, tournament_id: int):
    """Delete tournament (cascades to sessions, bookings, rankings)."""
    try:
        requests.delete(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
    except Exception as e:
        print(f"Warning: Failed to cleanup tournament {tournament_id}: {e}")


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def reward_policy_admin_token() -> Generator[str, None, None]:
    """Admin token for reward policy tests."""
    token = create_admin_token()
    yield token


@pytest.fixture(scope="function")
def reward_policy_players(reward_policy_admin_token: str) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Create 5 test players for reward policy testing.

    Returns:
        List of 5 players with email, password, id, initial_xp, initial_credits
    """
    players = create_player_users(reward_policy_admin_token, count=5, age_group="AMATEUR")
    yield players

    # Cleanup
    for player in players:
        cleanup_user(reward_policy_admin_token, player["id"])


@pytest.fixture(scope="function")
def reward_policy_tournament_complete(
    reward_policy_admin_token: str,
    reward_policy_players: List[Dict[str, Any]]
) -> Generator[Dict[str, Any], None, None]:
    """
    ✅ PRODUCTION-READY TOURNAMENT FIXTURE (WITH INSTRUCTOR WORKFLOW)

    Creates a tournament in COMPLETED state with FULL production workflow:
    - Instructor assignment via API
    - Attendance records created
    - Rankings with audit trail

    **PRODUCTION FLOW IMPLEMENTED:**
    1. ✅ Admin creates tournament → status: SEEKING_INSTRUCTOR
    2. ✅ Create instructor with LFA_COACH license
    3. ✅ Instructor accepts assignment via API → status: READY_FOR_ENROLLMENT
    4. ✅ Players enroll in tournament
    5. ✅ Attendance records created (PRESENT status)
    6. ✅ Rankings inserted (direct SQL - TODO: instructor submission endpoint)
    7. ✅ Mark tournament as COMPLETED
    8. ✅ Ready for reward distribution (all validations pass)

    **BACKEND VALIDATIONS SATISFIED:**
    - ✅ master_instructor_id IS NOT NULL
    - ✅ Attendance records exist (attendance_count > 0)
    - ✅ Rankings exist
    - ✅ All sessions have instructor_id assigned

    **Returns:**
    ```python
    {
        "tournament_id": int,
        "tournament": dict,  # Tournament details
        "instructor": dict,  # Instructor with token, license_id
        "players": list,     # 5 players with license_id
        "rankings": list,    # Rankings: 1ST, 2ND, 3RD, 2x PARTICIPANT
        "attendance": dict   # Attendance stats
    }
    ```

    **Scenario:** Direct Assignment (Admin assigns instructor, instructor accepts)

    **TODO:** Add Application scenario (instructor applies, admin approves, instructor accepts)
    """
    # Use microsecond-level timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

    print(f"\n{'='*80}")
    print(f"🏗️  CREATING PRODUCTION-READY TOURNAMENT FIXTURE")
    print(f"{'='*80}\n")

    # ============================================================================
    # STEP 1: Admin creates tournament (status: SEEKING_INSTRUCTOR)
    # ============================================================================
    print("  1️⃣ Creating tournament (status: SEEKING_INSTRUCTOR)...")
    tournament_result = create_tournament_via_api(
        reward_policy_admin_token,
        name=f"Reward Test Tournament {timestamp}",
        reward_policy_name="default",
        age_group="AMATEUR"
    )
    tournament_id = tournament_result["tournament_id"]
    print(f"     ✅ Tournament {tournament_id} created")

    # ============================================================================
    # STEP 2: Create instructor with LFA_COACH license
    # ============================================================================
    print("  2️⃣ Creating instructor with LFA_COACH license...")
    instructor = create_instructor_user(reward_policy_admin_token)
    print(f"     ✅ Instructor {instructor['id']} created (email: {instructor['email']})")
    print(f"     ✅ LFA_COACH license {instructor['license_id']} assigned")

    # ============================================================================
    # STEP 3: Instructor accepts assignment via API
    # ============================================================================
    print(f"  3️⃣ Instructor accepts tournament assignment...")
    accept_response = instructor_accepts_assignment(
        instructor["token"],
        tournament_id
    )
    print(f"     ✅ Assignment accepted via API")
    print(f"     ✅ Status → {accept_response['status']}")
    print(f"     ✅ Sessions updated: {accept_response['sessions_updated']}")
    print(f"     ✅ master_instructor_id: {accept_response['instructor_id']}")

    # ============================================================================
    # STEP 4: Players enroll in tournament
    # ============================================================================
    print(f"  4️⃣ Enrolling {len(reward_policy_players)} players...")
    player_ids = [p["id"] for p in reward_policy_players]
    enrollments = enroll_players_in_tournament(
        reward_policy_admin_token,
        tournament_id,
        player_ids
    )
    print(f"     ✅ {len(enrollments)} players enrolled")

    # ============================================================================
    # STEP 5: Create attendance records (PRODUCTION VALIDATION REQUIREMENT)
    # ============================================================================
    print(f"  5️⃣ Creating attendance records...")
    attendance_result = create_attendance_records(
        reward_policy_admin_token,
        tournament_id,
        player_ids
    )
    print(f"     ✅ {attendance_result['count']} attendance records created")
    print(f"     ✅ Sessions with attendance: {attendance_result['sessions']}")

    # ============================================================================
    # STEP 6: Set rankings (direct SQL - TODO: instructor submission endpoint)
    # ============================================================================
    print(f"  6️⃣ Setting tournament rankings...")
    rankings = [
        {"user_id": reward_policy_players[0]["id"], "placement": "1ST", "points": 15, "wins": 5, "draws": 0, "losses": 0},
        {"user_id": reward_policy_players[1]["id"], "placement": "2ND", "points": 12, "wins": 4, "draws": 0, "losses": 1},
        {"user_id": reward_policy_players[2]["id"], "placement": "3RD", "points": 9, "wins": 3, "draws": 0, "losses": 2},
        {"user_id": reward_policy_players[3]["id"], "placement": "PARTICIPANT", "points": 3, "wins": 1, "draws": 0, "losses": 4},
        {"user_id": reward_policy_players[4]["id"], "placement": "PARTICIPANT", "points": 0, "wins": 0, "draws": 0, "losses": 5}
    ]
    set_tournament_rankings(reward_policy_admin_token, tournament_id, rankings)
    print(f"     ✅ {len(rankings)} rankings set")

    # ============================================================================
    # STEP 7: Mark tournament as COMPLETED
    # ============================================================================
    print(f"  7️⃣ Marking tournament as COMPLETED...")
    mark_tournament_completed(reward_policy_admin_token, tournament_id)
    print(f"     ✅ Tournament status: COMPLETED")

    print(f"\n{'='*80}")
    print(f"✅ PRODUCTION-READY TOURNAMENT FIXTURE COMPLETE")
    print(f"{'='*80}\n")

    test_data = {
        "tournament_id": tournament_id,
        "tournament": tournament_result,
        "instructor": instructor,
        "players": reward_policy_players,
        "rankings": rankings,
        "attendance": attendance_result
    }

    yield test_data

    # Cleanup
    print(f"\n🧹 Cleaning up tournament {tournament_id}...")
    cleanup_tournament(reward_policy_admin_token, tournament_id)
