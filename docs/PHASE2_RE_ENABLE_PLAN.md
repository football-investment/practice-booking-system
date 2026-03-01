# Phase 2: Re-Enable POST/PATCH/PUT Input Validation Tests

**Branch:** `feature/skip-test-re-enable-phase-2`
**Base:** main (after PR #7 merge)
**Status:** 🟡 **PLANNED - Ready for Implementation**
**Estimated Effort:** 2-3 hours

---

## 🎯 Goal

Re-enable 11 core POST/PATCH/PUT input validation tests across 5 critical business domains.

**Why:** These tests validate Pydantic `extra='forbid'` behavior and protect against API accepting invalid payloads (security + data integrity).

---

## 📋 Implementation Plan

### Selected Tests (11 total)

#### 1️⃣ **tournaments** (3 tests)

**File:** `tests/integration/api_smoke/test_tournaments_smoke.py`

- ✅ `test_create_tournament_input_validation` (line ~1335)
  - **Method:** POST `/api/v1/tournaments`
  - **Invalid Payload:**
    ```python
    {
        "tournament_type_id": 99999,  # Non-existent ID
        "extra_forbidden_field": "invalid",  # Should trigger 422
        "name": "Test Tournament"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

- ✅ `test_update_tournament_input_validation` (line ~1107)
  - **Method:** PATCH `/api/v1/tournaments/{id}`
  - **Invalid Payload:**
    ```python
    {
        "status": "INVALID_STATUS",  # Invalid enum
        "extra_field": "forbidden"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

- ✅ `test_record_match_results_input_validation` (line ~TBD)
  - **Method:** PATCH `/api/v1/tournaments/{id}/record-results`
  - **Invalid Payload:**
    ```python
    {
        "session_id": 99999,  # Non-existent
        "winner_id": -1,  # Invalid
        "extra": "field"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

---

#### 2️⃣ **sessions** (2 tests)

**File:** `tests/integration/api_smoke/test_sessions_smoke.py`

- ✅ `test_create_session_input_validation`
  - **Method:** POST `/api/v1/sessions`
  - **Invalid Payload:**
    ```python
    {
        "instructor_id": 99999,  # Non-existent
        "start_date": "2020-01-01",  # Past date
        "extra_forbidden": "field"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

- ✅ `test_update_session_input_validation`
  - **Method:** PATCH `/api/v1/sessions/{id}`
  - **Invalid Payload:**
    ```python
    {
        "session_status": "INVALID",  # Invalid enum
        "extra": "field"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

---

#### 3️⃣ **semester_enrollments** (2 tests)

**File:** `tests/integration/api_smoke/test_semester_enrollments_smoke.py`

- ✅ `test_create_enrollment_input_validation`
  - **Method:** POST `/api/v1/enrollments`
  - **Invalid Payload:**
    ```python
    {
        "semester_id": 99999,  # Non-existent
        "credits": -100,  # Negative credits
        "forbidden_extra": "field"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

- ✅ `test_approve_enrollment_request_input_validation`
  - **Method:** POST `/api/v1/enrollments/{id}/approve`
  - **Invalid Payload:**
    ```python
    {
        "approval_status": "INVALID",
        "extra_field": "forbidden"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

---

#### 4️⃣ **bookings** (2 tests)

**File:** `tests/integration/api_smoke/test_bookings_smoke.py`

- ✅ `test_create_booking_input_validation` (line ~258)
  - **Method:** POST `/api/v1/bookings`
  - **Invalid Payload:**
    ```python
    {
        "session_id": 99999,  # Non-existent
        "duplicate_booking": true,  # Invalid field
        "extra": "field"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

- ✅ `test_confirm_booking_input_validation` (line ~372)
  - **Method:** POST `/api/v1/bookings/{id}/confirm`
  - **Invalid Payload:**
    ```python
    {
        "confirmation_code": "INVALID",
        "extra_forbidden": "field"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

---

#### 5️⃣ **users** (2 tests)

**File:** `tests/integration/api_smoke/test_users_smoke.py`

- ✅ `test_update_user_input_validation`
  - **Method:** PATCH `/api/v1/users/{id}`
  - **Invalid Payload:**
    ```python
    {
        "email": "invalid_email_format",  # Invalid format
        "role": "INVALID_ROLE",  # Invalid enum
        "extra_forbidden_field": "value"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

- ✅ `test_create_user_input_validation`
  - **Method:** POST `/api/v1/users`
  - **Invalid Payload:**
    ```python
    {
        "password": "short",  # Too short
        "extra": "field"
    }
    ```
  - **Expected:** 422 Unprocessable Entity

---

## 🔧 Implementation Steps

### Step 1: Remove Skip Decorators

For each test above:

1. **Find the skip decorator:**
   ```python
   @pytest.mark.skip(reason="Input validation requires domain-specific payloads")
   def test_create_tournament_input_validation(...):
   ```

2. **Remove the decorator:**
   ```python
   # Remove: @pytest.mark.skip(reason="Input validation requires domain-specific payloads")
   def test_create_tournament_input_validation(...):
   ```

3. **Remove the pytest.skip() call inside:**
   ```python
   # Remove this:
   pytest.skip("Input validation requires domain-specific payloads")
   ```

---

### Step 2: Add Domain-Specific Invalid Payloads

Replace generic invalid payloads with domain-specific ones:

**Before (generic):**
```python
def test_create_tournament_input_validation(...):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Invalid payload (empty or malformed)
    invalid_payload = {"invalid_field": "invalid_value"}
    response = api_client.post(
        '/api/v1/tournaments',
        json=invalid_payload,
        headers=headers
    )

    # Should return 422 Unprocessable Entity for validation errors
    assert response.status_code in [400, 422], (
        f"POST /api/v1/tournaments should reject invalid payload: {response.status_code}"
    )
```

**After (domain-specific):**
```python
def test_create_tournament_input_validation(...):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Invalid payload - domain-specific
    invalid_payload = {
        "tournament_type_id": 99999,  # Non-existent ID
        "extra_forbidden_field": "invalid",  # Pydantic extra='forbid' test
        "name": "Test"
    }
    response = api_client.post(
        '/api/v1/tournaments',
        json=invalid_payload,
        headers=headers
    )

    # Pydantic should return 422 for extra fields
    assert response.status_code == 422, (
        f"POST /api/v1/tournaments should return 422 for invalid payload: "
        f"{response.status_code} - {response.text}"
    )

    # Verify error message mentions forbidden field
    error_data = response.json()
    assert "extra_forbidden_field" in str(error_data).lower() or "extra" in str(error_data).lower()
```

---

### Step 3: Local Testing

Run each re-enabled test locally:

```bash
# Test individual domain
pytest tests/integration/api_smoke/test_tournaments_smoke.py::TestTournamentsSmoke::test_create_tournament_input_validation -v

# Test all re-enabled tests
pytest tests/integration/api_smoke/test_tournaments_smoke.py::TestTournamentsSmoke::test_create_tournament_input_validation \
       tests/integration/api_smoke/test_tournaments_smoke.py::TestTournamentsSmoke::test_update_tournament_input_validation \
       tests/integration/api_smoke/test_sessions_smoke.py::TestSessionsSmoke::test_create_session_input_validation \
       tests/integration/api_smoke/test_sessions_smoke.py::TestSessionsSmoke::test_update_session_input_validation \
       -v

# Expected: 11/11 PASSING (100%)
```

---

### Step 4: Verify Expected Failures

**Goal:** Confirm tests FAIL if Pydantic `extra='forbid'` is missing.

**Test:**
1. Temporarily remove `extra='forbid'` from a Pydantic schema
2. Run the corresponding test
3. **Expected:** Test FAILS (API accepts forbidden field → test detects bug)
4. Restore `extra='forbid'`
5. **Expected:** Test PASSES

**Example:**
```python
# app/schemas/tournament.py
class TournamentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')  # ← Remove this temporarily
    name: str
    tournament_type_id: int
```

If test still passes after removing `extra='forbid'`, the test is not effective!

---

## 📊 Success Criteria

### Before Phase 2
- 243 POST/PATCH/PUT tests: ALL SKIPPED
- 0 active input validation coverage

### After Phase 2
- ✅ 11 tests RE-ENABLED and PASSING
- ✅ 232 tests remain skipped (for future phases)
- ✅ Core domain coverage: tournaments, sessions, enrollments, bookings, users
- ✅ All tests validate Pydantic `extra='forbid'`
- ✅ Domain-specific invalid payloads
- ✅ 0 FAILED tests (100% pass rate)

---

## 🚀 Commit Strategy

### Commit 1: tournaments domain (3 tests)
```bash
git add tests/integration/api_smoke/test_tournaments_smoke.py
git commit -m "test(validation): Re-enable tournaments input validation (Phase 2 - 3/11)"
```

### Commit 2: sessions domain (2 tests)
```bash
git add tests/integration/api_smoke/test_sessions_smoke.py
git commit -m "test(validation): Re-enable sessions input validation (Phase 2 - 5/11)"
```

### Commit 3: enrollments domain (2 tests)
```bash
git add tests/integration/api_smoke/test_semester_enrollments_smoke.py
git commit -m "test(validation): Re-enable enrollments input validation (Phase 2 - 7/11)"
```

### Commit 4: bookings domain (2 tests)
```bash
git add tests/integration/api_smoke/test_bookings_smoke.py
git commit -m "test(validation): Re-enable bookings input validation (Phase 2 - 9/11)"
```

### Commit 5: users domain (2 tests)
```bash
git add tests/integration/api_smoke/test_users_smoke.py
git commit -m "test(validation): Re-enable users input validation (Phase 2 - 11/11 COMPLETE)"
```

### Commit 6: Documentation
```bash
git add docs/PHASE2_RE_ENABLE_PLAN.md docs/SKIP_TEST_ANALYSIS_PLAN.md
git commit -m "docs: Phase 2 complete - 11 validation tests re-enabled"
```

---

## 📋 PR #8 Template

**Title:** `test(validation): Phase 2 - Re-enable 11 core POST/PATCH/PUT input validation tests`

**Body:**
```markdown
# Phase 2: Re-Enable Core Input Validation Tests

## 🎯 Summary

Re-enabled 11 core POST/PATCH/PUT input validation tests across 5 critical business domains.

**Scope:**
- tournaments (3 tests)
- sessions (2 tests)
- semester_enrollments (2 tests)
- bookings (2 tests)
- users (2 tests)

---

## 📊 Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Active validation tests** | 0 | 11 | +11 ✅ |
| **Skipped tests** | 243 | 232 | -11 |
| **Test pass rate** | N/A | 100% (11/11) | ✅ |
| **Domains covered** | 0 | 5 | +5 ✅ |

---

## 🔧 Technical Details

### Validation Coverage

**Tournaments:**
- ✅ POST `/tournaments` - rejects extra fields
- ✅ PATCH `/tournaments/{id}` - validates enum values
- ✅ PATCH `/tournaments/{id}/record-results` - validates IDs

**Sessions:**
- ✅ POST `/sessions` - validates instructor_id + date
- ✅ PATCH `/sessions/{id}` - validates session_status enum

**Enrollments:**
- ✅ POST `/enrollments` - validates credits (non-negative)
- ✅ POST `/enrollments/{id}/approve` - validates status

**Bookings:**
- ✅ POST `/bookings` - validates session_id
- ✅ POST `/bookings/{id}/confirm` - validates confirmation

**Users:**
- ✅ PATCH `/users/{id}` - validates email format + role enum
- ✅ POST `/users` - validates password length

---

## ✅ Validation

- ✅ All 11 tests PASSING locally
- ✅ Domain-specific invalid payloads
- ✅ Pydantic `extra='forbid'` coverage verified
- ✅ No functional code changes (test-only)
- ✅ Based on Phase 1 clean baseline (PR #7)

---

See: [PHASE2_RE_ENABLE_PLAN.md](docs/PHASE2_RE_ENABLE_PLAN.md)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 🔄 Next Steps After PR #8 Merge

### Phase 3 (Future - Optional)
- Re-enable additional 10-15 POST/PATCH/PUT tests
- Domains: instructor_management, licenses, projects, coupons
- Target: 20-25 total active validation tests

---

**Status:** 🟡 **READY FOR IMPLEMENTATION**
**Estimated Time:** 2-3 hours
**Next Action:** Execute Steps 1-4, commit per domain, create PR #8

**Author:** Claude Sonnet 4.5
**Date:** 2026-03-01
