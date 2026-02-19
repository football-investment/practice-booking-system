# Reward/XP Pipeline — Hardened Core Declaration

**Date:** 2026-02-19
**Status: HARDENED CORE — freeze in effect**
**Sprint:** Reward/XP concurrency hardening (Phase A + B + C + D)

---

## Summary

All seven TOCTOU race conditions identified in `REWARD_XP_CONCURRENCY_AUDIT_2026-02-19.md`
are resolved. The reward/XP distribution pipeline is now protected by three independent layers.

---

## Protection Layers

### Layer 1 — Application guards

| Race | Guard |
|---|---|
| R01/R03 | `SELECT FOR UPDATE` on `Semester` row at start of `finalize()` + idempotency gate on `tournament_status` |
| R02 | `SELECT FOR UPDATE` on `TournamentParticipation` in `distribute_rewards_for_user()` |
| R02 | `IntegrityError` at commit → `db.rollback()` + `get_user_reward_summary()` (graceful 409 semantics) |
| R04 | `SELECT FOR UPDATE` on `UserLicense` before JSONB `football_skills` merge |
| R05 | `db.begin_nested()` SAVEPOINT in `award_badge()` → `IntegrityError` → rollback savepoint → re-query existing badge |
| R06 | `idempotency_key` set on `XPTransaction` + SAVEPOINT around insert |
| R06 | Credit `idempotency_key` already present; SAVEPOINT added to handle concurrent IntegrityError gracefully |
| R07 | Atomic `UPDATE users SET xp_balance = xp_balance + :delta RETURNING xp_balance` |
| R07 | Atomic `UPDATE users SET credit_balance = credit_balance + :delta RETURNING credit_balance` |

### Layer 2 — DB constraints (migration `rw01concurr00`)

| Constraint | Table | Race |
|---|---|---|
| `uq_user_semester_participation` | `tournament_participations` | R01/R02 (pre-existing, now paired with FOR UPDATE) |
| `uq_user_tournament_badge` | `tournament_badges` | R05 |
| `uq_xp_transaction_idempotency` | `xp_transactions` | R06 |
| `xp_transactions.idempotency_key` | column (nullable) | R06 |
| `credit_transactions.idempotency_key` | pre-existing UNIQUE | R06 |

### Layer 3 — Monitoring

- `scripts/validate_reward_pipeline.py` — weekly INV-R01…R06 checks
- First run: ✅ ALL CHECKS PASSED (2026-02-19 07:55:43 UTC)

---

## Test Coverage

| Suite | Result |
|---|---|
| `tests/unit/reward/test_reward_concurrency_p0.py` | **15 passed** |
| Full unit suite (`tests/unit/`) | **899 passed**, 2 skipped, 12 xfailed, 11 xpassed |

---

## Freeze Notice

This module is now **Hardened Core**. Changes to the following files require a
new concurrency audit before merging:

- `app/services/tournament/results/finalization/tournament_finalizer.py`
- `app/services/tournament/tournament_reward_orchestrator.py`
- `app/services/tournament/tournament_badge_service.py`
- `app/services/tournament/tournament_participation_service.py`
- `app/models/tournament_achievement.py`
- `app/models/xp_transaction.py`

---

## Weekly Monitoring Cadence

```bash
# Monday 09:00 UTC
0 9 * * 1 cd /path/to/project && python scripts/validate_reward_pipeline.py >> logs/reward_pipeline_weekly.log 2>&1
```

---

## Next Audit Target

`app/services/skill_progression_service.py` — EMA delta computation reads all
`TournamentParticipation` rows per user; write-back races with the orchestrator's
skill write-back (RACE-R04 cascade not fully closed at the skill service layer).
