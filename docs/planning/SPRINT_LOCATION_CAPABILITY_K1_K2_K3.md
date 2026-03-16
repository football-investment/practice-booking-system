# Sprint Backlog — Location Capability Hardening (K1 / K2 / K3)

**Status**: 🟡 Ready for sprint planning
**Created**: 2026-03-16
**Tracking**: `docs/architecture/domain-model.md` §8.5–8.6
**Test file**: `tests/integration/domain/test_location_capability_api.py` (LOC-API-01–10, 14 tests)

---

## CI status (as of 2026-03-16)

| Job | Path covered | Status |
|-----|-------------|--------|
| `unit-tests` (test-baseline-check.yml, line 63) | `tests/integration/domain/` | ✅ Automatic — LOC-API tests run on every PR |
| `migration-integrity` | `alembic upgrade head` from empty DB | ✅ Migration `2026_03_16_1000` covered |

**No workflow changes required.** `tests/integration/domain/` was already in the baseline
pytest command. 9177 passed, 1 xfailed on main as of this writing.

---

## K1 — Require `location_id` for ACADEMY types in `POST /api/v1/semesters/`

### Current behaviour
If `location_id` is omitted, the generic REST endpoint accepts ACADEMY types without any
location check (documented as "permissive stance" in LOC-API-08).

### Why this is an open gap
A client that calls `POST /api/v1/semesters/` with `specialization_type=LFA_PLAYER_PRE_ACADEMY`
and no `location_id` gets a valid 200 response. The semester is created without location context,
making it invisible to the CENTER/PARTNER enforcement layer. Only the admin form enforces the
stricter rule.

### Proposed implementation

**File:** `app/api/api_v1/endpoints/_semesters_main.py` — `create_semester()`

Add the following guard **before** the existing location-validation block:

```python
_ACADEMY_TYPES = {
    SpecializationType.LFA_PLAYER_PRE_ACADEMY,
    SpecializationType.LFA_PLAYER_YOUTH_ACADEMY,
    SpecializationType.LFA_PLAYER_AMATEUR_ACADEMY,
    SpecializationType.LFA_PLAYER_PRO_ACADEMY,
}

if spec_enum in _ACADEMY_TYPES and not semester_data.location_id:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": "Hiányzó helyszín",
            "message": "Academy Season típushoz kötelező megadni a location_id-t.",
        }
    )
```

**Test update:** `LOC-API-08` expects 200 today. Change expected status to 400 and add a
message assertion after the guard is live:
```python
# LOC-API-08 after K1 resolved:
assert resp.status_code == 400
assert "location_id" in _get_error_message(resp).lower()
```

**Acceptance criteria:**
- [ ] `POST /api/v1/semesters/` with ACADEMY type + no `location_id` → HTTP 400
- [ ] LOC-API-08 updated to expect 400
- [ ] All other LOC-API tests (01–07, 09–10) unchanged
- [ ] OpenAPI snapshot regenerated
- [ ] Full suite: 0 regressions

**Effort estimate:** ~30 min (code) + ~15 min (test update + snapshot)

---

## K2 — Block CENTER→PARTNER location type change when Academy semesters exist

### Current behaviour
`PATCH /api/v1/locations/{id}` (and the admin location-edit form) allow changing a location's
`location_type` from CENTER to PARTNER freely, even if active Academy Seasons are linked to
that location. The DB constraint only fires on semester INSERT/UPDATE, not on location UPDATE.

### Why this matters
If a CENTER is downgraded to PARTNER:
- Existing Academy semesters remain linked to a now-PARTNER location (data inconsistency).
- Future semester creation at that location correctly blocks ACADEMY types, but historical ones
  are orphaned in a semantically invalid state.

### Proposed implementation (two-phase)

#### Phase A — Block for active semesters (recommended, implement first)

**File:** location edit endpoint (check `app/api/api_v1/endpoints/locations.py` and
`app/api/web_routes/admin.py` — `admin_location_edit_submit`)

Add pre-check before committing a `location_type` downgrade:

