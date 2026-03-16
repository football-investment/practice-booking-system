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

---

## 9. Session Generation — Validation Chain


Every call to `TournamentSessionGenerator.generate_sessions()` passes through a layered
validation chain before any session record is written to the database.

### 9.1 Validation layers (in order of execution)

```
generate_sessions(tournament_id, ...)
  │
  ├─ [L1] GenerationValidator.can_generate_sessions()
  │        ↳ tournament status must be ONGOING / IN_PROGRESS
  │        ↳ sessions_generated must be False
  │        ↳ enrollment period must be closed
  │        → (False, reason)  if any condition fails
  │
  ├─ [L2] Campus schedule resolution
  │        ↳ get_campus_schedule() — per-campus or global defaults
  │
  ├─ [L3] Player-count determination
  │        ↳ prefer check-in confirmed pool; fall back to APPROVED enrollments
  │
  ├─ [L4] GamePreset min_players guard   ← NEW (Sprint 59 / 2026-03-16)
  │        ↳ if tournament.game_config_obj.game_preset exists:
  │              min_p = game_preset.game_config["metadata"]["min_players"]
  │              if min_p and player_count < min_p → return (False, msg, [])
  │        ↳ applies to BOTH HEAD_TO_HEAD and INDIVIDUAL_RANKING
  │        ↳ fires BEFORE format routing — no format-specific code runs
  │
  ├─ [L5] Format routing
  │   │
  │   ├─ INDIVIDUAL_RANKING
  │   │    ↳ built-in minimum: player_count >= 2
  │   │    ↳ delegates to IndividualRankingGenerator
  │   │
  │   └─ HEAD_TO_HEAD
  │        ↳ TournamentType.validate_player_count(player_count)
  │            — min_players / max_players / requires_power_of_two
  │        ↳ delegates to format generator (League / Knockout / Swiss / GroupKnockout)
  │
  └─ [L6] Database write (bulk INSERT + flush + commit)
```

### 9.2 GamePreset min_players guard — design rationale

**Why a separate guard instead of embedding in validate_player_count()?**

`TournamentType.validate_player_count()` is a pure model-layer method that operates on
player count, min/max bounds, and power-of-two constraints. It has no access to the
`GamePreset` relationship (which lives on the `Semester / GameConfiguration` side, not
on `TournamentType`). Adding preset awareness there would cross domain boundaries.

The guard is placed in the coordinator (`session_generator.py`) because it:
1. Has access to the full tournament object (including `game_config_obj → game_preset`)
2. Runs once per generation call, before any format-specific logic
3. Applies uniformly to all formats — no duplication in individual generators

**Access path:**

```python
tournament.game_config_obj      # GameConfiguration (via relationship)
    .game_preset                # GamePreset (via relationship)
    .game_config                # JSONB column
    ["metadata"]
    ["min_players"]             # int — minimum players required by this game type
```

If `game_preset` is `None` (no preset configured), the guard is skipped entirely.
If `min_players` is `0` or absent, the guard is also skipped (falsy check).

### 9.3 TournamentType constraint matrix

Production tournament types and their `validate_player_count()` constraints:

| Type | `min_players` | `max_players` | `requires_power_of_two` | Multi-campus eligible |
|------|--------------|--------------|------------------------|----------------------|
| `league` | 2 | 1024 | False | Yes (≥128) |
| `knockout` | 4 | 1024 | **True** | Yes (≥128, pow2 only) |
| `group_knockout` | 8 | **64** | False | No (max < 128) |
| `swiss` | 4 | **64** | False | No (max < 128) |

**Pattern A** (root-cause catalog, Sprint 59): Using the wrong tournament type in a
boundary/safety-gate test causes `validate_player_count()` to fire for a different reason
than the one under test, masking the actual branch.

- `knockout + 127` → fails **pow2** check, never reaches the safety gate
- `group_knockout + 127` → fails **max=64** check, never reaches the safety gate
- `league + 127` → **passes** (min=2, max=1024, no pow2) — correct type for safety-gate tests

**Test file**: `tests/unit/models/test_tournament_type_constraints.py` (TCM-01–23)

### 9.4 Adding a new GamePreset — checklist for future contributors

When a new `GamePreset` is introduced that imposes a player-count minimum:

1. Set `game_config["metadata"]["min_players"]` to the desired integer value in the preset
   JSON / DB record.
2. **No code change required** — the L4 guard in `session_generator.py` reads this field
   automatically for every generation call.
3. Add a unit test with `_mock_tournament(preset_min=<value>)` verifying the guard fires
   for `player_count < value` and passes for `player_count >= value`.
4. Add an integration test (SMOKE-22 pattern) if the preset is used in a real tournament
   type to confirm end-to-end enforcement.

### 9.5 API safety gate (large tournaments)

