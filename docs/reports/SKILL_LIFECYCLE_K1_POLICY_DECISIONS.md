# Skill Lifecycle (K1) — Policy Decisions Required

**Date:** 2026-02-24
**Status:** 🔴 BLOCKING Phase 1 — Awaiting User Decisions

---

## Critical Policy Decisions

Ezek a döntések meghatározzák a state machine logikáját, DB schema-t, és az üzleti szabályokat. **Phase 1 nem indulhat** amíg ezek nincsenek véglegesítve.

---

## Decision 1: Validation Requirement Policy

### Question
**Should all skill assessments require admin validation before becoming final?**

### Options

#### Option A: **No Validation Required** (Simpler, MVP approach)
```
State Machine: NOT_ASSESSED → ASSESSED → ARCHIVED
                                  ↓
                              ARCHIVED (when new assessment created)
```

**Pros:**
- ✅ Simpler state machine (3 states instead of 4)
- ✅ Faster implementation
- ✅ Less admin overhead
- ✅ Instructor assessments immediately trusted

**Cons:**
- ❌ No quality control gate
- ❌ Instructor errors propagate immediately
- ❌ No audit trail of validation

**DB Schema Impact:**
- Remove `validated_by`, `validated_at` columns
- Remove VALIDATED state from CHECK constraint
- UniqueConstraint: Only 1 ASSESSED per (user_license_id, skill_name)

**Use Case:**
- MVP system where instructors are highly trusted
- Low-stakes assessments (practice sessions)
- Small instructor team with high alignment

---

#### Option B: **Optional Validation** (Flexible, recommended)
```
State Machine: NOT_ASSESSED → ASSESSED → VALIDATED → ARCHIVED
                                  ↓           ↓
                              ARCHIVED    ARCHIVED (when new created)
```

**Pros:**
- ✅ Flexible: validation can be enforced per skill/level/context
- ✅ Quality control gate exists but not mandatory
- ✅ Can evolve: start without validation, add later
- ✅ Admin can validate high-stakes assessments selectively

**Cons:**
- ⚠️ More complex state machine (4 states)
- ⚠️ Need business rules to determine when validation required
- ⚠️ Two terminal paths (ASSESSED→ARCHIVED, VALIDATED→ARCHIVED)

**DB Schema Impact:**
- Keep `validated_by`, `validated_at` columns (nullable)
- VALIDATED state in CHECK constraint
- UniqueConstraint: 1 active (ASSESSED or VALIDATED) per skill
- Add `requires_validation` flag to assessments or skill config

**Use Case:**
- Production system with mixed trust levels
- High-stakes assessments (license progression) require validation
- Low-stakes assessments (practice) auto-accepted

**Business Rule Examples:**
```python
# Validation required for:
- License level 5+ assessments (high-stakes)
- New instructors (< 6 months tenure)
- Skills affecting license progression
- Student-disputed assessments

# Auto-accepted (no validation):
- License level 1-4 assessments
- Trusted instructors (> 1 year tenure)
- Practice session assessments
```

---

#### Option C: **Mandatory Validation** (Strictest, slowest)
```
State Machine: NOT_ASSESSED → ASSESSED → VALIDATED → ARCHIVED
                                              ↓
                                          ARCHIVED (only VALIDATED can be archived)
```

**Pros:**
- ✅ Maximum quality control
- ✅ Clear audit trail
- ✅ No invalid assessments in system

**Cons:**
- ❌ Admin bottleneck (every assessment needs validation)
- ❌ Slow turnaround time
- ❌ High admin overhead
- ❌ Blocks low-stakes assessments unnecessarily

**DB Schema Impact:**
- `validated_by`, `validated_at` NOT NULL (after validation)
- VALIDATED state required before ARCHIVED
- Cannot archive ASSESSED directly

**Use Case:**
- High-stakes certification system
- Regulatory compliance required
- Large instructor team with variable quality

---

### Recommendation: **Option B (Optional Validation)**

**Rationale:**
- Most flexible: can enforce validation where needed, skip where not
- Allows MVP launch without validation, add later
- Supports mixed use cases (high-stakes + low-stakes)
- Aligns with Priority 4 approach (optional features, not forced)

