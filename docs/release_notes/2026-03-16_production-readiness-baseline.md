# Release Note — Production Readiness Baseline

**Date:** 2026-03-16
**Tag:** `v2026.03.1-production-ready`
**PRs:** #32, #33, #34, #35
**Commits:** `cfbced9` (squash merge to main)
**Alembic migrations:** none in this release — infrastructure-only changes
**Risk level:** LOW — all new behaviour is additive; no schema changes; no API contract changes

---

## Summary

Four PRs delivered a complete production readiness overhaul covering
database resilience, graceful shutdown, background worker reliability,
operational observability, metrics labelling, alert thresholds, log
rotation, and deployment documentation.

The backend is now declared the **official stable production baseline**
at tag `v2026.03.1-production-ready`.

---

## Changes

### 1. Database connection resilience (PR #34)

| Setting | Default | Purpose |
|---------|---------|---------|
| `DB_CONNECT_TIMEOUT` | `10 s` | psycopg2 per-attempt connect timeout |
| `DB_STATEMENT_TIMEOUT_MS` | `0` (disabled) | per-statement wall-clock limit |
| `DB_STARTUP_RETRIES` | `5` | `wait_for_db()` retry count at startup |
| `DB_STARTUP_RETRY_DELAY` | `2.0 s` | exponential backoff initial delay |

`wait_for_db()` added to `app/database.py` — performs a `SELECT 1`
health-check with exponential backoff before the application starts
accepting traffic. Prevents serving requests while the database is
still initialising.

### 2. Connection pool tuning (PR #35)

| Setting | Default | Notes |
|---------|---------|-------|
| `DB_POOL_SIZE` | `20` | persistent connections per worker |
| `DB_MAX_OVERFLOW` | `30` | burst connections released when idle |
| `DB_POOL_RECYCLE` | `3600 s` | recycle connections after 1 hour |

All values are overridable via environment variables without a code
deploy. See runbook §9 for sizing recommendations.

### 3. Graceful shutdown (PR #35)

`stop_scheduler()` in `app/background/scheduler.py` now accepts a
`timeout` parameter (default: `settings.GRACEFUL_SHUTDOWN_TIMEOUT = 30 s`).
If APScheduler does not finish within the timeout, a `WARNING` is logged
and `scheduler.shutdown(wait=False)` is called as a force-stop fallback.

### 4. Celery broker resilience (PR #35)

| Config key | Value |
|------------|-------|
| `broker_connection_retry_on_startup` | `True` |
| `broker_connection_retry` | `True` |
| `broker_connection_max_retries` | `settings.CELERY_BROKER_CONNECTION_MAX_RETRIES` (default 10) |
| `broker_transport_options.socket_timeout` | `10 s` |
| `broker_transport_options.socket_connect_timeout` | `10 s` |
| `broker_transport_options.retry_on_timeout` | `True` |

Workers survive a brief Redis restart or delayed pod scheduling without
manual intervention.

### 5. Metrics labelling and cardinality guard (PR #33 / #34)

- `DomainMetrics.increment_labeled(name, labels)` — records counters
  with arbitrary label dimensions.
- `_ALLOWED_LABEL_VALUES` whitelist per label key; unknown values emit a
  `WARNING` on logger `app.metrics.cardinality` but are still recorded
  (non-blocking).
- `GET /metrics` response extended with `labeled_counters` key.

### 6. Alert thresholds (PR #33)

Four configurable alert thresholds (all via env vars, all evaluated by
`GET /metrics/alerts`):

| Setting | Default | Meaning |
|---------|---------|---------|
| `ALERT_REWARD_FAILURE_RATE` | `0.05` | >5 % reward failures |
| `ALERT_BOOKING_WAITLIST_RATE` | `0.30` | >30 % bookings waitlisted |
| `ALERT_ENROLLMENT_GATE_BLOCK_RATE` | `0.20` | >20 % enrollments gate-blocked |
| `ALERT_SLOW_QUERY_TOTAL` | `10` | >10 slow queries since start |

### 7. Log rotation (PR #33)

| Setting | Default |
|---------|---------|
| `LOG_DIR` | `logs` |
| `LOG_MAX_BYTES` | `10 MB` |
| `LOG_BACKUP_COUNT` | `5` |

Rotating file handler wired in `app/main.py`; `SLOW_QUERY_THRESHOLD_MS`
(default 200 ms) controls which queries are logged to `app.slow_query`.

### 8. Operational smoke test CI job (PR #34)

New `operational-smoke-test` job in `test-baseline-check.yml`:
- Starts PostgreSQL 15 + Redis 7 service containers
- Applies migrations (`alembic upgrade head`)
- Starts uvicorn; polls `/health/ready` up to 40 s
- Runs 6-endpoint Python smoke check
- Added to `baseline-report` needs list (required for "Safe to merge" gate)

### 9. Deployment documentation (PR #35)

`docs/operations/runbook.md` extended with:
- **§0** — Deployment sequence (migration → seed → start → health-poll → traffic)
- **§9** — Connection pool sizing guide (small / medium / large / XL tiers)
- **§10** — Graceful shutdown (uvicorn `--timeout-graceful-shutdown`, K8s `terminationGracePeriodSeconds`)
- **§11** — Production configuration profile (complete `.env.production` template + 10-item checklist)

---

## Bug fixes (same release)

| Fix | File |
|-----|------|
| `alembic downgrade base` crash — `DROP SCHEMA CASCADE` removed `alembic_version` before Alembic could delete its own row | `alembic/versions/2026_02_21_0859-1ec11c73ea62_squashed_baseline_schema.py` |
| Cypress ADM-WF-03 — `cy.click()` hit all 5 submit buttons on multi-section edit page | `cypress/e2e/web/admin/admin_full_workflow.cy.js` |
| Cypress ADM-RESP-12 — `.table-scroll-wrap` absent on `/admin/payments` when DB has no invoice data | `app/templates/admin/payments.html` |

---

## Test baseline

| Metric | Value |
|--------|-------|
| Tests passing | **9 158** |
| Expected failures (xfail) | 1 |
| Routes | 555 |
| CI jobs (Test Baseline Check) | 23 / 23 green |

---

## Deployment checklist

1. `alembic upgrade head` — no migrations in this release, but always run as a precaution.
2. Set new env vars if adjusting defaults (see §11 of runbook).
3. Restart uvicorn workers to pick up pool / timeout settings.
4. Verify `GET /health/ready` returns 200 before routing traffic.
5. Verify `GET /metrics/alerts` shows no active alerts after a brief warmup period.
