"""
Post-deploy smoke test — system_events feature

Usage (from project root):
    python scripts/validate_system_events_deploy.py

Exits 0 if all checks pass, 1 if any check fails.
Run this on every environment immediately after `alembic upgrade head`.
"""
import sys
import os

# Ensure project root is on the path so `app.*` imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

errors = []

print("=" * 60)
print("POST-DEPLOY SMOKE TEST — system_events")
print("=" * 60)

# ── 1. FK fixture user ────────────────────────────────────────
print("\n[1] FK fixture user (user_id=1)")
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id, email, role FROM users WHERE id = 1")).fetchone()
        assert row is not None, "user_id=1 does not exist — run seed script first"
        assert row[1] == "admin@lfa.com", f"unexpected email: {row[1]}"
        print(f"    OK — id={row[0]} email={row[1]} role={row[2]}")
except Exception as e:
    errors.append(f"[1] FK fixture: {e}")
    print(f"    FAIL — {e}")

# ── 2. Table schema ───────────────────────────────────────────
print("\n[2] system_events table schema")
try:
    with engine.connect() as conn:
        cols = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='system_events' ORDER BY ordinal_position"
        )).fetchall()
        expected = ["id", "created_at", "level", "event_type", "user_id", "role", "payload_json", "resolved"]
        actual = [c[0] for c in cols]
        assert actual == expected, f"column mismatch: {actual}"
        print(f"    OK — {', '.join(actual)}")
except Exception as e:
    errors.append(f"[2] Schema: {e}")
    print(f"    FAIL — {e}")

# ── 3. Critical indexes ───────────────────────────────────────
print("\n[3] Indexes")
try:
    with engine.connect() as conn:
        idxs = {r[0] for r in conn.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename='system_events'"
        )).fetchall()}
        required = {
            "ix_system_events_user_event_type_created",  # rate-limit query
            "ix_system_events_open_created",             # partial: WHERE resolved=false
            "ix_system_events_resolved",                 # filter by resolved flag
        }
        missing = required - idxs
        assert not missing, f"missing indexes: {missing}"
        print(f"    OK — {len(idxs)} total indexes, 3 critical confirmed")
except Exception as e:
    errors.append(f"[3] Indexes: {e}")
    print(f"    FAIL — {e}")

# ── 4. ENUM values ────────────────────────────────────────────
print("\n[4] systemeventlevel ENUM")
try:
    with engine.connect() as conn:
        labels = [r[0] for r in conn.execute(text(
            "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
            "WHERE t.typname='systemeventlevel' ORDER BY e.enumsortorder"
        )).fetchall()]
        assert labels == ["INFO", "WARNING", "SECURITY"], f"wrong values: {labels}"
        print(f"    OK — {labels}")
except Exception as e:
    errors.append(f"[4] ENUM: {e}")
    print(f"    FAIL — {e}")

# ── 5. Service layer: emit + rate-limit + resolve ─────────────
print("\n[5] SystemEventService — emit / rate-limit / resolve")
try:
    from sqlalchemy.orm import sessionmaker
    from app.services.system_event_service import SystemEventService
    from app.models.system_event import SystemEventLevel, SystemEventType

    db = sessionmaker(bind=engine)()
    svc = SystemEventService(db)

    e1 = svc.emit(SystemEventLevel.SECURITY, SystemEventType.MULTI_CAMPUS_BLOCKED, user_id=1)
    assert e1 is not None and e1.id is not None, "first emit returned None"

    e2 = svc.emit(SystemEventLevel.SECURITY, SystemEventType.MULTI_CAMPUS_BLOCKED, user_id=1)
    assert e2 is None, "rate-limit not working — second emit should return None"

    resolved = svc.mark_resolved(e1.id)
    assert resolved is not None and resolved.resolved is True, "mark_resolved failed"

    db.rollback()  # smoke test events are never persisted
    db.close()
    print(f"    OK — emit id={e1.id}, deduplicated, resolved=True")
except Exception as e:
    errors.append(f"[5] Service: {e}")
    print(f"    FAIL — {e}")

# ── 6. APScheduler config importable ─────────────────────────
print("\n[6] APScheduler — job function & CronTrigger importable")
try:
    from app.background.scheduler import system_events_purge_job, get_scheduler_status
    from apscheduler.triggers.cron import CronTrigger
    CronTrigger(hour=2, minute=0, timezone="UTC")  # validates config
    assert callable(system_events_purge_job)
    status = get_scheduler_status()
    assert "jobs" in status
    print(f"    OK — importable, CronTrigger valid")
    if not status["jobs"]:
        print(f"         NOTE: jobs=[] expected outside FastAPI — scheduler starts in app lifespan")
except Exception as e:
    errors.append(f"[6] APScheduler: {e}")
    print(f"    FAIL — {e}")

# ── 7. _assert_campus_scope fires SECURITY event ─────────────
print("\n[7] _assert_campus_scope → 403 + SECURITY event in DB")
try:
    from app.database import SessionLocal
    from app.api.api_v1.endpoints.tournaments.generate_sessions import _assert_campus_scope
    from fastapi import HTTPException
    from app.models.system_event import SystemEvent, SystemEventLevel
    from sqlalchemy import select

    class FakeInstructor:
        id = 1
        email = "admin@lfa.com"
        role = "INSTRUCTOR"

    db2 = SessionLocal()
    try:
        _assert_campus_scope(FakeInstructor(), [1, 2], None, db2)
        errors.append("[7] campus-scope: 403 not raised")
        print("    FAIL — expected HTTPException 403")
    except HTTPException as exc:
        assert exc.status_code == 403
        evt = db2.execute(
            select(SystemEvent)
            .where(SystemEvent.user_id == 1)
            .where(SystemEvent.level == SystemEventLevel.SECURITY)
            .order_by(SystemEvent.id.desc()).limit(1)
        ).scalar_one_or_none()
        assert evt is not None, "SECURITY event not written — SAVEPOINT may have failed"
        print(f"    OK — 403 raised, SECURITY event id={evt.id} event_type={evt.event_type}")
    finally:
        db2.rollback()
        db2.close()
except Exception as e:
    errors.append(f"[7] campus-scope: {e}")
    print(f"    FAIL — {e}")

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 60)
if errors:
    print(f"SMOKE TEST FAILED — {len(errors)} check(s) did not pass:")
    for err in errors:
        print(f"  • {err}")
    print("\nConsult OPERATIONS_RUNBOOK_SYSTEM_EVENTS.md Section 6 for remediation steps.")
    sys.exit(1)
else:
    print("SMOKE TEST PASSED — all 7 checks OK")
    print("Environment is ready to serve the system_events feature.")
print("=" * 60)