**Implementation:**
```python
# Add validation policy to skill assessment
assessment.requires_validation = determine_validation_requirement(
    license_level=license.current_level,
    instructor_tenure=get_instructor_tenure(assessed_by),
    skill_category=get_skill_category(skill_name)
)

# Validation enforcement
if assessment.requires_validation and assessment.status == 'ASSESSED':
    # Block progression until validated
    raise ValueError("Assessment requires admin validation before use")
```

---

## Decision 2: Auto-Archive Policy

### Question
**Should old assessments be automatically archived after N days, or only when new assessment created?**

### Options

#### Option A: **Manual Archive Only** (Recommended)
```
Archive Trigger: New assessment created for same skill
                 → Old assessment (ASSESSED or VALIDATED) → ARCHIVED
```

**Pros:**
- ✅ Simple: only 1 archive trigger
- ✅ No background jobs needed
- ✅ Assessment history always current (only latest active)
- ✅ Clear business logic: new replaces old

**Cons:**
- ⚠️ Old assessments stay active indefinitely if no new assessment
- ⚠️ Student could have ASSESSED assessment from 2 years ago

**DB Schema Impact:**
- No `expires_at` column needed
- Archive only on new assessment creation

**Business Rule:**
```python
def create_assessment(...):
    # Archive any existing ASSESSED or VALIDATED assessments
    old = db.query(FootballSkillAssessment).filter(
        user_license_id=user_license_id,
        skill_name=skill_name,
        status.in_(['ASSESSED', 'VALIDATED'])
    ).all()

    for assessment in old:
        assessment.status = 'ARCHIVED'
        assessment.archived_reason = "Replaced by new assessment"
```

---

#### Option B: **Time-Based Auto-Archive**
```
Archive Trigger:
  1. New assessment created (immediate)
  2. Assessment age > 90 days (background job)
```

**Pros:**
- ✅ Keeps assessment data fresh
- ✅ Prevents stale assessments
- ✅ Forces periodic re-assessment

**Cons:**
- ❌ Background job needed (cron / celery)
- ❌ More complex: 2 archive triggers
- ❌ May archive assessments unnecessarily
- ❌ What if student doesn't get re-assessed? (gap in data)

**DB Schema Impact:**
- Add `expires_at` column (default: created_at + 90 days)
- Add background job to archive expired assessments

**Business Rule:**
```python
# Background job (daily)
def archive_expired_assessments():
    expired = db.query(FootballSkillAssessment).filter(
        status.in_(['ASSESSED', 'VALIDATED']),
        expires_at < now()
    ).all()

    for assessment in expired:
        assessment.status = 'ARCHIVED'
        assessment.archived_reason = "Expired (90 days)"
```

---

### Recommendation: **Option A (Manual Archive Only)**

**Rationale:**
- Simpler: no background jobs, no expiration tracking
- Clear business logic: new replaces old
- Aligns with assessment workflow: instructors create new when needed
- No forced re-assessment schedule (instructor decides when)

**Exception Handling:**
- If stale assessments become problem, add warning in UI: "Last assessed 180 days ago"
- Instructor-driven re-assessment, not system-forced

---

## Decision 3: DISPUTED State Implementation

### Question
**When should we implement the DISPUTED state (student disputes assessment)?**

### Options

#### Option A: **Phase 1 — Include DISPUTED Now** (More complex)
```
State Machine:
  NOT_ASSESSED → ASSESSED → VALIDATED → ARCHIVED
                     ↓           ↓
                 DISPUTED → ASSESSED (re-assess)
                     ↓
                 VALIDATED (resolve dispute)
```

**Pros:**
- ✅ Complete state machine from start
- ✅ No schema migration later
- ✅ Supports student feedback loop

**Cons:**
- ❌ More complex initial implementation
- ❌ Need dispute resolution workflow (UI, notifications)
- ❌ Unknown: will disputes actually happen? (premature optimization)
- ❌ Delays Phase 1 completion

**Implementation Scope:**
- Add DISPUTED state to CHECK constraint
- Add `disputed_at`, `disputed_by`, `dispute_reason` columns
- Add API endpoints: POST /assessments/{id}/dispute, PUT /assessments/{id}/resolve
- Add E2E tests for dispute flow
- Add UI for dispute submission/resolution

**Effort:** +2-3 days, +8-12 hours

