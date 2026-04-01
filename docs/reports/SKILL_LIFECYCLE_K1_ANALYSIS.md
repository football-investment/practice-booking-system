# Skill Lifecycle (K1) — State Machine Analysis & Implementation Plan

**Date:** 2026-02-24
**Status:** 🔍 ANALYSIS COMPLETE — Ready for Implementation Planning
**Priority:** Production-grade robustness (not MVP)

---

## Executive Summary

Current skill system **lacks explicit lifecycle state machine**. System has:
- ✅ Row-level locking (`with_for_update()`)
- ✅ Partial idempotency (`award_skill_points()`)
- ✅ Audit trail (SkillReward table)
- ❌ **NO explicit state definition**
- ❌ **NO DB-level state integrity constraint**
- ❌ **NO invalid transition matrix**
- ❌ **NO comprehensive concurrency testing**

**Requirement:** Implement production-grade skill lifecycle state machine with same rigor as Priority 4 (Reward Distribution).

---

## Current System Architecture

### Models

#### 1. FootballSkillAssessment
```python
# app/models/football_skill_assessment.py
class FootballSkillAssessment(Base):
    id: int
    user_license_id: int
    skill_name: str  # 29 skills from skills_config.py
    points_earned: int
    points_total: int
    percentage: float  # 0-100
    assessed_by: int  # instructor_id
    assessed_at: datetime
    notes: str

    # ❌ MISSING: status/state field
    # ❌ MISSING: validation tracking
    # ❌ MISSING: lifecycle metadata
```

#### 2. UserLicense
```python
# app/models/license.py
class UserLicense(Base):
    id: int
    user_id: int
    specialization_type: str
    current_level: int
    football_skills: JSON  # Cached averages
    skills_last_updated_at: datetime
    skills_updated_by: int

    # ❌ MISSING: skill lifecycle state tracking
```

#### 3. SkillReward
```python
# app/models/skill_reward.py
class SkillReward(Base):
    id: int
    user_id: int
    source_type: str  # TOURNAMENT, TRAINING
    source_id: int
    skill_name: str
    points_awarded: int
    created_at: datetime

    # ✅ HAS: Audit trail
    # ✅ HAS: UniqueConstraint (via service layer)
    # ❌ MISSING: State tracking
```

### Services

#### 1. FootballSkillService
```python
# app/services/football_skill_service.py

def create_assessment(...):
    """
    ✅ Has: Validation (skill name, point range)
    ❌ Missing: State machine integration
    ❌ Missing: Idempotency (can create duplicate assessments)
    """

def recalculate_skill_average(...):
    """
    ✅ Has: Row-level locking (with_for_update())
    ✅ Has: JSON field update (flag_modified)
    ❌ Missing: State transition validation
    """

def award_skill_points(...):
    """
    ✅ Has: Idempotency (duplicate check + IntegrityError handling)
    ✅ Has: UniqueConstraint protection
    ✅ Has: Audit logging
    ❌ Missing: State machine integration
    """
```

#### 2. SkillProgressionService
```python
# app/services/skill_progression_service.py

def calculate_skill_value_from_placement(...):
    """
    ✅ Has: V3 EMA algorithm
    ✅ Has: Opponent factor (ELO-inspired)
    ✅ Has: Match performance modifier
    ❌ Missing: State validation (can calculate for invalid states)
    """
```

### Configuration

**29 Skills across 4 categories:**
- Outfield (11): ball_control, dribbling, finishing, shot_power, long_shots, volleys, crossing, passing, heading, tackle, marking
- Set Pieces (3): free_kicks, corners, penalties
- Mental (8): positioning_off, positioning_def, vision, aggression, reactions, composure, consistency, tactical_awareness
- Physical (7): acceleration, sprint_speed, agility, jumping, strength, stamina, balance

**Skill Value Range:** 40.0 (MIN_SKILL_VALUE) to 99.0 (MAX_SKILL_CAP)
**Default Baseline:** 50.0

---

## Proposed State Machine — Skill Assessment Lifecycle

