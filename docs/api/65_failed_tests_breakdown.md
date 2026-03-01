# 65 Failed Tests - CI Run 22537418667

**Date:** 2026-03-01 06:17
**Result:** 65 failed, 1212 passed, 445 skipped
**Progress:** 69 → 65 (-4 from BATCH 2: sessions/management)

---

## 📊 Category Breakdown

| Category | Count | Type |
|----------|-------|------|
| 🔴 MISSING_ENDPOINT | 37 | 404 - Endpoint not implemented |
| 🔴 AUTH_PERMISSION | 8 | 403 - Permission denied |
| 🔴 VALIDATION_BUG | 4 | 200 - Accepts empty body (should 422) |
| 🔴 ROUTING_MISMATCH | 16 | 404 - Path/prefix issue |

**Total:** 65 tests

---

## 🔴 VALIDATION_BUG: 4 tests (QUICK WIN - Similar to BATCH 2)

These endpoints accept empty body (200 OK) instead of validating (422):

| Endpoint | Domain | Fix |
|----------|--------|-----|
| `POST /api/v1/students/2/unverify` | Payment Verification | Add schema with `extra='forbid'` |
| `POST /api/v1/tournaments/{id}/calculate-rankings` | Tournaments | Add schema OR remove body requirement |
| `POST /api/v1/tournaments/{id}/finalize-group-stage` | Tournaments | Add schema OR remove body requirement |
| `POST /api/v1/tournaments/{id}/finalize-tournament` | Tournaments | Add schema OR remove body requirement |

**Effort:** 2-3 hours
**Impact:** -4 tests (65 → 61)

---

## 🔴 ROUTING_MISMATCH: 16 tests

Tests expect different path than where endpoint is mounted:

### Sessions (1 test)
- `POST /api/v1/{id}/check-in` → Should be `/api/v1/sessions/{id}/check-in`

### Campuses (3 tests) - **KNOWN ISSUE from BATCH 1**
- `POST /api/v1/locations/{id}/campuses` → Mounted at `/api/v1/admin/locations/{id}/campuses`
- `PUT /api/v1/campuses/{id}` → Mounted at `/api/v1/admin/campuses/{id}`
- `PATCH /api/v1/campuses/{id}/toggle-status` → Mounted at `/api/v1/admin/campuses/{id}/toggle-status`

### Coupons (4 tests) - **KNOWN ISSUE**
- All coupon endpoints expect `/api/v1/admin/coupons` prefix

### Other (8 tests)
- Various routing mismatches in projects, bookings, attendance, etc.

**Note:** These are test infrastructure issues, not code bugs. Endpoints exist but at different paths.

---

## 🔴 MISSING_ENDPOINT: 37 tests

Endpoints not implemented in OpenAPI schema:

### Invitation Codes (1 endpoint)
- `POST /api/v1/admin/invitation-codes`

### Invoices (2 endpoints)
- `POST /api/v1/invoices/{id}/verify`
- `POST /api/v1/invoices/{id}/unverify`

### LFA Coach Routes (2 endpoints)
- `POST /api/v1/instructor/students/{id}/certify/{license}`
- `POST /api/v1/instructor/students/{id}/track-teaching-hours/{license}`

### Licenses/Assessments (3 endpoints)
- `POST /api/v1/assessments/{id}/archive`
- `POST /api/v1/assessments/{id}/validate`
- `POST /api/v1/licenses/{id}/skills/{skill}/assess`

### Locations (2 endpoints)
- `POST /api/v1/admin/locations`
- `PUT /api/v1/admin/locations/{id}`

### Motivation (1 endpoint)
- `POST /api/v1/licenses/motivation-assessment`

### Onboarding (2 endpoints)
- `POST /api/v1/specialization/lfa-player/onboarding-submit`
- `POST /api/v1/specialization/select`

### Periods (4 endpoints)
- `POST /api/v1/lfa-player/amateur`
- `POST /api/v1/lfa-player/pre`
- `POST /api/v1/lfa-player/pro`
- `POST /api/v1/lfa-player/youth`

### Projects (1 endpoint)
- `POST /api/v1/projects/{id}/confirm-enrollment`

### Quiz (2 endpoints)
- `POST /api/v1/quizzes` (create)
- `POST /api/v1/quizzes/{id}/submit`

### Semester Generator (1 endpoint)
- `POST /api/v1/admin/semesters/generate`

### Sessions (1 endpoint)
- `POST /api/v1/sessions/cancel/{id}`

### System Events (2 endpoints)
- `PATCH /api/v1/system-events/{id}/resolve`
- `PATCH /api/v1/system-events/{id}/unresolve`

---

## 🔴 AUTH_PERMISSION: 8 tests

Permission denied (403) - likely role check too strict:

| Endpoint | Domain | Issue |
|----------|--------|-------|
| `POST /api/v1/{id}/enroll` | Projects | Student role check |
| `POST /api/v1/{id}/instructor/enroll/{student_id}` | Projects | Instructor role check |
| `POST /api/v1/{id}/milestones/{mid}/submit` | Projects | Student ownership |
| `POST /api/v1/{id}/milestones/{mid}/approve` | Projects | Instructor role check |
| `POST /api/v1/{session_id}/check-in` | Sessions | Instructor role check |
| `POST /api/v1/instructor/advance` | Licenses | Admin role check |
| `POST /api/v1/requests/{id}/accept` | Tournaments | Instructor acceptance |
| `POST /api/v1/tournaments/{id}/instructor-assignment/accept` | Tournaments | Assignment acceptance |

---

## 🎯 Next Batch Recommendation

### BATCH 3: VALIDATION_BUG - 4 endpoints (QUICK WIN)

**Files to modify:**
1. `app/api/api_v1/endpoints/payment_verification.py` - unverify endpoint
2. `app/api/api_v1/endpoints/tournaments/*.py` - calculate-rankings, finalize-group-stage, finalize-tournament

**Pattern (same as BATCH 2):**
- Create empty request schema with `model_config = {"extra": "forbid"}`
- Add to endpoint signature
- Update docstring with validation note

**Expected Impact:** 65 → 61 failed (-4 tests)
**Effort:** 2-3 hours
**Success Rate:** 100% (proven pattern from BATCH 2)

---

## Progress Tracker

| Batch | Domain | Tests Fixed | Running Total |
|-------|--------|-------------|---------------|
| Start | - | - | 73 |
| BATCH 1 | Campuses | -5 | 68 |
| BATCH 2 | Sessions/Management | -4 | **65** |
| BATCH 3 | Validation Bug (4 endpoints) | -4 (projected) | 61 (target) |

**Goal:** Below 60 failed tests
**Status:** 5 tests away from goal ✅
