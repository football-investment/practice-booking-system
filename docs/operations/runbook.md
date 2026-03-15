# Operations Runbook — GānCuju Education Center

Last updated: 2026-03-15

---

## Table of Contents

1. [Metrics Endpoint](#1-metrics-endpoint)
2. [Counter Definitions](#2-counter-definitions)
3. [Prometheus Integration](#3-prometheus-integration)
4. [Alert Thresholds](#4-alert-thresholds)
5. [Slow Query Handling](#5-slow-query-handling)
6. [Migration Rollback Procedure](#6-migration-rollback-procedure)
7. [Log Files and Retention](#7-log-files-and-retention)
8. [Health Endpoints](#8-health-endpoints)

---

## 1. Metrics Endpoint

The application exposes in-process domain event counters at two endpoints:

### JSON format (default)

```
GET /metrics
```

Response:

```json
{
  "counters": {
    "rewards_generated": 142,
    "rewards_failed": 3,
    "bookings_created": 512,
    "bookings_waitlisted": 18,
    "enrollment_attempts": 87,
    "enrollment_gate_blocked": 7,
    "slow_queries_total": 2
  }
}
```

Counters are **lifetime totals since the process started**.  In a multi-process
deployment (multiple uvicorn workers) each process maintains its own counters;
aggregate across workers at the load-balancer or log-aggregation layer.

### Alert evaluation

```
GET /metrics/alerts
```

Response (all clear):

```json
{
  "status": "ok",
  "thresholds": {
    "reward_failure_rate": {"value": 0.0206, "threshold": 0.05, "firing": false, ...},
    "booking_waitlist_rate": {"value": 0.034, "threshold": 0.30, "firing": false, ...},
    "enrollment_gate_block_rate": {"value": 0.08, "threshold": 0.20, "firing": false, ...},
    "slow_queries_total": {"value": 2, "threshold": 10, "firing": false, ...}
  }
}
```

`status` is `"warning"` when at least one threshold is `firing: true`.
Ratio-based alerts are only emitted after sufficient traffic (denominator > 0),
so a freshly restarted process with no traffic will not generate false positives.

---

## 2. Counter Definitions

| Counter | Meaning | Incremented in |
|---|---|---|
| `rewards_generated` | Successful `award_session_completion()` call — XP and points written to DB | `app/services/reward_service.py` |
| `rewards_failed` | `award_session_completion()` raised an exception — transaction rolled back | `app/services/reward_service.py` |
| `bookings_created` | Booking committed with status `CONFIRMED` | `app/api/api_v1/endpoints/bookings/student.py` |
| `bookings_waitlisted` | Booking committed with status `WAITLISTED` (session at capacity) | `app/api/api_v1/endpoints/bookings/student.py` |
| `enrollment_attempts` | `create_enrollment()` endpoint was called | `app/api/api_v1/endpoints/semester_enrollments/crud.py` |
| `enrollment_gate_blocked` | Enrollment blocked by parent-semester hierarchy gate (403 returned) | `app/api/api_v1/endpoints/semester_enrollments/crud.py` |
| `slow_queries_total` | SQL query exceeded the 200 ms slow-query threshold | `app/database.py` engine event listener |

---

## 3. Prometheus Integration

### Prometheus text format

```
GET /metrics?format=prometheus
```

Returns `text/plain; version=0.0.4` compatible output:

```
# HELP bookings_created_total Total bookings committed with status CONFIRMED.
# TYPE bookings_created_total counter
bookings_created_total 512
# HELP rewards_failed_total Total award_session_completion() calls that raised an exception.
# TYPE rewards_failed_total counter
rewards_failed_total 3
...
```

Counter names follow the Prometheus naming convention: `_total` suffix for
counters that were not already named with `_total` (e.g. `slow_queries_total`
is emitted as-is).

### Prometheus scrape config

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'gancuju-education-center'
    scrape_interval: 30s
    metrics_path: '/metrics'
    params:
      format: ['prometheus']
    static_configs:
      - targets: ['app:8000']
        labels:
          env: 'production'
```

### Grafana dashboard

Suggested PromQL queries:

```promql
# Reward failure rate (5-minute window)
rate(rewards_failed_total[5m]) / (rate(rewards_generated_total[5m]) + rate(rewards_failed_total[5m]))

# Booking waitlist rate
rate(bookings_waitlisted_total[5m]) / (rate(bookings_created_total[5m]) + rate(bookings_waitlisted_total[5m]))

# Enrollment gate block rate
rate(enrollment_gate_blocked_total[5m]) / rate(enrollment_attempts_total[5m])
```

Note: because counters are per-process lifetime totals (not time-series at the
application level), use `rate()` to compute per-window rates in Prometheus once
you have multiple scrape samples.

---

## 4. Alert Thresholds

### Configured thresholds (settable in `.env`)

| Alert | Default | Environment variable | Meaning |
|---|---|---|---|
| Reward failure rate | 5 % | `ALERT_REWARD_FAILURE_RATE=0.05` | More than 5 % of reward grants fail |
| Booking waitlist rate | 30 % | `ALERT_BOOKING_WAITLIST_RATE=0.30` | More than 30 % of booking attempts are waitlisted |
| Enrollment gate block rate | 20 % | `ALERT_ENROLLMENT_GATE_BLOCK_RATE=0.20` | More than 20 % of enrollment attempts are gate-blocked |
| Slow queries (absolute) | 10 | `ALERT_SLOW_QUERY_TOTAL=10` | More than 10 slow queries since process start |

### Response procedures

#### `reward_failure_rate` firing

1. Check `app/slow_query` logs for recent slow queries that may have caused timeouts.
2. Inspect `app.services.reward_service` logs for `event=reward_failed` — the `error=` field contains the exception repr.
3. Common causes: DB connection exhaustion, constraint violations (check `uq_event_reward_log_user_session`), disk I/O saturation.
4. If the error is transient (e.g. brief DB unavailability), the counter will stabilise automatically as the rate drops below threshold after a process restart.

#### `booking_waitlist_rate` firing

1. High waitlist rate means sessions are at capacity — check current session `capacity` values via admin UI (`/admin/sessions`).
2. If this is expected peak demand, no action needed.  Consider increasing session capacity or adding sessions.
3. If unexpected: verify `MAX_BOOKINGS_PER_SEMESTER` has not been lowered accidentally.

#### `enrollment_gate_block_rate` firing

1. Check which parent semester hierarchy gates are being triggered: look for `event=enrollment_gate_blocked` in structured logs with `user_id` and `semester_id`.
2. Common cause: students attempting to enroll in a child semester without completing the parent.  This is expected behaviour.
3. If the rate is unexpectedly high (e.g. > 50 %), verify semester prerequisite chains are configured correctly in the admin UI.

#### `slow_queries_total` firing

See [§5 Slow Query Handling](#5-slow-query-handling).

---

## 5. Slow Query Handling

### Detection

Queries exceeding **200 ms** are automatically logged to the `app.slow_query`
logger at `WARNING` level with the structured format:

```
event=slow_query duration_ms=342.1 statement=SELECT bookings.id AS bookings_id... request_id=abc123
```

The `request_id` field allows you to correlate the slow query with the HTTP
request that triggered it in the `LoggingMiddleware` access log.

### Investigation steps

1. **Identify the query** — search logs for `event=slow_query`.  The
   `statement` field contains the first 200 characters of the SQL.

2. **Run EXPLAIN ANALYZE** — copy the full statement from the application
   source and run:
   ```sql
   EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
   SELECT ...;
   ```

3. **Check for missing indexes** — look for `Seq Scan` on large tables.
   Common targets: `bookings(session_id)`, `bookings(user_id)`,
   `sessions(semester_id)`.

4. **Check connection pool** — if many queries are slow simultaneously, the
   pool may be exhausted.  Check `pool_size` (currently 20) and
   `max_overflow` (currently 30) in `app/database.py`.

5. **Apply a new index** — create an Alembic migration:
   ```python
   op.create_index("ix_table_column", "table", ["column"])
   ```
   Then run `alembic upgrade head` on production (zero-downtime for
   `CREATE INDEX CONCURRENTLY` — add `postgresql_concurrently=True` to the
   `create_index` call).

### Threshold adjustment

If normal queries regularly exceed 200 ms (e.g. aggregate dashboards), raise
the threshold in `app/database.py`:

```python
_SLOW_QUERY_THRESHOLD_MS: float = 500.0  # adjusted for reporting workload
```

---

## 6. Migration Rollback Procedure

### Safe rollback (one step back)

```bash
# Identify current revision
alembic current

# Downgrade exactly one step
alembic downgrade -1

# Verify
alembic current
```

### Rollback to a specific revision

```bash
alembic downgrade <revision_id>
# Example:
alembic downgrade 2026_03_15_1600
```

### Emergency rollback

If a migration is not safely reversible (e.g. data-destructive `DROP COLUMN`),
restore from the pre-migration database snapshot:

```bash
pg_restore -d $DATABASE_URL --clean --if-exists backup_pre_migration.dump
```

Then redeploy the previous application version.

### Migration volume validation

The CI pipeline runs a `migration-volume-test` job that:
1. Seeds 2 000 bookings + 500 reward rows on a fresh database.
2. Runs `EXPLAIN` to validate index usage on key queries.
3. Times `downgrade -1 + upgrade head` — must complete in ≤ 30 seconds.

This ensures new migrations do not introduce unbounded table scans on
production-scale data.

### Revision history

| Revision | Date | Description |
|---|---|---|
| `2026_03_15_1500` | 2026-03-15 | Unique constraint on EventRewardLog(user_id, session_id) |
| `2026_03_15_1600` | 2026-03-15 | Five composite indexes on bookings and sessions |
| `2026_03_13_1500` | 2026-03-13 | `performed_by_user_id` on credit_transactions |
| `2026_03_13_1400` | 2026-03-13 | SKILL_TIER_REACHED notification type |
| `2026_03_12_1200` | 2026-03-12 | Drop `location.venue` |
| `2026_03_12_1100` | 2026-03-12 | Remove legacy CouponType values |
| `2026_03_12_1000` | 2026-03-12 | Drop `semester.is_active` |

---

## 7. Log Files and Retention

### Log file location

Production log files are written to `logs/app.log` in the application working
directory (typically `/app/logs/app.log` in Docker).

### Rotation policy

Logs are rotated automatically by `RotatingFileHandler`:

| Parameter | Value |
|---|---|
| Max file size | 10 MB |
| Backup count | 5 |
| Max total disk | ~60 MB |

When `app.log` reaches 10 MB it is renamed to `app.log.1`, the previous
`app.log.1` becomes `app.log.2`, and so on up to `app.log.5`.  The oldest
file is deleted when a new rotation occurs.

### Mounting logs in Docker

```yaml
# docker-compose.yml
services:
  app:
    volumes:
      - ./logs:/app/logs
```

### Log format

Application log lines use structured `key=value` format (via `app/core/structured_log.py`):

```
event=reward_awarded user_id=42 session_id=7 xp=100 multiplier=1.5 request_id=abc123 operation_id=def456
```

HTTP access logs from `LoggingMiddleware` are JSON-formatted:

```json
{"event_type": "request_complete", "request_id": "...", "method": "POST", "url": "...", "status_code": 200, "process_time_ms": 12.4}
```

### External log shipping

For production log aggregation (ELK, Loki, Datadog), ship from the file:

```yaml
# Filebeat config
filebeat.inputs:
  - type: log
    paths: ["/app/logs/app.log*"]
    fields:
      service: gancuju-education-center
      env: production
```

Or configure the application logger to emit JSON to stdout and capture it with
your container orchestrator.

---

## 8. Health Endpoints

| Endpoint | Purpose | Success response |
|---|---|---|
| `GET /health` | Basic liveness | `{"status": "healthy"}` |
| `GET /health/live` | Kubernetes liveness probe | `{"status": "alive"}` |
| `GET /health/ready` | Kubernetes readiness probe | `{"status": "ready", "database": "healthy"}` |
| `GET /health/detailed` | Full system health (DB + workers) | `{"status": "healthy", "checks": {...}}` |
| `GET /health/worker` | Redis + Celery worker health | `{"status": "degraded"|"healthy"|"unhealthy", ...}` |

A `"degraded"` worker status means Redis is reachable but no Celery workers
are registered — background tasks (email, notifications) will not execute.
This is expected in development environments without a running worker.
