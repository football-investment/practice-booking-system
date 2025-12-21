# Web Routes Refactoring Status

**Date:** 2025-12-20
**Type:** 🔧 P0 REFACTORING
**Status:** ⏳ IN PROGRESS

---

## 📋 OVERVIEW

**Task:** Refactor monolithic `app/api/web_routes.py` (5,381 lines) into modular route files

**Reason:** Code quality audit identified this as a **God File anti-pattern** requiring immediate refactoring

**Approach:** Extract routes into functional modules while preserving all functionality

---

## ✅ COMPLETED STEPS

### Step 1: Directory Structure Created ✅
**Location:** `app/api/web_routes/`

**Files Created:**
- `__init__.py` - Router aggregation (empty, pending)
- `helpers.py` - ✅ **COMPLETE** (138 lines)
  - `update_specialization_xp()` - XP tracking helper
  - `get_lfa_age_category()` - Age category calculator
- `auth.py` - Authentication routes (pending)
- `onboarding.py` - Onboarding flow (pending)
- `dashboard.py` - Dashboard routes (pending)
- `specialization.py` - Specialization management (pending)
- `profile.py` - User profile (pending)
- `student_features.py` - Student features (pending)
- `sessions.py` - Session management (pending)
- `attendance.py` - Attendance workflow (pending)
- `quiz.py` - Quiz & assessment (pending)
- `instructor.py` - Instructor operations (pending)
- `instructor_dashboard.py` - Instructor dashboard (pending)
- `admin.py` - Admin dashboard (pending)

---

## 🎯 ROUTE DISTRIBUTION PLAN

### Total Routes: 59

| Module | Routes | Estimated LOC | Status |
|--------|--------|---------------|--------|
| **helpers.py** | 2 helpers | 138 lines | ✅ **COMPLETE** |
| auth.py | 6 routes | 200-250 | ⏳ Pending |
| onboarding.py | 7 routes | 300-350 | ⏳ Pending |
| dashboard.py | 2 routes | 400-450 | ⏳ Pending |
| specialization.py | 6 routes | 350-400 | ⏳ Pending |
| profile.py | 3 routes | 200-250 | ⏳ Pending |
| student_features.py | 4 routes | 250-300 | ⏳ Pending |
| sessions.py | 9 routes | 600-700 | ⏳ Pending |
| attendance.py | 3 routes | 250-300 | ⏳ Pending |
| quiz.py | 3 routes | 250-300 | ⏳ Pending |
| instructor.py | 5 routes | 350-400 | ⏳ Pending |
| instructor_dashboard.py | 3 routes | 250-300 | ⏳ Pending |
| admin.py | 8 routes | 400-450 | ⏳ Pending |
| **TOTAL** | **59 routes** | **~4,138 lines** | **2.5% Done** |

---

## 📝 DETAILED ROUTE BREAKDOWN

### Auth Routes (6 routes) - `auth.py`
```
Line 122:  GET  /                    - home()
Line 134:  GET  /login               - login_page()
Line 140:  POST /login               - login_submit()
Line 192:  GET  /logout              - logout()
Line 202:  GET  /age-verification    - age_verification_page()
Line 229:  POST /age-verification    - age_verification_submit()
```

### Onboarding Routes (7 routes) - `onboarding.py`
```
Line 949:  GET  /specialization/select               - specialization_select_page()
Line 981:  POST /specialization/select               - specialization_select_submit()
Line 1084: GET  /specialization/unlock               - specialization_unlock_get()
Line 1098: POST /specialization/unlock               - specialization_unlock()
Line 5185: GET  /onboarding/start                    - onboarding_start()
Line 5221: POST /onboarding/set-birthdate            - onboarding_set_birthdate()
Line 5255: POST /onboarding/select-specialization    - onboarding_select_specialization()
```

### Dashboard Routes (2 routes) - `dashboard.py`
```
Line 325: GET /dashboard            - dashboard()
Line 326: GET /dashboard-fresh      - dashboard() (cache bypass)
Line 788: GET /dashboard/{spec_type} - spec_dashboard()
```

### Specialization Routes (6 routes) - `specialization.py`
```
Line 1114: GET  /specialization/motivation                     - student_motivation_questionnaire_page()
Line 1152: POST /specialization/motivation-submit              - student_motivation_questionnaire_submit()
Line 1269: GET  /specialization/lfa-player/onboarding          - lfa_player_onboarding_page()
Line 1308: GET  /specialization/lfa-player/onboarding-cancel   - lfa_player_onboarding_cancel()
Line 1358: POST /specialization/lfa-player/onboarding-submit   - lfa_player_onboarding_submit()
Line 1447: POST /specialization/switch                          - specialization_switch()
```

