# Release Note — Enrollment Concurrency Hardening

**Date:** 2026-02-18
**Branch:** `feature/performance-card-option-a`
**Commits:** `ce53c11` (Phase B), `4f3b2f6` (RACE-04)
**Alembic migration:** `eb01concurr00` — **must run before deploy**
**Risk level:** LOW (additive DB constraints, no schema column changes)

---

## Summary

Full race condition hardening of the tournament enrollment pipeline.
Four TOCTOU races (identified in audit 2026-02-18) are now closed at both
the application layer and the DB layer.

---

## Changes

### DB-level (migration `eb01concurr00`)

| Change | Type | Effect |
|---|---|---|
| `uq_active_enrollment` partial unique index | `CREATE UNIQUE INDEX` on `semester_enrollments` | Blocks duplicate active enrollments at DB level |
| `chk_credit_balance_non_negative` | `CHECK` constraint on `users` | Rejects negative credit balances at DB level |

### Application-layer (`enroll.py`)

| Change | Endpoint | Effect |
|---|---|---|
| `SELECT FOR UPDATE` on tournament row | `POST /{id}/enroll` | Serializes concurrent capacity checks (RACE-01) |
| Atomic `UPDATE ... WHERE credit_balance >= cost` | `POST /{id}/enroll` | Eliminates credit double-spend window (RACE-03) |
| `IntegrityError` → HTTP 409 handler | `POST /{id}/enroll` | Safe response for concurrent duplicate requests (RACE-02) |
| `SELECT FOR UPDATE` on enrollment row | `DELETE /{id}/unenroll` | Serializes concurrent unenroll requests (RACE-04) |
| Atomic `UPDATE credit_balance + refund` | `DELETE /{id}/unenroll` | Defense-in-depth for refund atomicity (RACE-04) |

---

## Deploy Checklist

```
□ 1. Apply migration
      alembic upgrade head
      # Verifies: uq_active_enrollment index + chk_credit_balance_non_negative constraint

□ 2. Verify constraints live
      python scripts/validate_enrollment_pipeline.py
      # All 5 invariants must be GREEN (exit code 0)
      # INV-04 warnings for batch-seeded enrollments are expected and non-critical

□ 3. Restart application server
      # No code config changes required

□ 4. Run smoke test (enrollment + unenroll via UI)
      # Verify HTTP 200 on enroll, HTTP 200 on unenroll, balance updates correctly

□ 5. Run campus distribution check (existing monitor)
      python scripts/validate_campus_distribution.py
      # Must still pass — campus logic unaffected by this change
```

---

## Rollback

If rollback is required after deploy:

```bash
# 1. Revert application code
git revert ce53c11 4f3b2f6

# 2. Revert migration (removes index + CHECK constraint)
alembic downgrade -1

# ⚠️  NOTE: downgrade removes safety constraints — revert should be followed
#    immediately by a hotfix. Do NOT run without monitoring coverage.
```

---

## Monitoring Instructions (weekly)

Run the following scripts every Monday at 08:00 UTC (add to cron or CI schedule):

```bash
# Enrollment pipeline integrity (all 5 invariants)
python scripts/validate_enrollment_pipeline.py --since-days 7
# Expected output: ✅ ALL CHECKS PASSED
# INV-04 warnings for batch-created enrollments are normal — not errors

# Campus distribution check (existing — unchanged)
python scripts/validate_campus_distribution.py --since-days 7
# Expected output: ✅ All sessions have campus_id populated

# System events pipeline (existing — unchanged)
python scripts/validate_system_events_24h.py
# Expected output: ✅ No unresolved critical events in last 24h
```

**Alert conditions (escalate immediately):**
- `validate_enrollment_pipeline.py` exits 1 → duplicate enrollments or negative balances found
- `validate_campus_distribution.py` exits 1 → campus logic regression
- Any `ERROR:` line in enrollment pipeline output

**INV-04 known baseline (non-alerting):**
The 64 enrollments in semester_id=5782 created via `enrollment_service.py` batch
(2026-02-18 seeding) do not have `credit_transactions` rows — this is expected
because the batch helper bypasses the HTTP endpoint's credit audit trail.
All future enrollments via the HTTP endpoint will have matching transaction rows.

---

## Test Coverage

| File | Tests | Result |
|---|---|---|
| `tests/unit/tournament/test_enrollment_concurrency_p0.py` | 17 (P0 race documentation) | ✅ GREEN |
| `tests/unit/tournament/test_enrollment_phase_b_unit.py` | 22 (application-layer) | ✅ GREEN |
| `tests/database/test_enrollment_db_constraints.py` | 17 PostgreSQL integration | ✅ GREEN (1 skipped) |
| Full unit suite | 697 | ✅ 0 failed |

---

## Race Condition Register — Final State

| Race | Description | Fix | Status |
|---|---|---|---|
| RACE-01 | Capacity over-enrollment | `SELECT FOR UPDATE` on tournament row | ✅ Closed |
| RACE-02 | Duplicate active enrollment | `uq_active_enrollment` partial index | ✅ Closed |
| RACE-03 | Credit balance double-spend | Atomic SQL UPDATE + `CHECK >= 0` | ✅ Closed |
| RACE-04 | Unenroll double-refund | `SELECT FOR UPDATE` on enrollment row | ✅ Closed |

**All known enrollment pipeline concurrency risks are closed as of 2026-02-18.**

---

## Related Documents

- Full audit: `docs/features/ENROLLMENT_CONCURRENCY_AUDIT_2026-02-18.md`
- State machine architecture (stable): `docs/features/STATE_MACHINE_ARCHITECTURE.md`
- Campus scope model: `docs/features/CAMPUS_SCOPE_MODEL.md`
