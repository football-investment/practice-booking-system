# Post-BATCH 5 Analysis Template

**Run after CI completes**

---

## 🎯 CI Result

**CI Run:** [Insert Run Number]
**Date:** 2026-03-01
**Previous:** 60 failed
**Current:** [Insert] failed
**Delta:** [Insert] tests

---

## 📊 Quick Check Commands

```bash
# 1. Extract failed tests from CI logs
gh run view [RUN_ID] --log-failed | grep "FAILED tests/" | awk '{print $2}' > /tmp/failed_post_batch5.txt

# 2. Count total
wc -l /tmp/failed_post_batch5.txt

# 3. Domain clustering
cat /tmp/failed_post_batch5.txt | sed 's/.*test_\(.*\)_smoke.*/\1/' | sort | uniq -c | sort -rn

# 4. Compare with previous (60 failed)
comm -13 <(sort /tmp/failed_60.txt) <(sort /tmp/failed_post_batch5.txt) > /tmp/new_failures.txt
comm -23 <(sort /tmp/failed_60.txt) <(sort /tmp/failed_post_batch5.txt) > /tmp/fixed_tests.txt

# 5. Verify BATCH 5 impact
echo "Fixed tests (should include BATCH 5 targets):"
cat /tmp/fixed_tests.txt

echo "New failures (should be empty):"
cat /tmp/new_failures.txt
```

---

## 🎯 Expected BATCH 5 Impact

**Target tests (should be FIXED):**
- ✅ test_update_assignment_input_validation (instructor_management)
- ✅ test_update_master_instructor_input_validation (instructor_management)
- ✅ test_update_position_input_validation (instructor_management)
- ⚠️  test_create_campus_input_validation (campuses)
- ⚠️  test_toggle_campus_status_input_validation (campuses)
- ⚠️  test_update_campus_input_validation (campuses)

**Expected Result:**
- Best case: 60 → 54 (-6 tests)
- Likely case: 60 → 56 (-4 tests) - if 2 campus tests still fail due to existence check
- Worst case: 60 → 57 (-3 tests) - if only instructor_management worked

---

## 🔍 Next Batch Identification

### If result is 54-56 failed:
**Target:** Below 50 (-4 to -6 more tests needed)

**Candidate clusters (from 60-failed breakdown):**
1. **projects** (5 tests) - Mixed 404 + 403
2. **coupons** (4 tests) - All 404 (missing endpoints)
3. **periods** (4 tests) - All 404 (missing endpoints)
4. **licenses** (4 tests) - Mixed 404 + 403
5. **instructor_management remaining** (8 tests) - Missing endpoints

**Recommended BATCH 6:**
- Option A: **Coupons** (4 tests, 2-3 hours) → 56 → 52
- Option B: **Projects** (5 tests, check for quick fixes) → 56 → 51
- Option C: **Periods** (4 tests, implement missing endpoints) → 56 → 52

### If result is NOT below 56:
**Action:** Create new detailed breakdown, investigate unexpected failures

---

## 📋 Structured Path to 50

**Current:** [Insert after CI]
**Target:** Below 50
**Strategy:** 2-3 batches, each targeting 3-5 tests

**Batch sequence:**
1. BATCH 6: [Largest remaining cluster] → [X-4] failed
2. BATCH 7: [Next cluster] → [X-8] failed
3. BATCH 8: [Final cluster] → Below 50 ✅

---

## 🚨 Validation Pipeline Issue (Campus Tests)

**If campus tests still fail with 404:**

**Root Cause:** Endpoints check existence BEFORE validation
- Current order: Existence check → 404 if not found → Validation → 422 if invalid
- Test expectation: Validation → 422 for invalid input (regardless of existence)

**Impact:**
- 2 campus tests might still fail if test DB doesn't have ID 11
- This is correct API behavior (REST best practice: existence before validation)
- BUT: Test generator expects validation-first

**Solutions:**
- Option A: Fix test generator to accept 404 for input_validation tests (test infrastructure fix)
- Option B: Change endpoint order: validation → existence (API design change)
- Option C: Skip these 2 tests (mark as known limitation)

**Recommendation:** Option A (fix test generator) - API design is correct

---

## ✅ Verification Checklist

- [ ] CI run completed successfully
- [ ] Failed test count extracted
- [ ] Delta calculated (60 → X)
- [ ] BATCH 5 targets verified (3-6 tests fixed)
- [ ] No new failures introduced
- [ ] Domain clustering complete
- [ ] Next batch identified
- [ ] Breakdown document created

---

**Status:** Template ready for CI completion
**Next Action:** Wait for CI → Extract results → Execute analysis commands → Create fresh breakdown
