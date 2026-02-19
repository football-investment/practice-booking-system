# System Events — Operations Runbook

**Last updated:** 2026-02-17
**Relates to:** `docs/features/ARCHITECTURE_FREEZE_2026-02-17.md`

---

## QUICK REFERENCE — Emergency Rollback

```
ROLLBACK REVISION: e7f8a9b0c1d2
CURRENT HEAD:      se002residx00
```

```bash
# Immediate rollback (destroys system_events table + enum — all event data lost)
alembic downgrade e7f8a9b0c1d2

# Verify
alembic current    # → e7f8a9b0c1d2
psql $DATABASE_URL -c "SELECT to_regclass('public.system_events')"  # → NULL

# Smoke test after rollback
python -m pytest tests/unit/tournament/ -q
```

**Deploy scripts:**

| Purpose | Command |
|---------|---------|
| Initial / re-deploy | `alembic upgrade head` |
| Post-deploy smoke | `python scripts/validate_system_events_deploy.py` |
| 24-48h health check | `python scripts/validate_system_events_24h.py` |
| Emergency rollback | `alembic downgrade e7f8a9b0c1d2` |
| Manual purge | `curl -X POST /api/v1/system-events/purge -H "Authorization: Bearer $ADMIN_TOKEN"` |

---

## 1. Log monitoring & alerting — `SYSTEM_EVENT_WRITE_FAILED`

### What to alert on

The service emits a structured WARNING log key whenever a system_event write fails:

```
SYSTEM_EVENT_WRITE_FAILED — user_id=<N> event_type=<TYPE> error=<ExcClass>
```

**Why it matters:** This key fires when the write path is broken (migration not applied, DB constraint, network error). The business logic (403, etc.) still works, but security events are silently lost. Needs immediate investigation.

### Alert rules

#### Grep / ELK / Loki (Grafana)

```
# Alert: any SYSTEM_EVENT_WRITE_FAILED in last 5 minutes
grep_pattern: "SYSTEM_EVENT_WRITE_FAILED"
window:       5m
threshold:    count > 0
severity:     WARNING → page on-call
```

#### Sentry / error tracking

Add the log key as a Sentry fingerprint or filter rule:
```python
# In sentry_sdk initialization (app/main.py):
sentry_sdk.init(
    ...
    before_send=lambda event, hint: event if "SYSTEM_EVENT_WRITE_FAILED" not in str(event) else {
        **event, "fingerprint": ["system-event-write-failed"]
    },
)
```

#### Cloudwatch / similar

```json
{
  "filterPattern": "SYSTEM_EVENT_WRITE_FAILED",
  "metricName": "SystemEventWriteFailures",
  "metricNamespace": "LFA/SystemEvents",
  "metricValue": "1"
}
```

### Related alert: `SYSTEM_EVENT_PURGE_FAILED`

Same approach — the nightly purge job emits `SYSTEM_EVENT_PURGE_FAILED` on failure.
This is lower-severity (data is not lost, just not cleaned up), but should be tracked weekly.

---

## 2. Retention policy — scheduled purge

### Implemented

The nightly purge runs as an APScheduler job (registered in `app/background/scheduler.py`):

| Property | Value |
|----------|-------|
| Job ID | `system_events_purge` |
| Schedule | Daily at **02:00 UTC** |
| Retention | 90 days (default) — override via `SYSTEM_EVENT_RETENTION_DAYS` |
| Scope | RESOLVED events only — open events are never auto-deleted |
| Misfire grace | 1 hour (runs even if server was briefly down) |

### Manual purge (admin UI)

Admin Dashboard → **🔔 Üzenetek** → "Karbantartás" expander → adjust days → "Törlés indítása"

### Manual purge (API)

```bash
# Purge resolved events older than 90 days
curl -X POST "https://api.example.com/api/v1/system-events/purge?retention_days=90" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### Environment variable

```bash
# In .env or deployment config
SYSTEM_EVENT_RETENTION_DAYS=90   # 90 = default, minimum recommended: 30
```

### Verify the job is scheduled

```python
# From Python console / startup log
from app.background.scheduler import scheduler
[j for j in scheduler.get_jobs() if j.id == 'system_events_purge']
```

Or check the startup INFO log:
```
✅ Background scheduler started successfully
Scheduled jobs:
  - System Events Retention Purge (ID: system_events_purge): ...
