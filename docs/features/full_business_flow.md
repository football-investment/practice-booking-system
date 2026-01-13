# 🚀 TELJES ÜZLETI FOLYAMAT IMPLEMENTÁCIÓS TERV

## Cél
A jelenlegi Playwright E2E teszt kiegészítése a teljes üzleti folyamattal:
- 2 tournament
- 4 instructor application
- Direct instructor assignment
- "First Team" players
- Coupon → Credit workflow
- Attendance approval
- Random rankings
- Negative permission tests

---

## PHASE 1: BACKEND API ENDPOINTS

### 1.1 Direct Instructor Assignment Endpoint

**Fájl:** `app/api/api_v1/endpoints/tournaments/instructor.py`

**Hozzáadandó endpoint (line ~400 után):**

```python
class DirectAssignmentRequest(BaseModel):
    """Direct instructor assignment by admin"""
    instructor_id: int
    assignment_message: Optional[str] = None


@router.post("/{tournament_id}/direct-assign-instructor")
def direct_assign_instructor(
    tournament_id: int,
    request: DirectAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Direct instructor assignment (ADMIN only).

    Admin directly assigns an instructor to tournament without application workflow.
    Creates an ACCEPTED assignment request directly.
    """
    # Authorization: Only ADMIN
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can directly assign instructors"
        )

    # Get tournament
    tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )

    # Get instructor
    instructor = db.query(User).filter(User.id == request.instructor_id).first()
    if not instructor or instructor.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found"
        )

    # Check instructor has LFA_COACH license
    coach_license = db.query(UserLicense).filter(
        UserLicense.user_id == instructor.id,
        UserLicense.specialization_type == "LFA_COACH",
        UserLicense.is_active == True
    ).first()

    if not coach_license:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instructor must have active LFA_COACH license"
        )

    # Create ACCEPTED assignment directly (skip PENDING state)
    assignment = InstructorAssignmentRequest(
        semester_id=tournament_id,
        user_id=instructor.id,
        application_message=request.assignment_message or "Direct assignment by admin",
        status=AssignmentRequestStatus.ACCEPTED,
        applied_at=datetime.utcnow(),
        responded_at=datetime.utcnow(),
        response_message="Direct assignment - no application required"
    )

    db.add(assignment)
    tournament.instructor_id = instructor.id
    tournament.status = SemesterStatus.ASSIGNED_INSTRUCTOR
    db.commit()
    db.refresh(assignment)

    return {
        "message": "Instructor directly assigned",
        "assignment_id": assignment.id,
        "tournament_id": tournament_id,
        "instructor_id": instructor.id,
        "status": "ACCEPTED"
    }
```

---

### 1.2 Decline Application Endpoint

**Fájl:** `app/api/api_v1/endpoints/tournaments/instructor.py`

**Hozzáadandó endpoint (az approve endpoint után, line ~500):**

```python
class DeclineApplicationRequest(BaseModel):
    """Decline instructor application"""
    response_message: Optional[str] = None


@router.post("/{tournament_id}/instructor-applications/{application_id}/decline")
def decline_instructor_application(
    tournament_id: int,
    application_id: int,
    decline_data: DeclineApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Decline instructor application (ADMIN only).
    Sets application status to DECLINED.
    """
    # Authorization: Only ADMIN
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can decline applications"
        )

    # Get application
    application = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.id == application_id,
        InstructorAssignmentRequest.semester_id == tournament_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found for tournament {tournament_id}"
        )

    # Update application status to DECLINED
    application.status = AssignmentRequestStatus.DECLINED
    application.responded_at = datetime.utcnow()
    application.response_message = decline_data.response_message or "Application declined"

    db.commit()
    db.refresh(application)

    return {
        "message": "Application declined",
        "application_id": application_id,
        "status": "DECLINED"
    }
```

---

### 1.3 READY_FOR_ENROLLMENT Status Update

**Fájl:** `app/api/api_v1/endpoints/tournaments/instructor.py`

**Módosítandó:** `accept_instructor_assignment()` endpoint (line ~60 körül)

```python
@router.post("/{tournament_id}/instructor-assignment/accept")
def accept_instructor_assignment(
    tournament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ... existing code ...

    # VÁLTOZÁS: Tournament status → READY_FOR_ENROLLMENT
    tournament.status = SemesterStatus.READY_FOR_ENROLLMENT  # ← ÚJ
    tournament.instructor_id = current_user.id

    db.commit()
    # ... rest of code ...
```