### Profile Routes (3 routes) - `profile.py`
```
Line 1639: GET  /profile       - profile_page()
Line 1751: GET  /profile/edit  - profile_edit_page()
Line 1776: POST /profile/edit  - profile_edit_submit()
```

### Student Features (4 routes) - `student_features.py`
```
Line 1910: GET /about-specializations  - about_specializations_page()
Line 1935: GET /credits                - credits_page()
Line 2074: GET /progress               - progress_page()
Line 2279: GET /achievements           - achievements_page()
Line 2343: GET /calendar               - calendar_page()
```

### Sessions (9 routes) - `sessions.py`
```
Line 1498: POST /enrollment/request                  - enrollment_request()
Line 2365: GET  /sessions                            - sessions_page()
Line 2541: POST /sessions/book/{session_id}          - book_session()
Line 2603: POST /sessions/cancel/{session_id}        - cancel_booking()
Line 2674: GET  /sessions/{session_id}               - session_details()
Line 4104: GET  /api/sessions/calendar               - get_calendar_sessions()
Line 5001: GET  /semesters/enroll                    - semester_enrollment_page()
Line 5071: POST /semesters/request-enrollment        - request_semester_enrollment()
Line 5146: POST /semesters/withdraw-enrollment       - withdraw_semester_enrollment()
```

### Attendance (3 routes) - `attendance.py`
```
Line 2926: POST /sessions/{session_id}/attendance/mark            - mark_attendance()
Line 3070: POST /sessions/{session_id}/attendance/confirm         - confirm_attendance()
Line 3157: POST /sessions/{session_id}/attendance/change-request  - handle_change_request()
```

### Quiz (3 routes) - `quiz.py`
```
Line 3429: POST /sessions/{session_id}/unlock-quiz  - unlock_quiz()
Line 3491: GET  /quizzes/{quiz_id}/take             - take_quiz()
Line 3628: POST /quizzes/{quiz_id}/submit           - submit_quiz()
```

### Instructor (5 routes) - `instructor.py`
```
Line 3255: POST /instructor/specialization/toggle                        - toggle_instructor_specialization()
Line 3290: POST /sessions/{session_id}/start                             - start_session()
Line 3354: POST /sessions/{session_id}/stop                              - stop_session()
Line 3837: POST /sessions/{session_id}/evaluate-student/{student_id}     - evaluate_student_performance()
Line 3990: POST /sessions/{session_id}/evaluate-instructor               - evaluate_instructor_session()
```

### Instructor Dashboard (3 routes) - `instructor_dashboard.py`
```
Line 4549: GET  /instructor/enrollments                           - instructor_enrollments_page()
Line 4620: GET  /instructor/students/{student_id}/skills/{license_id}  - instructor_edit_student_skills_page()
Line 4680: POST /instructor/students/{student_id}/skills/{license_id}  - instructor_update_student_skills()
```

### Admin (8 routes) - `admin.py`
```
Line 4172: GET  /admin/users                                       - admin_users_page()
Line 4198: GET  /admin/semesters                                   - admin_semesters_page()
Line 4225: GET  /admin/enrollments                                 - admin_enrollments_page()
Line 4405: GET  /admin/payments                                    - admin_payments_page()
Line 4469: GET  /admin/coupons                                     - admin_coupons_page()
Line 4504: GET  /admin/invitation-codes                            - admin_invitation_codes_page()
Line 4835: GET  /admin/analytics                                   - admin_analytics_page()
Line 4879: GET  /admin/students/{student_id}/motivation/{specialization}  - motivation_assessment_page()
Line 4929: POST /admin/students/{student_id}/motivation/{specialization}  - motivation_assessment_submit()
```

---

## 🔧 REFACTORING STRATEGY

### Phase 1: Helpers & Shared Utilities ✅
- [x] Extract `update_specialization_xp()` to helpers.py
- [x] Extract `get_lfa_age_category()` to helpers.py
- [x] Create `web_routes/helpers.py` (138 lines)

### Phase 2: Extract Route Modules (Current)
**Approach:** Copy routes from web_routes.py to modular files

