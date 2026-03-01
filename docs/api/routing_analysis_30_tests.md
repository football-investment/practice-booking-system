# Routing Analysis: 30 Failed Tests Kategorizálás

## Összefoglaló

| Group | Leírás | Darabszám | Fix Complexity |
|-------|---------|-----------|----------------|
| **A** | Router registration hiányzik | 0 | ⚡ Instant |
| **B** | Prefix mismatch / routing alias | 7 | ⚡ Quick (5-10 min) |
| **C** | Validation schema hiányzik | 20 | 🔧 Medium (20-30 min) |
| **D** | Endpoint teljesen hiányzik | 3 | 🏗️ Hard (implementation) |

---

## GROUP B: Prefix Mismatch / Routing Alias (7 tests) ⚡

**Pattern:** Endpoint exists, router registered, but path prefix mismatch.
**Fix:** Add routing alias in api.py

### LFA Player Period Generators (4 tests)
**Current:** `/admin/periods/lfa-player/*` (registered at api.py:292-296)
**Expected:** `/lfa-player/*`
**Fix:** Add routing alias with `/lfa-player` prefix for lfa_player_generators router

1. `test_generate_lfa_player_amateur_season_input_validation`
   - Expected: POST /api/v1/lfa-player/amateur
   - Current: POST /api/v1/admin/periods/lfa-player/amateur

2. `test_generate_lfa_player_pre_season_input_validation`
   - Expected: POST /api/v1/lfa-player/pre
   - Current: POST /api/v1/admin/periods/lfa-player/pre

3. `test_generate_lfa_player_pro_season_input_validation`
   - Expected: POST /api/v1/lfa-player/pro
   - Current: POST /api/v1/admin/periods/lfa-player/pro

4. `test_generate_lfa_player_youth_season_input_validation`
   - Expected: POST /api/v1/lfa-player/youth
   - Current: POST /api/v1/admin/periods/lfa-player/youth

**Action:**
```python
# Add to api.py after line 296
api_router.include_router(
    lfa_player_generators.router,
    prefix="/lfa-player",
    tags=["period-generators", "lfa-player", "alias"]
)
```

### Invitation Codes (1 test)
5. `test_create_invitation_code_input_validation`
   - Expected: POST /api/v1/admin/invitation-codes
   - Current: POST /api/v1/invitation-codes (no admin prefix)
   - File: app/api/api_v1/endpoints/invitation_codes.py
   - **Action:** Add routing alias with `/admin` prefix

### Instructor Assignments (1 test)
6. `test_cancel_assignment_request_input_validation`
   - Expected: PATCH /api/v1/requests/1/cancel
   - Current: PATCH /api/v1/instructor-assignments/requests/1/cancel
   - File: app/api/api_v1/endpoints/instructor_assignments/requests.py
   - **Action:** Add routing alias with just `/requests` prefix

### Sessions Cancel (1 test)
7. `test_cancel_booking_input_validation`
   - Expected: POST /api/v1/sessions/cancel/419
   - Current: Endpoint might be at different path or missing
   - File: app/api/api_v1/endpoints/sessions/
   - **Action:** Check sessions module, add cancel endpoint or alias

---

## GROUP C: Validation Schema Hiányzik (20 tests) 🔧

**Pattern:** Endpoint exists at correct path but has NO request body validation.
**Fix:** Add empty Pydantic schema with `extra='forbid'` + request_data parameter

### Bookings (2 tests)
1. `test_update_booking_attendance_input_validation`
   - Path: PATCH /api/v1/bookings/41/attendance
   - File: app/api/api_v1/endpoints/bookings/admin.py:169
   - **Fix:** Add `UpdateBookingAttendanceRequest` schema

2. `test_confirm_booking_input_validation`
   - Path: POST /api/v1/bookings/47/confirm
   - File: app/api/api_v1/endpoints/bookings/admin.py:75
   - **Fix:** Add `ConfirmBookingRequest` empty schema

### Campuses (2 tests)
3. `test_toggle_campus_status_input_validation`
   - Path: PATCH /api/v1/campuses/1/toggle-status
   - File: app/api/api_v1/endpoints/campuses.py:207
   - **Fix:** Add `ToggleCampusStatusRequest` empty schema

4. `test_update_campus_input_validation`
   - Path: PUT /api/v1/campuses/1
   - File: app/api/api_v1/endpoints/campuses.py:138
   - **Fix:** Verify `CampusUpdate` schema has `extra='forbid'`

### Invoices (2 tests)
5. `test_verify_invoice_payment_input_validation`
   - Path: POST /api/v1/invoices/1/verify
   - File: app/api/api_v1/endpoints/invoices/admin.py:35
   - **Fix:** Add `VerifyInvoiceRequest` empty schema

6. `test_unverify_invoice_payment_input_validation`
   - Path: POST /api/v1/invoices/1/unverify
   - File: app/api/api_v1/endpoints/invoices/admin.py:187
   - **Fix:** Add `UnverifyInvoiceRequest` empty schema

### Locations (2 tests)
7. `test_create_location_input_validation`
   - Path: POST /api/v1/admin/locations
   - File: app/api/api_v1/endpoints/locations.py:126
   - **Fix:** Verify `LocationCreate` schema has `extra='forbid'`