### State Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SKILL ASSESSMENT LIFECYCLE                       │
└─────────────────────────────────────────────────────────────────────────┘

    [Initial State]
         │
         ▼
  ┌──────────────┐
  │ NOT_ASSESSED │  ← No assessment exists yet
  └──────────────┘
         │
         │ (1) Instructor creates assessment
         │     POST /licenses/{id}/skills/assess
         │     Requirements: instructor role, valid skill_name, points
         ▼
  ┌──────────────┐
  │   ASSESSED   │  ← Assessment created, awaiting validation
  └──────────────┘
         │
         ├──────────────────────────────────────┐
         │                                      │
         │ (2a) Admin validates                 │ (2b) New assessment created
         │      PUT /assessments/{id}/validate   │      → Archives old assessment
         │      Requirements: admin role         │
         ▼                                      ▼
  ┌──────────────┐                      ┌──────────────┐
  │  VALIDATED   │                      │   ARCHIVED   │  ← Replaced by newer assessment
  └──────────────┘                      └──────────────┘
         │                                      │
         │ (3) New assessment created           │ [Terminal State]
         │     → Archives validated assessment   │ No transitions allowed
         ▼
  ┌──────────────┐
  │   ARCHIVED   │
  └──────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Optional Future States (Phase 2)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ASSESSED ──(dispute)──▶ DISPUTED ──(re-assess)──▶ ASSESSED             │
│     │                        │                                            │
│     │                        └─(resolve)──▶ VALIDATED                    │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### State Definitions

| State | Description | Can Transition To | Terminal? |
|-------|-------------|-------------------|-----------|
| **NOT_ASSESSED** | No assessment exists for this skill | ASSESSED | No |
| **ASSESSED** | Instructor created assessment, pending validation | VALIDATED, ARCHIVED | No |
| **VALIDATED** | Admin/Lead Instructor approved assessment | ARCHIVED | No |
| **ARCHIVED** | Old assessment replaced by newer one | None | **Yes** |
| ~~DISPUTED~~ | *(Future)* Student disputes assessment | ASSESSED, VALIDATED | No |

### Transition Matrix

| From / To | NOT_ASSESSED | ASSESSED | VALIDATED | ARCHIVED | DISPUTED* |
|-----------|--------------|----------|-----------|----------|-----------|
| **NOT_ASSESSED** | ✅ Idempotent | ✅ Create | ❌ Invalid | ❌ Invalid | ❌ Invalid |
| **ASSESSED** | ❌ Invalid | ✅ Idempotent | ✅ Validate | ✅ Archive | ⚠️ Future |
| **VALIDATED** | ❌ Invalid | ❌ Invalid | ✅ Idempotent | ✅ Archive | ⚠️ Future |
| **ARCHIVED** | ❌ Invalid | ❌ Invalid | ❌ Invalid | ✅ Idempotent | ❌ Invalid |
| **DISPUTED*** | ❌ Invalid | ⚠️ Future | ⚠️ Future | ❌ Invalid | ✅ Idempotent |

*Future Phase 2 feature

### Invalid Transitions (Must Reject)

```python
INVALID_TRANSITIONS = {
    "NOT_ASSESSED": ["VALIDATED", "ARCHIVED", "DISPUTED"],  # Must create first
    "ASSESSED": ["NOT_ASSESSED"],  # Can't un-create
    "VALIDATED": ["NOT_ASSESSED", "ASSESSED"],  # Can't un-validate
    "ARCHIVED": ["NOT_ASSESSED", "ASSESSED", "VALIDATED", "DISPUTED"],  # Terminal
    "DISPUTED": ["NOT_ASSESSED", "ARCHIVED"]  # Must resolve first
}
```

---

## DB Schema Changes Required

### 1. Add `status` Column to FootballSkillAssessment

```sql
-- Migration: Add skill assessment lifecycle status
ALTER TABLE football_skill_assessments
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ASSESSED';

-- Create enum constraint (PostgreSQL)
ALTER TABLE football_skill_assessments
ADD CONSTRAINT ck_skill_assessment_status
CHECK (status IN ('NOT_ASSESSED', 'ASSESSED', 'VALIDATED', 'ARCHIVED', 'DISPUTED'));

-- Index for status queries
CREATE INDEX ix_skill_assessments_status ON football_skill_assessments(status);

-- Index for user + skill + status (common query pattern)
CREATE INDEX ix_skill_assessments_user_skill_status
ON football_skill_assessments(user_license_id, skill_name, status);
```

### 2. Add Validation Tracking

```sql
-- Add validation metadata
ALTER TABLE football_skill_assessments
ADD COLUMN validated_by INT REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN validated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN archived_by INT REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN archived_reason TEXT;

-- Add state transition audit
ALTER TABLE football_skill_assessments
ADD COLUMN previous_status VARCHAR(20),
ADD COLUMN status_changed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN status_changed_by INT REFERENCES users(id) ON DELETE SET NULL;
```

