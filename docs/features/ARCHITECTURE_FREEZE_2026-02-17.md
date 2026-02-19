# Architecture Freeze — 2026-02-17

**Branch:** `feature/performance-card-option-a`
**Status:** Stable milestone — patterns below are locked and must not be changed without a team decision.

---

## 1. Campus Scope Model

### Rule

| Role | campus_ids allowed | campus_schedule_overrides keys allowed |
|------|--------------------|----------------------------------------|
| ADMIN | 0…N (unrestricted) | 0…N (unrestricted) |
| INSTRUCTOR | 0 or 1 | 0 or 1 |

### Enforcement point

`_assert_campus_scope()` in [generate_sessions.py](../../app/api/api_v1/endpoints/tournaments/generate_sessions.py) is called **before any DB write**, so a 403 never leaves partial state.

```python
def _assert_campus_scope(
    current_user: User,
    campus_ids: Optional[List[int]],
    campus_schedule_overrides: Optional[dict],
    db: Optional[Session] = None,   # optional — unit tests pass None
) -> None:
```

- `db=None` → guard raises 403, logs `logger.warning`, no DB write (unit-test safe).
- `db=<session>` → guard raises 403, logs warning, AND emits a SECURITY system_event (rate-limited).

### Entry point audit (as of 2026-02-17)

| Endpoint | Roles | Guarded |
|----------|-------|---------|
| `POST /tournaments/{id}/generate-sessions` | Admin + Instructor | ✅ `_assert_campus_scope` |
| `lifecycle.py:461` (internal rebuild) | Admin only (no campus_ids param) | n/a |
| `lifecycle.py:1032` (internal rebuild) | Admin only (no campus_ids param) | n/a |
| `generator.py:2247` (OPS wizard) | Admin only (`get_current_admin_or_instructor_user` + admin check) | ✅ |

**Conclusion:** No instructor-accessible multi-campus bypass exists in the codebase.

### Test coverage

- `tests/unit/tournament/test_campus_scope_guard.py` — 13 unit tests (G-01…G-12, DB-free)
- `tests/unit/tournament/test_campus_scope_guard_integration.py` — 4 integration tests (I-01…I-04, FastAPI TestClient + PostgreSQL)

---

## 2. SAVEPOINT Isolation Pattern

### Problem

`SystemEventService.emit()` writes to `system_events` as a side effect of business logic (e.g., inside a 403 guard). If the write fails (table missing, constraint error, network glitch), the caller's transaction must not be affected — the 403 must still propagate.

### Solution

```python
savepoint = self.db.begin_nested()   # → SAVEPOINT sp1
try:
    # ... rate-limit check + INSERT
    savepoint.commit()               # → RELEASE SAVEPOINT sp1
    return event
except Exception as exc:
    savepoint.rollback()             # → ROLLBACK TO SAVEPOINT sp1
    logger.warning(
        "SYSTEM_EVENT_WRITE_FAILED — user_id=%s event_type=%s error=%s",
        user_id, event_type, type(exc).__name__, exc_info=True,
    )
    return None
```

### Rules

1. `emit()` is **always fire-and-forget** — callers never check the return value for correctness.
2. SAVEPOINT covers the entire emit body, including the rate-limit query (which also hits `system_events`).
3. The structured log key `SYSTEM_EVENT_WRITE_FAILED` is grep-able for production alerting.
4. This pattern must be preserved whenever emit() is extended.

### Why this matters in tests

The integration tests run against a real PostgreSQL DB without the `system_events` migration applied. The SAVEPOINT pattern allows tests to pass even though the table doesn't exist — the savepoint rolls back cleanly, the 403 still fires, and DB state is verified.

---

## 3. SystemEvent DB-Backed Monitoring

### Architecture

```
audit_logs     ← automatic HTTP middleware (every request, operational debug)
system_events  ← deliberate application logic (business/security events, admin-reviewable)
```

These are **separate concerns** and must not be merged.

### Table: `system_events`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `created_at` | TIMESTAMPTZ | server default now() |
| `level` | ENUM | INFO / WARNING / SECURITY |
| `event_type` | VARCHAR(100) | e.g. MULTI_CAMPUS_BLOCKED |
| `user_id` | INTEGER FK → users | nullable (SET NULL on delete) |
| `role` | VARCHAR(50) | snapshot of role at event time |
| `payload_json` | JSONB | arbitrary event-specific data |
| `resolved` | BOOLEAN | false = open, true = admin-acknowledged |

### Indexes

| Index | Covers |
|-------|--------|
| `ix_system_events_created_at` | time-range queries |
| `ix_system_events_level` | filter by SECURITY/WARNING/INFO |
| `ix_system_events_event_type` | filter by type |
| `ix_system_events_user_id` | per-user history |
| `ix_system_events_user_event_type_created` | rate-limit dedup query |
| `ix_system_events_resolved` | resolved filter |
| `ix_system_events_resolved_created` | paginated admin query (resolved + time) |
| `ix_system_events_open_created` (partial) | open-only view (most common) |