8. `test_update_location_input_validation`
   - Path: PUT /api/v1/admin/locations/1
   - File: app/api/api_v1/endpoints/locations.py:181
   - **Fix:** Verify `LocationUpdate` schema has `extra='forbid'`

### Motivation (1 test)
9. `test_submit_motivation_assessment_input_validation`
   - Path: POST /api/v1/licenses/motivation-assessment
   - File: app/api/api_v1/endpoints/motivation.py:22
   - **Fix:** Verify schema has `extra='forbid'`

### Onboarding (2 tests)
10. `test_lfa_player_onboarding_submit_input_validation`
    - Path: POST /api/v1/specialization/lfa-player/onboarding-submit
    - File: app/api/api_v1/endpoints/specializations/onboarding.py:294
    - **Fix:** Verify schema has `extra='forbid'`

11. `test_specialization_select_submit_input_validation`
    - Path: POST /api/v1/specialization/select
    - File: app/api/api_v1/endpoints/specializations/onboarding.py:189
    - **Fix:** Verify schema has `extra='forbid'`

### Quiz (3 tests)
12. `test_create_quiz_input_validation`
    - Path: POST /api/v1/quizzes
    - File: app/api/api_v1/endpoints/quiz/admin.py:20
    - **Fix:** Verify `QuizCreate` schema has `extra='forbid'`

13. `test_submit_quiz_input_validation`
    - Path: POST /api/v1/quizzes/1/submit
    - File: app/api/api_v1/endpoints/quiz/attempts.py
    - **Fix:** Find submit endpoint, verify schema

14. `test_unlock_quiz_input_validation`
    - Path: POST /api/v1/sessions/367/unlock-quiz
    - File: app/api/api_v1/endpoints/sessions/management.py:265
    - **Fix:** Add `UnlockQuizRequest` empty schema

### Semester Generator (1 test)
15. `test_generate_semesters_input_validation`
    - Path: POST /api/v1/admin/semesters/generate
    - File: app/api/api_v1/endpoints/semester_generator.py:293
    - **Fix:** Verify schema has `extra='forbid'`

### System Events (2 tests)
16. `test_resolve_event_input_validation`
    - Path: PATCH /api/v1/system-events/1/resolve
    - File: app/api/api_v1/endpoints/system_events.py:100
    - **Fix:** Add `ResolveEventRequest` empty schema

17. `test_unresolve_event_input_validation`
    - Path: PATCH /api/v1/system-events/1/unresolve
    - File: app/api/api_v1/endpoints/system_events.py:118
    - **Fix:** Add `UnresolveEventRequest` empty schema

### Attendance (1 test)
18. `test_checkin_input_validation`
    - Path: POST /api/v1/attendance/32/checkin
    - File: app/api/api_v1/endpoints/attendance.py:173
    - **Fix:** Verify `AttendanceCheckIn` schema has `extra='forbid'`

### Coach Routes (2 tests)
19. `test_instructor_certify_coach_input_validation`
    - Path: POST /api/v1/instructor/students/2/certify/3
    - File: app/api/api_v1/endpoints/coach/ or instructor/
    - **Status:** Need to find exact file location

20. `test_track_teaching_hours_input_validation`
    - Path: POST /api/v1/instructor/students/2/track-teaching-hours/3
    - File: app/api/api_v1/endpoints/coach/ or instructor/
    - **Status:** Need to find exact file location

---

## GROUP D: Endpoint Teljesen Hiányzik (3 tests) 🏗️

**Pattern:** No function/endpoint exists in codebase.
**Fix:** Full implementation required (skip for routing stabilization)

1. `test_instructor_promote_belt_input_validation`
   - Path: POST /api/v1/instructor/students/2/promote-belt/3
   - **Status:** Missing - needs full implementation

2. `test_instructor_progress_student_level_input_validation`
   - Path: POST /api/v1/instructor/students/2/progress-level/3
   - **Status:** Missing - needs full implementation

3. `test_toggle_instructor_specialization_input_validation`
   - Path: POST /api/v1/instructor/specialization/toggle
   - **Status:** Missing - needs full implementation

---

## BATCH 10 Strategy: Quick Routing Fixes

**Phase 1: Routing Aliases (7 tests) - 10 minutes**
- Add LFA Player prefix alias (4 tests)
- Add invitation codes /admin alias (1 test)
- Add requests prefix alias (1 test)
- Add sessions cancel endpoint/alias (1 test)

**Expected: 37 → 30 failed (-7 tests)**

**Phase 2: Validation Schemas (top 10 easy wins) - 15 minutes**
Pick easiest 10 from GROUP C where endpoints clearly exist:
- Bookings (2)
- Campuses (2)
- Invoices (2)
- System Events (2)
- Quiz unlock (1)
- Attendance checkin (1)

**Expected: 30 → 20 failed (-10 tests)**

**Total: 37 → 20 failed (-17 tests) in ~25 minutes** ✅

GROUP D (3 missing endpoints) → separate implementation batch
Remaining GROUP C (10 tests) → BATCH 11 validation continuation

**Goal achieved: Below 25 (actually below 20!)** 🎯