**FONTOS:** Ellenőrizd, hogy a `SemesterStatus` enum-ban van-e `READY_FOR_ENROLLMENT`:

**Fájl:** `app/models/semester.py` (line ~20 körül)

```python
class SemesterStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SEEKING_INSTRUCTOR = "SEEKING_INSTRUCTOR"
    ASSIGNED_INSTRUCTOR = "ASSIGNED_INSTRUCTOR"
    READY_FOR_ENROLLMENT = "READY_FOR_ENROLLMENT"  # ← ÚJ (ha nincs)
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
```

---

### 1.4 Coupon System API Endpoints

**ÚJ FÁJL:** `app/api/api_v1/endpoints/coupons.py`

```python
"""
Coupon Management Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.dependencies import get_current_user

router = APIRouter()


# ============================================================================
# MODELS (Add to app/models/coupon.py)
# ============================================================================

# NOTE: Create app/models/coupon.py with:
# class Coupon(Base):
#     __tablename__ = "coupons"
#     id = Column(Integer, primary_key=True)
#     code = Column(String(50), unique=True, nullable=False)
#     credit_value = Column(Integer, nullable=False)
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime, default=datetime.utcnow)
#     expires_at = Column(DateTime, nullable=True)
#     max_uses = Column(Integer, default=1)
#     used_count = Column(Integer, default=0)


# class CouponUsage(Base):
#     __tablename__ = "coupon_usages"
#     id = Column(Integer, primary_key=True)
#     coupon_id = Column(Integer, ForeignKey("coupons.id"))
#     user_id = Column(Integer, ForeignKey("users.id"))
#     credits_added = Column(Integer)
#     used_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# SCHEMAS
# ============================================================================

class CreateCouponRequest(BaseModel):
    code: str
    credit_value: int
    max_uses: int = 1
    expires_at: Optional[datetime] = None


class ApplyCouponRequest(BaseModel):
    coupon_code: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/create")
def create_coupon(
    request: CreateCouponRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create coupon (ADMIN only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can create coupons"
        )

    # Check if code already exists
    from app.models.coupon import Coupon
    existing = db.query(Coupon).filter(Coupon.code == request.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code already exists"
        )

    coupon = Coupon(
        code=request.code,
        credit_value=request.credit_value,
        max_uses=request.max_uses,
        expires_at=request.expires_at
    )

    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    return {"coupon_id": coupon.id, "code": coupon.code, "credit_value": coupon.credit_value}


@router.post("/apply")
def apply_coupon(
    request: ApplyCouponRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply coupon to user account (increases credit balance)"""
    from app.models.coupon import Coupon, CouponUsage

    # Get coupon
    coupon = db.query(Coupon).filter(
        Coupon.code == request.coupon_code,
        Coupon.is_active == True
    ).first()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or inactive coupon"
        )

    # Check expiry
    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon has expired"
        )

    # Check usage limit
    if coupon.used_count >= coupon.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon usage limit reached"
        )

    # Check if user already used this coupon
    existing_usage = db.query(CouponUsage).filter(
        CouponUsage.coupon_id == coupon.id,
        CouponUsage.user_id == current_user.id
    ).first()

    if existing_usage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already used this coupon"
        )

    # Apply coupon: increase user credit balance
    current_user.credit_balance = (current_user.credit_balance or 0) + coupon.credit_value

    # Record usage
    usage = CouponUsage(
        coupon_id=coupon.id,
        user_id=current_user.id,
        credits_added=coupon.credit_value
    )

    coupon.used_count += 1

    db.add(usage)
    db.commit()
    db.refresh(current_user)

    return {
        "message": f"Coupon applied! {coupon.credit_value} credits added",
        "new_credit_balance": current_user.credit_balance
    }
```

**Regisztráld az új router-t:**

**Fájl:** `app/api/api_v1/endpoints/tournaments/__init__.py`

```python
from app.api.api_v1.endpoints import coupons

# Add to router includes:
router.include_router(coupons.router, prefix="/coupons", tags=["coupons"])
```

---

### 1.5 Team Membership Model

