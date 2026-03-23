# Phase 5: Role-Based Access Control (RBAC) Testing

**Status:** ⚪ PROPOSED (Not Started)
**Priority:** 🔴 HIGH - Security Critical
**Estimated Tests:** ~40 tests
**Estimated Time:** 1-2 days

---

## Probléma Leírás

A jelenlegi 187/187 teszt **NEM tartalmaz autentikációs/autorizációs teszteket**:
- ❌ Nincs JWT token validáció teszt
- ❌ Nincs szerepkör-alapú hozzáférés ellenőrzés
- ❌ Nincs permission boundary teszt
- ❌ Nincs cross-role attack teszt

**Biztonsági Kockázat:**
- Diák hozzáférhet admin funkciókhoz
- Instructor módosíthat más instructor adatait
- Unauthorized user létrehozhat licenceket

---

## Meglévő Role System (app/dependencies.py)

```python
class UserRole(str, Enum):
    ADMIN = "admin"           # Teljes jogosultság
    INSTRUCTOR = "instructor" # Oktatói műveletek
    STUDENT = "student"       # Diák műveletek

# Protection Decorators
get_current_user()                      # ANY authenticated user
get_current_admin_user()                # ADMIN only
get_current_admin_or_instructor_user()  # ADMIN or INSTRUCTOR
get_current_user_web()                  # Web-based auth (cookie)
get_current_admin_user_web()            # Web admin (cookie)
```

---

## Tervezett Tesztek

### Task 1: Spec-Specific License API - RBAC (16 tests)

**File:** `implementation/05_rbac_tests/test_01_spec_license_rbac.py`

#### 1.1 LFA Player License RBAC (4 tests)
```python
def test_student_can_view_own_lfa_license():
    """Student can GET /api/v1/lfa-player/licenses/me"""

def test_student_cannot_view_other_lfa_license():
    """Student CANNOT GET /api/v1/lfa-player/licenses/{other_user_id}"""

def test_admin_can_create_lfa_license_for_any_user():
    """Admin CAN POST /api/v1/lfa-player/licenses/create for any user"""

def test_student_cannot_create_lfa_license_for_others():
    """Student CANNOT POST /api/v1/lfa-player/licenses/create for other_user_id"""
```

#### 1.2 GānCuju License RBAC (4 tests)
```python
def test_student_can_view_own_gancuju_license():
def test_student_cannot_promote_own_level():
    """Only INSTRUCTOR can POST /api/v1/gancuju/levels/promote"""
def test_instructor_can_promote_student_level():
def test_admin_can_manage_all_gancuju_licenses():
```

#### 1.3 Internship License RBAC (4 tests)
```python
def test_student_can_view_own_xp():
def test_student_cannot_add_xp_to_self():
    """Only INSTRUCTOR can POST /api/v1/internship/xp/add"""
def test_instructor_can_add_xp_to_students():
def test_admin_can_renew_any_license():
```

#### 1.4 Coach License RBAC (4 tests)
```python
def test_instructor_can_view_own_coach_license():
def test_instructor_cannot_promote_own_certification():
    """Only ADMIN can POST /api/v1/coach/certifications/promote"""
def test_admin_can_promote_any_coach_certification():
def test_student_cannot_access_coach_endpoints():
    """Students should get 403 Forbidden on coach endpoints"""
```

---

### Task 2: Existing API Endpoints - RBAC (12 tests)

**File:** `implementation/05_rbac_tests/test_02_existing_api_rbac.py`

#### 2.1 Session Management RBAC (4 tests)
```python
def test_student_can_view_available_sessions():
    """GET /api/v1/sessions/available (public or student)"""

def test_student_cannot_create_sessions():
    """POST /api/v1/sessions/create (403 Forbidden for student)"""

def test_instructor_can_create_sessions():
    """POST /api/v1/sessions/create (allowed for instructor)"""

def test_admin_can_delete_any_session():
    """DELETE /api/v1/sessions/{id} (admin only)"""
```

#### 2.2 Attendance Tracking RBAC (4 tests)
```python
def test_student_can_view_own_attendance():
    """GET /api/v1/attendance/me"""

def test_student_cannot_mark_attendance_for_others():
    """POST /api/v1/attendance/mark (403 Forbidden)"""

def test_instructor_can_mark_attendance():
    """POST /api/v1/attendance/mark (allowed for instructor)"""

def test_admin_can_edit_any_attendance():
    """PUT /api/v1/attendance/{id} (admin only)"""
```

