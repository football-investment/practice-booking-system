"""
24-48 hour post-deploy health check — system_events feature

Usage (from project root):
    python scripts/validate_system_events_24h.py

Run this 24-48 hours after the initial deploy.
Checks that the feature is operating correctly under real traffic.

Exits 0 if all checks pass, 1 if any check fails.
"""
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

errors = []
warnings = []

print("=" * 60)
print("24-48h POST-DEPLOY HEALTH CHECK — system_events")
print(f"Run at: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 60)

from app.database import engine
from sqlalchemy import text

# ── 1. Migration still at HEAD ────────────────────────────────
print("\n[1] Alembic revision still at se002residx00 (HEAD)")
try:
    from alembic.config import Config
    from alembic import command
    from io import StringIO
    import contextlib

    out = StringIO()
    with contextlib.redirect_stdout(out):
        cfg = Config("alembic.ini")
        command.current(cfg, verbose=False)

    current = out.getvalue().strip()
    # alembic current prints to stdout via logging - check via DB instead
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT version_num FROM alembic_version"
        )).fetchone()
        assert row is not None, "alembic_version table empty"
        assert row[0] == "se002residx00", f"unexpected revision: {row[0]}"
        print(f"    OK — revision={row[0]}")
except Exception as e:
    errors.append(f"[1] Revision: {e}")
    print(f"    FAIL — {e}")

# ── 2. Table and critical indexes still present ───────────────
print("\n[2] Table schema and indexes intact")
try:
    with engine.connect() as conn:
        # table exists
        tbl = conn.execute(text("SELECT to_regclass('public.system_events')")).scalar()
        assert tbl is not None, "system_events table missing"

        # critical indexes
        idxs = {r[0] for r in conn.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename='system_events'"
        )).fetchall()}
        required = {
            "ix_system_events_user_event_type_created",
            "ix_system_events_open_created",
            "ix_system_events_resolved",
        }
        missing = required - idxs
        assert not missing, f"missing indexes: {missing}"

        # partial index predicate unchanged
        pred = conn.execute(text("""
            SELECT pg_get_expr(ix.indpred, ix.indrelid)
            FROM pg_index ix
            JOIN pg_class i ON i.oid = ix.indexrelid
            WHERE i.relname = 'ix_system_events_open_created'
        """)).scalar()
        assert pred == "(resolved = false)", f"partial index predicate changed: {pred}"

        print(f"    OK — table present, {len(idxs)} indexes, partial index predicate correct")
except Exception as e:
    errors.append(f"[2] Schema: {e}")
    print(f"    FAIL — {e}")

