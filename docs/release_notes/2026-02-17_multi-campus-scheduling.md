# Release Note — Multi-Campus Scheduling & Campus Scope Enforcement

**Date:** 2026-02-17
**Branch:** `feature/performance-card-option-a`
**Type:** Architecture / Security / Feature

---

## Summary

This release introduces **per-campus parallel-field scheduling** for group-knockout
tournaments and establishes a role-based **Campus Scope Model** that is enforced
at every layer of the stack (backend API, frontend UI, automated tests).

---

## Changes

### 1. Multi-Campus Session Scheduling (Admin)

Previously the session generator used a single global `parallel_fields` value
even when a tournament spanned multiple campuses.

**What changed:**

- `session_generator.py` now resolves a `CampusScheduleConfig` for each campus
  in `campus_ids` and builds `campus_configs: Dict[int, dict]`.
- `group_knockout_generator.py` maintains independent `field_slots` pools per
  campus — sessions at Campus A never consume time-slots from Campus B.
- Global fallback preserved: `campus_configs=None` (or missing campus entry)
  falls back to the tournament's saved schedule config.
- Inter-phase break calculation uses `max()` across **all** campus time-pools.

**Supported per-campus overrides** (via `campus_schedule_overrides` in the
generate-sessions request body):

```json
{
  "campus_schedule_overrides": {
    "101": { "match_duration_minutes": 60, "parallel_fields": 2 },
    "202": { "match_duration_minutes": 45, "parallel_fields": 3 }
  }
}
```

---

### 2. Campus Scope Enforcement (Backend)

A new backend guard `_assert_campus_scope()` enforces single-campus scope for
instructors at the API boundary — independent of UI restrictions.

| Role | `campus_ids` allowed | `campus_schedule_overrides` keys |
|------|---------------------|----------------------------------|
| ADMIN | Any count | Any count |
| INSTRUCTOR | max 1 | max 1 |

Violations return **HTTP 403 Forbidden** before any DB writes, preventing
partial state.

**Security audit logging** — every blocked attempt emits a WARNING:
```
SECURITY: instructor multi-campus attempt blocked —
  user_id=42 email=instructor@lfa.com role=INSTRUCTOR campus_ids=[101, 202]
```

**Entry points audited** — all 6 code paths calling `generate_sessions()` were
reviewed. No unguarded instructor-accessible multi-campus path exists. See
[CAMPUS_SCOPE_MODEL.md](../features/CAMPUS_SCOPE_MODEL.md) for the full table.

---

### 3. Frontend — Role-Split Campus Selection UI

`streamlit_app/components/admin/tournament_list_dialogs.py`

| Role | Widget | Behaviour |
|------|--------|-----------|
| ADMIN | `st.multiselect` | 0–N campuses |
| INSTRUCTOR | `st.selectbox` | 0 or 1 campus |

When an instructor sees multiple campuses available, a blue info banner explains:
> "X campuses available — you have access to multiple campuses, but sessions can
> only be generated for one campus at a time."

`api_helpers_tournaments.py` — `generate_tournament_sessions()` now accepts an
optional `campus_ids: List[int]` parameter and includes it in the JSON payload.

---

### 4. Production Safety

`app/config.py` — added `ENVIRONMENT=production` enforcement:

- `DEBUG` must be `False` in production (prevents stack traces leaking to clients).
- `ADMIN_PASSWORD` must not be a weak default.
- `COOKIE_SECURE` must be `True`.
- `CORS_ALLOWED_ORIGINS` must not include localhost.

---

## Test Coverage

### Unit tests (DB-free)

| Suite | Tests | All pass |
|-------|-------|----------|
| `test_campus_scope_guard.py` | 13 (G-01…G-12) | ✅ |
| `test_multi_campus_scheduling.py` | 4 (TC-01…TC-04) | ✅ |

### Integration tests (HTTP + PostgreSQL rollback)

| Suite | Tests | All pass |
|-------|-------|----------|
| `test_campus_scope_guard_integration.py` | 4 (I-01…I-04) | ✅ |

**Total: 21 tests, 21 pass.**

---

## Migration / Deployment Notes

- No database schema changes — `campus_ids` and `campus_schedule_overrides` are
  request-body parameters, not new columns.
- `ENVIRONMENT=production` deployments must add `DEBUG=false` to their `.env`
  (or environment) — the app will refuse to start without it.
- No breaking changes to the existing single-campus generation path.

---

## References

- [CAMPUS_SCOPE_MODEL.md](../features/CAMPUS_SCOPE_MODEL.md) — full spec
- [`generate_sessions.py`](../../app/api/api_v1/endpoints/tournaments/generate_sessions.py) — backend guard
- [`group_knockout_generator.py`](../../app/services/tournament/session_generation/formats/group_knockout_generator.py) — per-campus scheduling
