# Domain Lifecycle Map

**Purpose**: Define ALL valid state transitions for core domain entities BEFORE fixing Category 3 tests.
**Created**: 2026-02-25
**Status**: Prerequisite for Category 3 work

---

## Architectural Principle

> **"Model the lifecycle first, fix tests second."**
>
> Category 3 failures are NOT test bugs — they are **business rule violations**.
> Fix tests by **aligning fixture setup with domain rules**, not by bypassing validation.

---

## 1. Tournament (Semester) Lifecycle

### 1.1 Status Enum Definition

**Source**: `app/models/semester.py:10-18`

```python
class SemesterStatus(str, enum.Enum):
    DRAFT = "DRAFT"                           # Admin created, no instructor, no sessions
    SEEKING_INSTRUCTOR = "SEEKING_INSTRUCTOR" # Admin looking for instructor
    INSTRUCTOR_ASSIGNED = "INSTRUCTOR_ASSIGNED" # Has instructor, no sessions yet
    READY_FOR_ENROLLMENT = "READY_FOR_ENROLLMENT" # Has instructor + sessions, students can enroll
    ONGOING = "ONGOING"                       # Past enrollment deadline, classes in progress
    COMPLETED = "COMPLETED"                   # All sessions finished
    CANCELLED = "CANCELLED"                   # Admin cancelled
```

### 1.2 Dual-Status Architecture (CRITICAL)

**⚠️ WARNING**: Tournament has TWO status fields:

| Field | Type | Source of Truth | Usage |
|-------|------|-----------------|-------|
| `status` | `Enum(SemesterStatus)` | **Business logic** | Validation, lifecycle transitions |
| `tournament_status` | `String` | **Legacy/UI** | Display, backwards compatibility |

**Anti-Pattern Found**:
```python
# ❌ DON'T: Check string field
if tournament.tournament_status == "ENROLLMENT_OPEN":

# ✅ DO: Check enum field
if tournament.status == SemesterStatus.READY_FOR_ENROLLMENT:
```

**Mapping (Legacy → Enum)**:
- `"ENROLLMENT_OPEN"` → `SemesterStatus.READY_FOR_ENROLLMENT`
- `"IN_PROGRESS"` → `SemesterStatus.ONGOING`

### 1.3 Valid State Transitions

**Source**: `app/services/tournament/status_service.py:35-45`

```
DRAFT (initial state)
  ↓
SEEKING_INSTRUCTOR
  ↓ ↑ (bidirectional: instructor assignment can be revoked)
PENDING_INSTRUCTOR_ACCEPTANCE
  ↓
INSTRUCTOR_CONFIRMED
  ↓
READY_FOR_ENROLLMENT
  ↓
OPEN_FOR_ENROLLMENT (deprecated, use READY_FOR_ENROLLMENT)
  ↓
IN_PROGRESS (alias for ONGOING)
  ↓
CLOSED (pre-completion state)
  ↓
COMPLETED (terminal)

CANCELLED (terminal, reachable from most states)
```

**Valid Transitions Table**:

| From Status | To Status (allowed) |
|-------------|---------------------|
| DRAFT | SEEKING_INSTRUCTOR |
| SEEKING_INSTRUCTOR | PENDING_INSTRUCTOR_ACCEPTANCE, INSTRUCTOR_CONFIRMED, CANCELLED |
| PENDING_INSTRUCTOR_ACCEPTANCE | INSTRUCTOR_CONFIRMED, SEEKING_INSTRUCTOR (reject), CANCELLED |
| INSTRUCTOR_CONFIRMED | READY_FOR_ENROLLMENT, SEEKING_INSTRUCTOR (reassign), CANCELLED |
| READY_FOR_ENROLLMENT | OPEN_FOR_ENROLLMENT, IN_PROGRESS, CANCELLED |
| OPEN_FOR_ENROLLMENT | IN_PROGRESS, CANCELLED |
| IN_PROGRESS | CLOSED, COMPLETED, CANCELLED |
| CLOSED | COMPLETED |
| COMPLETED | _(terminal)_ |
| CANCELLED | _(terminal)_ |

### 1.4 Business Rules by Status

#### DRAFT
- **Purpose**: Admin created tournament, no instructor assigned
- **Can create?**: ✅ Admin only
- **Can assign instructor?**: ❌ Must transition to SEEKING_INSTRUCTOR first
- **Can generate sessions?**: ❌ No instructor
- **Can students enroll?**: ❌ No sessions