**For Each Module:**
1. Read relevant lines from web_routes.py
2. Create new module file with proper imports
3. Copy route functions with minimal changes
4. Add module-specific router
5. Test imports

**Order of Extraction:** (Logical dependency order)
1. auth.py - Core authentication (no dependencies)
2. onboarding.py - Depends on auth
3. profile.py - Simple user data
4. student_features.py - Independent features
5. dashboard.py - Aggregates other data
6. specialization.py - Complex logic
7. sessions.py - Session management
8. attendance.py - Session-related
9. quiz.py - Session-related
10. instructor.py - Instructor operations
11. instructor_dashboard.py - Instructor UI
12. admin.py - Admin UI

### Phase 3: Router Aggregation
**File:** `web_routes/__init__.py`

```python
from fastapi import APIRouter
from . import (
    auth, onboarding, dashboard, specialization,
    profile, student_features, sessions, attendance,
    quiz, instructor, instructor_dashboard, admin
)

router = APIRouter(tags=["web"])

# Include all sub-routers
router.include_router(auth.router)
router.include_router(onboarding.router)
router.include_router(dashboard.router)
router.include_router(specialization.router)
router.include_router(profile.router)
router.include_router(student_features.router)
router.include_router(sessions.router)
router.include_router(attendance.router)
router.include_router(quiz.router)
router.include_router(instructor.router)
router.include_router(instructor_dashboard.router)
router.include_router(admin.router)
```

### Phase 4: Update Main Router
**File:** `app/api/web_routes.py` → Becomes slim router aggregator

**Replace with:**
```python
"""
Web routes for HTML template rendering
Refactored into modular components in web_routes/ directory
"""
from fastapi import APIRouter
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Import spec-based route modules
from .routes import lfa_player_routes, gancuju_routes, internship_routes, lfa_coach_routes

# Import web route modules
from .web_routes import (
    auth, onboarding, dashboard, specialization,
    profile, student_features, sessions, attendance,
    quiz, instructor, instructor_dashboard, admin
)

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["web"])

# Include web routes
router.include_router(auth.router)
router.include_router(onboarding.router)
router.include_router(dashboard.router)
router.include_router(specialization.router)
router.include_router(profile.router)
router.include_router(student_features.router)
router.include_router(sessions.router)
router.include_router(attendance.router)
router.include_router(quiz.router)
router.include_router(instructor.router)
router.include_router(instructor_dashboard.router)
router.include_router(admin.router)

# Include spec-based routes
router.include_router(lfa_player_routes.router)
router.include_router(gancuju_routes.router)
router.include_router(internship_routes.router)
router.include_router(lfa_coach_routes.router)
```

### Phase 5: Testing
- [ ] Import validation
- [ ] Backend startup test
- [ ] Route accessibility test
- [ ] Integration test with frontend

---

## ⚠️ CRITICAL CONSIDERATIONS

### Shared Dependencies
**All modules need:**
- `fastapi.APIRouter`
- `fastapi.templating.Jinja2Templates`
- Database session: `Depends(get_db)`
- Auth: `Depends(get_current_user_web)`
- Models imported locally to avoid circular dependencies

**Template setup** (needed in each module):
```python
from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
```

### Import Path Changes
**Old:**
```python
from ..models.user import User  # From web_routes.py
```

**New:**
```python
from ...models.user import User  # From web_routes/module.py (one more level)
```

### Helper Function Usage
**Old:**
```python
_update_specialization_xp(db, student_id, ...)  # Local function
```

**New:**
```python
from .helpers import update_specialization_xp  # Import from helpers
update_specialization_xp(db, student_id, ...)  # No underscore prefix
```

---

## 📊 PROGRESS TRACKING

**Overall Progress:** 2.5% (138 / 5,381 lines refactored)

**Completed:**
- ✅ Directory structure
- ✅ Helper functions extracted

**In Progress:**
- ⏳ Documentation

**Pending:**
- ⏳ 59 route functions across 13 modules
- ⏳ Router aggregation
- ⏳ Main router update
- ⏳ Testing

**Estimated Remaining Time:** 5-6 hours

---

## 🚀 NEXT STEPS

1. **Immediate:** Extract auth.py routes (lines 122-229)
2. **Then:** Extract onboarding.py routes
3. **Continue:** Systematically extract remaining 11 modules
4. **Finally:** Aggregate routers and test

---

**Status:** 🟡 Phase 1 Complete | Phase 2 Starting
**Last Updated:** 2025-12-20 19:35 CET