```

---

## 3. UI testing checklist — pagination and roles

Run these checks after any change to the Rendszerüzenetek tab or the system_events API.

### Admin role

| Test | Expected |
|------|----------|
| Open Admin Dashboard → 🔔 Üzenetek | Tab renders without error |
| Filter: Szint = SECURITY | Only SECURITY events shown |
| Filter: Állapot = "Csak nyitottak" | Only unresolved events shown |
| Navigate to page 2 (if >50 events) | Page 2 loads, offset = 50 |
| Click "Lezár" on an open event | Event disappears from open list; rerun shows resolved |
| Click "Újranyit" on resolved event | Event returns to open list |
| Karbantartás expander → "Törlés indítása" | Success message with deleted count |
| No events match filter | "Nincs megjeleníthető esemény" info shown |

### Instructor role

The Rendszerüzenetek tab is **Admin-only** — instructors have no access.

| Test | Expected |
|------|----------|
| Instructor logs in → Admin Dashboard | Redirect / access denied (role check in dashboard_header.py) |
| Direct API call `GET /api/v1/system-events` with instructor token | HTTP 403 |
| Direct API call `POST /api/v1/system-events/purge` with instructor token | HTTP 403 |

### Pagination edge cases

| Scenario | Expected |
|----------|----------|
| Total = 0 | "Nincs megjeleníthető esemény" |
| Total = 1 (< page size) | Page 1/1, no navigation buttons active |
| Total = 50 (= page size) | Page 1/1, "Következő" disabled |
| Total = 51 | Page 1/2, "Következő" active |
| Total = 51, navigate to page 2 | 1 event on page 2, "Előző" active, "Következő" disabled |

---

## 4. Architecture freeze document maintenance

**Rule:** Before any change to the 3 frozen patterns (Campus Scope, SAVEPOINT isolation, SystemEvent monitoring), update `ARCHITECTURE_FREEZE_2026-02-17.md` first and get team sign-off.

### What triggers a doc update

| Change | Action required |
|--------|----------------|
| New `event_type` added | Add to "Planned event types" table in freeze doc |
| New endpoint added to `/system-events` | Add to endpoint table |
| `_assert_campus_scope` signature change | Update function signature block + test matrix |
| New entry point for `generate_sessions` | Add to entry point audit table |
| Retention days changed | Update retention table |
| New index added to `system_events` | Add to index table |
| New campus scope rule | Update role table + test matrix |

### Maintenance checklist (before any PR merge touching frozen code)

```
[ ] ARCHITECTURE_FREEZE_2026-02-17.md is up to date
[ ] Tests pass: tests/unit/tournament/test_campus_scope_guard.py (13 tests)
[ ] Tests pass: tests/unit/tournament/test_campus_scope_guard_integration.py (4 tests)
[ ] SAVEPOINT pattern preserved in SystemEventService.emit()
[ ] SYSTEM_EVENT_WRITE_FAILED log key present in except block
[ ] purge_old_events() only deletes RESOLVED events
```

---

## 5. Developer guidelines — new event types

When adding a new system event type (e.g. `FAILED_LOGIN`, `SESSION_COLLISION`):

### Step 1: Add to `SystemEventType` enum

```python
# app/models/system_event.py
class SystemEventType(str, enum.Enum):
    ...
    FAILED_LOGIN = "FAILED_LOGIN"   # ← new
```

### Step 2: Emit using the service

```python
# In the relevant business logic
from app.services.system_event_service import SystemEventService
from app.models.system_event import SystemEventLevel, SystemEventType

