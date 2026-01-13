# Tournament Domain Gap Analysis

**Date:** 2026-01-12
**Status:** 🔴 CRITICAL - Business Logic Not Implemented
**Impact:** High - Tournament creation workflow incomplete

---

## Executive Summary

The tournament creation workflow has a **critical domain gap** between business requirements and implementation. Essential business attributes that define tournament behavior are either missing from the domain model or implemented implicitly, making them non-auditable, non-versionable, and non-testable.

**This is not a test failure - this is a domain model deficiency.**

---

## Missing Domain Attributes

### 1. `assignment_type` - Tournament Instructor Assignment Strategy

**Business Requirement:**
Tournaments must explicitly declare their instructor assignment strategy at creation time.

**Expected Values:**
- `OPEN_ASSIGNMENT` - Admin directly assigns instructor, tournament immediately open for enrollment
- `APPLICATION_BASED` - Instructors apply, admin approves, instructor accepts, then open for enrollment

**Current Implementation:**
❌ **MISSING** - Not a database column
❌ **IMPLICIT** - Inferred from `master_instructor_id IS NULL` vs `NOT NULL`
❌ **NON-AUDITABLE** - No history of which strategy was chosen
❌ **NON-VERSIONABLE** - Cannot track strategy changes

**Business Impact:**
- Cannot enforce business rules at creation time
- Cannot report on tournament types
- Cannot validate lifecycle transitions against intended strategy
- UI cannot reflect business intent

---

### 2. `max_players` - Tournament Player Capacity

**Business Requirement:**
Tournaments must have an explicit maximum player capacity that governs enrollment limits.

**Current Implementation:**
❌ **MISSING** - Not a database column
❌ **IMPLICIT** - Calculated as SUM(session.capacity)
❌ **BRITTLE** - Changes to session capacity silently change tournament capacity
❌ **VALIDATION GAP** - Cannot prevent session modifications that violate tournament business rules

**Business Impact:**
- Cannot enforce enrollment caps independently of session scheduling
- Cannot implement waitlists (no explicit capacity reference)
- Cannot implement pricing tiers based on capacity
- Cannot validate session changes against tournament intent

---

### 3. `enrollment_cost` - Tournament Enrollment Price

**Business Requirement:**
Tournaments must have an explicit enrollment fee that players pay to participate.

**Current Implementation:**
⚠️ **PARTIAL** - Column exists in `semesters.enrollment_cost`
⚠️ **DEFAULT ONLY** - Not settable via UI during creation
⚠️ **HARDCODED FALLBACK** - Code defaults to 500 if NULL: `enrollment_cost or 500`

**Code Evidence:**
```python
# app/api/api_v1/endpoints/tournaments/enroll.py:47
enrollment_cost = tournament.enrollment_cost or 500

# app/api/api_v1/endpoints/tournaments/available.py:82
"enrollment_cost": tournament.enrollment_cost or 500,
```

**Business Impact:**
- Cannot set custom pricing during tournament creation
- All tournaments effectively cost 500 credits (hardcoded default)
- Cannot implement dynamic pricing strategies
- Business rule (price must be explicit) not enforced

---

## Current Domain Model

### Database Schema (`semesters` table)
```sql
Table "public.semesters"
Column                  | Type                        | Nullable
------------------------+-----------------------------+----------
id                      | integer                     | not null
enrollment_cost         | integer                     | not null  ← EXISTS but not UI-settable
master_instructor_id    | integer                     |           ← Used implicitly for assignment_type
tournament_status       | character varying(50)       |           ← Lifecycle state
-- MISSING: assignment_type enum
-- MISSING: max_players integer
```

---

## API Gap Analysis

### Tournament Creation Endpoints

#### 1. `POST /api/v1/tournaments/generate` (Current UI)
```python
class TournamentGenerateRequest(BaseModel):
    name: str
    date: str
    specialization_type: SpecializationType
    age_group: Optional[str]
    campus_id: int
    sessions: List[SessionConfig]
    reward_policy_name: str
    # ❌ MISSING: assignment_type
    # ❌ MISSING: max_players
    # ❌ MISSING: enrollment_cost
```

