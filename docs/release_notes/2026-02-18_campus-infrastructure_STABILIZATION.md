# Campus Infrastructure — Stabilization Notice

**Date:** 2026-02-18
**Branch:** `feature/performance-card-option-a`
**Status:** 🔒 FROZEN — 1-sprint stabilization period

---

## Freeze Scope

The following modules are **read-only** for the duration of this sprint:

| Module | Why frozen |
|---|---|
| `app/services/tournament/session_generation/utils.py` — `pick_campus()` | Core round-robin logic; 25 tests cover all invariants |
| `app/api/api_v1/endpoints/tournaments/ops_scenario.py` — `OpsScenarioRequest.campus_ids` | Required field contract; changes would break wizard payload chain |
| `app/services/tournament/status_validator.py` — `ENROLLMENT_OPEN` gate | Lifecycle precondition; silent removal would allow venue-less tournaments |
| `streamlit_app/components/admin/ops_wizard/steps/step3_h2h.py` — `_render_campus_selector()` | Shared UI helper; also used by step3_individual |
| All format generators — `campus_id` assignment via `pick_campus()` | Session distribution; any change requires coordinated test update |

**Exception process:** A freeze override requires a comment in this file with date, author, and rationale before the commit.

---

## Production Monitoring

Run weekly during the stabilization period:

```bash
python scripts/validate_campus_distribution.py --since-days 7
```

Expected output:
- ✅ 0 sessions missing `campus_id` (post-refactor)
- Per-campus distribution table (skew alert if any campus > 60%)
- 0 campus-related OPS errors in `system_events`

Alert threshold: any `❌ FAILED` exit code triggers immediate review of the campus pipeline.

---

## What Was Hardened (Summary)

| Layer | Change | Test |
|---|---|---|
| Schema | `OpsScenarioRequest.campus_ids` required (min 1) | OPS-1, OPS-1b |
| Validation | Active campus check (422 on invalid IDs) | OPS-2, OPS-2b |
| Lifecycle | `ENROLLMENT_OPEN` blocked without `campus_id` | SV-01 → SV-03 |
| Generation | `pick_campus()` round-robin for all 5 format generators | L-01 → BC-01, K-01 → BC-01, S-01 → BC-02, IR-01 |
| Wizard | Step 3 location→campus cascade selector, payload chain | Manual QA |

Reference: [CAMPUS_INFRASTRUCTURE_2026-02-18.md](../features/CAMPUS_INFRASTRUCTURE_2026-02-18.md)

---

## Next Audit Target: Scoring Pipeline

**Decision date:** 2026-02-18
**Rationale:** Campus refactor is stable; scoring pipeline is the highest-risk unaudited area.

### Scope

| File | Lines | Risk |
|---|---|---|
| `app/services/tournament/results/finalization/session_finalizer.py` | 351 | XP assignment per session result |
| `app/services/tournament/results/finalization/tournament_finalizer.py` | 329 | Final XP flush + badge triggers |
| `app/services/tournament/results/calculators/ranking_aggregator.py` | 276 | Multi-round aggregation logic |
| `app/services/tournament/results/finalization/group_stage_finalizer.py` | 216 | Group → knockout advancement |
| `app/services/tournament/results/calculators/standings_calculator.py` | 187 | League point table |
| `app/services/tournament/results/validators/result_validator.py` | 133 | Input guard |
| `app/services/tournament/results/calculators/advancement_calculator.py` | 164 | Bracket seeding after groups |
| **Total** | **~1 740 L** | |

### Audit Objectives

1. **Correctness:** Does `ranking_aggregator.py` handle `ROUNDS_BASED` multi-round scoring correctly? Does it respect `ranking_direction` (ASC vs DESC)?
2. **Coupling:** Is `session_finalizer` → `tournament_finalizer` a clean handoff, or are there hidden state mutations?
3. **Coverage:** What is the unit test coverage of these 7 files? Are edge cases (ties, forfeit, partial results) covered?
4. **XP distribution:** Does the reward orchestrator receive correct ranked player lists from the finalizer chain?

### Suggested First Step

```bash
python -m pytest tests/unit/tournament/ -k "finaliz or scoring or ranking or result" -v --tb=short
```

Identify untested paths → prioritize for new unit tests before any refactoring.

---

## Timeline

| Date | Event |
|---|---|
| 2026-02-18 | Campus infrastructure frozen; stabilization starts |
| 2026-02-18 + 1 week | First `validate_campus_distribution.py` run |
| Sprint end | Freeze lifted; scoring pipeline audit begins |