---

#### Option B: **Phase 2 — Add DISPUTED Later** (Recommended)
```
Phase 1 State Machine (Minimal Viable):
  NOT_ASSESSED → ASSESSED → [VALIDATED] → ARCHIVED

Phase 2 State Machine (When disputes occur):
  Add DISPUTED state via migration
  Extend API with dispute endpoints
```

**Pros:**
- ✅ Simpler Phase 1 (focus on core lifecycle)
- ✅ Faster implementation (7 days → 5 days)
- ✅ Validate need first: do students actually dispute?
- ✅ Easier to test and stabilize

**Cons:**
- ⚠️ Need schema migration later (but simple: just add DISPUTED to enum)
- ⚠️ Cannot handle disputes in Phase 1 (manual workaround: delete + re-assess)

**Implementation Scope (Phase 1):**
- 4 states: NOT_ASSESSED, ASSESSED, VALIDATED, ARCHIVED
- No dispute columns
- No dispute API endpoints

**Migration Path (Phase 2):**
```sql
-- Add DISPUTED to CHECK constraint
ALTER TABLE football_skill_assessments
DROP CONSTRAINT ck_skill_assessment_status;

ALTER TABLE football_skill_assessments
ADD CONSTRAINT ck_skill_assessment_status
CHECK (status IN ('NOT_ASSESSED', 'ASSESSED', 'VALIDATED', 'ARCHIVED', 'DISPUTED'));

-- Add dispute tracking
ALTER TABLE football_skill_assessments
ADD COLUMN disputed_at TIMESTAMP,
ADD COLUMN disputed_by INT REFERENCES users(id),
ADD COLUMN dispute_reason TEXT;
```

**Effort:** Phase 1: -2 days, Phase 2: +2 days (when needed)

---

### Recommendation: **Option B (Phase 2 — Add DISPUTED Later)**

**Rationale:**
- YAGNI principle: build it when you need it
- Simpler Phase 1 → faster stabilization
- Unknown demand: disputes may be rare
- Easy migration path: just extend enum + add columns
- Aligns with "production-grade core first, features later"

**Manual Workaround (Phase 1):**
- Student disputes via email/message to admin
- Admin can delete ASSESSED assessment + ask instructor to re-assess
- Admin can directly create new assessment (override)

---

## Summary of Recommendations

| Decision | Recommended Option | Rationale |
|----------|-------------------|-----------|
| **1. Validation** | **Option B: Optional Validation** | Flexible, supports mixed use cases, can evolve |
| **2. Auto-Archive** | **Option A: Manual Archive Only** | Simpler, no background jobs, instructor-driven |
| **3. DISPUTED State** | **Option B: Phase 2 — Later** | Faster Phase 1, validate need first, easy migration |

---

## Resulting State Machine (Phase 1)

### With Recommendations Applied:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SKILL ASSESSMENT LIFECYCLE — PHASE 1                  │
└─────────────────────────────────────────────────────────────────────────┘

    [Initial State]
         │
         ▼
  ┌──────────────┐
  │ NOT_ASSESSED │  ← No assessment exists
  └──────────────┘
         │
         │ (1) Instructor creates assessment
         │     POST /licenses/{id}/skills/assess
         ▼
  ┌──────────────┐
  │   ASSESSED   │  ← Assessment created
  └──────────────┘
         │
         ├─────────────────────────────────────────┐
         │                                         │
         │ (2a) Admin validates (optional)         │ (2b) New assessment created
         │      PUT /assessments/{id}/validate     │      → Archives old
         │      Required if: high-stakes           │
         ▼                                         ▼
  ┌──────────────┐                         ┌──────────────┐
  │  VALIDATED   │                         │   ARCHIVED   │  ← Replaced
  └──────────────┘                         └──────────────┘
         │                                         │
         │ (3) New assessment created              │ [Terminal]
         │     → Archives validated                │ No transitions
         ▼
  ┌──────────────┐
  │   ARCHIVED   │
  └──────────────┘
