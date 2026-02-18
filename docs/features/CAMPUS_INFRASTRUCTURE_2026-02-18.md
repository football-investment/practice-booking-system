# Campus Infrastructure — Architecture Reference

**Date:** 2026-02-18
**Branch:** `feature/performance-card-option-a`
**Commits:** `fba16e3` (implementation), `bc2b22d` (test suite)
**Status:** ✅ Production-hardened — 25/25 tests passing, 541 unit tests green

> **Related document:** [ARCHITECTURE_FREEZE_2026-02-17.md](ARCHITECTURE_FREEZE_2026-02-17.md)
> covers the campus *scope / access-control* model (ADMIN vs INSTRUCTOR restrictions).
> This document covers the campus *infrastructure selection* model (explicit input,
> round-robin allocation, lifecycle preconditions).

---

## 1. Mandatory Infrastructure Input (`campus_ids`)

### Rule

**Every session-generation path requires explicit campus IDs from the caller.**
Auto-discovery of active campuses from the database is removed.

### Before (removed)

```python
# ops_scenario.py — DELETED
physical_campuses = db.query(Campus.id).filter(
    Campus.is_active == True,
    Campus.address.isnot(None),
).order_by(Campus.id).limit(8).all()
campus_ids = [c.id for c in physical_campuses] if physical_campuses else []
```

### After

```python
# ops_scenario.py — CURRENT
campus_ids = request.campus_ids          # from OpsScenarioRequest (required, min 1)
active_campuses = db.query(Campus.id).filter(
    Campus.id.in_(campus_ids),
    Campus.is_active == True,
).all()
invalid_ids = [cid for cid in campus_ids if cid not in {c.id for c in active_campuses}]
if invalid_ids:
    raise HTTPException(422, f"Campus IDs {invalid_ids} not found or inactive.")
```

### Schema enforcement

`OpsScenarioRequest.campus_ids` is a **required** field with `min_length=1`:

```python
campus_ids: List[int] = Field(
    ...,
    min_length=1,
    description="Explicit campus IDs for session distribution (required, min 1). "
                "Auto-discovery is disabled.",
)
```

A missing or empty `campus_ids` raises `pydantic.ValidationError` before the request
reaches any handler — no DB access occurs.

### Entry points

| Entry point | campus_ids source |
|---|---|
| `POST /tournaments/ops/run-scenario` | `OpsScenarioRequest.campus_ids` (required) |
| `POST /tournaments/{id}/generate-sessions` | Request body (optional; instructor scope guard applies) |
| `PATCH /{id}` status → `IN_PROGRESS` | `generate_sessions()` internal call (inherits from tournament config) |

---

## 2. Round-Robin Campus Allocation

### Rule

Sessions are distributed across campuses using a **stateless round-robin** keyed on
the zero-based session index within the generator's output list.

### Implementation

```python
# app/services/tournament/session_generation/utils.py

def pick_campus(session_index: int, campus_ids: Optional[List[int]]) -> Optional[int]:
    """
    Round-robin campus selection.

    Returns campus_ids[session_index % len(campus_ids)] when campus_ids is
    provided, otherwise None (session inherits tournament.campus_id — existing
    single-campus behaviour).
    """
    if not campus_ids:
        return None
    return campus_ids[session_index % len(campus_ids)]
```

Usage in every format generator:

```python
sessions.append({
    ...
    "campus_id": pick_campus(len(sessions), campus_ids),
})
```

### Properties

| Property | Value |
|---|---|
| Stateless | No DB read inside the helper |
| Deterministic | Same input → same output; reproducible in tests |
| Backward-compatible | `campus_ids=None` or `[]` → `campus_id=None` (inherits from `tournament.campus_id`) |
| Distribution | Even ± 1 session across all campuses |

### Covered generators (as of 2026-02-18)

| Generator | Format | campus_ids kwarg |
|---|---|---|
| `LeagueGenerator` | INDIVIDUAL_RANKING + HEAD_TO_HEAD | ✅ |
| `KnockoutGenerator` | HEAD_TO_HEAD (incl. 3rd-place playoff) | ✅ |
| `SwissGenerator` | HEAD_TO_HEAD (1v1) + INDIVIDUAL_RANKING (pods) | ✅ |
| `IndividualRankingGenerator` | INDIVIDUAL_RANKING | ✅ (`pick_campus(0, …)`) |
| `GroupKnockoutGenerator` | GROUP_KNOCKOUT | ✅ (pre-existing, unchanged) |

---

## 3. `ENROLLMENT_OPEN` Campus Precondition

### Rule

A tournament cannot transition to `ENROLLMENT_OPEN` unless `campus_id` is set.
This is the **earliest lifecycle gate** that prevents session generation on a
venue-less tournament — catching the misconfiguration before any player enrolls.

