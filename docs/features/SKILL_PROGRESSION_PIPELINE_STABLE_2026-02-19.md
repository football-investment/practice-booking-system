# Skill Progression Pipeline — Hardened Core Declaration

**Date:** 2026-02-19
**Status: HARDENED CORE — freeze in effect**
**Sprint:** Skill progression concurrency hardening (Phase A + B)

---

## Summary

All four actionable race conditions identified in
`SKILL_PROGRESSION_CONCURRENCY_AUDIT_2026-02-19.md` are resolved.
The skill progression pipeline is protected by two independent layers.

---

## Protection Layers

### Layer 1 — Application guards

| Race | Guard |
|---|---|
| RACE-S01 | `ORDER BY (achieved_at ASC, id ASC)` in all four history-replay queries — deterministic EMA ordering when concurrent inserts share the same `server_default=NOW()` timestamp |
| RACE-S02 | `SELECT FOR UPDATE` on `UserLicense` in `recalculate_skill_average` — serialises assessment writes with concurrent tournament Step 1.5 writes; eliminates stale-JSONB last-writer-wins overwrite |
| RACE-S03 | `_normalise_skill_entry()` helper in orchestrator — float-format entries promoted to dict before deep-merge loop; `recalculate_skill_average` writes `baseline` sub-key for dict-format entries instead of replacing with float |
| RACE-S05 | Write-once guard in `record_tournament_participation`: `if participation.skill_rating_delta is None` — prevents recomputation on retry |
| RACE-S06 | No action (acceptable — reads `baseline` field, write-once at onboarding) |

### Layer 2 — Monitoring

- `scripts/validate_skill_pipeline.py` — weekly INV-S01..S04 checks
- First run: ✅ PASSED WITH WARNINGS (0 errors, 14 pre-hardening legacy warnings — expected)

---

## Test Coverage

| Suite | Result |
|---|---|
| `tests/unit/skill/test_skill_progression_concurrency_p0.py` | **11 passed** |
| Full unit suite (`tests/unit/`) | **910 passed**, 2 skipped, 12 xfailed, 11 xpassed |

---

## Freeze Notice

This module is now **Hardened Core**.  Changes to the following files require a
new concurrency audit before merging:

- `app/services/skill_progression_service.py`
- `app/services/tournament/tournament_reward_orchestrator.py` ← also in Reward/XP freeze
- `app/services/tournament/tournament_participation_service.py` ← also in Reward/XP freeze
- `app/services/football_skill_service.py`

Phase B changes to `tournament_reward_orchestrator.py` and
`tournament_participation_service.py` have been verified against the existing
Reward/XP P0 suite (`tests/unit/reward/test_reward_concurrency_p0.py`) —
**15/15 passed, 0 regressions**.

---

## Weekly Monitoring Cadence

```bash
# Monday 09:00 UTC
0 9 * * 1 cd /path/to/project && python scripts/validate_skill_pipeline.py >> logs/skill_pipeline_weekly.log 2>&1
```

---

## Residual Risk (accepted)

| Risk | Status |
|---|---|
| `skill_rating_delta` may reflect incomplete EMA history for sibling concurrent tournaments | ACCEPTED — field is audit-only; `football_skills` write-back is authoritative and correct |
| Pre-hardening `current_level` values < 40.0 on 14 skill slots | ACCEPTED — written by older code before EMA floor was enforced; healed on next tournament finalization for the affected user |
| Float-format entry rate 32% | ACCEPTED — pre-existing assessment-only users; normalised to dict on next tournament finalization |

---

## Implementation Reference

| Fix | File | Lines |
|---|---|---|
| P1 — FOR UPDATE in assessment | `football_skill_service.py` | `recalculate_skill_average` (line ~116) |
| P2 — `_normalise_skill_entry` helper | `tournament_reward_orchestrator.py` | module-level + Step 1.5 loop |
| P3 — Stable ORDER BY | `skill_progression_service.py` | 4 history-replay queries |
| P4 — Write-once `skill_rating_delta` | `tournament_participation_service.py` | Phase 2 block (~line 265) |
