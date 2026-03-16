# Domain Model — Practice Booking System

Last updated: 2026-03-16

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

---

## 8. Location Capabilities — CENTER vs PARTNER

Locations (`app/models/location.py`) carry a `location_type` of either `CENTER` or `PARTNER`.
The type controls which semester specialization types can be hosted there.

### 8.1 Capability matrix

| Semester type | `PARTNER` location | `CENTER` location |
|--------------|-------------------|------------------|
| Tournament (all age groups) | ✅ | ✅ |
| Mini Season — PRE / YOUTH / AMATEUR / PRO | ✅ | ✅ |
| Academy Season — PRE / YOUTH / AMATEUR / PRO | ❌ | ✅ |

Academy Season types (`LFA_PLAYER_*_ACADEMY`) require a full-time facility (CENTER).
Partner venues are limited to shorter programs that do not require permanent infrastructure.

### 8.2 Enforcement layers (defence-in-depth)

The rule is enforced at three independent layers so that no single bypass can violate it.

#### Layer 1 — Service (`app/services/location_validation_service.py`)
`LocationValidationService.can_create_semester_at_location(location_id, spec_type, db)` is the
single source of truth. All creation flows call this method.

```python
result = LocationValidationService.can_create_semester_at_location(loc_id, spec_enum, db)
if not result["allowed"]:
    raise HTTPException(400, detail=result["reason"])
```

`CENTER_ONLY_TYPES` contains the four Academy Season variants.
`PARTNER_ALLOWED_TYPES` contains everything else.

#### Layer 2 — API routes

| Endpoint | Guard |
|----------|-------|
| `POST /api/v1/semesters/generate/academy` (`academy_generator.py`) | Direct `location_type != CENTER` check + service call |
| `POST /api/v1/semesters/` (`_semesters_main.py`) | Service call when `location_id` is provided |
| `POST /admin/semesters/new` (`admin.py`) | Service call + **requires** `location_id` for ACADEMY types |

The admin route enforces an additional rule: selecting an Academy Season specialization type
without specifying a location returns a form error. This ensures the rule is never silently
skipped through the admin UI.

#### Layer 3 — Database constraint (`migration 2026_03_16_1000`)

A PostgreSQL `CHECK` constraint on the `semesters` table acts as a last line of defence
against direct DB writes or future tools that bypass the application layer:

```sql
-- Helper function (STABLE — cached per query)
CREATE FUNCTION campus_location_type(p_campus_id INTEGER)
RETURNS TEXT LANGUAGE sql STABLE AS $$
    SELECT l.location_type::text
    FROM campuses c JOIN locations l ON l.id = c.location_id
    WHERE c.id = p_campus_id
$$;

-- Constraint: passes when campus_id is NULL, type is not ACADEMY,
-- or the campus's parent location is CENTER
ALTER TABLE semesters
ADD CONSTRAINT chk_academy_season_requires_center_location
CHECK (
    campus_id IS NULL
    OR specialization_type IS NULL
    OR specialization_type NOT IN (
        'LFA_PLAYER_PRE_ACADEMY', 'LFA_PLAYER_YOUTH_ACADEMY',
        'LFA_PLAYER_AMATEUR_ACADEMY', 'LFA_PLAYER_PRO_ACADEMY'
    )
    OR campus_location_type(campus_id) = 'CENTER'
);
```

**Why `campus_id IS NULL` passes:** The `semesters.campus_id` column is optional — semesters
may be created in DRAFT state before a campus is assigned. The NULL path is intentional so that
existing rows are unaffected. The campus → location check only activates when a campus is
explicitly linked.

### 8.3 Adding a new location type

If a third location type is introduced in the future:

1. Add the new value to `LocationType` enum (`app/models/location.py`).
2. Write a migration to add the value to the PostgreSQL `locationtype` enum.
3. Update `LocationValidationService.CENTER_ONLY_TYPES` / `PARTNER_ALLOWED_TYPES` accordingly.
4. Update the DB constraint to cover the new type.
5. Add SMOKE tests covering the new type's capabilities.

### 8.4 Tests

| Test | Coverage |
|------|---------|
| `TestSmoke20LocationCapabilityEnforcement` (SMOKE-20a–d) | End-to-end admin form (web route) enforcement |
| `TestAcademySeasonGeneratorLocationRules` (LOC-API-01–04) | `POST /api/v1/semesters/generate-academy-season` — PARTNER → 400, CENTER → 201, 404, type whitelist |
| `TestGenericSemesterCreateLocationRules` (LOC-API-05–08) | `POST /api/v1/semesters/` — PARTNER+ACADEMY → 400, CENTER+ACADEMY → 201, PARTNER+Mini → 201, K1 open |
| `TestAcademySeasonGeneratorAuthBoundary` (LOC-API-09–10) | Unauthenticated → 401, student → 403 |

SMOKE-20 cases:
- **20a** PARTNER + ACADEMY type → 200 form error
- **20b** CENTER + ACADEMY type → 303 created
- **20c** PARTNER + Mini Season → 303 created
- **20d** No location + ACADEMY type → 200 form error (location required)