#### SEEKING_INSTRUCTOR
- **Purpose**: Actively recruiting instructor
- **Can instructor apply?**: ✅ Yes
- **Can admin assign instructor?**: ✅ Yes (direct assignment)
- **Can generate sessions?**: ❌ Wait for instructor confirmation
- **Can students enroll?**: ❌ No sessions yet

#### PENDING_INSTRUCTOR_ACCEPTANCE
- **Purpose**: Instructor invited, waiting for acceptance
- **Can instructor accept?**: ✅ Yes (transitions to INSTRUCTOR_CONFIRMED)
- **Can instructor decline?**: ✅ Yes (reverts to SEEKING_INSTRUCTOR)
- **Can generate sessions?**: ❌ Wait for acceptance
- **Can students enroll?**: ❌ No sessions yet

#### INSTRUCTOR_CONFIRMED
- **Purpose**: Instructor accepted, ready for session generation
- **Can generate sessions?**: ✅ Yes
- **Can students enroll?**: ❌ Wait for READY_FOR_ENROLLMENT
- **Next step**: Admin generates sessions → auto-transition to READY_FOR_ENROLLMENT

#### READY_FOR_ENROLLMENT
- **Purpose**: Sessions generated, accepting student enrollments
- **Can students enroll?**: ✅ Yes (subject to capacity, balance, prerequisites)
- **Can students unenroll?**: ✅ Yes (with refund policy)
- **Can instructor submit results?**: ❌ Not started yet
- **Next step**: Enrollment deadline passes → auto-transition to ONGOING

#### ONGOING
- **Purpose**: Classes in progress
- **Can students enroll?**: ❌ Enrollment closed
- **Can students unenroll?**: ⚠️ Partial refund only
- **Can instructor submit results?**: ✅ Yes
- **Next step**: All sessions completed → admin transitions to COMPLETED

#### COMPLETED
- **Purpose**: Terminal state, all sessions finished
- **Can modify?**: ❌ Read-only
- **Can distribute rewards?**: ✅ Yes

#### CANCELLED
- **Purpose**: Terminal state, tournament aborted
- **Can resume?**: ❌ Must create new tournament
- **Refund policy**: ✅ Full refund to enrolled students

---

## 2. Instructor Application Lifecycle

### 2.1 Status Enum Definition

**Source**: `app/models/instructor_assignment.py:317-321`

```python
class ApplicationStatus(enum.Enum):
    PENDING = "PENDING"     # Waiting for master review
    ACCEPTED = "ACCEPTED"   # Master accepted
    DECLINED = "DECLINED"   # Master declined
```

### 2.2 State Transitions

```
(Instructor applies)
  ↓
PENDING
  ↓ (master decision)
  ├──> ACCEPTED (terminal)
  └──> DECLINED (terminal)
```

### 2.3 Business Rules

#### Application Creation
- **Who can apply?**: Instructor with `UserRole.INSTRUCTOR`
- **Prerequisites**:
  - Tournament status = `SEEKING_INSTRUCTOR`
  - Instructor has required license level
  - No existing application for this tournament
- **Auto-creates**: `InstructorPositionApplication` record

#### PENDING
- **Can instructor withdraw?**: ✅ Yes (soft-delete application)
- **Can master review?**: ✅ Yes (accept/decline)
- **Timeout policy**: None (applications remain pending indefinitely)

#### ACCEPTED
- **Effect**: Tournament status → `INSTRUCTOR_CONFIRMED`
- **Reversible?**: ⚠️ Yes (admin can reassign)
- **Instructor assigned to**: `Semester.master_instructor_id`

#### DECLINED
- **Effect**: Application marked declined, tournament remains `SEEKING_INSTRUCTOR`
- **Can re-apply?**: ✅ Yes (create new application)

---

## 3. Student Enrollment Lifecycle

### 3.1 Status Enum Definition

**Source**: `app/models/semester_enrollment.py:15-20`

```python
class EnrollmentStatus(enum.Enum):
    PENDING = "pending"      # Student requested, waiting for admin approval
    APPROVED = "approved"    # Admin approved, enrollment active
    REJECTED = "rejected"    # Admin rejected the request
    WITHDRAWN = "withdrawn"  # Student withdrew their request
```

### 3.2 State Transitions

```
(Student enrolls)
  ↓
PENDING
  ↓ (admin decision)
  ├──> APPROVED ──┬──> WITHDRAWN (student unenrolls)
  │               └──> (is_active=False) (admin deactivates)
  └──> REJECTED (terminal)
```

### 3.3 Business Rules

#### Enrollment Creation
- **Who can enroll?**: Student with `UserRole.STUDENT`
- **Prerequisites**:
  - Tournament status IN (`READY_FOR_ENROLLMENT`, `ONGOING`)
  - Student has sufficient credit balance
  - Tournament not at capacity
  - Student not already enrolled
