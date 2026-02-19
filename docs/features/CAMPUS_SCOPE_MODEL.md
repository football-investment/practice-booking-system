# Campus Scope Model

> **Status:** Implemented & tested — 2026-02-17
> **Branch:** `feature/performance-card-option-a`

## Overview

The Campus Scope Model defines which campus(es) a user is allowed to target when
generating tournament sessions.  It is a role-based access control (RBAC) rule
that is enforced at **three levels**:

| Level | Layer | File |
|-------|-------|------|
| 1 | Backend API guard (primary) | `app/api/api_v1/endpoints/tournaments/generate_sessions.py` |
| 2 | Frontend widget restriction | `streamlit_app/components/admin/tournament_list_dialogs.py` |
| 3 | Unit + integration tests | `tests/unit/tournament/test_campus_scope_guard.py` / `test_campus_scope_guard_integration.py` |

---

## Role Rules

### ADMIN
- **Multi-campus allowed** — no restriction on `campus_ids` count.
- Can pass `campus_ids=[1, 2, 3]` and `campus_schedule_overrides` with N keys.
- UI: `st.multiselect()` — zero or more campuses.

### INSTRUCTOR
- **Single-campus only** — at most 1 entry in `campus_ids` and at most 1 key
  in `campus_schedule_overrides`.
- Sending `campus_ids=[101, 202]` (2+ IDs) → **HTTP 403 Forbidden**.
- Sending `campus_schedule_overrides` with 2+ keys → **HTTP 403 Forbidden**.
- UI: `st.selectbox()` — single campus or "no override".
- The `campus_ids` check fires **before** the `campus_schedule_overrides` check.

---

## Backend Guard (`_assert_campus_scope`)

Location: [`app/api/api_v1/endpoints/tournaments/generate_sessions.py:315`](../../app/api/api_v1/endpoints/tournaments/generate_sessions.py)

```python
def _assert_campus_scope(current_user, campus_ids, campus_schedule_overrides):
    if current_user.role == UserRole.ADMIN:
        return  # Admins: unrestricted

    # Instructor check 1: campus_ids
    if campus_ids and len(campus_ids) > 1:
        raise HTTPException(status_code=403,
            detail="Instructors may only generate sessions for a single campus. ...")

    # Instructor check 2: campus_schedule_overrides
    if campus_schedule_overrides and len(campus_schedule_overrides) > 1:
        raise HTTPException(status_code=403,
            detail="Instructors may only configure schedule overrides for a single campus. ...")
```

**Critical property:** called BEFORE any DB writes → a 403 never leaves partial state.

---

## Endpoint Authorization

`POST /api/v1/tournaments/{id}/generate-sessions`
uses `Depends(get_current_admin_or_instructor_user)`.

Both admins and instructors can reach this endpoint, but instructors are
restricted by `_assert_campus_scope`.

---

## Entry Point Audit

All code paths that call `generator.generate_sessions()`:

| Entry point | Auth | campus_ids supported? | Guard present? |
|-------------|------|-----------------------|----------------|
| `POST /tournaments/{id}/generate-sessions` | Admin + Instructor | Yes | ✅ `_assert_campus_scope` at line 383 |
| `PATCH /tournaments/{id}/status` (auto-gen) | Any auth user | No (`campus_ids=None` only) | ✅ Not needed — no multi-campus path |
| `PATCH /tournaments/{id}` (auto-gen on status→IN_PROGRESS) | Any auth user | No | ✅ Not needed |
| `POST /ops/run-scenario` (OPS wizard) | Admin only (line 1848 check) | Yes (auto from DB) | ✅ Admin-only guard is sufficient |
| Celery task `generate_sessions_task` | Internal only, no HTTP | Via dispatching endpoint | ✅ Guard runs at dispatch time |
| Thread fallback `_run_generation_in_background` | Internal only | Via dispatching endpoint | ✅ Guard runs at dispatch time |

**Conclusion:** No unguarded instructor-accessible multi-campus path exists.

---

## Test Matrix

### Unit tests (DB-free) — `test_campus_scope_guard.py`

| ID | Role | campus_ids | overrides | Expected |
|----|------|-----------|-----------|----------|
| G-01 | ADMIN | None | None | ✅ allowed |
| G-02a | ADMIN | [] | None | ✅ allowed |
| G-02b | ADMIN | [1,2,3] | None | ✅ allowed |
| G-03 | ADMIN | None | {1:{}, 2:{}} | ✅ allowed |
| G-04 | ADMIN | [1,2] | {1:{}, 2:{}} | ✅ allowed |
| G-05 | INSTRUCTOR | None | None | ✅ allowed |
| G-06 | INSTRUCTOR | [] | None | ✅ allowed |
| G-07 | INSTRUCTOR | [42] | None | ✅ allowed |
| G-08 | INSTRUCTOR | [42, 99] | None | 🚫 HTTP 403 |
| G-09 | INSTRUCTOR | [1,2,3] | None | 🚫 HTTP 403 |
| G-10 | INSTRUCTOR | None | {42:{}} | ✅ allowed |
| G-11 | INSTRUCTOR | None | {42:{}, 99:{}} | 🚫 HTTP 403 |
| G-12 | INSTRUCTOR | [42, 99] | {42:{}} | 🚫 HTTP 403 (campus_ids checked first) |

### Integration tests (HTTP + DB) — `test_campus_scope_guard_integration.py`

| ID | Scenario | Expected |
|----|----------|----------|
| I-01 | Instructor + campus_ids=[101,202] → HTTP 403, 0 sessions in DB | ✅ passes |
| I-02 | Instructor + 2 override keys → HTTP 403, 0 sessions in DB | ✅ passes |
| I-03 | Admin + campus_ids=[101,202] → NOT 403 (guard passes) | ✅ passes |
| I-04 | Instructor + campus_ids=[42] → NOT 403 (single campus OK) | ✅ passes |

---

## Frontend Behaviour

File: [`streamlit_app/components/admin/tournament_list_dialogs.py`](../../streamlit_app/components/admin/tournament_list_dialogs.py)

```
ADMIN view:
  Campus(es) — multi-venue        [multiselect]
  [ Campus Buda (ID 1) ×  Campus Pest (ID 2) ×  ... ]

INSTRUCTOR view:
  Campus                          [selectbox]
  [ — No campus override —  ▼ ]
```

The UI restriction is advisory — the backend guard is the authoritative enforcement.

---

## API Payload

```json
POST /api/v1/tournaments/{id}/generate-sessions
{
  "parallel_fields": 2,
  "session_duration_minutes": 60,
  "break_minutes": 10,
  "number_of_rounds": 1,
  "campus_ids": [101, 202],
  "campus_schedule_overrides": {
    "101": { "parallel_fields": 2, "match_duration_minutes": 60 },
    "202": { "parallel_fields": 3, "match_duration_minutes": 45 }
  }
}
```

- `campus_ids`: optional list of campus IDs. `null` = use tournament's default campus.
- `campus_schedule_overrides`: optional per-campus schedule overrides keyed by campus ID (as string).

**Instructor constraint:** at most 1 entry in `campus_ids` AND at most 1 key in `campus_schedule_overrides`.