An additional gate exists at the API layer (`ops_scenario.py`):

```
_OPS_CONFIRM_THRESHOLD = 128

if player_count >= 128 and not confirmed:
    → HTTP 422 "Confirmation required for large tournaments"
```

This gate is separate from the validation chain above and fires before
`generate_sessions()` is called. It requires an explicit `confirmed=True` flag from the
operator for tournaments with 128 or more players.

**Pattern A relevance**: Tests targeting this gate must use `league` as the tournament type
(not `knockout` or `group_knockout`) — see §9.3.

### 9.6 Format generator isolation — DB write boundary

All five format generators are **pure computation**: they receive arguments, build a
`List[Dict[str, Any]]`, and return it. They do **not** hold a direct DB reference
beyond what the coordinator passes, and they never call `db.add()`, `db.commit()`,
or `db.flush()`.

The DB write boundary is strictly in the coordinator (`session_generator.py`):

```
coordinator.generate_sessions()
  │
  ├─ L1–L4  validation (read-only queries)
  │
  ├─ format_generator.generate(...)   ← pure computation, returns List[Dict]
  │     LeagueGenerator               no db.add / db.commit / db.flush
  │     KnockoutGenerator             no db.add / db.commit / db.flush
  │     SwissGenerator                no db.add / db.commit / db.flush
  │     GroupKnockoutGenerator        no db.add / db.commit / db.flush
  │     IndividualRankingGenerator    no db.add / db.commit / db.flush
  │
  └─ [DB write] for session_data in sessions:
         SessionModel(**session_data) → db.add()
     db.flush()                       ← single bulk INSERT
     tournament_config.sessions_generated = True
     db.commit()                      ← single commit for the entire generation
```

**Proof**: `grep -rn "db\.add\|db\.commit\|db\.flush" formats/` returns 0 results.
Verified in CI via unit tests and SMOKE-22a/b/c (real-DB).

This design makes the L4 guard the **sole** gatekeeper before any DB mutation occurs.
If the guard returns `(False, ...)`, no `SessionModel` row is ever written.

### 9.7 Manual session creation — domain boundary

`POST /api/v1/sessions/` creates standalone sessions directly (admin/instructor action).
This path does **not** go through `TournamentSessionGenerator` and is intentionally
exempt from the L4 guard.

**Why the exemption is safe:**

| Property | Tournament session (generated) | Manual session (`POST /sessions/`) |
|----------|-------------------------------|-------------------------------------|
| `auto_generated` | `True` | `False` (not in schema → default) |
| `tournament_phase` | `GROUP_STAGE / KNOCKOUT / ...` | `None` (not in schema) |
| `participant_user_ids` | bracket-assigned players | `None` (not in schema) |
| `group_identifier` | group label (e.g. "A") | `None` (not in schema) |
| `event_category` | `MATCH` (set by coordinator) | `TRAINING` (schema default) |

`SessionCreate` (the schema for `POST /sessions/`) exposes only the deprecated
`is_tournament_game: bool = False` field, which maps to `event_category` via a
property setter. Even if a caller sets `is_tournament_game=True`, the resulting row
has no `tournament_phase`, no `auto_generated=True`, and no `participant_user_ids` —
it is structurally distinguishable from a generated tournament bracket slot.

**Domain rule (explicit):**

> A session created via `POST /api/v1/sessions/` is an **administrative override**
> — a one-off session that an admin or instructor manually schedules within a semester.
> It is NOT a bracket slot. The GamePreset `min_players` constraint applies to the
> tournament **bracket** (the full schedule generated by `TournamentSessionGenerator`),
> not to individual administrative sessions.
>
> If a future feature needs to enforce preset constraints on manual sessions, add a
> dedicated guard to `sessions/crud.py:create_session()` that reads the semester's
> `game_config_obj.game_preset.game_config["metadata"]["min_players"]` and compares
> it to the current enrollment count. This is a deliberate future-extension point,
> not an oversight.

### 9.8 Lifecycle regeneration stability

A failed `generate_sessions()` call (guard returns `False`) is **fully idempotent**:

- No `SessionModel` rows are written (generator isolation — §9.6)
- `tournament_config.sessions_generated` remains `False`
- No `db.commit()` is called

The tournament is therefore in an identical state to before the call, and a second
attempt after resolving the blocking condition (e.g. enrolling more players) succeeds
normally.

**Test evidence (SMOKE-22c)**:
```
preset min=8, 5 players enrolled
→ generate_sessions() → (False, "...requires at least 8...", [])
→ sessions_generated = False  ✓  (state unchanged)
→ 3 more players enrolled (total 8)
→ generate_sessions() → (True, "Successfully generated N sessions", [...])
→ sessions_generated = True   ✓  (flag set, sessions in DB)
```

Last updated: 2026-03-16