### Rate limiting

Same `(user_id, event_type)` → at most 1 record per **10 minutes**.
Controlled by `_RATE_LIMIT_MINUTES = 10` in `system_event_service.py`.

### Retention

- Default: **90 days** for resolved events.
- Open events: kept indefinitely until an admin resolves them.
- Override: `SYSTEM_EVENT_RETENTION_DAYS` environment variable.
- Purge endpoint: `POST /api/v1/system-events/purge?retention_days=90` (admin only).
- Purge UI: "Karbantartás" expander in the Rendszerüzenetek admin tab.

### Admin UI

Admin Dashboard → **🔔 Üzenetek** tab (`active_tab = 'system_events'`):
- Filter by level (SECURITY / WARNING / INFO / all)
- Filter by resolved status (open / resolved / all)
- Paginated list (50 events per page) with next/prev navigation
- Per-event Lezár / Újranyit buttons
- Retention purge section (expandable)

### Planned event types (future)

| event_type | Level | Trigger |
|------------|-------|---------|
| `MULTI_CAMPUS_BLOCKED` | SECURITY | Instructor → 2+ campus_ids → 403 |
| `MULTI_CAMPUS_OVERRIDE_BLOCKED` | SECURITY | Instructor → 2+ override keys → 403 |
| `FAILED_LOGIN` | WARNING | Future: auth brute-force detection |
| `SESSION_COLLISION` | WARNING | Future: double-booking detection |
| `TOURNAMENT_GENERATION_ERROR` | WARNING | Future: generation failure |
| `DATA_INCONSISTENCY` | WARNING | Future: data integrity checks |

---

## Migration chain (as of 2026-02-17)

```
...
e7f8a9b0c1d2  add_tournament_checked_in_at_to_enrollments
se001create00  create_system_events_table
se002residx00  add_system_events_resolved_index   ← HEAD
```

To apply:
```bash
alembic upgrade head
```

### Migration idempotency guarantees

| Concern | Solution |
|---------|----------|
| `systemeventlevel` enum already exists (retry after partial failure) | `DO $$ BEGIN CREATE TYPE … EXCEPTION WHEN duplicate_object THEN null; END $$;` |
| SQLAlchemy re-issuing `CREATE TYPE` after the DO block | `PgENUM(…, create_type=False)` — `sqlalchemy.dialects.postgresql.ENUM`, not `sa.Enum` |
| Downgrade | `op.execute("DROP TYPE systemeventlevel")` — only runs if table already dropped |

### Staging upgrade validation steps

```bash
# 1. Apply
alembic upgrade head

# 2. Confirm HEAD
alembic current                              # must show: se002residx00 (head)

# 3. Verify table and indexes
psql -c "\d system_events"                   # 8 columns, 9 indexes
psql -c "\dT systemeventlevel"               # enum values: INFO, WARNING, SECURITY

# 4. Smoke-test API
curl -H "Authorization: Bearer $ADMIN_TOKEN" /api/v1/system-events   # 200 []
```

---

## 4. Post-Deploy Monitoring

### Signals to watch immediately after migration

| Log key | Source | Meaning | Action |
|---------|--------|---------|--------|
| `SYSTEM_EVENT_WRITE_FAILED` | `system_event_service.py` | `emit()` SAVEPOINT rolled back | Check DB health — table missing, FK violation, or disk pressure |
| `SYSTEM_EVENT_PURGE_FAILED` | `scheduler.py` | APScheduler 02:00 UTC purge crashed | Manual: `POST /api/v1/system-events/purge` |
| `sqlalchemy.exc.ProgrammingError: relation "system_events" does not exist` | Any endpoint | Migration not applied on this node | Run `alembic upgrade head` on the affected node |
| `psycopg2.errors.DuplicateObject: type "systemeventlevel" already exists` | Migration | Partial previous migration left orphan enum | `psql -c "DROP TYPE IF EXISTS systemeventlevel CASCADE"` then re-run `alembic upgrade head` |

### APScheduler health check

```python
from app.background.scheduler import get_scheduler_status
print(get_scheduler_status())
# Expected: {"jobs": [{"id": "system_events_purge", "next_run_utc": "2026-02-18T02:00:00+00:00", …}]}
```

### FK fixture note (unit tests)

Rate-limit unit tests (`TestSystemEventRateLimit`) use:
- `user_id=1` → permanently seeded `admin@lfa.com` (System Administrator) — stable on any migrated environment
- `user_id=None` → anonymous; distinct rate-limit bucket; nullable FK, no constraint violation

If tests fail with `ForeignKeyViolation` on a fresh environment, the seed user is missing.
Run the standard seed script before the test suite.

---

*Frozen by: Claude Code / feature/performance-card-option-a — 2026-02-17*
*Updated: 2026-02-17 — added migration idempotency table, staging validation steps, post-deploy monitoring section*