- **Effect**:
  - Deduct `enrollment_cost` from `credit_balance` (atomic with row-level lock)
  - Create `SemesterEnrollment` with `request_status=PENDING`

#### PENDING
- **Can student cancel?**: ✅ Yes (transitions to WITHDRAWN, 50% refund)
- **Can admin approve?**: ✅ Yes (transitions to APPROVED, sets `is_active=True`)
- **Can admin reject?**: ✅ Yes (transitions to REJECTED, 100% refund)

#### APPROVED
- **Can student unenroll?**: ✅ Yes (transitions to WITHDRAWN)
- **Refund policy**:
  - Before tournament starts: 50% refund
  - After tournament starts: 0% refund (policy TBD)
- **Can admin deactivate?**: ✅ Yes (sets `is_active=False`, enrollment remains APPROVED)

#### REJECTED
- **Reversible?**: ❌ Terminal state
- **Refund**: 100% automatic (credits restored)

#### WITHDRAWN
- **Reversible?**: ❌ Terminal state
- **Refund**: 50% automatic (credits restored)
- **Can re-enroll?**: ✅ Yes (create new enrollment request)

---

## 4. Session Lifecycle

### 4.1 Status Values

**Source**: Inferred from codebase (no explicit enum found)

```python
# String-based status (no enum)
session_status: str
  - "scheduled" / "pending" (initial)
  - "in_progress" (instructor checked in)
  - "completed" (results submitted)
  - "cancelled" (admin cancelled)
```

### 4.2 State Transitions

```
(Session auto-generated)
  ↓
scheduled/pending
  ↓ (instructor check-in)
in_progress
  ↓ (instructor submits results)
completed (terminal)

cancelled (terminal, reachable from any state)
```

### 4.3 Business Rules

#### scheduled/pending
- **Can instructor check in?**: ✅ Yes (if assigned to session)
- **Can admin modify?**: ✅ Yes (reschedule, reassign instructor)
- **Can students view?**: ✅ Yes (if enrolled in tournament)

#### in_progress
- **Can instructor submit results?**: ✅ Yes
- **Can admin modify?**: ⚠️ Limited (cannot reassign instructor)

#### completed
- **Can modify?**: ❌ Read-only
- **Can view results?**: ✅ Yes (students, instructors, admin)

---

## 5. Credit Transaction Lifecycle

### 5.1 Transaction Types

**Source**: `app/models/credit_transaction.py` (inferred)

```python
transaction_type: str
  - "PAYMENT" (admin adds credits)
  - "ENROLLMENT" (student enrolls in tournament, debit)
  - "REFUND" (student unenrolls, credit)
  - "REWARD" (tournament completion, credit)
```

### 5.2 Immutability Rule

**⚠️ CRITICAL**: Credit transactions are **append-only**.

- **Cannot modify**: Existing transactions are immutable
- **Cannot delete**: Audit trail preservation
- **Reversal**: Create offsetting transaction (REFUND)

### 5.3 Balance Calculation

```python
credit_balance = SUM(
  + PAYMENT.amount
  - ENROLLMENT.amount
  + REFUND.amount
  + REWARD.amount
)
```

**Atomic Protection**:
```python
# Row-level lock prevents race conditions
student = db.query(User).filter(User.id == student_id).with_for_update().first()
if student.credit_balance < enrollment_cost:
    raise InsufficientCreditsError
student.credit_balance -= enrollment_cost
```

---

## 6. Category 3 Test Fixture Requirements

### 6.1 Fixture Setup Helpers (TO BE CREATED)

```python
# tests/integration/api_smoke/lifecycle_helpers.py

def transition_tournament_to_seeking_instructor(tournament_id, admin_token, db):
    """Transition tournament from DRAFT to SEEKING_INSTRUCTOR"""
    # Implementation: Update status, validate transition

def transition_tournament_to_ready_for_enrollment(tournament_id, admin_token, db):
    """
    Full setup for enrollment-ready tournament:
    1. Assign instructor
    2. Generate sessions
    3. Transition to READY_FOR_ENROLLMENT
    """
    # Implementation: Multi-step setup

def create_instructor_application(tournament_id, instructor_token, db):
    """Create instructor application for tournament"""
    # Implementation: POST /tournaments/{id}/instructor-applications

def approve_instructor_application(application_id, admin_token, db):
    """Admin approves instructor application"""
    # Implementation: POST /tournaments/instructor-applications/{id}/approve
```

### 6.2 Required Fixture Data for Category 3 Tests

