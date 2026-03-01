# BATCH 11 - URL Mismatch Audit (2026-03-01)

## Összefoglaló

**29 failed tests** kategorizálva URL pattern mismatch szerint.

| Pattern Type | Count | Fix Type | Examples |
|--------------|-------|----------|----------|
| **PREFIX: /periods/ instead of direct** | 4 | Remove `/periods/` | /periods/lfa-player/* → /lfa-player/* |
| **PREFIX: /quiz/ instead of /quizzes/** | 3 | Replace `/quiz/` → `/quizzes/` | /quiz/quizzes/* → /quizzes/* |
| **BUSINESS LOGIC 404 (ID lookup)** | ~15 | Fixture/Mock (out of scope) | attendance/{id}/checkin |
| **TRUE ENDPOINT MISSING** | ~7 | Implementation needed | POST /api/v1/instructor/specialization/toggle |

---

## GROUP A: Clear Path Mismatch - PREFIX Issues (7 tests) ⚡

**Fix Type:** Simple find/replace in test files

### A.1 Periods - /periods/lfa-player/* → /lfa-player/* (4 tests)

| Test Function | Expected URL | Actual URL in Test | Line | Fix |
|---------------|-------------|-------------------|------|-----|
| `test_generate_lfa_player_amateur_season_input_validation` | `/api/v1/lfa-player/amateur` | `/api/v1/periods/lfa-player/amateur` | test_periods_smoke.py:83 | Remove `/periods` |
| `test_generate_lfa_player_pre_season_input_validation` | `/api/v1/lfa-player/pre` | `/api/v1/periods/lfa-player/pre` | test_periods_smoke.py:161 | Remove `/periods` |
| `test_generate_lfa_player_pro_season_input_validation` | `/api/v1/lfa-player/pro` | `/api/v1/periods/lfa-player/pro` | test_periods_smoke.py:239 | Remove `/periods` |
| `test_generate_lfa_player_youth_season_input_validation` | `/api/v1/lfa-player/youth` | `/api/v1/periods/lfa-player/youth` | test_periods_smoke.py:317 | Remove `/periods` |

**Fix Command:**
```bash
# test_periods_smoke.py - Replace all occurrences
sed -i '' 's|/api/v1/periods/lfa-player/|/api/v1/lfa-player/|g' tests/integration/api_smoke/test_periods_smoke.py
```

### A.2 Quiz - /quiz/* → /quizzes/* (3 tests)

| Test Function | Expected URL | Actual URL in Test | Line | Fix |
|---------------|-------------|-------------------|------|-----|
| `test_submit_quiz_input_validation` | `/api/v1/quizzes/{id}/submit` | `/api/v1/quiz/quizzes/{id}/submit` | test_quiz_smoke.py:914 | Remove `/quiz` prefix |
| `test_unlock_quiz_input_validation` | `/api/v1/sessions/{id}/unlock-quiz` | `/api/v1/quiz/sessions/{id}/unlock-quiz` | test_quiz_smoke.py:995 | Remove `/quiz` prefix |

**Fix Command:**
```bash
# test_quiz_smoke.py - Replace quiz/ prefix
sed -i '' 's|/api/v1/quiz/quizzes/|/api/v1/quizzes/|g' tests/integration/api_smoke/test_quiz_smoke.py
sed -i '' 's|/api/v1/quiz/sessions/|/api/v1/sessions/|g' tests/integration/api_smoke/test_quiz_smoke.py
```

**TOTAL GROUP A: 7 tests → instant fix**

---

## GROUP B: Business Logic 404 (ID-based lookup) (~15 tests) 🔧

**Pattern:** Endpoint létezik, de ID nem található az adatbázisban. **NEM test path issue!**

**Fix Type:** Fixture vagy mock - OUT OF SCOPE for BATCH 11

### Examples:
1. `test_checkin_input_validation` - POST /api/v1/attendance/57705/checkin
   - Error: "Booking not found" 
   - Fix: Create valid booking fixture

2. `test_toggle_campus_status_input_validation` - PATCH /api/v1/campuses/11/toggle-status
   - Error: Campus ID 11 not found
   - Fix: Create campus ID 11 fixture

3. `test_update_campus_input_validation` - PUT /api/v1/campuses/11
   - Error: Campus ID 11 not found
   - Fix: Create campus ID 11 fixture

4. `test_instructor_promote_belt_input_validation` - POST /api/v1/instructor/students/36400/promote-belt/72137
   - Error: Student/License not found
   - Fix: Create student/license fixtures

5. `test_instructor_progress_student_level_input_validation` - POST /api/v1/instructor/students/36400/progress-level/72137
   - Error: Student/License not found
   - Fix: Create student/license fixtures

6. `test_instructor_certify_coach_input_validation` - POST /api/v1/instructor/students/36400/certify/72137
   - Error: Student/License not found
   - Fix: Create student/license fixtures

7. `test_track_teaching_hours_input_validation` - POST /api/v1/instructor/students/36400/track-teaching-hours/72137
   - Error: Student/License not found
   - Fix: Create student/license fixtures

**Decision:** SKIP in BATCH 11 - different fix strategy needed

---

## GROUP C: True Endpoint Missing (~7 tests) 🏗️

**Pattern:** Endpoint not implemented or router not registered. **Implementation required.**

**Fix Type:** Implementation - OUT OF SCOPE for BATCH 11

### Examples:
1. `test_create_invitation_code_input_validation` - POST /api/v1/admin/invitation-codes
   - Status: Endpoint missing or routing issue

2. `test_toggle_instructor_specialization_input_validation` - POST /api/v1/instructor/specialization/toggle
   - Status: Endpoint missing

3. `test_create_location_input_validation` - POST /api/v1/admin/locations
   - Status: Endpoint missing

4. `test_update_location_input_validation` - PUT /api/v1/admin/locations/1
   - Status: Endpoint missing

5. `test_submit_motivation_assessment_input_validation` - POST /api/v1/licenses/motivation-assessment
   - Status: Endpoint missing

6. `test_lfa_player_onboarding_submit_input_validation` - POST /api/v1/specialization/lfa-player/onboarding-submit
   - Status: Endpoint missing

7. `test_specialization_select_submit_input_validation` - POST /api/v1/specialization/select
   - Status: Endpoint missing

**Decision:** SKIP in BATCH 11 - requires endpoint implementation

---

## BATCH 11 Execution Plan

### Phase 2: Fix Only GROUP A (7 clear path mismatches)

**Commands:**
```bash
# Periods - Remove /periods/ prefix
sed -i '' 's|/api/v1/periods/lfa-player/|/api/v1/lfa-player/|g' tests/integration/api_smoke/test_periods_smoke.py

# Quiz - Remove /quiz/ prefix
sed -i '' 's|/api/v1/quiz/quizzes/|/api/v1/quizzes/|g' tests/integration/api_smoke/test_quiz_smoke.py
sed -i '' 's|/api/v1/quiz/sessions/|/api/v1/sessions/|g' tests/integration/api_smoke/test_quiz_smoke.py
```

**Expected Impact:** 29 → 22 (-7 tests)

**Verification:**
```bash
pytest tests/integration/api_smoke/ --tb=no --maxfail=100 -q
```

---

## Decision Matrix

| Action | Tests Fixed | Effort | Risk |
|--------|-------------|--------|------|
| **GROUP A: Path Fix** | **7** | ⚡ 5 min | ✅ Zero |
| GROUP B: Fixture/Mock | 15 | 🔧 2-3 hours | ⚠️ Medium |
| GROUP C: Implementation | 7 | 🏗️ 4-6 hours | ⚠️ High |

**Recommendation:** Execute GROUP A only in BATCH 11.