```

### State Transitions (Phase 1):

| From / To | NOT_ASSESSED | ASSESSED | VALIDATED | ARCHIVED |
|-----------|--------------|----------|-----------|----------|
| **NOT_ASSESSED** | ✅ Idempotent | ✅ Create | ❌ Invalid | ❌ Invalid |
| **ASSESSED** | ❌ Invalid | ✅ Idempotent | ✅ Validate* | ✅ Archive |
| **VALIDATED** | ❌ Invalid | ❌ Invalid | ✅ Idempotent | ✅ Archive |
| **ARCHIVED** | ❌ Invalid | ❌ Invalid | ❌ Invalid | ✅ Idempotent |

*Validation is optional (business rule determines if required)

---

## DB Schema (Phase 1 — Final)

### With Recommendations Applied:

```sql
-- Add status column with CHECK constraint
ALTER TABLE football_skill_assessments
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ASSESSED'
CHECK (status IN ('NOT_ASSESSED', 'ASSESSED', 'VALIDATED', 'ARCHIVED'));

-- Validation tracking (nullable — optional validation)
ALTER TABLE football_skill_assessments
ADD COLUMN validated_by INT REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN validated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN requires_validation BOOLEAN NOT NULL DEFAULT FALSE;

-- Archive tracking
ALTER TABLE football_skill_assessments
ADD COLUMN archived_by INT REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN archived_reason TEXT;

-- State transition audit
ALTER TABLE football_skill_assessments
ADD COLUMN previous_status VARCHAR(20),
ADD COLUMN status_changed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN status_changed_by INT REFERENCES users(id) ON DELETE SET NULL;

-- Indexes
CREATE INDEX ix_skill_assessments_status
ON football_skill_assessments(status);

CREATE INDEX ix_skill_assessments_user_skill_status
ON football_skill_assessments(user_license_id, skill_name, status);

-- UniqueConstraint: Only 1 active (ASSESSED or VALIDATED) per skill
CREATE UNIQUE INDEX uq_skill_assessment_active
ON football_skill_assessments(user_license_id, skill_name)
WHERE status IN ('ASSESSED', 'VALIDATED');
```

**No columns for:**
- ~~`expires_at`~~ (no time-based auto-archive)
- ~~`disputed_at`, `disputed_by`, `dispute_reason`~~ (Phase 2)

---

## Business Rules (Phase 1 — Final)

### Validation Policy

```python
def determine_validation_requirement(
    license_level: int,
    instructor_tenure_days: int,
    skill_category: str
) -> bool:
    """
    Determine if assessment requires admin validation.

    Returns:
        True if validation required, False if auto-accepted
    """
    # High-stakes assessments require validation
    if license_level >= 5:
        return True

    # New instructors require validation
    if instructor_tenure_days < 180:  # < 6 months
        return True

    # Critical skills require validation
    CRITICAL_SKILLS = ['mental', 'set_pieces']  # categories
    if skill_category in CRITICAL_SKILLS:
        return True

    # Default: auto-accepted (no validation)
    return False
```

### Archive Policy

```python
def create_assessment(...):
    """
    Create new assessment with auto-archive of old.

    Archive Trigger: New assessment created
    Archive Target: Any ASSESSED or VALIDATED for same skill
    """
    # Archive old assessments
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
        ...,
        status='ASSESSED',
        requires_validation=determine_validation_requirement(...)
    )
```

---

## Updated Implementation Effort (Phase 1 Only)

| Phase | Days | Hours | Change |
|-------|------|-------|--------|
| 1: DB Schema Migration | 1 | 4 | No change |
| 2: Service Layer | 2 | 6-8 | **-4 hours** (no DISPUTED logic) |
| 3: API Endpoints | 3 | 4-6 | **-2 hours** (no dispute endpoints) |
| 4: E2E Tests | 4-5 | 10-12 | **-4 hours** (no dispute tests) |
| 5: CI Integration | 5 | 2 | No change |
| **TOTAL** | **5 days** | **26-32 hours** | **-10 hours faster** |

**Previous:** 7 days, 32-42 hours
**With Recommendations:** 5 days, 26-32 hours

---

## Action Required

**User must decide:**

1. ✅ Accept recommendations (Option B for all 3 decisions)?
2. ✅ Modify any recommendation?
3. ✅ Add/remove any business rules?

**After decisions confirmed:**
- Phase 1 can start immediately
- No further policy blockers

---

**Status:** 🔴 AWAITING USER APPROVAL — Phase 1 BLOCKED until decisions finalized
