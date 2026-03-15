# Domain Model — Practice Booking System

Last updated: 2026-03-15

---

## 1. Semester Hierarchy

Semesters are the top-level container for all academy activity. A semester can be
standalone or nested inside a parent semester via `parent_semester_id`.

### 1.1 SemesterCategory

| Value | Description |
|-------|-------------|
| `ACADEMY_SEASON` | Full-year or multi-month program (root of a hierarchy) |
| `MINI_SEASON` | Shorter program, may be nested under ACADEMY_SEASON |
| `CAMP` | Intensive multi-day event, may be nested under any parent |
| `TOURNAMENT` | Competitive event with session generation |

### 1.2 Hierarchy model

```
ACADEMY_SEASON (parent_semester_id = NULL)
├── MINI_SEASON  (parent_semester_id = academy.id)
├── CAMP         (parent_semester_id = academy.id)
└── TOURNAMENT   (parent_semester_id = academy.id)
```

Only one level of nesting is enforced by the enrollment gate.
Deeper nesting is stored in the schema but not validated beyond the immediate parent.

### 1.3 Key schema fields

| Field | Type | Notes |
|-------|------|-------|
| `semester_category` | `SemesterCategory` enum | Required for hierarchy |
| `parent_semester_id` | `Integer FK → semesters.id` | NULL for root programs |
| `status` | `SemesterStatus` | DRAFT → READY_FOR_ENROLLMENT → ONGOING → COMPLETED |

---

## 2. Session Event Dimensions

Sessions carry two independent dimensions: *structural type* and *event category*.

### 2.1 SessionType (delivery modality)

| Value | Description |
|-------|-------------|
| `on_site` | Physical attendance at a campus |
| `virtual` | Online / video session |
| `hybrid` | Both on-site and virtual participants |

### 2.2 EventCategory (semantic role)

| Value | XP default | Description |
|-------|-----------|-------------|
| `TRAINING` | 50 XP | Skill-building session, coaching, practice |
| `MATCH` | 100 XP | Competitive fixture or tournament round |

### 2.3 session_reward_config (optional override)

A JSONB field on `Session` that overrides the category XP default for a specific session.

```json
{
  "v": 1,
  "base_xp": 200,
  "skill_areas": ["dribbling", "passing"]
}
```

XP resolution priority (highest → lowest):
1. `session.session_reward_config["base_xp"]` (if present)
2. Event category default (`MATCH=100`, `TRAINING=50`)
3. Legacy `session.base_xp` field (fallback when `event_category` is NULL)

---

## 3. Enrollment Flow

### 3.1 Standalone semester (no parent)

```
POST /api/v1/semester-enrollments/enroll
  → no parent gate check
  → SemesterEnrollment created (is_active=True, request_status=APPROVED)
```

### 3.2 Nested semester (parent_semester_id set)

```
POST /api/v1/semester-enrollments/enroll
  → gate: check active parent enrollment
      SELECT * FROM semester_enrollments
      WHERE user_id = :user_id
        AND semester_id = :parent_semester_id
        AND is_active = TRUE
  → if not found: HTTP 403 "Student must be enrolled in the parent program before joining this nested semester"
  → if found: enrollment created normally
```

### 3.3 SemesterEnrollment states

| `is_active` | `request_status` | Meaning |
|-------------|-----------------|---------|
| `False` | `PENDING` | Application submitted, awaiting admin approval |
| `True` | `APPROVED` | Active enrollment — student has access |
| `False` | `REJECTED` | Application rejected |

Only `is_active=True` enrollments pass the parent gate.

---

## 4. Reward Flow

### 4.1 EventRewardLog

An append-only audit table that records XP and points awarded when a student
completes a session. One row per `(user_id, session_id)` — upserted on re-award.

| Field | Description |
|-------|-------------|
| `user_id` | Student who earned the reward |
| `session_id` | Session that was completed |
| `xp_earned` | XP after multiplier applied: `int(base_xp × multiplier)` |
| `points_earned` | Points (currently mirrors `xp_earned`) |
| `multiplier_applied` | Multiplier used (default 1.0) |
| `skill_areas_affected` | JSON list of skill areas (caller-supplied) |

### 4.2 award_session_completion()

```python
from app.services.reward_service import award_session_completion

log = award_session_completion(
    db,
    user_id=student.id,
    session=session_obj,
    multiplier=1.5,             # optional, default 1.0
    skill_areas=["dribbling"],  # optional, default None
)
# log.xp_earned == int(base_xp * multiplier)
```

**Idempotency guarantee**: if called a second time for the same `(user_id, session_id)`,
the existing row is updated (not duplicated). The latest `multiplier` and computed
`xp_earned` overwrite the previous values.

### 4.3 Reward service sequence diagram

```
caller
  │
  ├─ award_session_completion(db, user_id, session, multiplier, skill_areas)
  │     │
  │     ├─ _resolve_base_xp(session)          ← priority: config > category > legacy
  │     │     └─ returns int (e.g. 50, 100, 200)
  │     │
  │     ├─ xp = int(base_xp * multiplier)
  │     │
  │     ├─ existing = db.query(EventRewardLog).filter(user_id, session_id).first()
  │     │
  │     ├─ if existing:
  │     │     existing.xp_earned = xp
  │     │     existing.multiplier_applied = multiplier
  │     │     existing.skill_areas_affected = skill_areas
  │     │     db.commit()
  │     │     return existing
  │     │
  │     └─ else:
  │           new_log = EventRewardLog(...)
  │           db.add(new_log); db.commit()
  │           return new_log
  │
  └─ returns EventRewardLog (always the single canonical row for this user+session)
```

---

## 5. Test patterns

### SAVEPOINT-isolated integration tests

```python
# tests/integration/conftest.py provides:
#   test_db  — SAVEPOINT-isolated SQLAlchemy session (function-scoped)
#   client   — FastAPI TestClient sharing the same session
#   student_user, admin_user, admin_token

def test_example(test_db, student_user, client, admin_token):
    sem = build_semester(test_db)          # flush() only — no commit needed
    sess = build_session(test_db, sem.id)
    lic = build_user_license(test_db, user_id=student_user.id)

    # API call sees the flushed data (same session)
    resp = client.post("/api/v1/semester-enrollments/enroll", ...)

    # Service call works directly on test_db
    log = award_session_completion(test_db, user_id=student_user.id, session=sess)
```

### Error contract

All HTTP errors use the envelope format (not FastAPI's default `{"detail": "..."}`):

```json
{
  "error": {
    "code": "http_403",
    "message": "Student must be enrolled in the parent program ...",
    "timestamp": "2026-03-15T12:00:00Z",
    "request_id": "<uuid>"
  }
}
```

Use `tests/fixtures/api_error_helpers.py` for assertions:

```python
from tests.fixtures.api_error_helpers import assert_error_contains
assert_error_contains(resp, "parent program")
```