### 3. Update Existing Data

```sql
-- Backfill existing assessments
UPDATE football_skill_assessments
SET status = 'ASSESSED',
    status_changed_at = assessed_at,
    status_changed_by = assessed_by
WHERE status IS NULL OR status = '';

-- Mark old assessments as VALIDATED (grace period)
-- Business rule: Assessments older than 30 days assumed valid
UPDATE football_skill_assessments
SET status = 'VALIDATED',
    validated_at = assessed_at,
    validated_by = assessed_by
WHERE assessed_at < NOW() - INTERVAL '30 days'
  AND status = 'ASSESSED';
```

---

## Idempotency Strategy

### 1. Create Assessment (ASSESSED)

**Current:** No idempotency — multiple assessments can be created for same skill on same day

**Proposed:**
```python
def create_assessment_idempotent(
    user_license_id: int,
    skill_name: str,
    points_earned: int,
    points_total: int,
    assessed_by: int,
    notes: Optional[str] = None
) -> Tuple[FootballSkillAssessment, bool]:
    """
    Create assessment with idempotency.

    Business Rule: Only 1 ASSESSED assessment per (user_license_id, skill_name) at a time.

    Returns:
        (assessment, created) where created=True if new, False if existing

    Idempotency Key: (user_license_id, skill_name, status='ASSESSED')
    """
    # Check for existing ASSESSED assessment
    existing = db.query(FootballSkillAssessment).filter(
        FootballSkillAssessment.user_license_id == user_license_id,
        FootballSkillAssessment.skill_name == skill_name,
        FootballSkillAssessment.status == 'ASSESSED'
    ).first()

    if existing:
        logger.info(f"🔒 IDEMPOTENT: ASSESSED assessment already exists (id={existing.id})")
        return (existing, False)

    # Archive any old assessments (ASSESSED or VALIDATED)
    old_assessments = db.query(FootballSkillAssessment).filter(
        FootballSkillAssessment.user_license_id == user_license_id,
        FootballSkillAssessment.skill_name == skill_name,
        FootballSkillAssessment.status.in_(['ASSESSED', 'VALIDATED'])
    ).all()

    for old in old_assessments:
        old.status = 'ARCHIVED'
        old.archived_at = datetime.now(timezone.utc)
        old.archived_by = assessed_by
        old.archived_reason = "Replaced by new assessment"
        old.previous_status = old.status

    # Create new assessment
    assessment = FootballSkillAssessment(
        user_license_id=user_license_id,
        skill_name=skill_name,
        points_earned=points_earned,
        points_total=points_total,
        percentage=calculate_percentage(points_earned, points_total),
        assessed_by=assessed_by,
        assessed_at=datetime.now(timezone.utc),
        notes=notes,
        status='ASSESSED'
    )

    db.add(assessment)
    db.flush()

    # Recalculate average (with existing row-level locking)
    recalculate_skill_average(user_license_id, skill_name)

    return (assessment, True)
```

### 2. Validate Assessment (VALIDATED)

```python
def validate_assessment(
    assessment_id: int,
    validated_by: int
) -> FootballSkillAssessment:
    """
    Validate assessment with state transition check.

    Valid Transitions: ASSESSED → VALIDATED
    Idempotent: VALIDATED → VALIDATED (no-op)

    Raises:
        ValueError: If invalid state transition
    """
    assessment = db.query(FootballSkillAssessment).filter(
        FootballSkillAssessment.id == assessment_id
    ).with_for_update().first()

    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    # Idempotent: Already validated
    if assessment.status == 'VALIDATED':
        logger.info(f"🔒 IDEMPOTENT: Assessment already VALIDATED (id={assessment_id})")
        return assessment

    # Invalid transition
    if assessment.status not in ['ASSESSED']:
        raise ValueError(
            f"Invalid state transition: {assessment.status} → VALIDATED. "
            f"Assessment must be ASSESSED before validation."
        )

    # Valid transition
    assessment.previous_status = assessment.status
    assessment.status = 'VALIDATED'
    assessment.validated_by = validated_by
    assessment.validated_at = datetime.now(timezone.utc)
    assessment.status_changed_at = datetime.now(timezone.utc)
    assessment.status_changed_by = validated_by

    db.flush()

    return assessment
```

### 3. Archive Assessment (ARCHIVED)