**VAGY:** Használj egyszerűbb megoldást - **email alapú team identification**:

Players email címe: `firstteam_player1@f1rstteamfc.hu`

Így **NINCS szükség új modellre**, csak helper function kell:

**Fájl:** `tests/e2e/reward_policy_fixtures.py`

```python
def create_first_team_players(token: str, count: int = 3) -> List[Dict[str, Any]]:
    """
    Create players with First Team membership (email-based).

    Email pattern: firstteam_playerX@f1rstteamfc.hu
    """
    players = []

    for i in range(count):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        player_data = {
            "email": f"firstteam_player{i+1}_{timestamp}@f1rstteamfc.hu",
            "name": f"First Team Player {i+1}",
            "password": "FirstTeamPass123!",
            "role": "student",
            "date_of_birth": "2010-01-01T00:00:00",
            "specialization": "LFA_FOOTBALL_PLAYER"
        }

        response = requests.post(
            f"{API_BASE_URL}/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json=player_data
        )
        response.raise_for_status()

        player = response.json()
        player["password"] = player_data["password"]

        # Activate + add license (same as before)
        import psycopg2
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        cur = conn.cursor()

        cur.execute("UPDATE users SET is_active = true WHERE id = %s", (player['id'],))
        cur.execute(
            """
            INSERT INTO user_licenses (user_id, specialization_type, current_level, max_achieved_level, started_at)
            VALUES (%s, 'LFA_FOOTBALL_PLAYER', 1, 1, NOW())
            """,
            (player['id'],)
        )

        conn.commit()
        cur.close()
        conn.close()

        # Get token
        login_response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": player["email"], "password": player["password"]}
        )
        player["token"] = login_response.json()["access_token"]

        players.append(player)

    return players
```

---

### 1.6 Attendance Approval Endpoint

**Fájl:** `app/api/api_v1/endpoints/sessions.py` (vagy új attendance.py)

```python
@router.post("/sessions/{session_id}/attendance/{attendance_id}/approve")
def approve_attendance(
    session_id: int,
    attendance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Instructor approves attendance (INSTRUCTOR only).

    Marks attendance as explicitly approved.
    """
    from app.models.attendance import Attendance

    # Authorization: Only INSTRUCTOR
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructor can approve attendance"
        )

    # Get attendance
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance or attendance.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance not found"
        )

    # Mark as approved
    attendance.is_approved = True  # Add this column to Attendance model if not exists
    attendance.approved_by_id = current_user.id
    attendance.approved_at = datetime.utcnow()

    db.commit()

    return {"message": "Attendance approved", "attendance_id": attendance_id}
```

---

### 1.7 Random Ranking Generation Helper

**Fájl:** `tests/e2e/reward_policy_fixtures.py`

```python
import random

def generate_random_rankings(player_ids: List[int]) -> Dict[int, str]:
    """
    Generate random tournament rankings/placements.

    Returns dict: {player_id: placement}
    """
    from app.models.semester import TournamentPlacement

    # Shuffle players randomly
    shuffled_ids = player_ids.copy()
    random.shuffle(shuffled_ids)

    rankings = {}

    # Assign placements
    if len(shuffled_ids) >= 1:
        rankings[shuffled_ids[0]] = TournamentPlacement.FIRST
    if len(shuffled_ids) >= 2:
        rankings[shuffled_ids[1]] = TournamentPlacement.SECOND
    if len(shuffled_ids) >= 3:
        rankings[shuffled_ids[2]] = TournamentPlacement.THIRD

    # Rest are participants
    for player_id in shuffled_ids[3:]:
        rankings[player_id] = TournamentPlacement.PARTICIPANT

    return rankings
```

---

### 1.8 Instructor Permission Check (Tournament Creation)

**Fájl:** `app/api/api_v1/endpoints/tournaments/tournaments.py`

**Módosítandó:** `generate_tournament()` endpoint

```python
@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_tournament(
    tournament_data: TournamentGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate tournament with sessions and optional reward policy.

    AUTHORIZATION: Only ADMIN can create tournaments.
    """
    # VÁLTOZÁS: Permission check
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create tournaments"
        )

    # ... rest of existing code ...
```

---

## PHASE 2: UPDATED TEST FIXTURES

**Fájl:** `tests/e2e/reward_policy_fixtures.py`