**Creates tournament with:**
- ✅ Basic metadata (name, date, location)
- ✅ Sessions with individual capacities
- ❌ No assignment strategy specification
- ❌ No explicit enrollment cost
- ❌ No max player limit
- Status: `SEEKING_INSTRUCTOR` (requires instructor assignment flow)

---

#### 2. `POST /api/v1/tournaments/` (Lifecycle API - Unused by UI)
```python
class TournamentCreateRequest(BaseModel):
    name: str
    specialization_type: SpecializationType
    start_date: str
    end_date: str
    location_id: Optional[int]
    # ❌ MISSING: assignment_type
    # ❌ MISSING: max_players
    # ❌ MISSING: enrollment_cost
```

**Creates tournament in `DRAFT` status, but also lacks critical fields.**

---

## UI Gap Analysis

### Tournament Creation Form (`streamlit_app/components/tournaments/player_tournament_generator.py`)

**Current Form Fields:**
- ✅ Location & Campus (outside form)
- ✅ Tournament Name
- ✅ Tournament Date
- ✅ Age Group
- ✅ Session Template / Custom Sessions
- ✅ Reward Policy

**Missing Business-Critical Fields:**
- ❌ Assignment Type selector (OPEN_ASSIGNMENT / APPLICATION_BASED)
- ❌ Max Players input
- ❌ Enrollment Cost / Price input

**Code Location:** Lines 67-308
**Form Submit:** Line 268 - `st.form_submit_button("🏆 Create Tournament")`

---

## Test Failure Analysis

### Test: `test_tournament_enrollment_open_assignment.py`

**Test Intent:** ✅ CORRECT
Validate complete OPEN_ASSIGNMENT tournament enrollment workflow:
1. Admin creates tournament with direct instructor assignment
2. Players enroll and pay enrollment fee
3. Admin manages enrollments

**Test Failure Reason:** ❌ **DOMAIN GAP, NOT TEST ERROR**

```python
# Line 90-93: Test expects these fields to exist
page.get_by_label("Tournament Name").fill(TOURNAMENT_NAME)
page.get_by_label("Assignment Type").select_option("OPEN_ASSIGNMENT")  # ← MISSING
page.get_by_label("Max Players").fill("5")                             # ← MISSING
page.get_by_label("Price (Credits)").fill("500")                       # ← MISSING
```

**Diagnosis:**
The test correctly models the business requirement. The UI and domain model are incomplete.

**Test Status:** 🔴 **INTENTIONALLY FAILING**
This test failure **signals a business logic gap**, not a test defect.

---

## Impact Assessment

### Business Impact: 🔴 HIGH

1. **Cannot enforce tournament business rules at creation**
   - No way to declare intended assignment strategy
   - No way to set custom pricing
   - No way to cap total enrollments

2. **Data Integrity Risks**
   - Implicit assignment_type can be misinterpreted
   - Session capacity changes silently affect tournament capacity
   - Hardcoded 500 credit default masks business intent

3. **Audit & Compliance**
   - Cannot audit which tournaments were intended as OPEN vs APPLICATION_BASED
   - Cannot track pricing strategy decisions
   - Cannot validate lifecycle transitions against business rules

4. **Feature Development Blocked**
   - Cannot implement waitlists (no explicit capacity)
   - Cannot implement dynamic pricing (no explicit price field in creation)
   - Cannot implement strategy-specific validation rules

---

## Architectural Issues

### 1. **Implicit vs Explicit Domain Model**

**Current (Implicit):**
```python
# Assignment type inferred from instructor presence
if tournament.master_instructor_id:
    assignment_type = "OPEN_ASSIGNMENT"
else:
    assignment_type = "APPLICATION_BASED"
```

**Problems:**
- Not auditable
- Not versionable
- Fragile to schema changes
- Cannot distinguish "not yet assigned" from "application-based"

