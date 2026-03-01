# 37 Failed Tests - Kategorikus Breakdown (2026-03-01)

## Összefoglaló

| Kategória | Darabszám | % |
|-----------|-----------|---|
| **Routing (404)** | 30 | 81.1% |
| **Permission (403)** | 3 | 8.1% |
| **Fixture/Data** | 4 | 10.8% |
| **Validation** | 0 | 0% |
| **TOTAL** | **37** | **100%** |

---

## 1. Routing Issues (404) - 30 tests

**Pattern:** Endpoint does not exist or not registered. Test expects 422 on invalid input but gets 404.

### Attendance (1 test)
1. `test_checkin_input_validation` - POST /api/v1/attendance/32/checkin

### Bookings (2 tests)
2. `test_update_booking_attendance_input_validation` - PATCH /api/v1/bookings/41/attendance
3. `test_confirm_booking_input_validation` - POST /api/v1/bookings/47/confirm

### Campuses (2 tests)
4. `test_toggle_campus_status_input_validation` - PATCH /api/v1/campuses/1/toggle-status
5. `test_update_campus_input_validation` - PUT /api/v1/campuses/1

### Gancuju Routes (1 test)
6. `test_instructor_promote_belt_input_validation` - POST /api/v1/instructor/students/2/promote-belt/3

### Instructor Assignments (1 test)
7. `test_cancel_assignment_request_input_validation` - PATCH /api/v1/requests/1/cancel

### Instructor (1 test)
8. `test_toggle_instructor_specialization_input_validation` - POST /api/v1/instructor/specialization/toggle

### Internship Routes (1 test)
9. `test_instructor_progress_student_level_input_validation` - POST /api/v1/instructor/students/2/progress-level/3

### Invitation Codes (1 test)
10. `test_create_invitation_code_input_validation` - POST /api/v1/admin/invitation-codes

### Invoices (2 tests)
11. `test_unverify_invoice_payment_input_validation` - POST /api/v1/invoices/1/unverify
12. `test_verify_invoice_payment_input_validation` - POST /api/v1/invoices/1/verify

### LFA Coach Routes (2 tests)
13. `test_instructor_certify_coach_input_validation` - POST /api/v1/instructor/students/2/certify/3
14. `test_track_teaching_hours_input_validation` - POST /api/v1/instructor/students/2/track-teaching-hours/3

### Locations (2 tests)
15. `test_create_location_input_validation` - POST /api/v1/admin/locations
16. `test_update_location_input_validation` - PUT /api/v1/admin/locations/1

### Motivation (1 test)
17. `test_submit_motivation_assessment_input_validation` - POST /api/v1/licenses/motivation-assessment

### Onboarding (2 tests)
18. `test_lfa_player_onboarding_submit_input_validation` - POST /api/v1/specialization/lfa-player/onboarding-submit
19. `test_specialization_select_submit_input_validation` - POST /api/v1/specialization/select

### Periods (4 tests)
20. `test_generate_lfa_player_amateur_season_input_validation` - POST /api/v1/lfa-player/amateur
21. `test_generate_lfa_player_pre_season_input_validation` - POST /api/v1/lfa-player/pre
22. `test_generate_lfa_player_pro_season_input_validation` - POST /api/v1/lfa-player/pro
23. `test_generate_lfa_player_youth_season_input_validation` - POST /api/v1/lfa-player/youth

### Quiz (3 tests)
24. `test_create_quiz_input_validation` - POST /api/v1/quizzes
25. `test_submit_quiz_input_validation` - POST /api/v1/quizzes/1/submit
26. `test_unlock_quiz_input_validation` - POST /api/v1/sessions/367/unlock-quiz

### Semester Generator (1 test)
27. `test_generate_semesters_input_validation` - POST /api/v1/admin/semesters/generate

### Sessions (1 test)
28. `test_cancel_booking_input_validation` - POST /api/v1/sessions/cancel/419

### System Events (2 tests)
29. `test_resolve_event_input_validation` - PATCH /api/v1/system-events/1/resolve
30. `test_unresolve_event_input_validation` - PATCH /api/v1/system-events/1/unresolve

---

## 2. Permission Issues (403) - 3 tests

**Pattern:** Endpoint checks permission BEFORE validating input. Should return 422 on invalid input, not 403.

1. `test_check_in_to_session_input_validation` - POST /api/v1/422/check-in
   - Returns 403 instead of 422 on invalid body

2. `test_accept_instructor_request_input_validation` - POST /api/v1/requests/1/accept
   - Returns 403 instead of 422 on invalid body

3. `test_accept_instructor_assignment_input_validation` - POST /api/v1/tournaments/566/instructor-assignment/accept
   - Returns 403 instead of 422 on invalid body

**Fix:** Move validation BEFORE permission checks in FastAPI dependency chain.

---

## 3. Fixture/Data Issues (happy_path tests) - 4 tests

**Pattern:** Endpoint exists, validation works, but test setup/fixtures are broken.

1. `test_stop_session_happy_path` - test_instructor_smoke.py
   - Error: 400 "Session has not been started yet"
   - Issue: Test tries to stop a session that was never started

2. `test_unlock_quiz_happy_path` - test_instructor_smoke.py
   - Error: AttributeError 'Session' object has no attribute 'quiz_id'
   - Issue: Session model missing quiz_id field or test fixture incomplete

3. `test_archive_assessment_happy_path` - test_licenses_smoke.py
   - Error: 400 "Assessment 1 not found"
   - Issue: Test fixture doesn't create assessment before trying to archive

4. `test_validate_assessment_happy_path` - test_licenses_smoke.py
   - Error: 400 "Assessment 1 not found"
   - Issue: Test fixture doesn't create assessment before trying to validate

**Fix:** Update test fixtures to properly set up test data.

---

## 4. Validation Issues - 0 tests

All validation issues currently manifest as routing (404) problems. Once endpoints are implemented/registered, validation schemas will need to be added.

---

## Döntési Mátrix

### Option A: Routing + Permission elimination (30 + 3 = 33 tests)
- **Scope:** Fix routing (implement/register missing endpoints) + fix permission order
- **Impact:** 37 → 4 (89.2% reduction)
- **Effort:** High (30 endpoints to implement/investigate)
- **Risk:** Medium (might reveal more hidden issues)

### Option B: Fixture stabilization first (4 tests)
- **Scope:** Fix test fixtures for happy_path tests
- **Impact:** 37 → 33 (10.8% reduction)
- **Effort:** Low (fix 4 test fixtures)
- **Risk:** Low (isolated to test code)

---

## Javasolt Stratégia

**👉 Option A: Routing + Permission elimination**

**Indoklás:**
- Routing (30) + Permission (3) = **33 tests (89.2%)**
- Fixture csak 4 test (10.8%) - ez külön kezelhető később
- 30 routing issue nagy része lehet gyors fix (missing router registration, routing alias)
- Hasonló a BATCH 7-8-9 mintához

**Következő lépések:**
1. Routing analysis - kategorizálás domain szerint
2. Gyors quick wins (router registration, aliasok)
3. Permission fix (3 endpoint - validation before auth check)
4. Fixture fixes külön batch-ben (test stabilization)

**Cél:** 37 → <10 (routing/permission elimination)
