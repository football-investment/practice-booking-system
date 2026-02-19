# Release Note — System Events (Rendszerüzenetek)

**Date:** 2026-02-17
**Branch:** `feature/performance-card-option-a`
**Type:** Architecture / Security / Monitoring

---

## Summary

Introduces a **DB-backed structured event log** (`system_events` table) for deliberate
business and security events.  Admins can view, filter, resolve, and purge events via
the new **Rendszerüzenetek** tab in the Admin Dashboard.

---

## Migration Chain

```
e7f8a9b0c1d2  add_tournament_checked_in_at_to_enrollments  (previous HEAD)
se001create00  create_system_events_table
se002residx00  add_system_events_resolved_index              ← HEAD
```

To upgrade:

```bash
alembic upgrade head
```

### Key migration notes

| Item | Detail |
|------|--------|
| New table | `system_events` — 8 columns, JSONB payload |
| New PG type | `systemeventlevel ENUM ('INFO', 'WARNING', 'SECURITY')` |
| ENUM creation | Idempotent `DO $$ BEGIN … EXCEPTION WHEN duplicate_object` block |
| Alembic `create_type` | Uses `PgENUM(…, create_type=False)` — SQLAlchemy must **not** re-issue `CREATE TYPE` after the DO block |
| Indexes | 9 indexes including composite `(user_id, event_type, created_at)` for rate-limit queries and partial `WHERE resolved = false` for open-event dashboard |
| FK | `user_id → users.id ON DELETE SET NULL` (nullable) |

---

## New Components

### Backend

| File | Role |
|------|------|
| `app/models/system_event.py` | SQLAlchemy model — `SystemEvent`, `SystemEventLevel`, `SystemEventType` |
| `app/services/system_event_service.py` | Service: `emit()`, `get_events()`, `mark_resolved()`, `purge_old_events()` |
| `app/api/api_v1/endpoints/system_events.py` | REST endpoints — `GET /system-events`, `PATCH /{id}/resolve`, `PATCH /{id}/unresolve`, `POST /purge` |
| `app/background/scheduler.py` | APScheduler daily purge job at 02:00 UTC (misfire grace 1 h) |

### Frontend (Streamlit)

| File | Role |
|------|------|
| `streamlit_app/api_helpers_system_events.py` | API client helpers |
| `streamlit_app/components/admin/system_events_tab.py` | Admin UI — filter, paginate (50/page), resolve, purge |
| `streamlit_app/pages/Admin_Dashboard.py` | Registered as 8th tab: `🔔 Üzenetek` |

---

## Critical Implementation Patterns

### SAVEPOINT isolation (`emit()`)

```python
savepoint = self.db.begin_nested()
try:
    if self._is_rate_limited(user_id, event_type):
        savepoint.commit(); return None
    event = SystemEvent(...)
    self.db.add(event); self.db.flush(); savepoint.commit()
    return event
except Exception as exc:
    savepoint.rollback()
    logger.warning("SYSTEM_EVENT_WRITE_FAILED …", exc_info=True)
    return None
```

The entire `emit()` body — rate-limit query AND INSERT — runs inside a SAVEPOINT.
If the table is missing or any constraint fails, only the savepoint rolls back.
The outer transaction (e.g. a 403 response) continues unaffected.

### Rate limiting

One event per `(user_id, event_type)` per 10 minutes.  Enforced by querying the
composite index `ix_system_events_user_event_type_created`.

### Retention

Default 90 days (env `SYSTEM_EVENT_RETENTION_DAYS`).  Only **resolved** events are
purged; open events are never deleted automatically.  Manual purge available via
`POST /api/v1/system-events/purge`.

---

## Test Coverage

```
tests/unit/tournament/test_system_event_service.py  15/15 PASSED
  TestSystemEventPurge     (5 tests) — retention boundary, open-event protection
  TestSystemEventRateLimit (3 tests) — deduplication within 10-min window
  TestSystemEventRead      (4 tests) — pagination, level filter, resolved filter
  TestSystemEventResolve   (3 tests) — mark_resolved / mark_unresolved / missing ID
```

### FK fixture note

Rate-limit tests use:
- `user_id=1` — permanently seeded `admin@lfa.com` (System Administrator, id=1)
- `user_id=None` — anonymous (nullable FK) — distinct rate-limit bucket from user_id=1

This is stable on every environment that has run the standard seed/migration sequence.

---

## Post-Deploy Checklist

- [ ] `alembic upgrade head` completes with no errors on staging/production
- [ ] `alembic current` shows `se002residx00 (head)`
- [ ] `GET /api/v1/system-events` returns 200 for an ADMIN token
- [ ] Admin Dashboard → 🔔 Üzenetek tab renders without error
- [ ] Trigger a multi-campus scope violation → verify SECURITY event appears in the tab
- [ ] `POST /api/v1/system-events/purge` returns `{"deleted": 0, …}` on fresh DB
- [ ] APScheduler log shows `system_events_purge_job` registered at startup

---

## Monitoring Signals

| Log key | Meaning | Action |
|---------|---------|--------|
| `SYSTEM_EVENT_WRITE_FAILED` | `emit()` SAVEPOINT rolled back | Investigate DB health; table missing or FK violation |
| `SYSTEM_EVENT_PURGE_FAILED` | APScheduler purge job crashed | Check scheduler logs; run manual purge via API |

---

## Related Documents

- [ARCHITECTURE_FREEZE_2026-02-17.md](../features/ARCHITECTURE_FREEZE_2026-02-17.md)
- [OPERATIONS_RUNBOOK_SYSTEM_EVENTS.md](../features/OPERATIONS_RUNBOOK_SYSTEM_EVENTS.md)
- [CAMPUS_SCOPE_MODEL.md](../features/CAMPUS_SCOPE_MODEL.md)
