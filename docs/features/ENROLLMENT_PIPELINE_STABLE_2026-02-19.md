# Enrollment Pipeline — Hardened Core Declaration

**Date:** 2026-02-19
**Status: HARDENED CORE — freeze + monitor**

---

## What "Hardened Core" means

The enrollment pipeline has passed a full concurrency audit + hardening sprint:
1. **Phase A — Read-only race map audit** (2026-02-18): identified 4 TOCTOU race conditions
2. **Phase B — DB-level concurrency guards** (commit `ce53c11`): B-01/02/03/04 implemented
3. **RACE-04 fix** (commit `4f3b2f6`): unenroll double-refund eliminated
4. **Formal closure + monitoring** (commit `f47e098`): invariant script + release note

"Hardened Core" means:
- All 4 TOCTOU race conditions are **closed** with 3-layer protection
- Every critical code path has dedicated unit tests (29 unit + 17 DB integration)
- Production refactoring requires a new audit sprint — not ad-hoc changes
- Changes to hardened modules need a test-first approach (RED → GREEN)

---

## Covered and hardened modules

| Module | Tests | Status |
|---|---|---|
| `app/api/api_v1/endpoints/tournaments/enroll.py` | 22 unit + 17 DB | ✅ HARDENED |
| `app/services/tournament/enrollment_service.py` | P0 concurrency | ✅ HARDENED |
| `alembic/versions/2026_02_18_1000-eb01_enrollment_concurrency_guards.py` | migration applied | ✅ HARDENED |

---

## Three-layer protection summary

| Layer | Mechanism | Covers |
|---|---|---|
| **Application** | `SELECT FOR UPDATE` (B-03, RACE-04) | Capacity check + unenroll serialization |
| **Application** | Atomic `SQL UPDATE` with rowcount guard (B-02, RACE-04) | Credit deduction + refund |
| **Application** | `IntegrityError` → HTTP 409 (B-01) | Duplicate enroll detection |
| **DB constraint** | `uq_active_enrollment` partial unique index | Duplicate active enrollment |
| **DB constraint** | `chk_credit_balance_non_negative` CHECK | Negative credit floor |
| **Monitoring** | `scripts/validate_enrollment_pipeline.py` INV-01…INV-05 | Weekly invariant checks |

---

## Race condition register (all closed)

| ID | Description | Fix | Status |
|---|---|---|---|
| RACE-01 | Capacity TOCTOU (concurrent enroll bypasses max_players) | SELECT FOR UPDATE on semester row (B-03) | ✅ Closed |
| RACE-02 | Duplicate active enroll (same player twice) | `uq_active_enrollment` partial unique index (B-01) + IntegrityError → 409 | ✅ Closed |
| RACE-03 | Credit deduction TOCTOU (two threads both see sufficient balance) | Atomic SQL UPDATE + rowcount guard (B-02) | ✅ Closed |
| RACE-04 | Unenroll double-refund (two concurrent unenroll requests) | FOR UPDATE on enrollment row + atomic SQL refund | ✅ Closed |

---

## Total test coverage (enrollment pipeline)

| Suite | Tests | Runtime |
|---|---|---|
| P0 concurrency (mock) | 17 | ~0.2s |
| Phase B unit (mock) | 22 | ~0.3s |
| DB integration (PostgreSQL) | 17 (1 skipped) | ~2s |
| **Total** | **56** | **~2.5s** |

---

## Open bugs (tracked, not blocking hardened status)

None. All known TOCTOU risks are resolved.

INV-04 baseline: 20 batch-seeded enrollments without `credit_transaction` audit rows — pre-existing data, non-critical, documented in release note.

---

## Monitoring cadence

| Script | Frequency | Alert condition |
|---|---|---|
| `scripts/validate_enrollment_pipeline.py` | Weekly (Monday 08:00) | Exit code 1 (any ERROR) |
| INV-01: duplicate active enrollments | weekly | count > 0 |
| INV-02: negative credit balances | weekly | count > 0 |
| INV-03: WITHDRAWN zombie rows | weekly | count > 0 |
| INV-04: missing audit trail | weekly | count > 50 (allow baseline 20) |
| INV-05: migration constraints live | weekly | constraint missing |

---

## Freeze notice

The following modules are FROZEN until the next dedicated audit sprint:

```
app/api/api_v1/endpoints/tournaments/enroll.py  ← enrollment concurrency
app/services/tournament/enrollment_service.py   ← enrollment service layer
```

**Rule:** Any PR touching these files must include a failing test first,
then the fix. No refactoring without a corresponding test proving the
current behavior is preserved.

---

## Next high-risk area: Booking Pipeline

**Decision: Booking pipeline audit (session conflicts + double-booking)**

### Why booking pipeline?

Session conflict and double-booking are higher financial and reputational risk:
- A double-booked session slot creates immediate operational conflict (two players, one physical slot)
- Credit implications are real-money adjacent in production
- TOCTOU patterns are expected to mirror the enrollment pipeline

### Sprint sequence (same methodology)

| Phase | Deliverable |
|---|---|
| A | Read-only race map: `BOOKING_CONCURRENCY_AUDIT_2026-02-19.md` |
| B | P0 test hardening: document races as failing tests |
| C | DB-level guards where needed |
| D | `scripts/validate_booking_pipeline.py` invariant monitor |

### Deferred (after booking sprint)

- **Reward/XP pipeline** — lower operational risk, deferred

---

## Commit history (this hardening sprint)

| Commit | Description |
|---|---|
| `18891f8` | fix(state-machine): SM-BUG-01 P2 + enrollment P0 tests (17 tests) |
| `ce53c11` | feat(enrollment): Phase B — B-01/02/03/04 + 29 tests |
| `4f3b2f6` | fix(enrollment): RACE-04 + 10 tests |
| `f47e098` | docs(enrollment): formal closure + release note + weekly monitor |
