# Scoring Pipeline Architecture

> Status: **STABLE** — P0 + P1 hardening complete (2026-02-18)
> Test coverage: 74 unit tests (51 P0 + 23 P1), all GREEN

---

## Overview

The scoring pipeline converts raw round-by-round performance data into
tournament rankings and XP rewards. It has **three separate execution
pathways** depending on tournament format.

---

## 1. Strategy Selection

```
Tournament.scoring_type (string)
        │
        ▼
RankingStrategyFactory.create(scoring_type)
  app/services/tournament/ranking/strategies/factory.py
        │
        ├─ "TIME_BASED"    → TimeBasedStrategy     (MIN/MAX of times across rounds)
        ├─ "SCORE_BASED"   → ScoreBasedStrategy    (SUM of scores, DESC)
        ├─ "ROUNDS_BASED"  → RoundsBasedStrategy   (MIN or MAX across rounds)
        ├─ "DISTANCE_BASED"→ ScoreBasedStrategy    (alias, SUM, DESC)
        └─ "PLACEMENT"     → PlacementStrategy     (SUM of placements, ASC)
                                                    ← BUG-02 fixed 2026-02-18
```

### Aggregation rules

| Strategy | Aggregation | Sort | `aggregation_method` in JSONB |
|---|---|---|---|
| TIME_BASED | MIN or MAX (direction-sensitive) | ASC (default) | `MIN_VALUE` / `MAX_VALUE` |
| SCORE_BASED | SUM | DESC | `SUM` |
| ROUNDS_BASED | MIN or MAX (direction-sensitive) | ASC (default) | `MIN_VALUE` / `MAX_VALUE` |
| DISTANCE_BASED | SUM | DESC | `SUM` |
| PLACEMENT | SUM of placements | ASC (fixed) | `SUM_PLACEMENT` |

**`ranking_direction` override** (BUG-01 fixed 2026-02-18):
- Flows: `SessionFinalizer` → `RankingService.calculate_rankings(ranking_direction=...)` → `strategy._group_by_value(direction_override=...)`
- TIME_BASED / ROUNDS_BASED respect `ranking_direction` for both aggregation AND sort
- SCORE_BASED / PLACEMENT always SUM; `ranking_direction` only overrides sort

### Tie-breaking

Same `final_value` → same rank. Next rank skips:
```
Example: 3 players, scores [50, 40, 40]
→ Rank 1: player A (50)
→ Rank 2: players B, C (40) — TIED
→ Rank 4: (skipped)
```

---

## 2. Execution Pathways

### Pathway IR — INDIVIDUAL_RANKING

```
Admin records round results
        │
        ▼
POST /tournaments/{id}/sessions/{sid}/finalize-individual-ranking
        │
        ▼
SessionFinalizer.finalize()
  app/services/tournament/results/finalization/session_finalizer.py
        │
        ├─ Idempotency Guard #1: session.game_results already set? → ValueError
        ├─ Idempotency Guard #2: TournamentRanking rows exist? → ValueError
        ├─ Validate all rounds completed (rounds_data.completed_rounds == total_rounds)
        ├─ RankingService.calculate_rankings(scoring_type, round_results, ranking_direction)
        │       └─ Strategy.calculate_rankings() → List[RankGroup]
        ├─ RankingService.convert_to_legacy_format() → performance_rankings, wins_rankings
        ├─ Write session.game_results (JSONB) — includes aggregation_method label
        ├─ update_tournament_rankings() → TournamentRanking rows + calculate_ranks()
        └─ db.commit()

                        ↑
        NO reward distribution here
        Admin must separately trigger TournamentFinalizer or rewards_v2 API
```

### Pathway H2H — HEAD_TO_HEAD / KNOCKOUT

```
Admin records match result (winner/loser)
        │
        ▼
POST /tournaments/{id}/sessions/{sid}/finalize
        │
        ▼
TournamentFinalizer.finalize()
  app/services/tournament/results/finalization/tournament_finalizer.py
        │
        ├─ check_all_matches_completed() — all sessions have game_results?
        │       └─ IR session special case: TournamentRanking rows count as complete
        ├─ update_tournament_rankings_table() — write final standings
        ├─ tournament.tournament_status = "COMPLETED"
        ├─ db.flush()
        └─ distribute_rewards_for_tournament(db, tournament_id)   ← ONLY call site #1
                app/services/tournament/tournament_reward_orchestrator.py
```

### Pathway GK — GROUP + KNOCKOUT