| Test | Required Setup | Helper Function |
|------|----------------|-----------------|
| test_apply_to_tournament_happy_path | Tournament status = SEEKING_INSTRUCTOR | `transition_tournament_to_seeking_instructor()` |
| test_get_my_tournament_application_happy_path | Instructor application exists | `create_instructor_application()` |
| test_accept_instructor_assignment_happy_path | Tournament status = PENDING_INSTRUCTOR_ACCEPTANCE | (part of assignment flow) |
| test_delete_tournament_reward_config_happy_path | Fix property setter bug in endpoint | (endpoint fix, not fixture) |

---

## 7. Category 3 Implementation Strategy

### Phase 1: Create Lifecycle Helpers (Days 1-2)
1. Implement `lifecycle_helpers.py` with status transition functions
2. Add validation for each transition
3. Write unit tests for helpers

### Phase 2: Fix Test Fixtures (Days 3-4)
1. Update test_apply_to_tournament_happy_path
   - Setup: Call `transition_tournament_to_seeking_instructor()`
   - Verify: 400 → 200/201
2. Update test_get_my_tournament_application_happy_path
   - Setup: Call `create_instructor_application()`
   - Verify: 404 → 200
3. Update test_accept_instructor_assignment_happy_path
   - Setup: Create application + wait for admin invitation
   - Verify: 400 → 200

### Phase 3: Endpoint Bugs (Day 5)
1. Fix test_delete_tournament_reward_config_happy_path
   - Root cause: `tournament.reward_config` property has no setter
   - Solution: Implement setter or use different approach
   - Verify: 500 → 200

### Expected Outcome
- **40 FAILED → 25-30 FAILED**
- All remaining failures are **true business logic gaps**, not fixture issues

---

## 8. Validation Rules Reference

### Tournament Creation Rules
- [x] Admin-only operation
- [x] `start_date` < `end_date`
- [x] Initial status = DRAFT
- [x] `tournament_status` synced with `status` enum

### Instructor Application Rules
- [x] Tournament status = SEEKING_INSTRUCTOR
- [x] Instructor has required license level (check `UserLicense` table)
- [x] No duplicate applications (1 per instructor per tournament)

### Student Enrollment Rules
- [x] Tournament status IN (READY_FOR_ENROLLMENT, ONGOING)
- [x] `credit_balance >= enrollment_cost` (atomic check with `with_for_update()`)
- [x] Capacity check: `current_enrollments < max_players`
- [x] No duplicate enrollments

### Unenrollment Rules
- [x] Enrollment exists and `request_status = APPROVED`
- [x] Refund = 50% of `enrollment_cost`
- [x] Update `request_status` to WITHDRAWN
- [x] Set `is_active = False`

---

## 9. Anti-Patterns to Avoid

### ❌ DON'T: Bypass Validation in Tests
```python
# ❌ BAD: Force invalid state
tournament.status = "READY_FOR_ENROLLMENT"  # Skip validation
db.commit()
```

```python
# ✅ GOOD: Use valid transition
transition_tournament_to_ready_for_enrollment(tournament_id, admin_token, db)
```

### ❌ DON'T: Mock Domain Logic
```python
# ❌ BAD: Mock business rules
with patch('app.services.enrollment.check_balance', return_value=True):
    enroll_student(...)  # Bypasses real validation
```

```python
# ✅ GOOD: Setup real data
add_credits_to_student(student_id, amount=500, db)
enroll_student(...)  # Real validation passes
```

### ❌ DON'T: Mix Status Fields
```python
# ❌ BAD: Use legacy string field
if tournament.tournament_status == "ENROLLMENT_OPEN":

# ✅ GOOD: Use enum field
if tournament.status == SemesterStatus.READY_FOR_ENROLLMENT:
```

---

## 10. References

### Models
- `app/models/semester.py` — Tournament (Semester) model
- `app/models/instructor_assignment.py` — Instructor application model
- `app/models/semester_enrollment.py` — Student enrollment model
- `app/models/user.py` — User and UserRole enum

### Services
- `app/services/tournament/status_service.py` — Valid transitions
- `app/services/tournament/status_validator.py` — Transition validation
- `app/api/api_v1/endpoints/tournaments/lifecycle.py` — Lifecycle API

### Tests (E2E Examples)
- `app/tests/test_tournament_workflow_e2e.py`
- `app/tests/test_instructor_assignment_e2e.py`
- `app/tests/test_refund_workflow_e2e.py`

---

**Status**: Ready for Category 3 implementation
**Next Step**: Create `lifecycle_helpers.py` before touching any tests