SystemEventService(db).emit(
    SystemEventLevel.WARNING,
    SystemEventType.FAILED_LOGIN,
    user_id=user.id,
    role=str(user.role),
    payload={
        "email": user.email,
        "ip_address": request.client.host,
        "attempt_count": attempt_count,
    },
)
```

### Rules that must always hold

1. **SAVEPOINT pattern** — `emit()` already uses it. Never bypass by calling `db.add()` + `db.flush()` directly outside the service.
2. **Rate limiting** — `emit()` already rate-limits to 1 per 10 min per (user_id, event_type). Do not add a second rate-limit layer.
3. **Fire-and-forget** — Callers must not rely on `emit()` return value for correctness. The return is only for testing/debugging.
4. **Role guard for reads** — All `/system-events` API endpoints are admin-only. Never expose to INSTRUCTOR or lower.
5. **Payload privacy** — Never put raw passwords, tokens, or PII beyond email+user_id in `payload_json`.
6. **Update the freeze doc** — Add new event type to the "Planned event types" table in `ARCHITECTURE_FREEZE_2026-02-17.md`.

### Level selection guide

| Situation | Level |
|-----------|-------|
| Attempted policy violation (403 fired) | SECURITY |
| Suspicious but not blocked (rate limit spike, odd pattern) | WARNING |
| Normal but notable business event (large tournament created, bulk enroll) | INFO |

---

## 6. Production Release Monitoring

Run this checklist immediately after `alembic upgrade head` is applied to production.

### 6.1 Migration verification

```bash
# On the production app node:
alembic current
# Expected output: se002residx00 (head)

# Via psql — verify enum and table exist:
psql $DATABASE_URL -c "\dT systemeventlevel"
psql $DATABASE_URL -c "\d system_events"
```

**If `systemeventlevel` already exists but the table does not (partial failure from a previous attempt):**

```bash
psql $DATABASE_URL -c "DROP TYPE IF EXISTS systemeventlevel CASCADE"
alembic upgrade head
```

### 6.2 First 15 minutes after deploy

Watch for these log patterns:

```
# GOOD — emit() writing normally
INFO ... SystemEventService.emit user_id=... event_type=MULTI_CAMPUS_BLOCKED

# BAD — SAVEPOINT rolled back, event not stored (non-fatal but needs investigation)
WARNING ... SYSTEM_EVENT_WRITE_FAILED — user_id=... event_type=... error=IntegrityError

# BAD — migration not applied on this node
ERROR ... ProgrammingError: relation "system_events" does not exist
```

### 6.3 APScheduler startup confirmation

Check the application startup log for:

```
INFO  [apscheduler] Added job "system_events_purge_job" to job store 'default'
INFO  [apscheduler] Scheduler started
```

To confirm via API (admin token required):

```bash
# No dedicated endpoint — use get_scheduler_status() in a shell or check logs
# Manual purge to validate the code path:
curl -X POST /api/v1/system-events/purge \
     -H "Authorization: Bearer $ADMIN_TOKEN"
# Expected: {"deleted": 0, "retention_days": 90, "message": "Purged 0 resolved events…"}
```

### 6.4 Functional smoke test

```bash
# 1. Trigger a campus scope violation (use an INSTRUCTOR token + 2 campus_ids):
curl -X POST /api/v1/tournaments/generate-sessions \
     -H "Authorization: Bearer $INSTRUCTOR_TOKEN" \
     -d '{"campus_ids":[1,2], …}'
# Expected: 403 Forbidden

# 2. Check Admin Dashboard → 🔔 Üzenetek — SECURITY event must appear
# 3. Mark the test event as resolved

# 4. Verify paginated list (page 0, SECURITY filter):
curl "/api/v1/system-events?level=SECURITY&resolved=false&limit=50&offset=0" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 6.5 Known safe errors (do not page)

| Error | Why it's safe | Response |
|-------|--------------|----------|
| `SYSTEM_EVENT_WRITE_FAILED` once at startup | Race before first DB connection is warmed | Monitor frequency; page if > 5/min |
| `SYSTEM_EVENT_PURGE_FAILED` during deploy restart | APScheduler misfired while app was down; misfire_grace=3600 s recovers automatically | No action unless repeated |

### 6.6 Rollback procedure

```bash
alembic downgrade e7f8a9b0c1d2   # reverts se002residx00 + se001create00
```

This drops the `system_events` table and the `systemeventlevel` enum.
All event data is permanently lost — only do this if the feature must be removed entirely.

---

*Maintained by the internship project team — update this file with each significant system_events change.*
*Last updated: 2026-02-17 — Section 6 (production release monitoring) added.*
