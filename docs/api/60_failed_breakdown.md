# 60 Failed Tests - Fresh Breakdown (BATCH 4 Result)

**CI Run:** 22538731131
**Date:** 2026-03-01 07:43
**Result:** 60 failed, 1217 passed, 445 skipped

**Progress:** 73 → 68 → 65 → 61 → **60** (-13 tests total, 82% of "below 60" goal)

---

## 📊 Domain Clustering

| Domain | Count | Type |
|--------|-------|------|
| **🎯 instructor_management** | **11** | **BIGGEST CLUSTER** |
| projects | 5 | Mixed (404 + 403) |
| periods | 4 | All 404 (missing endpoints) |
| licenses | 4 | Mixed (404 + 403) |
| coupons | 4 | All 404 (missing endpoints) |
| quiz | 3 | All 404 (missing endpoints) |
| instructor | 3 | Mixed (start PASSED, stop/unlock failed) |
| campuses | 3 | All 404 (routing mismatch) |
| tournaments | 2 | 403 (permission issues) |
| system_events | 2 | All 404 (missing endpoints) |
| sessions | 2 | Mixed |
| onboarding | 2 | All 404 (missing endpoints) |
| locations | 2 | All 404 (missing endpoints) |
| lfa_coach_routes | 2 | All 404 (missing endpoints) |
| invoices | 2 | All 404 (missing endpoints) |
| bookings | 2 | All 404 (missing endpoints) |
| Other (7 domains) | 7 | 1 test each |

**Total:** 60 tests

---

## 🎯 BATCH 5 Target: instructor_management (11 tests)

**All 11 tests fail with 404** - Missing endpoints or routing mismatches

### Routing Mismatches (3 tests)
These expect resource prefix but get root path:

| Test | Expected Path | Actual Call | Fix |
|------|---------------|-------------|-----|
| `test_update_assignment_input_validation` | `/instructor-management/assignments/{id}` | `PATCH /api/v1/1` | Path alias OR test fix |
| `test_update_master_instructor_input_validation` | `/instructor-management/masters/{id}` | `PATCH /api/v1/1` | Path alias OR test fix |
| `test_update_position_input_validation` | `/instructor-management/positions/{id}` | `PATCH /api/v1/1` | Path alias OR test fix |

### Missing Endpoints (8 tests)
These endpoints don't exist in the API:

| Endpoint | Test | Functionality |
|----------|------|---------------|
| `POST /instructor-management/applications` | 4 tests | Create application (multiple test variants) |
| `POST /instructor-management/masters/direct-hire` | 1 test | Direct hire master instructor |
| `POST /instructor-management/masters/hire-from-application` | 1 test | Hire from application |
| `PATCH /instructor-management/applications/{id}` | 1 test | Review application |
| `PATCH /offers/{id}/respond` | 1 test | Respond to offer |

---

## 🎯 Recommendation: BATCH 5 Strategy

### Option A: Quick Win - Routing Fixes (3 tests, 1 hour)
Fix the 3 routing mismatch tests:
- Either add path aliases to instructor_management router
- OR fix test expectations to use correct paths

**Impact:** 60 → 57 failed (-3 tests)
**Effort:** Low
**Risk:** Low (routing only)

### Option B: Instructor Management Implementation (8 tests, 2-3 days)
Implement the 8 missing endpoints:
- 4x application endpoints
- 2x master instructor hiring
- 1x review application
- 1x respond to offer

**Impact:** 60 → 52 failed (-8 tests)
**Effort:** High
**Risk:** Medium (new business logic)

### Option C: Mixed Approach (5 tests, 4 hours)
1. Fix 3 routing mismatches
2. Pick 2 simplest missing endpoints (e.g., respond to offer)

**Impact:** 60 → 55 failed (-5 tests)
**Effort:** Medium
**Risk:** Low-Medium

---

## 🎯 Other Quick Win Candidates

### Campuses (3 tests) - All Routing Mismatches
Same as before - tests expect `/campuses/` but endpoints at `/admin/campuses/`

**Fix:** Already validated in BATCH 1, just need path aliases
**Impact:** -3 tests
**Effort:** 1 hour

### Coupons (4 tests) - All 404 Missing Endpoints
All missing coupon management endpoints

**Fix:** Implement coupon endpoints
**Impact:** -4 tests
**Effort:** 2-3 hours

---

## 📈 Path to < 50 Failed Tests

**Current:** 60 failed

**Achievable batches:**
1. **BATCH 5A:** Routing fixes (instructor_management + campuses) → 54 failed (-6)
2. **BATCH 5B:** Coupons (4 endpoints) → 50 failed (-4)
3. **BATCH 5C:** Projects (5 tests, check for quick fixes) → 45 failed (-5)

**Total:** 60 → 45 in 3 batches (2-3 days)

---

## 🏆 Recommended Next Step

**BATCH 5: Routing Fixes Bundle (6 tests, 2 hours)**

Combine:
- 3 instructor_management routing fixes
- 3 campuses routing fixes

Both are the same pattern (missing resource prefix), proven approach from previous batches.

**Expected:** 60 → 54 failed (-6 tests)
**Confidence:** High (routing-only, no business logic)
**Momentum:** Continues systematic reduction toward 50
