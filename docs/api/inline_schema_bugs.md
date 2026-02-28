# Inline Schema Bugs - Validation Required

**Date:** 2026-02-28
**Status:** OPEN (needs fixing)
**Priority:** P2 (not blocking critical paths)

---

## Summary

3 endpoints have **required request body** but **empty schema** (properties=[]):
- Request validation exists but schema is undefined
- Tests correctly fail with validation errors
- API design needs fixing - either add schema or remove body requirement

---

## Affected Endpoints

### 1. POST /api/v1/debug/log-error

**Current State:**
- Request body: REQUIRED
- Schema: INLINE (empty properties)
- Test status: FAILING (correctly - validates empty schema)

**Issue:**
```python
requestBody: {
  required: True,
  content: {
    'application/json': {
      schema: {
        properties: {},      # EMPTY!
        required: []         # NO FIELDS!
      }
    }
  }
}
```

**Expected Behavior:**
Frontend error logging should accept:
```python
class FrontendErrorRequest(BaseModel):
    message: str
    stack_trace: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
```

**Test:** `test_debug_smoke.py::test_log_frontend_error_input_validation`

**Action Required:**
- [ ] Add Pydantic model `FrontendErrorRequest` to endpoint
- [ ] Update OpenAPI schema with proper fields
- [ ] Re-run test to confirm pass

---

### 2. POST /api/v1/licenses/admin/sync/all

**Current State:**
- Request body: REQUIRED
- Schema: INLINE (empty properties)
- Test status: FAILING

**Issue:**
Same as above - empty schema but required body.

**Expected Behavior:**
Admin sync operation likely needs **no input** (bulk operation):
```python
# Option 1: Remove body requirement
@router.post("/admin/sync/all")
async def sync_all_users(
    db: Session = Depends(get_db),
    # NO request body parameter
):
    ...

# Option 2: Add optional filter schema
class SyncAllRequest(BaseModel):
    force_refresh: bool = False
    campus_ids: Optional[List[int]] = None
```

**Test:** `test_licenses_smoke.py::test_sync_all_users_input_validation`

**Action Required:**
- [ ] Decide: remove body requirement OR add schema
- [ ] Update endpoint implementation
- [ ] Update OpenAPI schema

---

### 3. POST /api/v1/licenses/instructor/advance

**Current State:**
- Request body: REQUIRED
- Schema: INLINE (empty properties)
- Test status: FAILING

**Issue:**
Same inline schema bug.

**Expected Behavior:**
Instructor license advancement likely needs:
```python
class InstructorAdvanceRequest(BaseModel):
    instructor_id: int
    target_level: str  # e.g., "LFA_COACH", "SENIOR_COACH"
    notes: Optional[str] = None
```

**Test:** `test_licenses_smoke.py::test_instructor_advance_license_input_validation`

**Action Required:**
- [ ] Add Pydantic model `InstructorAdvanceRequest`
- [ ] Update endpoint to accept typed body
- [ ] Update OpenAPI schema

---

## Root Cause

All 3 endpoints likely use **inline Body()** without Pydantic model:

```python
# WRONG (causes empty schema):
@router.post("/endpoint")
async def handler(
    data: dict = Body(...),  # ❌ Inline dict, no schema
):
    ...

# CORRECT:
class MyRequest(BaseModel):
    field1: str
    field2: int

@router.post("/endpoint")
async def handler(
    data: MyRequest,  # ✅ Pydantic model, full schema
):
    ...
```

---

## Impact

**Tests:** 3 tests correctly failing (not removed)
**Users:** Likely no impact - endpoints may accept any JSON currently
**API Quality:** Low - inconsistent validation, no documentation

**Priority:** P2 - Not blocking critical user flows, but reduces API quality

---

## Fix Strategy

1. **debug/log-error:** Add `FrontendErrorRequest` schema
2. **licenses/admin/sync/all:** Remove body requirement (bulk operation)
3. **licenses/instructor/advance:** Add `InstructorAdvanceRequest` schema

**Estimated Effort:** 2-3 hours (all 3 endpoints)

---

## Related Tests (KEPT, NOT REMOVED)

```
tests/integration/api_smoke/test_debug_smoke.py::test_log_frontend_error_input_validation
tests/integration/api_smoke/test_licenses_smoke.py::test_sync_all_users_input_validation
tests/integration/api_smoke/test_licenses_smoke.py::test_instructor_advance_license_input_validation
```

These tests will pass once inline schemas are properly defined.

---

**Status:** Documented, tests kept, fix deferred to P2 priority