**Correct (Explicit):**
```python
# Assignment type is a first-class domain attribute
tournament.assignment_type  # Enum: OPEN_ASSIGNMENT | APPLICATION_BASED
```

---

### 2. **Derived vs Declared Capacity**

**Current (Derived):**
```python
max_players = sum(session.capacity for session in tournament.sessions)
```

**Problems:**
- Session changes silently change tournament capacity
- Cannot implement business rule: "capacity cannot exceed N regardless of sessions"
- Cannot implement waitlist (what is the reference capacity?)

**Correct (Declared):**
```python
tournament.max_players  # Explicit business constraint
# Sessions must satisfy: sum(session.capacity) <= tournament.max_players
```

---

### 3. **Hardcoded vs Configurable Pricing**

**Current (Hardcoded Fallback):**
```python
enrollment_cost = tournament.enrollment_cost or 500  # Fallback to 500
```

**Problems:**
- Business rule (price must be explicit) not enforced
- All tournaments effectively cost 500 credits
- Cannot implement pricing strategies

**Correct (Explicit Required):**
```python
tournament.enrollment_cost  # Required, no default, set during creation
```

---

## Proposed Solution Architecture

### 1. Database Migration

```sql
-- Add explicit domain attributes
ALTER TABLE semesters
  ADD COLUMN assignment_type VARCHAR(30)
    CHECK (assignment_type IN ('OPEN_ASSIGNMENT', 'APPLICATION_BASED'));

ALTER TABLE semesters
  ADD COLUMN max_players INTEGER
    CHECK (max_players > 0);

-- Make enrollment_cost explicit (remove NULL default behavior)
ALTER TABLE semesters
  ALTER COLUMN enrollment_cost SET NOT NULL;

-- Add validation constraint
ALTER TABLE semesters
  ADD CONSTRAINT valid_assignment_type_instructor
  CHECK (
    (assignment_type = 'OPEN_ASSIGNMENT' AND master_instructor_id IS NOT NULL)
    OR
    (assignment_type = 'APPLICATION_BASED' AND master_instructor_id IS NULL)
  );
```

---

### 2. API Schema Update

```python
class TournamentGenerateRequest(BaseModel):
    name: str
    date: str
    specialization_type: SpecializationType
    age_group: Optional[str]
    campus_id: int
    sessions: List[SessionConfig]
    reward_policy_name: str

    # NEW: Explicit business attributes
    assignment_type: Literal["OPEN_ASSIGNMENT", "APPLICATION_BASED"]
    max_players: int = Field(..., gt=0, description="Maximum tournament participants")
    enrollment_cost: int = Field(..., gt=0, description="Enrollment fee in credits")

    # OPEN_ASSIGNMENT requires instructor
    instructor_id: Optional[int] = Field(
        None,
        description="Required if assignment_type=OPEN_ASSIGNMENT"
    )

    @validator('instructor_id')
    def validate_instructor_for_open_assignment(cls, v, values):
        if values.get('assignment_type') == 'OPEN_ASSIGNMENT' and v is None:
            raise ValueError('instructor_id required for OPEN_ASSIGNMENT')
        if values.get('assignment_type') == 'APPLICATION_BASED' and v is not None:
            raise ValueError('instructor_id must be null for APPLICATION_BASED')
        return v

    @validator('max_players')
    def validate_capacity_vs_sessions(cls, v, values):
        sessions = values.get('sessions', [])
        total_session_capacity = sum(s.capacity for s in sessions)
        if total_session_capacity > v:
            raise ValueError(
                f'Session capacity ({total_session_capacity}) '
                f'exceeds max_players ({v})'
            )
        return v
```

---

### 3. UI Form Update

