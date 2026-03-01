# 29 Failed Tests - Kategorizált Breakdown (2026-03-01, post-BATCH 10)

## Összefoglaló

**Előzmény:** 39 → 31 (BATCH 10 Phase 2) → 29 (BATCH 10 Phase 3)

| Kategória | Darabszám | % | Priority |
|-----------|-----------|---|----------|
| **404 (Routing/Missing Endpoint)** | 20+ | ~69% | P1 |
| **Fixture/Data Issues** | 4 | ~14% | P2 |
| **Validation Schema** | 3-5 | ~17% | P1 |

---

## 1. Routing/404 Issues (~20 tests)

**Pattern:** Endpoint returns 404 instead of 422. Lehet hogy: endpoint hiányzik, routing konfig rossz, vagy ID-based lookup-nál nincs valid ID fixture.

### Attendance (1 test)
1. `test_checkin_input_validation` - POST /api/v1/attendance/57672/checkin
   - Error: 404 "Booking not found"
   - Root cause: ID 57672 nem létezik fixture-ben

### Campuses (2 tests)
2. `test_toggle_campus_status_input_validation` - PATCH /api/v1/campuses/1/toggle-status
3. `test_update_campus_input_validation` - PUT /api/v1/campuses/1

### Gancuju (1 test)
4. `test_instructor_promote_belt_input_validation` - POST /api/v1/instructor/students/2/promote-belt/3

### Instructor Assignments (1 test)
5. `test_cancel_assignment_request_input_validation` - PATCH /api/v1/requests/1/cancel

### Instructor (1 test)
6. `test_toggle_instructor_specialization_input_validation` - POST /api/v1/instructor/specialization/toggle

### Internship (1 test)
7. `test_instructor_progress_student_level_input_validation` - POST /api/v1/instructor/students/2/progress-level/3

### Invitation Codes (1 test)
8. `test_create_invitation_code_input_validation` - POST /api/v1/admin/invitation-codes

### LFA Coach Routes (2 tests)
9. `test_instructor_certify_coach_input_validation` - POST /api/v1/instructor/students/2/certify/3
10. `test_track_teaching_hours_input_validation` - POST /api/v1/instructor/students/2/track-teaching-hours/3

### Locations (2 tests)
11. `test_create_location_input_validation` - POST /api/v1/admin/locations
12. `test_update_location_input_validation` - PUT /api/v1/admin/locations/1

### Motivation (1 test)
13. `test_submit_motivation_assessment_input_validation` - POST /api/v1/licenses/motivation-assessment

### Onboarding (2 tests)
14. `test_lfa_player_onboarding_submit_input_validation` - POST /api/v1/specialization/lfa-player/onboarding-submit
15. `test_specialization_select_submit_input_validation` - POST /api/v1/specialization/select

### Periods (4 tests)
16. `test_generate_lfa_player_amateur_season_input_validation` - POST /api/v1/lfa-player/amateur
17. `test_generate_lfa_player_pre_season_input_validation` - POST /api/v1/lfa-player/pre
18. `test_generate_lfa_player_pro_season_input_validation` - POST /api/v1/lfa-player/pro
19. `test_generate_lfa_player_youth_season_input_validation` - POST /api/v1/lfa-player/youth

### Quiz (3 tests)
20. `test_create_quiz_input_validation` - POST /api/v1/quizzes
21. `test_submit_quiz_input_validation` - POST /api/v1/quizzes/1/submit
22. `test_unlock_quiz_input_validation` - POST /api/v1/sessions/367/unlock-quiz

### Semester Generator (1 test)
23. `test_generate_semesters_input_validation` - POST /api/v1/admin/semesters/generate

### Sessions (1 test)
24. `test_cancel_booking_input_validation` - POST /api/v1/sessions/cancel/419

### Tournaments (1 test)
25. `test_accept_instructor_request_input_validation` - POST /api/v1/requests/1/accept

---

## 2. Fixture/Data Issues (4 tests)

**Pattern:** Endpoint exists, validation works, but test fixture setup broken.

1. `test_get_all_bookings_happy_path` - Bookings smoke
2. `test_stop_session_happy_path` - Instructor smoke
3. `test_unlock_quiz_happy_path` - Instructor smoke
4. `test_validate_assessment_happy_path` - Licenses smoke

---

## 3. Validation Schema Issues (0-3 tests)

**Pattern:** Endpoint exists at correct path but validation schema hiányzik vagy rossz.

- Quiz validation schemas already have extra='forbid' (BATCH 10 Phase 2)
- Onboarding schemas already have extra='forbid' (BATCH 10 Phase 2)
- Locations/Campuses schemas need verification

**Remaining candidates:**
- Campuses (2) - need to check if schemas have extra='forbid'
- Locations (2) - need to check if schemas have extra='forbid'

---

## Következő Lépések (Javasolt Stratégia)

### Option A: STOP Quick Wins - Részletes Investigation
- **Scope:** Végezzünk el 3-5 konkrét teszt verbose futtatását
- **Goal:** Pontos root cause per teszt (404 oka: endpoint missing? fixture missing? routing?)
- **Impact:** Megértjük a valódi okokat

### Option B: Targeted Fixture Fixes (Low-Hanging Fruit)
- **Scope:** 4 happy_path fixture issue → gyors fix
- **Impact:** 29 → 25 (-4 tests)
- **Effort:** Low (1-2 óra)

### Option C: Comprehensive Routing Analysis
- **Scope:** 20+ routing issue → systematikus endpoint verification
- **Impact:** 29 → <10 (potenciálisan)
- **Effort:** High (4-6 óra)

---

## Recommendation

**👉 Option A: Detailed Investigation First**

Futassunk 3 konkrét testet verbose módban:
1. `test_checkin_input_validation` (404 Booking not found)
2. `test_generate_lfa_player_amateur_season_input_validation` (404 routing?)
3. `test_create_quiz_input_validation` (schema vagy routing?)

**Goal:** Objektív root cause analysis → data-driven döntés a következő batch-hez

**STOP:** Ne implementáljunk újabb batch-et addig, amíg nincs tiszta kép a 404-ek okáról.