#### 2.3 User Management RBAC (4 tests)
```python
def test_student_can_view_own_profile():
    """GET /api/v1/users/me"""

def test_student_cannot_view_all_users():
    """GET /api/v1/users (403 Forbidden for student)"""

def test_admin_can_view_all_users():
    """GET /api/v1/users (admin only)"""

def test_admin_can_change_user_role():
    """PUT /api/v1/users/{id}/role (admin only)"""
```

---

### Task 3: Cross-Role Attack Prevention (12 tests)

**File:** `implementation/05_rbac_tests/test_03_cross_role_attacks.py`

#### 3.1 Privilege Escalation Attempts (4 tests)
```python
def test_student_cannot_escalate_to_admin():
    """Student cannot PUT /api/v1/users/me with role=ADMIN"""

def test_instructor_cannot_escalate_to_admin():
    """Instructor cannot change own role to ADMIN"""

def test_student_cannot_use_admin_endpoints_with_forged_token():
    """Forged JWT with role=ADMIN should fail signature validation"""

def test_expired_admin_token_is_rejected():
    """Expired JWT should return 401 Unauthorized"""
```

#### 3.2 Horizontal Privilege Escalation (4 tests)
```python
def test_student_cannot_modify_other_student_profile():
    """Student A cannot PUT /api/v1/users/{student_B_id}"""

def test_instructor_cannot_modify_other_instructor_licenses():
    """Instructor A cannot modify Instructor B's coach license"""

def test_student_cannot_view_other_student_xp():
    """Student A cannot GET /api/v1/internship/licenses/{student_B_id}"""

def test_instructor_can_only_view_assigned_students():
    """Instructor can view students in their sessions, not all students"""
```

#### 3.3 Resource Ownership Validation (4 tests)
```python
def test_license_ownership_validated_on_update():
    """Cannot update license you don't own (even with valid token)"""

def test_enrollment_ownership_validated_on_cancel():
    """Cannot cancel enrollment for another user"""

def test_credit_purchase_requires_own_license():
    """Cannot purchase credits for another user's license"""

def test_skill_update_requires_license_ownership():
    """Cannot update skills on another user's LFA Player license"""
```

---

## Teszt Infrastruktúra Követelmények

### 1. Test User Creation
```python
# Fixture to create test users with different roles
@pytest.fixture
def test_users(db):
    admin = create_user(email="admin@test.com", role=UserRole.ADMIN)
    instructor = create_user(email="instructor@test.com", role=UserRole.INSTRUCTOR)
    student1 = create_user(email="student1@test.com", role=UserRole.STUDENT)
    student2 = create_user(email="student2@test.com", role=UserRole.STUDENT)

    return {
        'admin': admin,
        'instructor': instructor,
        'student1': student1,
        'student2': student2
    }
```

### 2. JWT Token Generation
```python
# Generate valid JWT tokens for testing
def get_auth_headers(user):
    from app.core.auth import create_access_token
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}
```