```
Admin records group stage results
        │
        ▼
GroupStageFinalizer.finalize()
  app/services/tournament/results/finalization/group_stage_finalizer.py
        │
        ├─ Calculate group standings (StandingsCalculator)
        ├─ Advance top-N players to knockout bracket (AdvancementCalculator)
        ├─ Seed knockout sessions
        └─ db.commit()
                        ↑
        NO reward distribution (intermediate step)

        │
        ▼ (after knockout bracket completes)

TournamentFinalizer.finalize()
  (same as Pathway H2H above)
        └─ distribute_rewards_for_tournament()   ← terminal step
```

---

## 3. Reward Distribution

```
Two legitimate call sites:

1. TournamentFinalizer.finalize()           ← automatic (all H2H + GK tournaments)
   app/.../finalization/tournament_finalizer.py:297

2. POST /tournaments/{id}/rewards           ← manual admin trigger
   app/api/api_v1/endpoints/tournaments/rewards_v2.py:80
   Requires tournament.status == "COMPLETED"
   Allows force_redistribution override
```

Any other call site for `distribute_rewards_for_tournament()` is a bug.
Verified by RP-05 in `tests/unit/tournament/test_scoring_pipeline_p1.py`.

### Reward orchestrator flow

```
distribute_rewards_for_tournament(db, tournament_id)
  app/services/tournament/tournament_reward_orchestrator.py
        │
        ├─ Load TournamentRanking rows (rank + user_id)
        ├─ Load reward policy (tournament config or default)
        ├─ Calculate XP per rank tier
        └─ Write SemesterEnrollment.xp_earned for each participant
```

---

## 4. Key Invariants

| ID | Invariant | Verified by |
|---|---|---|
| INV-01 | SessionFinalizer never distributes rewards | RP-01 |
| INV-02 | TournamentFinalizer always distributes rewards on success | RP-02 |
| INV-03 | GroupStageFinalizer never distributes rewards | RP-04 |
| INV-04 | Exactly 2 production call sites for distribute_rewards | RP-05 |
| INV-05 | SessionFinalizer is idempotent (double-finalize raises ValueError) | Guard #1, #2 |
| INV-06 | ranking_direction flows end-to-end (SessionFinalizer → Strategy) | P0 BUG-01 tests |
| INV-07 | PLACEMENT always sorts ASC regardless of ranking_direction | P0 BUG-02 tests |
| INV-08 | aggregation_method JSONB matches actual strategy used | P1 BUG-03 tests |

---

## 5. Files Reference

| Layer | File | Role |
|---|---|---|
| Strategy | `app/services/tournament/ranking/strategies/factory.py` | Factory |
| Strategy | `app/services/tournament/ranking/strategies/base.py` | ABC + `_group_by_value` |
| Strategy | `app/services/tournament/ranking/strategies/time_based.py` | MIN/MAX |
| Strategy | `app/services/tournament/ranking/strategies/score_based.py` | SUM DESC |
| Strategy | `app/services/tournament/ranking/strategies/rounds_based.py` | MIN/MAX |
| Strategy | `app/services/tournament/ranking/strategies/placement.py` | SUM ASC |
| Dispatch | `app/services/tournament/ranking/ranking_service.py` | Facade |
| Finalizer | `app/services/tournament/results/finalization/session_finalizer.py` | IR pathway |
| Finalizer | `app/services/tournament/results/finalization/tournament_finalizer.py` | H2H/GK terminal |
| Finalizer | `app/services/tournament/results/finalization/group_stage_finalizer.py` | GK group phase |
| Reward | `app/services/tournament/tournament_reward_orchestrator.py` | XP distribution |
| Support | `app/services/tournament/leaderboard_service.py` | `get_or_create_ranking`, `calculate_ranks` |

---

## 6. Known Remaining Bugs (not yet fixed)

From original audit (`docs/features/SCORING_PIPELINE_AUDIT_2026-02-18.md`):

| ID | Severity | Description |
|---|---|---|
| BUG-04 | MEDIUM | `wins_rankings` always empty (RankingService.convert_to_legacy_format) |
| BUG-05 | MEDIUM | H2H pathway bypasses RankingService entirely — uses raw win/loss counts |
| BUG-06 | LOW | GROUP_KNOCKOUT advancement uses hardcoded top-2 (ignores tournament config) |
| BUG-07 | LOW | `measurement_unit` ignored in wins_rankings legacy format |
| BUG-08 | LOW | GroupStageFinalizer: tiebreaker for equal points is undefined |
| BUG-09 | LOW | `check_all_sessions_finalized` uses `semester_id == tournament_id` (confusing alias) |
| DEBT-02 | INFO | `RankingAggregator` class still exists in codebase (only __init__ removed) |