```python
# streamlit_app/components/tournaments/player_tournament_generator.py

with st.form("create_tournament_form"):
    # ... existing fields ...

    # NEW: Assignment Type Selector
    assignment_type = st.selectbox(
        "Assignment Type *",
        options=["OPEN_ASSIGNMENT", "APPLICATION_BASED"],
        help="OPEN: Admin assigns instructor directly. APPLICATION: Instructors apply."
    )

    # NEW: Instructor Selection (conditional)
    instructor_id = None
    if assignment_type == "OPEN_ASSIGNMENT":
        instructors = _get_available_instructors()
        instructor_id = st.selectbox(
            "Assign Instructor *",
            options=instructors,
            format_func=lambda x: x['name']
        )

    # NEW: Max Players
    max_players = st.number_input(
        "Max Players *",
        min_value=1,
        max_value=100,
        value=20,
        help="Maximum participants for this tournament"
    )

    # NEW: Enrollment Cost
    enrollment_cost = st.number_input(
        "Enrollment Cost (Credits) *",
        min_value=0,
        value=500,
        step=50,
        help="Credits required to enroll"
    )

    # ... session configuration ...

    # VALIDATION: Sessions cannot exceed max_players
    total_session_capacity = sum(s['capacity'] for s in sessions)
    if total_session_capacity > max_players:
        st.error(
            f"⚠️ Session capacity ({total_session_capacity}) "
            f"exceeds max players ({max_players})"
        )
        submit_disabled = True
```

---

## Acceptance Criteria

### Domain Model
- [ ] `assignment_type` column exists with CHECK constraint
- [ ] `max_players` column exists with CHECK constraint
- [ ] `enrollment_cost` is NOT NULL and required at creation
- [ ] Database constraint validates assignment_type + instructor_id consistency

### API
- [ ] `TournamentGenerateRequest` includes all three explicit fields
- [ ] Pydantic validators enforce business rules
- [ ] API returns 400 with clear error for rule violations
- [ ] Existing tournaments backfilled with inferred assignment_type

### UI
- [ ] Tournament creation form includes Assignment Type selector
- [ ] Form includes Max Players input
- [ ] Form includes Enrollment Cost input
- [ ] Form validates session capacity <= max_players before submit
- [ ] OPEN_ASSIGNMENT shows instructor selector, APPLICATION_BASED hides it

### Tests
- [ ] `test_tournament_enrollment_open_assignment.py` passes (uses UI form)
- [ ] `test_tournament_enrollment_application_based.py` passes (uses UI form)
- [ ] API tests validate all three fields are required
- [ ] API tests validate business rule enforcement

---

## Migration Strategy

### Phase 1: Add Columns (Non-Breaking)
1. Add `assignment_type`, `max_players` as nullable columns
2. Backfill existing tournaments:
   - `assignment_type`: Infer from `master_instructor_id`
   - `max_players`: Calculate from session capacity sum
3. Add CHECK constraints

### Phase 2: Update API (Non-Breaking)
1. Update `TournamentGenerateRequest` schema
2. Add validation logic
3. Keep backward compatibility with optional fields initially

### Phase 3: Update UI (Breaking for Admins)
1. Add new form fields
2. Update form submission logic
3. Add client-side validation

### Phase 4: Make Required (Breaking)
1. Make `assignment_type`, `max_players` NOT NULL
2. Remove optional defaults from API
3. Enforce at API layer

---

## Related Documentation

- [Tournament Lifecycle State Machine](./TOURNAMENT_LIFECYCLE.md)
- [Instructor Assignment Workflows](../workflows/TOURNAMENT_INSTRUCTOR_ASSIGNMENT.md)
- [Enrollment Business Rules](../workflows/TOURNAMENT_ENROLLMENT_RULES.md)

---

## Decision Record

**Decision:** Document domain gap, do NOT implement workarounds
**Rationale:** Test failure correctly signals business logic deficiency
**Status:** Accepted - 2026-01-12
**Stakeholders:** Engineering Team

**The test is correct. The domain model is incomplete. This is intentional technical debt to be resolved in a future iteration.**

---

## Notes

This document was created during Playwright E2E test development when it became apparent that the tournament creation UI does not expose business-critical attributes that the test (correctly) expects to exist.

Rather than hacking the test with SQL updates or API workarounds, we chose to document the root cause: **the domain model does not match the business requirements**.

The test will remain failing until the domain model, API, and UI are updated to properly support explicit assignment type, max players, and enrollment cost fields.