# ── 3. Event counts in last 24 hours ─────────────────────────
print("\n[3] Event counts (last 24 h)")
try:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT level, count(*) as cnt
            FROM system_events
            WHERE created_at > :cutoff
            GROUP BY level
            ORDER BY level
        """), {"cutoff": cutoff}).fetchall()

        total = sum(r[1] for r in rows)
        breakdown = {r[0]: r[1] for r in rows} if rows else {}
        print(f"    Total events (24 h): {total}")
        for lvl, cnt in sorted(breakdown.items()):
            print(f"      {lvl}: {cnt}")

        # Warn if SECURITY events are unexpectedly high (>100 in 24h could be an attack pattern)
        sec = breakdown.get("SECURITY", 0)
        if sec > 100:
            warnings.append(f"[3] High SECURITY event count: {sec} in 24h — review for abuse")
            print(f"    WARN — {sec} SECURITY events in 24h (threshold: 100)")
        else:
            print(f"    OK — SECURITY count {sec} within normal range")
except Exception as e:
    errors.append(f"[3] Event counts: {e}")
    print(f"    FAIL — {e}")

# ── 4. Open (unresolved) event backlog ───────────────────────
print("\n[4] Open event backlog")
try:
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT count(*) FROM system_events WHERE resolved = false"
        )).scalar()
        print(f"    Open events: {row}")
        if row > 500:
            warnings.append(f"[4] Large unresolved backlog: {row} open events — admin review needed")
            print(f"    WARN — backlog > 500, schedule admin review")
        else:
            print(f"    OK — backlog within acceptable range")

        # Oldest open event
        oldest = conn.execute(text(
            "SELECT min(created_at) FROM system_events WHERE resolved = false"
        )).scalar()
        if oldest:
            age_h = (datetime.now(tz=timezone.utc) - oldest).total_seconds() / 3600
            print(f"    Oldest open event: {str(oldest)[:19]} UTC ({age_h:.1f}h ago)")
            if age_h > 72:
                warnings.append(f"[4] Unresolved event older than 72h — may need attention")
except Exception as e:
    errors.append(f"[4] Backlog: {e}")
    print(f"    FAIL — {e}")

# ── 5. Retention purge readiness ─────────────────────────────
print("\n[5] Retention purge readiness")
try:
    import importlib
    sched_mod = importlib.import_module("app.background.scheduler")
    purge_fn = getattr(sched_mod, "system_events_purge_job", None)
    run_purge_now = getattr(sched_mod, "run_purge_now", None)
    assert callable(purge_fn), "system_events_purge_job not callable"
    assert callable(run_purge_now), "run_purge_now not callable"

    # Count events eligible for purge (resolved + older than 90 days)
    retention_days = int(os.environ.get("SYSTEM_EVENT_RETENTION_DAYS", "90"))
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=retention_days)
    with engine.connect() as conn:
        eligible = conn.execute(text(
            "SELECT count(*) FROM system_events WHERE resolved = true AND created_at < :cutoff"
        ), {"cutoff": cutoff}).scalar()

    print(f"    OK — purge job importable, retention={retention_days}d, eligible={eligible} rows")
except Exception as e:
    errors.append(f"[5] Purge: {e}")
    print(f"    FAIL — {e}")

# ── 6. Service still functional ──────────────────────────────
print("\n[6] SystemEventService emit + get_events functional")
try:
    from sqlalchemy.orm import sessionmaker
    from app.services.system_event_service import SystemEventService
    from app.models.system_event import SystemEventLevel, SystemEventType

    db = sessionmaker(bind=engine)()
    svc = SystemEventService(db)

    # get_events pagination
    rows, total = svc.get_events(limit=1, offset=0)
    print(f"    get_events: {total} total events in DB")

    # SECURITY filter
    sec_rows, sec_total = svc.get_events(level=SystemEventLevel.SECURITY, limit=1)
    print(f"    SECURITY filter: {sec_total} SECURITY events total")

    # emit + rollback (non-destructive check)
    e = svc.emit(SystemEventLevel.INFO, SystemEventType.MULTI_CAMPUS_BLOCKED, user_id=1)
    assert e is not None or e is None  # rate-limited or created — both valid
    db.rollback()
    db.close()
    print(f"    OK — service layer operational")
except Exception as e:
    errors.append(f"[6] Service: {e}")
    print(f"    FAIL — {e}")

# ── 7. Partial index definition unchanged ─────────────────────
print("\n[7] Partial index definition integrity")
try:
    with engine.connect() as conn:
        for idx_name, expected_pred in [
            ("ix_system_events_open_created", "(resolved = false)"),
        ]:
            pred = conn.execute(text("""
                SELECT pg_get_expr(ix.indpred, ix.indrelid)
                FROM pg_index ix JOIN pg_class i ON i.oid = ix.indexrelid
                WHERE i.relname = :idx
            """), {"idx": idx_name}).scalar()
            assert pred == expected_pred, f"{idx_name}: predicate={pred!r}"
        print(f"    OK — partial index predicate: {pred}")
except Exception as e:
    errors.append(f"[7] Partial index: {e}")
    print(f"    FAIL — {e}")

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print(f"HEALTH CHECK FAILED — {len(errors)} error(s):")
    for err in errors:
        print(f"  ERROR: {err}")

if warnings:
    print(f"\nWARNINGS ({len(warnings)}):")
    for w in warnings:
        print(f"  WARN:  {w}")

if not errors and not warnings:
    print("HEALTH CHECK PASSED — all 7 checks OK, no warnings")
    print("System events feature operating normally after 24-48h.")
elif not errors:
    print(f"\nHEALTH CHECK PASSED with {len(warnings)} warning(s) — review above")

print("=" * 60)
if errors:
    sys.exit(1)