### 3. FastAPI TestClient
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Example authenticated request
response = client.get(
    "/api/v1/lfa-player/licenses/me",
    headers=get_auth_headers(student1)
)
```

---

## Védendő Végpontok Kategóriái

### 🔴 Admin Only Endpoints
```
POST   /api/v1/users/{id}/role           # Change user role
DELETE /api/v1/users/{id}                # Delete user
POST   /api/v1/semesters/create          # Create semester
PUT    /api/v1/coach/certifications/promote  # Promote coach cert
```

### 🟡 Admin or Instructor Endpoints
```
POST   /api/v1/sessions/create           # Create session
PUT    /api/v1/attendance/mark           # Mark attendance
POST   /api/v1/internship/xp/add         # Add XP to student
POST   /api/v1/gancuju/levels/promote    # Promote GānCuju level
```

### 🟢 Student (Self Only) Endpoints
```
GET    /api/v1/lfa-player/licenses/me   # View own license
GET    /api/v1/internship/licenses/me   # View own XP
POST   /api/v1/lfa-player/credits/purchase  # Purchase credits (own)
GET    /api/v1/sessions/available        # View available sessions
```

### ⚪ Public Endpoints (No Auth)
```
POST   /api/v1/auth/login               # Login
POST   /api/v1/auth/register            # Register
GET    /api/v1/health                   # Health check
```

---

## Spec-Specific License Endpoints - RBAC Matrix

| Endpoint | Admin | Instructor | Student (Self) | Student (Other) |
|----------|-------|------------|----------------|-----------------|
| **LFA Player** |
| `POST /lfa-player/licenses/create` | ✅ Any User | ✅ Any User | ✅ Self Only | ❌ 403 |
| `GET /lfa-player/licenses/me` | ✅ | ✅ | ✅ | N/A |
| `GET /lfa-player/licenses/{id}` | ✅ Any | ❌ 403 | ✅ Self Only | ❌ 403 |
| `PUT /lfa-player/skills/update` | ✅ Any | ✅ Assigned Students | ✅ Self Only | ❌ 403 |
| `POST /lfa-player/credits/purchase` | ✅ Any | ❌ 403 | ✅ Self Only | ❌ 403 |
| **GānCuju** |
| `POST /gancuju/licenses/create` | ✅ Any | ✅ Any | ✅ Self Only | ❌ 403 |
| `POST /gancuju/competitions/record` | ✅ Any | ✅ Assigned | ❌ 403 | ❌ 403 |
| `POST /gancuju/levels/promote` | ✅ Any | ✅ Assigned | ❌ 403 | ❌ 403 |
| `POST /gancuju/teaching/record` | ✅ Any | ✅ Self + Assigned | ✅ Self Only | ❌ 403 |
| **Internship** |
| `POST /internship/licenses/create` | ✅ Any | ✅ Any | ✅ Self Only | ❌ 403 |
| `POST /internship/xp/add` | ✅ Any | ✅ Assigned | ❌ 403 | ❌ 403 |
| `POST /internship/licenses/renew` | ✅ Any | ❌ 403 | ✅ Self Only | ❌ 403 |
| `GET /internship/licenses/{id}/expiry` | ✅ Any | ✅ Assigned | ✅ Self Only | ❌ 403 |
| **Coach** |
| `POST /coach/licenses/create` | ✅ Any | ✅ Self Only | ❌ 403 | ❌ 403 |
| `POST /coach/hours/theory/add` | ✅ Any | ✅ Self Only | ❌ 403 | ❌ 403 |
| `POST /coach/certifications/promote` | ✅ Any | ❌ 403 | ❌ 403 | ❌ 403 |
| `POST /coach/certifications/renew` | ✅ Any | ✅ Self Only | ❌ 403 | ❌ 403 |

---

## Sikerkritériumok

### Must Have
- ✅ All 40 RBAC tests passing
- ✅ JWT token validation working
- ✅ Role-based endpoint protection enforced
- ✅ Ownership validation on resources
- ✅ No privilege escalation possible

### Nice to Have
- Audit logging for failed auth attempts
- Rate limiting on auth endpoints
- IP-based access restrictions for admin
- Two-factor authentication (2FA) support

---

## Implementációs Lépések

### 1. Add RBAC Protection to Spec-Specific APIs
```python
# Example: app/api/api_v1/endpoints/lfa_player.py

from ....dependencies import get_current_user, get_current_admin_user

@router.post("/licenses/create")
async def create_license(
    user_id: int,
    age_group: str,
    current_user: User = Depends(get_current_user),  # ADD THIS
    db: Session = Depends(get_db)
):
    # Validate user can only create for self (unless admin)
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )

    # ... rest of logic
```

### 2. Create Test Fixtures
```python
# implementation/05_rbac_tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import create_access_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_headers(db):
    admin = create_test_user(role=UserRole.ADMIN)
    token = create_access_token(data={"sub": admin.email})
    return {"Authorization": f"Bearer {token}"}

# Similar for instructor_headers, student_headers
```

### 3. Write RBAC Tests
```python
# implementation/05_rbac_tests/test_01_spec_license_rbac.py

def test_student_cannot_create_license_for_others(client, student_headers):
    """Student CANNOT create LFA Player license for another user"""

    response = client.post(
        "/api/v1/lfa-player/licenses/create",
        json={
            "user_id": 999,  # Different user
            "age_group": "YOUTH"
        },
        headers=student_headers
    )

    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]
```

---

## Összefoglalás

**Jelenlegi Helyzet:**
- ✅ Funkcionalitás: 187/187 teszt
- ❌ RBAC/Security: 0/40 teszt

**Következő Lépések:**
1. Phase 5 RBAC tesztek írása (40 teszt)
2. Spec-specific API védelem hozzáadása
3. Ownership validáció implementálása
4. Security audit elvégzése

**Becsült Munka:**
- Teszt írás: 1 nap
- API védelem hozzáadása: 0.5 nap
- Validáció és javítás: 0.5 nap
- **Összesen: 2 nap**

**Priority:** 🔴 HIGH - Prod deployment előtt kötelező!
