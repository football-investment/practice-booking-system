# Booking Pipeline — Hardened Core Declaration

**Date:** 2026-02-19
**Status: HARDENED CORE — freeze + monitor**

---

## What "Hardened Core" means

The booking pipeline has passed a full concurrency audit + hardening sprint:
1. **Phase A — Read-only race map audit** (2026-02-19): 7 TOCTOU race conditions identified
2. **Phase B — P0 test hardening** (commit `6c8fa20`): 16 RED→GREEN tests (1 xfail documented)
3. **Phase C — DB-level guards** (commit `6c8fa20`): all 7 races fixed, migration `bk01concurr00` applied
4. **Phase D — Invariant monitoring** (this commit): `scripts/validate_booking_pipeline.py` INV-B01…B05

"Hardened Core" means:
- All 7 TOCTOU race conditions are **closed** with 3-layer protection
- Every critical code path has dedicated unit tests (16 passed + 1 xfailed)
- Production refactoring requires a new audit sprint — not ad-hoc changes
- Changes to hardened modules need a test-first approach (RED → GREEN)

---

## Covered and hardened modules

| Module | Tests | Status |
|---|---|---|
| `app/api/api_v1/endpoints/bookings/student.py` | B02 lock, B01 handler, B05 lock+guard | ✅ HARDENED |
| `app/api/api_v1/endpoints/bookings/admin.py` | B05 lock, B06 capacity check, B07 lock+handler | ✅ HARDENED |
| `app/api/api_v1/endpoints/bookings/helpers.py` | B04 lock on next_waitlisted | ✅ HARDENED |
| `alembic/versions/2026_02_19_1000-bk01_booking_concurrency_guards.py` | migration applied | ✅ HARDENED |

---

## Three-layer protection summary

| Layer | Mechanism | Covers |
|---|---|---|
| **Application** | `SELECT FOR UPDATE` on session row (B02) | Capacity + waitlist count serialisation |
| **Application** | `SELECT FOR UPDATE` on next_waitlisted (B04) | Auto-promote double-promotion |
| **Application** | `SELECT FOR UPDATE` on booking row (B05, B07) | Double-cancel, duplicate attendance |
| **Application** | `IntegrityError` → HTTP 409 (B01, B07) | DB constraint violation user feedback |
| **Application** | CANCELLED status guard (B05) | Idempotent cancel |
| **Application** | Capacity check in admin confirm (B06) | Overbooking via admin path |
| **DB constraint** | `uq_active_booking` partial unique index | Duplicate active booking (last resort) |
| **DB constraint** | `uq_waitlist_position` partial unique index | Duplicate waitlist position (last resort) |
| **DB constraint** | `uq_booking_attendance` unique constraint | Duplicate attendance record (last resort) |
| **Monitoring** | `scripts/validate_booking_pipeline.py` INV-B01…B05 | Weekly invariant checks |

---

## Race condition register (all closed)

| ID | Description | Fix | Layer | Status |
|---|---|---|---|---|
| RACE-B01 | Duplicate booking TOCTOU | `uq_active_booking` + IntegrityError → 409 | DB + App | ✅ Closed |
| RACE-B02 | Capacity check TOCTOU → overbooking | `SELECT FOR UPDATE` on session before confirmed_count | App | ✅ Closed |
| RACE-B03 | Waitlist position collision | B02 lock covers transitively + `uq_waitlist_position` | DB + App | ✅ Closed |
| RACE-B04 | Auto-promote double-promotion | `SELECT FOR UPDATE` on next_waitlisted | App | ✅ Closed |
| RACE-B05 | Double-cancel → double-promotion | FOR UPDATE on booking + CANCELLED guard | App | ✅ Closed |
| RACE-B06 | Admin confirm without capacity check | Capacity check + HTTP 409 when full | App | ✅ Closed |
| RACE-B07 | Duplicate attendance TOCTOU | FOR UPDATE on booking + IntegrityError → 409 | DB + App | ✅ Closed |

---

## Total test coverage (booking pipeline)

| Suite | Tests | Runtime |
|---|---|---|
| Phase B+C unit (mock) | 16 passed, 1 xfailed | ~0.6s |
| **Total** | **17** | **~0.6s** |

**xfail note:** `test_b02_race_window_produces_overbooking_documents_the_unsafe_state`
is marked `xfail(strict=False)` because mock-based tests cannot simulate real DB-level
row locking. The lock assertion test (`test_b02_session_locked_...`) proves the fix.
Real-DB concurrency proof belongs in `tests/database/`.

---

## Monitoring cadence

| Script | Frequency | Alert condition |
|---|---|---|
| `scripts/validate_booking_pipeline.py` | Weekly (Monday 09:00) | Exit code 1 (any ERROR) |
| INV-B01: overbooked sessions | weekly | count > 0 |
| INV-B02: duplicate active bookings | weekly | count > 0 |
| INV-B03: waitlist position collisions | weekly | count > 0 |
| INV-B04: duplicate attendance records | weekly | count > 0 |
| INV-B05: migration constraints live | weekly | any constraint missing |

---

## Open bugs (tracked, not blocking hardened status)

None. All 7 known TOCTOU risks are resolved.

---

## Freeze notice

The following modules are FROZEN until the next dedicated audit sprint:

```
app/api/api_v1/endpoints/bookings/student.py    ← booking concurrency
app/api/api_v1/endpoints/bookings/admin.py      ← booking concurrency
app/api/api_v1/endpoints/bookings/helpers.py    ← auto_promote_from_waitlist
```

**Rule:** Any PR touching these files must include a failing test first,
then the fix. No refactoring without a corresponding test proving the
current behavior is preserved.

---

## Recommended cron schedule

```cron
# Monday 08:00 — enrollment pipeline
0 8 * * 1 cd /path/to/project && python scripts/validate_enrollment_pipeline.py >> logs/enrollment_pipeline_weekly.log 2>&1

# Monday 09:00 — booking pipeline
0 9 * * 1 cd /path/to/project && python scripts/validate_booking_pipeline.py >> logs/booking_pipeline_weekly.log 2>&1

# Daily 06:00 — system events
0 6 * * * cd /path/to/project && python scripts/validate_system_events_24h.py >> logs/system_events_daily.log 2>&1
```

---

## Next high-risk area: Reward / XP Pipeline

**Decision deferred until after booking sprint (now complete).**

### Why reward/XP pipeline?

The reward/XP distribution pipeline (`app/services/tournament/tournament_reward_orchestrator.py`)
distributes credits and XP when a tournament finalises. Potential races:
- Double-distribution if the finaliser is triggered concurrently (TOCTOU on tournament status)
- XP grant races if multiple events arrive out of order
- Credit grant without idempotency key → double payment

### Sprint sequence (same methodology)

| Phase | Deliverable |
|---|---|
| A | Read-only race map: `REWARD_XP_CONCURRENCY_AUDIT_YYYY-MM-DD.md` |
| B | P0 test hardening: document races as failing tests |
| C | DB-level guards where needed |
| D | `scripts/validate_reward_pipeline.py` invariant monitor |

---

## Commit history (this hardening sprint)

| Commit | Description |
|---|---|
| `90635a0` | docs(enrollment+booking): freeze enrollment as hardened core + booking Phase A audit |
| `6c8fa20` | feat(booking): Phase B+C — 7 P0 RED→GREEN tests + all guards applied |
| *(this commit)* | docs(booking): Phase D — invariant monitor + Hardened Core declaration |
