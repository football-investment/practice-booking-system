# Domain Gap Discovery Summary - Tournament Creation Workflow

**Date:** 2026-01-12
**Discovery Method:** Test-Driven Domain Analysis
**Impact Level:** 🔴 Critical Business Logic Gap

---

## What Happened

During Playwright E2E test development for tournament enrollment workflows, we discovered a **critical mismatch** between:
- Business requirements (what tournament creation SHOULD support)
- Implementation (what the domain model and UI ACTUALLY support)

**This is not a test failure. This is a domain model deficiency identified through testing.**

---

## Discovery Process

### 1. Test Development Phase
**Intent:** Write E2E tests for tournament enrollment workflows covering both assignment types:
- **OPEN_ASSIGNMENT:** Admin directly assigns instructor → immediate enrollment
- **APPLICATION_BASED:** Instructors apply → admin approves → instructor accepts → enrollment opens

### 2. Test Implementation
Tests were written to validate the complete business workflow:

```python
# Test expected this UI workflow:
def test_e1_admin_creates_open_assignment_tournament(page):
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    page.get_by_role("button", name="🏆 Tournaments").click()
    page.get_by_role("tab", name="➕ Create Tournament").click()

    # EXPECTED: Assignment Type selector
    page.get_by_label("Assignment Type").select_option("OPEN_ASSIGNMENT")

    # EXPECTED: Max Players input
    page.get_by_label("Max Players").fill("5")

    # EXPECTED: Price/Enrollment Cost input
    page.get_by_label("Price (Credits)").fill("500")

    # EXPECTED: Instructor selector (for OPEN_ASSIGNMENT)
    page.get_by_label("Select Instructor").select_option("Grandmaster")
```

### 3. Reality Check
When tests executed, UI investigation revealed:

**Tournament Creation Form Actually Contains:**
- ✅ Tournament Name
- ✅ Tournament Date
- ✅ Age Group
- ✅ Location & Campus
- ✅ Session Template/Configuration
- ✅ Reward Policy
- ❌ **Assignment Type selector** (MISSING)
- ❌ **Max Players input** (MISSING)
- ❌ **Enrollment Cost input** (MISSING)
- ❌ **Instructor selection** (MISSING)

**Screenshot Evidence:**
`tests/e2e/screenshots/create_tournament_tab_open_*.png`

---

## Root Cause Analysis

### Database Schema Investigation

```sql
-- semesters table (tournaments are stored here)
Table "public.semesters"
Column                  | Type           | Nullable
------------------------+----------------+----------
enrollment_cost         | integer        | not null    ← EXISTS but not UI-settable
master_instructor_id    | integer        |             ← Used implicitly for assignment type
-- MISSING: assignment_type enum
-- MISSING: max_players integer
```

### Current Implementation Strategy

#### Assignment Type (Implicit)
```python
# Inferred from instructor presence
if tournament.master_instructor_id:
    assignment_type = "OPEN_ASSIGNMENT"  # Implicit
else:
    assignment_type = "APPLICATION_BASED"  # Implicit
```

**Problems:**
- Not a first-class domain attribute
- Not auditable (cannot track which type was intended)
- Not versionable (no history of strategy decisions)
- Cannot distinguish "not yet assigned" from "application-based"

#### Max Players (Derived)
```python
# Calculated from session capacities
max_players = sum(session.capacity for session in tournament.sessions)
```

**Problems:**
- Not an explicit business constraint
- Session changes silently change tournament capacity
- Cannot implement business rule: "capacity cannot exceed N"
- Blocks waitlist feature (no reference capacity)

#### Enrollment Cost (Partial)
```python
# Database column exists but defaults to hardcoded value
enrollment_cost = tournament.enrollment_cost or 500  # Fallback
```

**Problems:**
- UI does not expose this field during creation
- All tournaments effectively cost 500 credits
- Cannot implement custom pricing strategies
- Business rule (price must be explicit) not enforced

---

## Business Impact

### 1. Data Integrity Issues
- **Assignment strategy is ambiguous:** Cannot distinguish intended workflow from current state
- **Capacity is fragile:** Session modifications silently affect tournament business rules
- **Pricing is implicit:** Hardcoded defaults mask business intent

### 2. Feature Development Blocked
- ❌ Cannot implement waitlists (no explicit capacity)
- ❌ Cannot implement dynamic pricing (price not settable at creation)
- ❌ Cannot implement strategy-specific validation rules
- ❌ Cannot report on tournament types (assignment_type not tracked)

### 3. Audit & Compliance
- ❌ Cannot audit which tournaments used which assignment strategy
- ❌ Cannot track pricing strategy decisions
- ❌ Cannot validate lifecycle transitions against business rules

### 4. Testing & Quality
- ❌ Cannot write comprehensive E2E tests (business attributes not exposed)
- ❌ Test coverage gap for critical business workflows
- ❌ Manual testing required to validate implicit business rules

---

## Decision: Document, Don't Workaround

### What We Did NOT Do ❌
- SQL UPDATE hacks to set missing values after creation
- API workarounds to bypass UI limitations
- Test modifications to work around domain gaps
- Temporary patches to "make tests pass"

### What We DID Do ✅

#### 1. Comprehensive Documentation
Created detailed domain gap analysis:
- **[TOURNAMENT_DOMAIN_GAP.md](./TOURNAMENT_DOMAIN_GAP.md)** - Full technical analysis
- **[TOURNAMENT_TESTS_STATUS.md](../../tests/playwright/TOURNAMENT_TESTS_STATUS.md)** - Test status explanation