```python
def archive_assessment(
    assessment_id: int,
    archived_by: int,
    reason: str
) -> FootballSkillAssessment:
    """
    Archive assessment with state transition check.

    Valid Transitions: ASSESSED → ARCHIVED, VALIDATED → ARCHIVED
    Idempotent: ARCHIVED → ARCHIVED (no-op)

    Raises:
        ValueError: If invalid state transition
    """
    assessment = db.query(FootballSkillAssessment).filter(
        FootballSkillAssessment.id == assessment_id
    ).with_for_update().first()

    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    # Idempotent: Already archived
    if assessment.status == 'ARCHIVED':
        logger.info(f"🔒 IDEMPOTENT: Assessment already ARCHIVED (id={assessment_id})")
        return assessment

    # Invalid transition
    if assessment.status not in ['ASSESSED', 'VALIDATED']:
        raise ValueError(
            f"Invalid state transition: {assessment.status} → ARCHIVED. "
            f"Only ASSESSED or VALIDATED assessments can be archived."
        )

    # Valid transition
    assessment.previous_status = assessment.status
    assessment.status = 'ARCHIVED'
    assessment.archived_by = archived_by
    assessment.archived_at = datetime.now(timezone.utc)
    assessment.archived_reason = reason
    assessment.status_changed_at = datetime.now(timezone.utc)
    assessment.status_changed_by = archived_by

    db.flush()

    return assessment
```

---

## Concurrency Edge Cases

### Scenario 1: Concurrent Assessment Creation (Same Skill)

**Race Condition:**
```
Thread A: Check existing ASSESSED → None
Thread B: Check existing ASSESSED → None
Thread A: Create assessment (id=1, status=ASSESSED)
Thread B: Create assessment (id=2, status=ASSESSED)  ❌ DUPLICATE
```

**Solution 1: UniqueConstraint on (user_license_id, skill_name, status)**
```sql
-- Partial unique index (PostgreSQL)
CREATE UNIQUE INDEX uq_skill_assessment_active
ON football_skill_assessments(user_license_id, skill_name)
WHERE status IN ('ASSESSED', 'VALIDATED');
```

**Solution 2: Row-Level Locking on UserLicense**
```python
def create_assessment_with_lock(...):
    # Lock UserLicense row to serialize concurrent assessment creation
    with lock_timer("skill", "UserLicense", user_license_id, logger):
        license = db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).with_for_update().first()

        # Check existing + create assessment (atomic)
        existing = check_existing_assessed(user_license_id, skill_name)
        if existing:
            return (existing, False)

        # Create new assessment
        return create_assessment_internal(...)
```

### Scenario 2: Concurrent Validation (Same Assessment)

**Race Condition:**
```
Thread A: Validate assessment (id=1, ASSESSED → VALIDATED)
Thread B: Validate assessment (id=1, ASSESSED → VALIDATED)
```

**Solution: Row-Level Locking with Idempotency**
```python
def validate_assessment(...):
    assessment = db.query(FootballSkillAssessment).filter(
        FootballSkillAssessment.id == assessment_id
    ).with_for_update().first()  # ✅ Blocks concurrent access

    # Idempotent check
    if assessment.status == 'VALIDATED':
        return assessment  # ✅ Second thread returns existing

    # Validate
    assessment.status = 'VALIDATED'
    ...
```

### Scenario 3: Concurrent Archive + Create New Assessment

**Race Condition:**
```
Thread A: Create new assessment → Archives old assessment (id=1)
Thread B: Create new assessment → Archives old assessment (id=1)
Thread A: Creates new (id=2, status=ASSESSED)
Thread B: Creates new (id=3, status=ASSESSED)  ❌ DUPLICATE
```

**Solution: Combine UniqueConstraint + Row-Level Locking**
- UniqueConstraint prevents multiple ASSESSED assessments
- Row-level locking on UserLicense serializes archive + create sequence

---

## Test Coverage Plan (Production-Grade)

### Test 1: `test_skill_assessment_full_lifecycle` ✅

**Purpose:** Full E2E skill assessment lifecycle

**Flow:**
1. Create instructor + student with LFA_FOOTBALL_PLAYER license
2. Instructor creates assessment (NOT_ASSESSED → ASSESSED)
3. Verify status = ASSESSED, validated_by = None
4. Admin validates assessment (ASSESSED → VALIDATED)
5. Verify status = VALIDATED, validated_by = admin_id, validated_at set
6. Instructor creates new assessment → old auto-archived (VALIDATED → ARCHIVED)
7. Verify old status = ARCHIVED, new status = ASSESSED