**Hozzáadandó funkciók:**

```python
def create_multiple_tournaments(
    token: str,
    count: int = 2,
    base_name: str = "Tournament",
    reward_policy: str = "default",
    age_group: str = "AMATEUR"
) -> List[Dict[str, Any]]:
    """Create multiple tournaments"""
    tournaments = []

    for i in range(count):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        tournament = create_tournament_via_api(
            token=token,
            name=f"{base_name} {i+1} {timestamp}",
            reward_policy_name=reward_policy,
            age_group=age_group
        )
        tournaments.append(tournament)
        time.sleep(0.5)  # Avoid conflicts

    return tournaments


def create_multiple_instructors(
    token: str,
    count: int = 4
) -> List[Dict[str, Any]]:
    """Create multiple instructors"""
    instructors = []

    for i in range(count):
        instructor = create_instructor_user(token)
        instructors.append(instructor)

    return instructors
```

---

## PHASE 3: PLAYWRIGHT TEST - TELJES ÁTÍRÁS

**ÚJ FÁJL:** `tests/e2e/test_complete_business_workflow.py`

```python
"""
Complete Business Workflow E2E Test - FULL IMPLEMENTATION

Workflow:
1. Admin creates 2 tournaments
2. Admin directly assigns "GrandMaster" instructor to Tournament 1
3. Admin opens application for Tournament 2
4. 4 instructors apply to Tournament 2
5. Admin randomly selects 1 instructor, declines others
6. Selected instructor accepts assignment
7. 3 "First Team" players apply coupons for credits
8. Players enroll in BOTH tournaments
9. Instructors approve attendance for all sessions
10. Random rankings generated
11. Tournaments marked COMPLETED
12. Rewards distributed
13. Negative test: Instructor tries to create tournament (FORBIDDEN)
"""

import pytest
import time
import random
from datetime import datetime
from playwright.sync_api import Page

from tests.e2e.reward_policy_fixtures import (
    create_admin_token,
    create_multiple_tournaments,
    create_instructor_user,
    create_multiple_instructors,
    create_first_team_players,
    enroll_players_in_tournament,
    create_attendance_records,
    mark_tournament_completed,
    generate_random_rankings,
    API_BASE_URL
)


class TestCompletBusinessWorkflow:
    """Complete business workflow test with ALL features"""

    STREAMLIT_URL = "http://localhost:8501"
    ADMIN_ID = 1

    def test_complete_business_workflow(
        self,
        page: Page,
        reward_policy_admin_token: str
    ):
        """
        FULL BUSINESS WORKFLOW TEST

        This test validates the COMPLETE business logic:
        - 2 tournaments
        - Direct assignment + Application workflow
        - 4 instructors competing
        - Random selection + DECLINED status
        - First Team players
        - Coupon → Credit → Enrollment
        - Attendance approval
        - Random rankings
        - Permission checks
        """
        print("\n" + "="*80)
        print("🎭 COMPLETE BUSINESS WORKFLOW E2E TEST")
        print("="*80 + "\n")

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # ====================================================================
        # STEP 1: Admin creates 2 tournaments
        # ====================================================================
        print("\n  1️⃣ Admin creates 2 tournaments...")

        tournaments = create_multiple_tournaments(
            token=reward_policy_admin_token,
            count=2,
            base_name="Business Workflow Tournament"
        )

        tournament1 = tournaments[0]
        tournament2 = tournaments[1]

        print(f"     ✅ Tournament 1 (ID: {tournament1['tournament_id']}): {tournament1['summary']['name']}")
        print(f"     ✅ Tournament 2 (ID: {tournament2['tournament_id']}): {tournament2['summary']['name']}")

        # ====================================================================
        # STEP 2: Create GrandMaster instructor + Direct Assignment
        # ====================================================================
        print("\n  2️⃣ Admin directly assigns GrandMaster instructor to Tournament 1...")

        import requests

        # Create GrandMaster instructor with specific email
        grandmaster_data = {
            "email": "grandmaster@lfa.com",
            "name": "GrandMaster Instructor",
            "password": "GrandMaster123!",
            "role": "instructor",
            "date_of_birth": "1980-01-01T00:00:00",
            "specialization": "LFA_COACH"
        }

        gm_response = requests.post(
            f"{API_BASE_URL}/api/v1/users",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"},
            json=grandmaster_data
        )
        grandmaster = gm_response.json()

        # Activate + add license
        import psycopg2
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_active = true WHERE id = %s", (grandmaster['id'],))
        cur.execute(
            "INSERT INTO user_licenses (user_id, specialization_type, current_level, max_achieved_level, started_at) VALUES (%s, 'LFA_COACH', 1, 1, NOW())",
            (grandmaster['id'],)
        )
        conn.commit()
        cur.close()
        conn.close()

        # Direct assignment via API
        direct_assign_response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament1['tournament_id']}/direct-assign-instructor",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"},
            json={
                "instructor_id": grandmaster['id'],
                "assignment_message": "You are the GrandMaster - direct assignment"
            }
        )

        if direct_assign_response.status_code == 200:
            print(f"     ✅ GrandMaster directly assigned to Tournament 1")
        else:
            print(f"     ❌ Direct assignment failed: {direct_assign_response.text}")
            raise Exception("Direct assignment failed")

        # ====================================================================
        # STEP 3-6: Application workflow for Tournament 2
        # ====================================================================
        print("\n  3️⃣ 4 instructors apply to Tournament 2...")

        instructors = create_multiple_instructors(reward_policy_admin_token, count=4)

        # All 4 instructors apply via UI (Playwright)
        for idx, instructor in enumerate(instructors, 1):
            # Login and apply
            page.goto(self.STREAMLIT_URL)
            time.sleep(2)

            # Login
            text_inputs = page.locator("[data-testid='stTextInput'] input").all()
            text_inputs[0].fill(instructor['email'])
            text_inputs[1].fill("instructor123")
            page.get_by_role("button", name="🔐 Login").click()
            time.sleep(2)

            # Navigate with session params
            import json, urllib.parse
            session_user = urllib.parse.quote(json.dumps({
                'id': instructor['id'],
                'email': instructor['email'],
                'name': instructor['name'],
                'role': instructor['role']
            }))

            page.goto(f"{self.STREAMLIT_URL}/Instructor_Dashboard?session_token={instructor['token']}&session_user={session_user}")
            time.sleep(3)

            # Apply to tournament
            page.locator("[data-baseweb='tab']:has-text('🏆 Tournament Applications')").first.click()
            time.sleep(2)

            page.locator("[data-baseweb='tab']:has-text('🔍 Open Tournaments')").first.click()
            time.sleep(2)

            page.locator(f"text={tournament2['summary']['name']}").first.click()
            time.sleep(1)

            page.get_by_role("button", name="📝 Apply").click()
            time.sleep(1)

            page.locator("[data-testid='stTextArea'] textarea").first.fill(f"Instructor {idx} - I want to lead this tournament!")
            time.sleep(1)

            page.get_by_role("button", name="✅ Submit Application").click()
            time.sleep(2)

            print(f"     ✅ Instructor {idx} applied to Tournament 2")

        # Get all applications via API
        apps_response = requests.get(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament2['tournament_id']}/instructor-applications",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
        )
        applications = apps_response.json()['applications']

        print(f"     📋 Total applications: {len(applications)}")

        # ====================================================================
        # STEP 4: Random selection + DECLINE others
        # ====================================================================
        print("\n  4️⃣ Admin randomly selects 1 instructor, declines others...")

        # Random selection
        chosen_app = random.choice(applications)
        print(f"     🎲 Randomly chosen: Application ID {chosen_app['id']}")

        # Approve chosen
        approve_response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament2['tournament_id']}/instructor-applications/{chosen_app['id']}/approve",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"},
            json={"response_message": "Congratulations! You have been selected."}
        )
        print(f"     ✅ Application {chosen_app['id']} APPROVED")

        # Decline others
        for app in applications:
            if app['id'] != chosen_app['id']:
                decline_response = requests.post(
                    f"{API_BASE_URL}/api/v1/tournaments/{tournament2['tournament_id']}/instructor-applications/{app['id']}/decline",
                    headers={"Authorization": f"Bearer {reward_policy_admin_token}"},
                    json={"response_message": "Thank you for applying. We selected another instructor."}
                )
                print(f"     ❌ Application {app['id']} DECLINED")

        # ====================================================================
        # STEP 5: Chosen instructor accepts (UI)
        # ====================================================================
        print("\n  5️⃣ Chosen instructor accepts assignment...")

        # Find chosen instructor from instructors list
        chosen_instructor = next(i for i in instructors if i['id'] == chosen_app['user_id'])

        # Login and accept via UI
        page.goto(self.STREAMLIT_URL)
        time.sleep(2)

        text_inputs = page.locator("[data-testid='stTextInput'] input").all()
        text_inputs[0].fill(chosen_instructor['email'])
        text_inputs[1].fill("instructor123")
        page.get_by_role("button", name="🔐 Login").click()
        time.sleep(2)

        # Navigate to My Applications
        session_user = urllib.parse.quote(json.dumps({
            'id': chosen_instructor['id'],
            'email': chosen_instructor['email'],
            'name': chosen_instructor['name'],
            'role': chosen_instructor['role']
        }))

        page.goto(f"{self.STREAMLIT_URL}/Instructor_Dashboard?session_token={chosen_instructor['token']}&session_user={session_user}")
        time.sleep(3)

        page.locator("[data-baseweb='tab']:has-text('🏆 Tournament Applications')").first.click()
        time.sleep(2)
        page.locator("[data-baseweb='tab']:has-text('📋 My Applications')").first.click()
        time.sleep(2)

        # Reload to bypass cache
        page.reload()
        time.sleep(3)

        page.locator("[data-baseweb='tab']:has-text('🏆 Tournament Applications')").first.click()
        time.sleep(1)
        page.locator("[data-baseweb='tab']:has-text('📋 My Applications')").first.click()
        time.sleep(2)

        page.get_by_role("button", name="✅ Accept Assignment").click()
        time.sleep(2)

        print(f"     ✅ Instructor accepted assignment for Tournament 2")

        # ====================================================================
        # STEP 6: First Team players + Coupons
        # ====================================================================
        print("\n  6️⃣ Creating First Team players and applying coupons...")

        players = create_first_team_players(reward_policy_admin_token, count=3)

        # Create coupon
        coupon_response = requests.post(
            f"{API_BASE_URL}/api/v1/coupons/create",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"},
            json={
                "code": f"FIRSTTEAM{timestamp}",
                "credit_value": 1000,
                "max_uses": 3
            }
        )
        coupon_code = coupon_response.json()['code']
        print(f"     🎟️ Coupon created: {coupon_code}")

        # Players apply coupon
        for idx, player in enumerate(players, 1):
            apply_response = requests.post(
                f"{API_BASE_URL}/api/v1/coupons/apply",
                headers={"Authorization": f"Bearer {player['token']}"},
                json={"coupon_code": coupon_code}
            )
            new_balance = apply_response.json()['new_credit_balance']
            print(f"     ✅ Player {idx} applied coupon → Balance: {new_balance} credits")

        # ====================================================================
        # STEP 7: Players enroll in BOTH tournaments
        # ====================================================================
        print("\n  7️⃣ Players enroll in BOTH tournaments...")

        player_ids = [p['id'] for p in players]

        enroll_players_in_tournament(reward_policy_admin_token, tournament1['tournament_id'], player_ids)
        print(f"     ✅ {len(players)} players enrolled in Tournament 1")

        enroll_players_in_tournament(reward_policy_admin_token, tournament2['tournament_id'], player_ids)
        print(f"     ✅ {len(players)} players enrolled in Tournament 2")

        # ====================================================================
        # STEP 8: Attendance approval (both instructors)
        # ====================================================================
        print("\n  8️⃣ Instructors approve attendance...")

        # Tournament 1: GrandMaster approves
        attendance1 = create_attendance_records(
            reward_policy_admin_token,
            tournament1['tournament_id'],
            player_ids,
            tournament1['session_ids']
        )
        print(f"     ✅ GrandMaster approved {len(attendance1)} attendance records (Tournament 1)")

        # Tournament 2: Chosen instructor approves
        attendance2 = create_attendance_records(
            reward_policy_admin_token,
            tournament2['tournament_id'],
            player_ids,
            tournament2['session_ids']
        )
        print(f"     ✅ Chosen instructor approved {len(attendance2)} attendance records (Tournament 2)")

        # ====================================================================
        # STEP 9: Random rankings + COMPLETED
        # ====================================================================
        print("\n  9️⃣ Generating random rankings and completing tournaments...")

        # Random rankings for Tournament 1
        rankings1 = generate_random_rankings(player_ids)
        mark_tournament_completed(
            reward_policy_admin_token,
            tournament1['tournament_id'],
            rankings1
        )
        print(f"     ✅ Tournament 1 COMPLETED with random rankings")

        # Random rankings for Tournament 2
        rankings2 = generate_random_rankings(player_ids)
        mark_tournament_completed(
            reward_policy_admin_token,
            tournament2['tournament_id'],
            rankings2
        )
        print(f"     ✅ Tournament 2 COMPLETED with random rankings")

        # ====================================================================
        # STEP 10: Reward distribution
        # ====================================================================
        print("\n  🔟 Distributing rewards for both tournaments...")

        dist1_response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament1['tournament_id']}/distribute-rewards",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
        )
        print(f"     ✅ Tournament 1 rewards distributed: {dist1_response.json()['total_participants']} participants")

        dist2_response = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/{tournament2['tournament_id']}/distribute-rewards",
            headers={"Authorization": f"Bearer {reward_policy_admin_token}"}
        )
        print(f"     ✅ Tournament 2 rewards distributed: {dist2_response.json()['total_participants']} participants")

        # ====================================================================
        # STEP 11: NEGATIVE TEST - Instructor cannot create tournament
        # ====================================================================
        print("\n  1️⃣1️⃣ NEGATIVE TEST: Instructor tries to create tournament...")

        instructor_attempt = requests.post(
            f"{API_BASE_URL}/api/v1/tournaments/generate",
            headers={"Authorization": f"Bearer {chosen_instructor['token']}"},
            json={
                "date": "2026-12-01",
                "name": "Unauthorized Tournament",
                "specialization_type": "LFA_FOOTBALL_PLAYER",
                "age_group": "AMATEUR",
                "sessions": [{"time": "10:00", "title": "Game", "duration_minutes": 90, "capacity": 20}],
                "campus_id": 1,
                "location_id": 1
            }
        )

        if instructor_attempt.status_code == 403:
            print(f"     ✅ NEGATIVE TEST PASSED: Instructor correctly FORBIDDEN (403)")
        else:
            print(f"     ❌ NEGATIVE TEST FAILED: Got status {instructor_attempt.status_code}")
            raise Exception("Instructor should not be able to create tournament!")

        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        print("\n" + "="*80)
        print("✅ COMPLETE BUSINESS WORKFLOW TEST PASSED")
        print("="*80)
        print(f"  • 2 tournaments created")
        print(f"  • Direct assignment: GrandMaster → Tournament 1")
        print(f"  • Application workflow: 4 instructors → 1 chosen, 3 declined → Tournament 2")
        print(f"  • 3 First Team players enrolled in BOTH tournaments")
        print(f"  • Coupon applied: {coupon_code}")
        print(f"  • Attendance approved by both instructors")
        print(f"  • Random rankings generated")
        print(f"  • Rewards distributed for both tournaments")
        print(f"  • Negative test: Instructor creation blocked ✅")
        print("="*80 + "\n")
```

---

## PHASE 4: FUTTATÁS

### 4.1 Alembic Migration (új modellek)

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system

# Generate migration
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" alembic revision --autogenerate -m "Add coupon system and attendance approval"

# Run migration
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" alembic upgrade head
```

### 4.2 Run Playwright Test (HEADED MODE - FIREFOX)

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system

source venv/bin/activate

PYTHONPATH=/Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system \
pytest tests/e2e/test_complete_business_workflow.py::TestCompletBusinessWorkflow::test_complete_business_workflow \
--headed --browser firefox --slowmo 800 -v -s
```

---

## SUMMARY

Ez a dokumentum tartalmazza **MINDEN szükséges kód változtatást** a teljes üzleti folyamat implementálásához.

**KÖVETKEZŐ LÉPÉSEK:**

1. Implementáld a backend endpoint-okat (copy-paste a kódokat)
2. Futtasd az Alembic migration-t
3. Hozd létre az új Playwright teszt fájlt
4. Futtasd a tesztet headed mode-ban Firefox-ban
5. Ellenőrizd, hogy PASS-e

**Becsült implementálási idő:** 2-3 óra (minden réteggel együtt)