LOC-API cases (file: `tests/integration/domain/test_location_capability_api.py`):
- **LOC-API-01** PARTNER + ACADEMY type (all 4 variants) → 400 from `generate-academy-season`
- **LOC-API-02** CENTER + ACADEMY type → 201 or 409 (duplicate code)
- **LOC-API-03** Non-existent `location_id` → 404
- **LOC-API-04** Non-ACADEMY type sent to academy generator → 400 (type whitelist)
- **LOC-API-05** PARTNER + ACADEMY via generic `POST /semesters/` → 400
- **LOC-API-06** CENTER + ACADEMY via generic `POST /semesters/` → 201
- **LOC-API-07** PARTNER + Mini Season via generic `POST /semesters/` → 201
- **LOC-API-08** ACADEMY type without `location_id` → 201 (K1 open — currently permissive)
- **LOC-API-09** Unauthenticated → 401
- **LOC-API-10** Student token → 403

### 8.5 Open business decisions (K1–K3)

The following decisions were identified during the 2026-03-16 audit. Each is documented with
the current behaviour, the options, and a recommended stance.

---

#### K1 — Does `POST /api/v1/semesters/` require `location_id` for ACADEMY types?

**Current behaviour (OPEN — permissive):**
If `location_id` is omitted, the generic semester create endpoint accepts ACADEMY types without
any location check. LOC-API-08 guards and documents this stance.

**Options:**
| Option | Description | Impact |
|--------|-------------|--------|
| A — Permissive (current) | No `location_id` required; validation only fires when provided | Allows creating ACADEMY semesters without linking them to a location (useful in DRAFT stage) |
| B — Required | `location_id` is required whenever `specialization_type` is an ACADEMY type; returns 400 otherwise | Closes the gap; all ACADEMY semesters are location-aware from creation |

**Recommendation:** Option B when the product is ready for mandatory location linking.
To apply: add a guard at the top of `create_semester` in `_semesters_main.py`; update
LOC-API-08 expected status from 200 to 400.

---

#### K2 — Should changing a location from CENTER to PARTNER be blocked if Academy semesters exist?

**Current behaviour (OPEN — not enforced):**
`PATCH /api/v1/locations/{id}` does not validate existing semesters before allowing a
`location_type` change. A CENTER could be downgraded to PARTNER while active Academy seasons
reference it. The DB constraint fires only on INSERT/UPDATE of the semester's `campus_id`, not
on location type changes.

**Options:**
| Option | Description |
|--------|-------------|
| A — Ignore (current) | Location type changes are unrestricted; historical semesters remain linked to a now-PARTNER location |
| B — Warn only | Allow the change but emit a structured log warning listing affected Academy semesters |
| C — Block | Return 409 if any `ONGOING` or `READY_FOR_ENROLLMENT` Academy semester references this location |

**Recommendation:** Option C for active semesters; Option B for historical ones.
To apply: add a pre-check in the location update handler (admin or API) that queries
`semesters WHERE location_id = ? AND specialization_type IN (ACADEMY_TYPES) AND status IN (ACTIVE_STATUSES)`.

---

#### K3 — Should session generation differ by location type (CENTER vs PARTNER)?

**Current behaviour (RESOLVED — location-agnostic):**
Session generation is entirely location-agnostic. The rule "ACADEMY Seasons only at CENTER"
is enforced at the *semester creation* level. Once a semester is created, its sessions are
generated with the same properties regardless of whether the host location is CENTER or PARTNER.

This is an intentional design decision (see §8.6 below). K3 is therefore not an open gap
but a documented architectural stance.

**If differentiation is desired in the future:**
Define session-property overrides per `LocationType` in a config table or strategy map.
The generator functions in `app/services/session_generator.py` would need to accept
a `location_type` parameter and apply the appropriate overrides.

---

### 8.6 Session generation — location-agnostic by design

Session properties (type, capacity, duration, count per week, `event_category`) are determined
exclusively by the semester's `specialization_type`, `SemesterCategory`, and the game-preset
templates — **not** by the host location's type.

This is a deliberate choice for the following reasons:

1. **Predictability**: Coaches and students see the same session structure regardless of venue.
2. **Operational simplicity**: Adding a new location does not require configuring session templates.
3. **Business rule separation**: "Which program can run here?" (location capability) is a
   different question from "What does a session look like?" (program structure). Mixing them
   would create tight coupling between location metadata and academic programme design.

**Consequence**: If a CENTER location decides to run a Mini Season in addition to its Academy
Seasons, the Mini Season sessions are generated with identical properties to those at a PARTNER
location. Any physical differences (e.g., longer field available at CENTER) must be expressed
through the game-preset template, not through the location type.

**Test evidence**: `TestAcademySeasonGeneratorLocationRules` (LOC-API-02) confirms that once
the location check passes, a CENTER-hosted Academy Season is created with the standard semester
template. No location-specific session overrides are applied.
