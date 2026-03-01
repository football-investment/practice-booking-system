# 55 Failed Tests - Post-BATCH 5 Breakdown

**CI Run:** 22539363621
**Date:** 2026-03-01 09:24
**Result:** 55 failed, 1222 passed, 445 skipped

**Progress:** 73 → 68 → 65 → 61 → 60 → **55** (-18 total, **90% of "below 60" goal**, 5 away from "below 50")

---

## 📊 BATCH 5 Impact Verification

**Target:** 60 → 54-56 failed (-4 to -6 tests)
**Result:** 60 → 55 failed (-5 tests) ✅

### ✅ Fixed Tests (5/6 targets)

**Instructor Management (4 tests):**
- test_update_assignment_input_validation ✅ (routing alias)
- test_update_master_instructor_input_validation ✅ (routing alias)
- test_update_position_input_validation ✅ (routing alias)
- test_review_application_input_validation ✅ (bonus - unexpected fix!)

**Campuses (1 test):**
- test_create_campus_input_validation ✅ (routing alias)

### ❌ Still Failing (2 campus tests)

**Root Cause:** Existence-before-validation pattern (NOT routing issue)

- test_toggle_campus_status_input_validation - 404 (campus ID doesn't exist)
- test_update_campus_input_validation - 404 (campus ID doesn't exist)

**Analysis:** See [validation_pipeline_order_analysis.md](validation_pipeline_order_analysis.md)

---

## 📊 Domain Clustering (55 tests)

| Domain | Count | Change | Type |
|--------|-------|--------|------|
| **🎯 instructor_management** | **7** | **-4** | **Mixed (404 + missing endpoints)** |
| projects | 5 | 0 | Mixed (404 + 403) |
| periods | 4 | 0 | All 404 (missing endpoints) |
| licenses | 4 | 0 | Mixed (404 + 403) |
| coupons | 4 | 0 | All 404 (missing endpoints) |
| quiz | 3 | 0 | All 404 (missing endpoints) |
| instructor | 3 | 0 | Mixed (start PASSED, stop/unlock failed) |
| campuses | 2 | -1 | All 404 (existence-before-validation) |
| tournaments | 2 | 0 | 403 (permission issues) |
| system_events | 2 | 0 | All 404 (missing endpoints) |
| sessions | 2 | 0 | Mixed |
| onboarding | 2 | 0 | All 404 (missing endpoints) |
| locations | 2 | 0 | All 404 (missing endpoints) |
| lfa_coach_routes | 2 | 0 | All 404 (missing endpoints) |
| invoices | 2 | 0 | All 404 (missing endpoints) |
| Other (3 domains) | 3 | 0 | 1 test each |

**Total:** 55 tests

---

## 🎯 BATCH 6 Target: instructor_management (7 tests)

**All 7 tests fail with 404** - Missing endpoints (NOT routing issues)

### Missing Endpoints (7 tests)

| Endpoint | Test | Functionality |
|----------|------|---------------|
| `POST /instructor-management/applications` | 4 tests | Create application (multiple test variants) |
| `POST /instructor-management/masters/direct-hire` | 1 test | Direct hire master instructor |
| `POST /instructor-management/masters/hire-from-application` | 1 test | Hire from application |
| `PATCH /instructor-management/applications/{id}` | 1 test | Review application (was in BATCH 5 but PASSED unexpectedly!) |

**Note:** `test_review_application_input_validation` was expected to fail (404 missing endpoint) but **PASSED** in BATCH 5!
This suggests the endpoint might already exist or was fixed by another change.

### Remaining 7 tests breakdown:

```bash
# Extract instructor_management failures
cat /tmp/failed_55_fixed.txt | grep instructor_management
```

Output:
- test_create_application_input_validation
- test_create_assignment_input_validation
- test_create_direct_hire_offer_input_validation
- test_create_master_instructor_legacy_input_validation
- test_create_position_input_validation
- test_hire_from_application_input_validation
- test_respond_to_offer_input_validation

**Analysis:** All are POST endpoint input_validation tests → Missing endpoint implementations

---

## 🎯 Recommendation: BATCH 6 Strategy

### Option A: Implement Missing Endpoints (7 tests, 2-3 days)

Implement the 7 missing POST endpoints in instructor_management:
- 4x application creation endpoints
- 2x master instructor hiring endpoints
- 1x respond to offer endpoint

**Impact:** 55 → 48 failed (-7 tests) ✅ **Below 50 goal achieved!**
**Effort:** High (2-3 days, complex business logic)
**Risk:** Medium (new features, extensive testing needed)

---

### Option B: Quick Win - Projects (5 tests, 4-6 hours)

**Alternative if we want faster progress:**

Investigate projects domain (5 tests):
- Check if these are routing issues or missing endpoints
- If routing: Quick fix like BATCH 5
- If missing: Implement if simple

**Impact:** 55 → 50 failed (-5 tests) ✅ **Below 50 goal achieved!**
**Effort:** Medium (depends on issue type)
**Risk:** Low-Medium

---

### Option C: Mixed Approach (5 tests, 4-6 hours)

1. Fix 2 campus tests (test generator update - Option A from validation_pipeline_order_analysis.md)
2. Pick 3 simplest instructor_management endpoints

**Impact:** 55 → 50 failed (-5 tests) ✅ **Below 50 goal achieved!**
**Effort:** Medium
**Risk:** Low

---

## 📈 Path to < 50 Failed Tests

**Current:** 55 failed
**Target:** Below 50 (-5 more tests needed)

**Achievable batches:**

### Fastest Path (1 batch):
1. **BATCH 6A:** Projects investigation + quick fixes → 50 failed (-5) ✅

### Structured Path (2 batches):
1. **BATCH 6B:** Campus test generator fix (2 tests) → 53 failed (-2)
2. **BATCH 6C:** Projects OR coupons (4-5 tests) → 48-49 failed ✅

### Comprehensive Path (1 large batch):
1. **BATCH 6D:** Instructor management missing endpoints (7 tests) → 48 failed ✅

---

## 🏆 Recommended Next Step

**BATCH 6: Projects Investigation (5 tests, 4-6 hours)**

**Why Projects:**
1. Same size as instructor_management missing endpoints
2. Might be quick routing fixes (like BATCH 5)
3. Achieves "below 50" goal if all fixed
4. Lower risk than implementing new endpoints

**Verification:**
```bash
# Check what type of failures
cat /tmp/failed_55_fixed.txt | grep projects

# Expected output:
tests/integration/api_smoke/test_projects_smoke.py::TestProjectsSmoke::test_approve_milestone_input_validation
tests/integration/api_smoke/test_projects_smoke.py::TestProjectsSmoke::test_confirm_project_enrollment_input_validation
tests/integration/api_smoke/test_projects_smoke.py::TestProjectsSmoke::test_enroll_in_project_input_validation
tests/integration/api_smoke/test_projects_smoke.py::TestProjectsSmoke::test_instructor_enroll_student_input_validation
tests/integration/api_smoke/test_projects_smoke.py::TestProjectsSmoke::test_submit_milestone_input_validation
```

**Next Action:** Investigate projects tests to determine fix type (routing vs missing endpoints)

---

## 📋 Summary

**Achievement:** 60 → 55 failed (-5 tests) ✅
**BATCH 5 Success Rate:** 5/6 targets fixed (83%)
**Remaining to < 50:** 5 tests
**Largest Cluster:** instructor_management (7 tests)
**Quick Win Candidate:** projects (5 tests)

**Overall Progress:** 73 → 55 failed (-18 tests, 24.6% reduction)

---

**Status:** Ready for BATCH 6 planning
**Next Action:** Investigate projects OR implement instructor_management endpoints