### Implementation

```python
# app/services/tournament/status_validator.py

if new_status == "ENROLLMENT_OPEN":
    if not tournament.master_instructor_id:
        return False, "Cannot open enrollment: No instructor assigned"
    if not hasattr(tournament, 'max_players') or tournament.max_players is None:
        return False, "Cannot open enrollment: Max participants not configured"
    # campus_id gate (added 2026-02-18)
    if not getattr(tournament, 'campus_id', None):
        return False, (
            "Cannot open enrollment: No campus assigned. "
            "Set campus_id via PATCH /{id} before opening enrollment."
        )
```

### Lifecycle impact

```
DRAFT
  └─ SEEKING_INSTRUCTOR      ← campus_id NOT required yet
       └─ PENDING_INSTRUCTOR_ACCEPTANCE
            └─ INSTRUCTOR_CONFIRMED
                 └─ ENROLLMENT_OPEN    ← campus_id REQUIRED (gate added here)
                      └─ ENROLLMENT_CLOSED
                           └─ IN_PROGRESS  ← sessions generated here
```

Setting `campus_id=None` is permitted through `INSTRUCTOR_CONFIRMED`.
The admin must call `PATCH /{id}` with `campus_id` before opening enrollment.

### Recovery

```http
PATCH /api/v1/tournaments/{id}
Content-Type: application/json

{"campus_id": 42}
```

---

## 4. OPS Wizard Campus Selection (Frontend)

### State keys

| Key | Type | Default | Description |
|---|---|---|---|
| `wizard_location_id_saved` | `int \| None` | `None` | Selected location (city) |
| `wizard_campus_ids_saved` | `List[int]` | `[]` | Selected campus IDs |
| `wizard_campus_labels_saved` | `List[str]` | `[]` | Human-readable campus names (for review/summary display) |

### UI flow (Step 3)

```
Location selectbox  (get_locations → active only)
    │
    └─ Campus multiselect  (get_campuses_by_location → active only)
            │
            ├─ ≥1 campus selected → step valid, Next enabled
            └─ 0 campuses         → st.error, Next disabled
```

Step 3 is invalid if no campus is selected — the wizard cannot advance to Step 4
(game preset) without at least one campus confirmed.

### Payload path

```
wizard_campus_ids_saved
    → launch.py  →  trigger_ops_scenario(campus_ids=…)
    → api_helpers_monitor.py  →  POST /ops/run-scenario  {"campus_ids": […]}
    → OpsScenarioRequest.campus_ids  →  validated (min 1)
    → session_generator.generate_sessions(campus_ids=…)
    → pick_campus() per session
```

---

## 5. Test Coverage

**File:** `tests/unit/tournament/test_multi_campus_round_robin.py`
**Tests:** 25 (all DB-free, 0.83s)

| Class | Tests | What's validated |
|---|---|---|
| `TestPickCampus` | 4 | Round-robin math, None/empty fallback |
| `TestLeagueGeneratorMultiCampus` | 4 | All sessions have campus_id; distribution covers all 3 campuses; backward-compat |
| `TestKnockoutGeneratorMultiCampus` | 4 | 7 sessions + playoff all have campus_id; index-by-index assertion |
| `TestSwissGeneratorMultiCampus` | 3 | HEAD_TO_HEAD and pod paths; backward-compat |
| `TestIndividualRankingGeneratorMultiCampus` | 2 | Single session → campus_ids[0]; None fallback |
| `TestOpsScenarioRequestCampusValidation` | 4 | Missing/empty campus_ids → ValidationError; valid values accepted |
| `TestStatusValidatorCampusPrecondition` | 4 | campus_id=None/0 blocks ENROLLMENT_OPEN; campus_id=5 passes; other transitions unaffected |

---

## 6. Invariants — Do Not Break

These invariants are enforced by the test suite and must be maintained in all
future modifications to the campus infrastructure:

1. **`pick_campus(i, None)` → `None`** — never raises, always backward-compatible.
2. **`pick_campus(i, [])` → `None`** — empty list treated same as None.
3. **`pick_campus(i, ids)` → `ids[i % len(ids)]`** — pure modulo, no state.
4. **All format generators pass `campus_ids` through `**kwargs`** — new generators
   must follow the same convention; adding a positional `campus_ids` parameter is
   a breaking API change.
5. **`ENROLLMENT_OPEN` without `campus_id` is always rejected** — do not add
   bypass paths (e.g., admin-only override) without a team decision recorded here.
6. **`OpsScenarioRequest.campus_ids` is required (`min_length=1`)** — the field
   must not become Optional without removing the auto-discovery prohibition first.