**Validations:**
- ✅ State transitions follow state machine
- ✅ Timestamps populated correctly
- ✅ Auto-archiving works (old → ARCHIVED when new created)
- ✅ Cached average updated after each assessment

**Runtime:** ~2s

---

### Test 2: `test_skill_assessment_invalid_transitions` ✅

**Purpose:** Negative path validation — invalid state transitions

**Test Cases:**
1. **Cannot validate non-existent assessment** → HTTP 404 ✅
2. **Cannot validate ARCHIVED assessment** → HTTP 400 ✅
3. **Cannot archive ARCHIVED assessment** → Idempotent (no-op) ✅
4. **Cannot create VALIDATED assessment directly** → Must be ASSESSED first ✅

**Runtime:** ~1.5s

---

### Test 3: `test_skill_assessment_idempotency` ✅

**Purpose:** Idempotency validation

**Test Cases:**
1. **Create same assessment twice** → Returns existing (created=False) ✅
2. **Validate same assessment twice** → Idempotent (no change) ✅
3. **Archive same assessment twice** → Idempotent (no change) ✅

**Runtime:** ~1.5s

---

### Test 4: `test_concurrent_skill_assessment_creation` ✅ **CONCURRENCY**

**Purpose:** Concurrency stress test — race condition protection

**Scenario:**
- 3 threads create assessment for same skill simultaneously
- Simulates high-concurrency production environment

**Expected Behavior:**
- Thread 1: HTTP 201 (created, id=1)
- Thread 2, 3: HTTP 200 (idempotent, returns id=1) OR HTTP 409 (UniqueViolation)

**Validations:**
- ✅ Only 1 FootballSkillAssessment with status=ASSESSED
- ✅ Cached average updated exactly once
- ✅ No duplicate ASSESSED assessments

**Runtime:** ~2s

---

### Test 5: `test_concurrent_skill_validation` ✅ **CONCURRENCY**

**Purpose:** Concurrent validation protection

**Scenario:**
- Create 1 ASSESSED assessment
- 3 threads validate same assessment simultaneously

**Expected Behavior:**
- Thread 1: HTTP 200 (validated, status=VALIDATED)
- Thread 2, 3: HTTP 200 (idempotent, already VALIDATED)

**Validations:**
- ✅ validated_at timestamp set exactly once
- ✅ validated_by = first thread's user_id
- ✅ No race condition artifacts

**Runtime:** ~2s

---

### Test 6: `test_concurrent_archive_and_create` ✅ **CONCURRENCY**

**Purpose:** Concurrent archive + create new assessment

**Scenario:**
- Create 1 VALIDATED assessment (id=1)
- 3 threads simultaneously create new assessment (should archive id=1)

**Expected Behavior:**
- Thread 1: HTTP 201 (created id=2, archived id=1)
- Thread 2, 3: HTTP 200 (idempotent, returns id=2)

**Validations:**
- ✅ Old assessment (id=1) archived exactly once
- ✅ Only 1 new ASSESSED assessment created
- ✅ No duplicate ASSESSED assessments

**Runtime:** ~2.5s

---

### Performance Targets

| Test | Runtime | Target | Status |
|------|---------|--------|--------|
| Full Lifecycle | ~2.0s | <10s | ✅ |
| Invalid Transitions | ~1.5s | <5s | ✅ |
| Idempotency | ~1.5s | <5s | ✅ |
| Concurrent Creation | ~2.0s | <10s | ✅ |
| Concurrent Validation | ~2.0s | <10s | ✅ |
| Concurrent Archive+Create | ~2.5s | <10s | ✅ |
| **Total** | **11.5s** | **<30s** | ✅ |

**Stability:** 0 flake in 20 runs (MANDATORY)

---

## Implementation Phases

### Phase 1: DB Schema Migration (Day 1, 4 hours)

**Tasks:**
1. Create Alembic migration for FootballSkillAssessment schema changes
2. Add status column with CHECK constraint
3. Add validation/archive tracking columns
4. Create indexes
5. Backfill existing data
6. Test migration (up + down)

**Files:**
- `alembic/versions/YYYYMMDD_add_skill_assessment_lifecycle.py` (NEW)
- `app/models/football_skill_assessment.py` (MODIFY)

---

### Phase 2: Service Layer Updates (Day 2-3, 8-12 hours)