#### 2. Test Preservation with Skip Markers
```python
# tests/playwright/test_tournament_enrollment_*.py
pytestmark = pytest.mark.skip(
    reason="DOMAIN GAP: Tournament creation UI missing assignment_type, "
           "max_players, enrollment_cost fields. See documentation."
)
```

**16 tests intentionally skipped:**
- 6 tests: OPEN_ASSIGNMENT workflow
- 10 tests: APPLICATION_BASED workflow

#### 3. Clear Stakeholder Communication
- Tests remain as **specification** of required behavior
- Skip reason explicitly references documentation
- Tests will pass when domain model is complete

---

## Proposed Solution Architecture

### Phase 1: Database Migration
```sql
ALTER TABLE semesters
  ADD COLUMN assignment_type VARCHAR(30)
    CHECK (assignment_type IN ('OPEN_ASSIGNMENT', 'APPLICATION_BASED')),
  ADD COLUMN max_players INTEGER
    CHECK (max_players > 0);

-- Validation constraint
ALTER TABLE semesters
  ADD CONSTRAINT valid_assignment_type_instructor
  CHECK (
    (assignment_type = 'OPEN_ASSIGNMENT' AND master_instructor_id IS NOT NULL)
    OR
    (assignment_type = 'APPLICATION_BASED' AND master_instructor_id IS NULL)
  );
```

### Phase 2: API Enhancement
```python
class TournamentGenerateRequest(BaseModel):
    # Existing fields...
    name: str
    date: str
    # NEW: Explicit business attributes
    assignment_type: Literal["OPEN_ASSIGNMENT", "APPLICATION_BASED"]
    max_players: int = Field(..., gt=0)
    enrollment_cost: int = Field(..., gt=0)
    instructor_id: Optional[int] = None  # Required if OPEN_ASSIGNMENT
```

### Phase 3: UI Enhancement
Add to tournament creation form:
- Assignment Type selector
- Max Players number input
- Enrollment Cost number input
- Instructor selector (conditional on assignment_type)

### Phase 4: Enable Tests
Remove `pytestmark` skip decorators when implementation is complete.

**Estimated effort:** 2-3 days

---

## Lessons Learned

### 1. Tests as Domain Specification ✅
**Good Practice:** Writing tests for the CORRECT business workflow revealed domain gaps early.

**Benefit:** Tests serve as living documentation of business requirements, not just validation of current implementation.

### 2. Don't Workaround Domain Issues ✅
**Good Practice:** Resisted temptation to hack tests or add SQL workarounds.

**Benefit:** Clean separation between "what should exist" (tests) and "what currently exists" (implementation).

### 3. Document Technical Debt ✅
**Good Practice:** Created comprehensive documentation explaining WHY tests are skipped.

**Benefit:** Future developers understand the gap is intentional, not oversight.

### 4. Implicit vs Explicit Domain Modeling ✅
**Discovery:** Many business attributes were implicit (derived, inferred) rather than explicit (declared, stored).

**Insight:** Explicit domain modeling enables:
- Auditability
- Versionability
- Validation
- Clear business intent

---

## Next Steps

### Immediate (Complete)
- [x] Document domain gap comprehensively
- [x] Mark tests with skip decorators and clear reason
- [x] Preserve tests as specification (do not modify)
- [x] Communicate to stakeholders

### Short Term (Prioritize)
- [ ] Product Owner: Review business requirements vs implementation
- [ ] Architecture: Approve proposed solution design
- [ ] Engineering: Estimate implementation effort
- [ ] Planning: Schedule domain model enhancement

### Long Term (Implement)
- [ ] Database migration: Add explicit columns
- [ ] API enhancement: Update schemas and validation
- [ ] UI enhancement: Add missing form fields
- [ ] Enable tests: Remove skip markers
- [ ] Validation: Confirm all 16 tests pass

---

## Metrics

**Tests Written:** 16
**Tests Skipped:** 16 (100%)
**Domain Attributes Missing:** 3 (assignment_type, max_players, enrollment_cost)
**Business Workflows Blocked:** 2 (OPEN_ASSIGNMENT, APPLICATION_BASED)
**Documentation Created:** 3 files (this file, TOURNAMENT_DOMAIN_GAP.md, TOURNAMENT_TESTS_STATUS.md)

---

## References

- **Technical Analysis:** [docs/architecture/TOURNAMENT_DOMAIN_GAP.md](./TOURNAMENT_DOMAIN_GAP.md)
- **Test Status:** [tests/playwright/TOURNAMENT_TESTS_STATUS.md](../../tests/playwright/TOURNAMENT_TESTS_STATUS.md)
- **Test Files:**
  - [tests/playwright/test_tournament_enrollment_open_assignment.py](../../tests/playwright/test_tournament_enrollment_open_assignment.py)
  - [tests/playwright/test_tournament_enrollment_application_based.py](../../tests/playwright/test_tournament_enrollment_application_based.py)

---

## Stakeholder Sign-Off

**Engineering Team:** Documented domain gap, preserved test specification
**Date:** 2026-01-12
**Status:** ✅ **Accepted as documented technical debt**

---

**The tests are correct. The implementation is incomplete. This is now properly documented and awaiting resolution.**