```python
from app.models.semester import Semester, SemesterStatus
from app.models.specialization import SpecializationType

_ACADEMY_TYPES = [
    SpecializationType.LFA_PLAYER_PRE_ACADEMY.value,
    SpecializationType.LFA_PLAYER_YOUTH_ACADEMY.value,
    SpecializationType.LFA_PLAYER_AMATEUR_ACADEMY.value,
    SpecializationType.LFA_PLAYER_PRO_ACADEMY.value,
]
_ACTIVE_STATUSES = [SemesterStatus.READY_FOR_ENROLLMENT, SemesterStatus.ONGOING]

if (old_type == LocationType.CENTER
        and new_type == LocationType.PARTNER):
    conflict = db.query(Semester).filter(
        Semester.location_id == location_id,
        Semester.specialization_type.in_(_ACADEMY_TYPES),
        Semester.status.in_(_ACTIVE_STATUSES),
    ).first()
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Aktív Academy Season létezik",
                "message": (
                    f"Nem lehet CENTER→PARTNER típust változtatni: "
                    f"'{conflict.name}' ({conflict.code}) aktív Academy Season "
                    f"ehhez a helyszínhez van rendelve."
                ),
                "conflicting_semester_id": conflict.id,
            }
        )
```

#### Phase B — Warn for historical semesters (optional, implement later)

Emit a structured log warning if there are DRAFT/COMPLETED Academy semesters linked to the
location. No blocking — only observability.

**New integration test (K2 test suite):**

```
POST /api/v1/semesters/   → create Academy semester at CENTER location
PATCH /api/v1/locations/{id}  body: {"location_type": "PARTNER"}
  → expect 409 while semester is ACTIVE
  → set semester status to COMPLETED → expect 200 (historical, not blocked)
```

**Acceptance criteria:**
- [x] CENTER→PARTNER type change blocked when ACTIVE Academy semester exists → 409
- [x] CENTER→PARTNER allowed when only COMPLETED/DRAFT Academy semesters exist → 200
- [x] PARTNER→CENTER allowed unconditionally
- [x] Both REST API and admin form enforce the rule
- [x] New integration tests for all three cases (LOC-API-13/14/15 + SMOKE-21a/b/c)
- [ ] Structured log warning emitted for historical-semester case (Phase B — deferred)

**Effort estimate:** ~1.5h (code both endpoints) + ~1h (tests)

---

## K3 — Session generation: location-agnostic (RESOLVED — no action)

### Decision: architecture is correct as-is

Session properties (type, capacity, duration, count, `event_category`) are determined by
`specialization_type` and game-preset templates, **not** by `LocationType`. This is intentional.

**Rationale** (documented in `docs/architecture/domain-model.md` §8.6):
- Predictability: same programme structure regardless of venue
- Operational simplicity: adding a new location requires no template config
- Business rule separation: *which programme can run here* ≠ *what does a session look like*

**No code changes planned.** K3 is closed.

If the product evolves to require location-specific session overrides (e.g., extended field
time at CENTER locations), the entry point is `app/services/session_generator.py` — accept
a `location_type` kwarg and apply per-type overrides from a strategy map. Document that
requirement as a new feature request, not a bug fix.

---

## Execution order

| # | Item | Status | Sprint |
|---|------|--------|--------|
| 1 | CI verification | ✅ Done | 2026-03-16 |
| 2 | K3 decision documented | ✅ Done | 2026-03-16 |
| 3 | K1 — require location_id for ACADEMY (REST) | ✅ Done | 2026-03-16 |
| 4 | K2 Phase A — block CENTER→PARTNER downgrade (active semesters) | ✅ Done | 2026-03-16 |
| 4b | K2 admin form smoke tests (SMOKE-21a/b/c) | ✅ Done | 2026-03-16 |
| 5 | K2 Phase B — warn for historical semesters | ⬜ Deferred | Sprint+2 |

---

## Key references

| Resource | Link |
|----------|------|
| Architecture decision record | [domain-model.md §8](../architecture/domain-model.md#8-location-capabilities--center-vs-partner) |
| Open decisions (K1–K3) | [domain-model.md §8.5](../architecture/domain-model.md#85-open-business-decisions-k1k3) |
| Session-level stance | [domain-model.md §8.6](../architecture/domain-model.md#86-session-generation--location-agnostic-by-design) |
| LOC-API test file | [`tests/integration/domain/test_location_capability_api.py`](../../tests/integration/domain/test_location_capability_api.py) |
| DB constraint migration | [`alembic/versions/2026_03_16_1000-...py`](../../alembic/versions/2026_03_16_1000-add_location_type_check_constraint_to_semesters.py) |
| LocationValidationService | [`app/services/location_validation_service.py`](../../app/services/location_validation_service.py) |
| CI job (unit-tests) | [`.github/workflows/test-baseline-check.yml`](../../.github/workflows/test-baseline-check.yml) line 63 |