**Tasks:**
1. Update FootballSkillService with state machine logic
2. Implement idempotent create_assessment()
3. Implement validate_assessment()
4. Implement archive_assessment()
5. Add state transition validation
6. Add row-level locking for concurrency

**Files:**
- `app/services/football_skill_service.py` (MODIFY)
- `app/services/skill_state_machine.py` (NEW — state machine logic)

---

### Phase 3: API Endpoints (Day 4, 6-8 hours)

**Tasks:**
1. Update POST /licenses/{id}/skills/assess (create assessment)
2. Add PUT /assessments/{id}/validate (validate assessment)
3. Add DELETE /assessments/{id}/archive (archive assessment)
4. Add GET /assessments/{id}/history (view state transition history)
5. Add error handling for invalid transitions

**Files:**
- `app/api/api_v1/endpoints/licenses/skills.py` (MODIFY)
- `app/api/api_v1/endpoints/skills/lifecycle.py` (NEW)

---

### Phase 4: E2E Tests (Day 5-6, 12-16 hours)

**Tasks:**
1. Implement 6 production-grade E2E tests (see Test Coverage Plan)
2. Run 20x sequential validation (0 flake requirement)
3. Run parallel validation (pytest -n auto)
4. Performance profiling (<30s total runtime)

**Files:**
- `tests_e2e/integration_critical/test_skill_assessment_lifecycle.py` (NEW)

---

### Phase 5: CI Integration (Day 7, 2 hours)

**Tasks:**
1. Add new test suite to GitHub Actions
2. Make BLOCKING on main branch
3. Add performance thresholds

**Files:**
- `.github/workflows/test-baseline-check.yml` (MODIFY)

---

## Total Effort Estimate

| Phase | Days | Hours | Priority |
|-------|------|-------|----------|
| 1: DB Schema Migration | 1 | 4 | P0 |
| 2: Service Layer | 2-3 | 8-12 | P0 |
| 3: API Endpoints | 4 | 6-8 | P0 |
| 4: E2E Tests | 5-6 | 12-16 | P0 |
| 5: CI Integration | 7 | 2 | P0 |
| **TOTAL** | **7 days** | **32-42 hours** | **~1.5 week sprint** |

---

## Success Criteria

### 1. State Machine Compliance
- ✅ All state transitions validated
- ✅ Invalid transitions rejected with clear error messages
- ✅ Idempotency at every state (create, validate, archive)

### 2. DB Integrity
- ✅ CHECK constraint enforces valid statuses
- ✅ UniqueConstraint prevents duplicate ASSESSED assessments
- ✅ Indexes optimize common queries

### 3. Concurrency Safety
- ✅ Row-level locking prevents race conditions
- ✅ 0 flake in 20 runs
- ✅ Idempotent responses under concurrent load

### 4. Test Coverage
- ✅ 6 production-grade E2E tests
- ✅ 100% state transition coverage
- ✅ Concurrency stress tests (3 threads)
- ✅ <30s total runtime

### 5. API Maturity
- ✅ Idempotent operations return HTTP 200 (not 500)
- ✅ Clear error messages for invalid transitions
- ✅ State history audit trail

---

## Open Questions

1. **Validation Requirement:** Should all assessments require admin validation, or only certain skills/levels?
   - **Proposal:** Phase 1 = no validation required, Phase 2 = add validation for high-stakes assessments

2. **Auto-Archive Policy:** Should old assessments be auto-archived after N days?
   - **Proposal:** No auto-archive, only explicit archive when new assessment created

3. **Dispute Flow:** When to implement DISPUTED state?
   - **Proposal:** Phase 2 (future), current scope = NOT_ASSESSED, ASSESSED, VALIDATED, ARCHIVED only

4. **Concurrent Access:** Should assessment creation lock entire UserLicense or just skill-specific row?
   - **Proposal:** Lock UserLicense row (coarser lock, simpler concurrency model)

---

## References

- Priority 4 Report: [PRIORITY_4_REWARD_DISTRIBUTION_REPORT.md](./PRIORITY_4_REWARD_DISTRIBUTION_REPORT.md)
- Skills Config: [app/skills_config.py](app/skills_config.py)
- Current Service: [app/services/football_skill_service.py](app/services/football_skill_service.py)
- Current Model: [app/models/football_skill_assessment.py](app/models/football_skill_assessment.py)

---

**Status:** 🔍 ANALYSIS COMPLETE — Ready for user review and Phase 1 kickoff

**Next Step:** User approval → Begin Phase 1 (DB Schema Migration)
