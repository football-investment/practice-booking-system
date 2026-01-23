# Tournament Enrollment E2E Tests - Status

**Last Updated:** 2026-01-12
**Status:** 🔴 Intentionally Failing (Domain Gap)

---

## Test Files

### 1. `test_tournament_enrollment_open_assignment.py`
**Tests:** OPEN_ASSIGNMENT tournament enrollment workflow (6 tests)
**Status:** 🔴 FAILING - Domain gap
**Reason:** UI does not support explicit assignment type, max players, enrollment cost fields

### 2. `test_tournament_enrollment_application_based.py`
**Tests:** APPLICATION_BASED tournament enrollment workflow (10 tests)
**Status:** 🔴 FAILING - Domain gap
**Reason:** UI does not support explicit assignment type, max players, enrollment cost fields

---

## Why Are These Tests Failing?

**These tests are NOT defective. They correctly model the business requirements.**

The tests fail because the **domain model and UI are incomplete**. Essential business attributes required for tournament creation are missing:

1. **`assignment_type`** - OPEN_ASSIGNMENT vs APPLICATION_BASED (implicit, not explicit)
2. **`max_players`** - Tournament capacity (derived from sessions, not declared)
3. **`enrollment_cost`** - Enrollment fee (has database column but not settable via UI)

---

## Test Design Philosophy

These tests were written to **validate the correct business workflow**, not the current incomplete implementation.

**Test Intent:**
```python
# Line 90-113: Tournament Creation (OPEN_ASSIGNMENT)
page.get_by_label("Tournament Name").fill(TOURNAMENT_NAME)
page.get_by_label("Assignment Type").select_option("OPEN_ASSIGNMENT")  # ← MISSING
page.get_by_label("Max Players").fill("5")                             # ← MISSING
page.get_by_label("Price (Credits)").fill("500")                       # ← MISSING
page.get_by_label("Select Instructor").select_option("Grandmaster")    # ← CONDITIONAL
```

**What the test expects:**
- Explicit assignment type selection during creation
- Explicit max player capacity setting
- Explicit enrollment cost/price configuration
- Instructor selection when using OPEN_ASSIGNMENT

**What the current UI provides:**
- ✅ Tournament Name
- ✅ Tournament Date
- ✅ Age Group
- ✅ Location & Campus
- ✅ Session Templates
- ❌ Assignment Type selector
- ❌ Max Players input
- ❌ Enrollment Cost input
- ❌ Instructor selection (for OPEN_ASSIGNMENT)

---

## Root Cause Analysis

**See:** [docs/architecture/TOURNAMENT_DOMAIN_GAP.md](../../docs/architecture/TOURNAMENT_DOMAIN_GAP.md)

**Summary:**
The current implementation uses:
- **Implicit assignment type** - Inferred from `master_instructor_id IS NULL` vs `NOT NULL`
- **Derived max players** - Calculated from `SUM(session.capacity)`
- **Hardcoded enrollment cost** - Defaults to 500 if not set: `enrollment_cost or 500`

This creates:
- Non-auditable business decisions
- Non-versionable attributes
- Brittle capacity management
- Inflexible pricing

---

## Decision: Do NOT Modify Tests

**We are NOT adding workarounds to these tests.**

**Why?**
1. **Tests model correct business behavior** - They validate what SHOULD exist
2. **Tests serve as specification** - They document required domain model
3. **Test failure signals domain gap** - This is intentional, not a bug
4. **Workarounds hide the problem** - SQL hacks or API patches mask architectural issues

**These tests will remain failing until the domain model, API, and UI are properly implemented.**

---

## Current Workaround Tests

If you need **working** tournament enrollment E2E tests against the **current incomplete implementation**, use these instead:

### API-Based Tournament Creation (Works Today)
- `tests/e2e/test_ui_instructor_application_workflow.py`
  - Creates tournaments via API: `create_tournament_via_api()`
  - Tests instructor application workflow
  - Status: ✅ PASSING

### Simple UI Tournament Generator (Works Today)
- `tests/e2e/test_ui_complete_business_workflow.py`
  - Uses existing UI form (no assignment type, limited fields)
  - Creates basic tournaments via `/generate` API
  - Status: ✅ PASSING

**These tests work because they avoid the missing domain attributes.**

---

## Resolution Path

To make these tests pass, the following changes are required:

### 1. Database Migration
```sql
ALTER TABLE semesters
  ADD COLUMN assignment_type VARCHAR(30)
    CHECK (assignment_type IN ('OPEN_ASSIGNMENT', 'APPLICATION_BASED')),
  ADD COLUMN max_players INTEGER
    CHECK (max_players > 0);
```

### 2. API Schema Update
```python
class TournamentGenerateRequest(BaseModel):
    # ... existing fields ...
    assignment_type: Literal["OPEN_ASSIGNMENT", "APPLICATION_BASED"]
    max_players: int
    enrollment_cost: int
    instructor_id: Optional[int]  # Required if OPEN_ASSIGNMENT
```

### 3. UI Form Update
```python
# Add form fields:
- Assignment Type selector
- Max Players number input
- Enrollment Cost number input
- Instructor selector (conditional on assignment_type)
```

### 4. Business Rule Validation
```python
# Enforce:
- assignment_type + instructor_id consistency
- max_players >= SUM(session.capacity)
- enrollment_cost > 0
```

**Estimated effort:** 2-3 days (migration + API + UI + validation)

---

## Test Execution

### Run Failing Tests (Intentional)
```bash
# OPEN_ASSIGNMENT workflow
pytest tests/playwright/test_tournament_enrollment_open_assignment.py --headed --browser firefox

# APPLICATION_BASED workflow
pytest tests/playwright/test_tournament_enrollment_application_based.py --headed --browser firefox
```

**Expected result:** ❌ Tests fail at tournament creation form (missing fields)

### Run Working Workaround Tests
```bash
# API-based tournament creation
pytest tests/e2e/test_ui_instructor_application_workflow.py --headed --browser firefox

# Simple UI generator
pytest tests/e2e/test_ui_complete_business_workflow.py --headed --browser firefox
```

**Expected result:** ✅ Tests pass (avoid missing domain attributes)

---

## Related Documentation

- [Tournament Domain Gap Analysis](../../docs/architecture/TOURNAMENT_DOMAIN_GAP.md) - Full technical analysis
- [Tournament Lifecycle](../../docs/architecture/TOURNAMENT_LIFECYCLE.md) - Status state machine
- [Instructor Assignment Workflows](../../docs/workflows/TOURNAMENT_INSTRUCTOR_ASSIGNMENT.md) - Assignment type flows

---

## Stakeholder Communication

**For Product Owners:**
These tests validate critical business requirements that are not yet implemented. The test failures indicate missing features, not test defects.

**For Developers:**
Do not modify these tests to work around the domain gap. They serve as the specification for proper tournament creation functionality.

**For QA:**
Use the "Current Workaround Tests" section for validating existing functionality. These tests validate future functionality.

---

## Timeline

- **2026-01-12:** Tests created, domain gap identified and documented
- **TBD:** Domain model enhancement (assignment_type, max_players)
- **TBD:** API schema update
- **TBD:** UI form enhancement
- **TBD:** Tests expected to pass

---

**The tests are correct. The implementation is incomplete. This is documented technical debt.**
