# Scoring Pipeline — Read-Only Audit Report

**Date:** 2026-02-18
**Branch:** `feature/performance-card-option-a`
**Scope:** Read-only audit — no code changes. Documentation of execution graph, coverage gaps, and decision point risks before refactoring.
**Status:** 🔍 AUDIT COMPLETE — refactoring NOT yet started

---

## 1. Dependency Map — Execution Graph

### 1a. INDIVIDUAL_RANKING path (session-level finalization)

```
ResultSubmission endpoint  (app/api/api_v1/endpoints/tournaments/results/submission.py)
  │
  ├── round result recorded → session.rounds_data updated
  │
  └── "finalize session" trigger
        │
        └── SessionFinalizer.finalize()               [session_finalizer.py:130]
              │
              ├── IDEMPOTENCY GUARD #1: session.game_results not None → ValueError
              ├── IDEMPOTENCY GUARD #2: TournamentRanking rows exist → ValueError
              ├── format check: session.match_format == "INDIVIDUAL_RANKING"
              ├── validate_all_rounds_completed()     [line 47]
              │
              ├── reads: tournament.ranking_direction (line 235)  ← ⚠️ READ BUT NOT FORWARDED
              ├── reads: tournament.scoring_type      (line 236)
              ├── reads: tournament.measurement_unit  (line 237)
              │
              ├── RankingService.calculate_rankings(             [ranking_service.py:30]
              │       scoring_type=scoring_type,                 ← ranking_direction NOT passed
              │       round_results=round_results,
              │       participants=participants
              │   )
              │       │
              │       └── RankingStrategyFactory.create(scoring_type)  [strategies/factory.py]
              │               │
              │               ├── "TIME_BASED"      → TimeBasedStrategy  (ASC, MIN)
              │               ├── "SCORE_BASED"     → ScoreBasedStrategy (DESC, SUM)
              │               ├── "ROUNDS_BASED"    → RoundsBasedStrategy (DESC, MAX)  ← ⚠️ always DESC
              │               ├── "DISTANCE_BASED"  → ScoreBasedStrategy (DESC, SUM)   ← ⚠️ same as SCORE_BASED
              │               └── "PLACEMENT"       → ScoreBasedStrategy (DESC, SUM)   ← ⚠️ WRONG: placement needs ASC
              │
              ├── RankingService.convert_to_legacy_format()  → performance_rankings, wins_rankings=[]
              │
              ├── saves game_results JSONB:
              │       aggregation_method: "BEST_VALUE"  ← ⚠️ HARDCODED — wrong for SCORE_BASED (SUM) and TIME_BASED (MIN)
              │
              ├── SessionFinalizer.update_tournament_rankings()  [line 71]
              │       ├── get_or_create_ranking() per player
              │       ├── ranking.points = Decimal(final_value)
              │       └── calculate_ranks(db, tournament_id)     [leaderboard_service.py]
              │
              └── check_all_sessions_finalized()  [line 103]
                      └── returns True/False — does NOT auto-trigger TournamentFinalizer
```

### 1b. HEAD_TO_HEAD path (tournament-level finalization)

```
Admin triggers COMPLETED status change
  │
  └── TournamentFinalizer.finalize()              [tournament_finalizer.py:229]
        │
        ├── get_all_sessions()
        ├── check_all_matches_completed()          [line 58]
        │       ├── game_results set → complete (H2H standard path)
        │       └── INDIVIDUAL_RANKING special path:
        │               rounds_data complete OR TournamentRanking rows exist → accept
        │
        ├── extract_final_rankings()               [line 96]
        │       ├── query: phase=KNOCKOUT, title ilike "%final%"   ← ⚠️ FRAGILE: title-based lookup
        │       └── query: phase=KNOCKOUT, title ilike "%3rd%"     ← ⚠️ FRAGILE: title-based lookup
        │
        ├── update_tournament_rankings_table()     [line 160]
        │       ├── upsert podium ranks (1st, 2nd, 3rd)
        │       └── insert NULL-rank rows for all enrolled non-podium players
        │
        ├── tournament.tournament_status = "COMPLETED"
        │
        └── distribute_rewards_for_tournament()   [tournament_reward_orchestrator.py]
                ├── load_reward_policy_from_config()  — supports 3 config formats
                ├── participation_service.distribute_xp()
                ├── badge_service.evaluate_badges()
                └── on failure: silently caught → tournament stays COMPLETED  ← ⚠️ SILENT FAILURE
                    tournament.tournament_status = "REWARDS_DISTRIBUTED" (only on success)
```

### 1c. GROUP_KNOCKOUT path (intermediate finalization)

```
Admin triggers "finalize group stage"
  │
  └── GroupStageFinalizer.finalize()              [group_stage_finalizer.py:124]
        │
        ├── get_group_sessions() — TournamentPhase.GROUP_STAGE
        ├── check_all_matches_completed()  — game_results != None
        │
        ├── StandingsCalculator.calculate_group_standings()  [standings_calculator.py:37]
        │       ├── reads: session.game_results["raw_results"] (H2H format)
        │       ├── fallback: raw list (old format)
        │       └── points: WIN=3, DRAW=1, LOSS=0
        │               tie-break: points > goal_diff > goals_for   ← ⚠️ NO head-to-head tiebreaker
        │
        ├── AdvancementCalculator.calculate_advancement()    [advancement_calculator.py:130]
        │       ├── get_qualified_participants(top_n=2)       ← ⚠️ top_n HARDCODED to 2
        │       └── apply_crossover_seeding()
        │               bracket: seed[i] vs seed[total-1-i]
        │
        └── snapshot → tournament_config_obj.enrollment_snapshot
              └── print() fallback if no tournament_config_obj   ← ⚠️ silent print not logging
```

### 1d. RankingAggregator (DEPRECATED — legacy path)

```
RankingAggregator                                [ranking_aggregator.py]
  ├── parse_measured_value()   — regex r'[\d.]+' from string
  ├── aggregate_user_values()  — respects ranking_direction (ASC→MIN, DESC→MAX)
  ├── calculate_performance_rankings()  — handles ties
  └── calculate_wins_rankings()         — round-winner counting

Status: Instantiated in SessionFinalizer.__init__() but NEVER CALLED in finalize().
        Used nowhere in modern flow. Dead code kept for "backward compatibility"
        (no callers found in active code paths).
```

---

## 2. Coverage Report

### 2a. Files with dedicated unit tests

| Component | Test file | Tests | Status |
|---|---|---|---|
| `AdvancementCalculator` | `tests/unit/tournament/test_advancement_calculator.py` | 16 | ✅ 16/16 pass |
| `RankingAggregator` | — | 0 | ❌ No tests |
| `SessionFinalizer` | `tests/integration/test_dual_path_prevention.py` | 5 | ❌ 1 fail + 4 ERROR (broken fixture) |
| `TournamentFinalizer` | — | 0 | ❌ No tests |
| `GroupStageFinalizer` | — | 0 | ❌ No tests (only covered indirectly via e2e) |
| `StandingsCalculator` | — | 0 | ❌ No tests |
| `ResultValidator` | — | 0 | ❌ No tests |
| `RankingService` | — | 0 | ❌ No tests |
| `RoundsBasedStrategy` | — | 0 | ❌ No tests |
| `TimeBasedStrategy` | — | 0 | ❌ No tests |
| `ScoreBasedStrategy` | — | 0 | ❌ No tests |
| `HeadToHeadLeagueRankingStrategy` | — | 0 | ❌ No tests |
| `HeadToHeadKnockoutRankingStrategy` | — | 0 | ❌ No tests |
| `HeadToHeadGroupKnockoutRankingStrategy` | — | 0 | ❌ No tests |
| `RankingStrategyFactory` | — | 0 | ❌ No tests |
| `TournamentRewardOrchestrator` | — | 0 | ❌ No tests (covered by e2e only) |

**Summary: 16/16 unit tests pass, but 14 of 16 classes have zero dedicated unit tests.**

### 2b. Integration / e2e coverage (indirect)

| Test file | Covers | DB required |
|---|---|---|
| `tests/unit/tournament/test_advancement_calculator.py` | `AdvancementCalculator`, `get_qualified_participants`, seeding | No (mock DB) |
| `tests/integration/test_dual_path_prevention.py` | `SessionFinalizer` idempotency | Yes (broken: `Semester.format` property setter error) |
| `tests/tournament_types/test_knockout_tournament.py` | Knockout lifecycle (e2e) | Yes |
| `tests/tournament_types/test_league_e2e_api.py` | League lifecycle (e2e) | Yes |
| `tests/e2e/golden_path/test_golden_path_api_based.py` | Full lifecycle (e2e) | Yes |
| `tests/e2e_frontend/*` | UI workflow covering finalization | Yes + browser |

### 2c. Untested scoring branches (high priority)

| Branch | Location | Risk |
|---|---|---|
| `ranking_direction="ASC"` with `TimeBasedStrategy` | `SessionFinalizer:235` | Unclear — direction not forwarded |
| `scoring_type="PLACEMENT"` full flow | `factory.py:70` | Maps to `ScoreBasedStrategy` (DESC) — likely wrong |
| `scoring_type="DISTANCE_BASED"` full flow | `factory.py:66` | Maps to `ScoreBasedStrategy` — may be correct |
| `check_all_matches_completed` IR special path | `tournament_finalizer.py:83` | Not unit tested |
| `extract_final_rankings` with no 3rd-place match | `tournament_finalizer.py:148` | Empty result, no test |
| `update_tournament_rankings_table` NULL-rank insert | `tournament_finalizer.py:215` | No test |
| `StandingsCalculator` with 0 goals (0-0 draw) | `standings_calculator.py:132` | No test |
| `StandingsCalculator` three-way tie | `standings_calculator.py:172` | No test |
| `AdvancementCalculator` with odd-count seeded list | `advancement_calculator.py:117` | No test |
| Reward distribution failure path | `tournament_finalizer.py:308` | Silent catch — no test |
| Multi-format reward config parsing (`_extract_tier`) | `orchestrator.py:38` | No test |

---

## 3. Decision Point Analysis — XP / ranking_direction / ROUNDS_BASED

### 3a. `ranking_direction` — Disconnect Between Model and Strategy

**Location:** `session_finalizer.py:235` + `ranking_service.py:30`

```python
# session_finalizer.py:235
ranking_direction = tournament.ranking_direction or "ASC"   # ← READ

# session_finalizer.py:266
rank_groups = self.ranking_service.calculate_rankings(
    scoring_type=scoring_type,
    round_results=round_results,
    participants=participants                                 # ← ranking_direction NOT PASSED
)
```

**Consequence:** The `ranking_direction` field on the tournament model has **zero effect** on ranking calculation in the modern flow. Each strategy hardcodes its sort direction:

| Strategy | Hardcoded direction | `ranking_direction` field honoured? |
|---|---|---|
| `TimeBasedStrategy` | ASC (lowest time wins) | ❌ NO |
| `ScoreBasedStrategy` | DESC (highest score wins) | ❌ NO |
| `RoundsBasedStrategy` | DESC (highest best-round wins) | ❌ NO |
| `RankingAggregator` (deprecated) | Respects `ranking_direction` | N/A (not called) |

**Risk:** An admin-configured `ranking_direction="ASC"` on a `SCORE_BASED` tournament (e.g., "fewest errors wins") would be silently ignored — the strategy always ranks DESC. The stored `ranking_direction` in `game_results` JSONB correctly reflects the *intended* direction, but the *computed* rankings reflect the strategy's hardcoded direction.

---

### 3b. `ROUNDS_BASED` — Aggregation Hardcoded as MAX

**Location:** `rounds_based.py:42` + `session_finalizer.py:292`

```python
# rounds_based.py:42
def aggregate_value(self, values: List[float]) -> float:
    return max(values) if values else 0.0    # ← always MAX, no override

# session_finalizer.py:292
"aggregation_method": "BEST_VALUE",          # ← metadata always "BEST_VALUE"
```

**Decision tree at the `ROUNDS_BASED` strategy:**

```
multi-round tournament (scoring_type = "ROUNDS_BASED")
  │
  └── RoundsBasedStrategy.aggregate_value()
        │
        ├── always: max(values)      ← picks best single round
        └── always: sort DESC        ← higher is better

  NOT implemented:
        ├── SUM aggregation          (e.g., total points across rounds)
        └── AVG aggregation          (e.g., average time across rounds)
```

**When is `ROUNDS_BASED` assigned?**

```python
# individual_ranking_generator.py:118
if number_of_rounds > 1:
    scoring_type_value = 'ROUNDS_BASED'     # ← overrides tournament.scoring_type
```

So ANY multi-round IR tournament (regardless of whether it's TIME_BASED or SCORE_BASED) gets `ROUNDS_BASED` scoring at the session level. The original `scoring_type` is preserved only in `structure_config.scoring_method` (metadata), not in the actual ranking path.

---

### 3c. XP Distribution — Decision Points

**Location:** `tournament_finalizer.py:297` + `tournament_reward_orchestrator.py`

**Trigger:** `TournamentFinalizer.finalize()` calls `distribute_rewards_for_tournament()` automatically.

**XP assignment logic (orchestrator):**

```
TournamentRanking rows (per user, per tournament)
  │
  ├── rank = 1  →  reward_config["first_place"] or ["1"]  →  XP + credits
  ├── rank = 2  →  reward_config["second_place"] or ["2"]  →  XP + credits
  ├── rank = 3  →  reward_config["third_place"] or ["3"]   →  XP + credits
  └── rank = NULL  →  PARTICIPANT tier  →  fixed XP (no placement bonus)
```

**Config format ambiguity:** `_extract_tier()` tries 3 different key formats:
```python
# Key lookup order per tier:
1st place:  "first_place"  OR  "1"
2nd place:  "second_place" OR  "2"
3rd place:  "third_place"  OR  "3"
participant: "participant"  OR  "4"
```

**XP multiplier legacy path:**
```python
# _extract_tier() lines 54-57
if not xp and "xp_multiplier" in tier:
    base_xp = {"first_place": 500, "1": 500, "second_place": 300, ...}.get(key, 50)
    xp = int(base_xp * tier["xp_multiplier"])
```

Hardcoded base XP values (500/300/200/50) — not configurable via tournament settings.

**Silent failure path:**
```python
# tournament_finalizer.py:308
except Exception as e:
    logger.error("❌ Auto reward distribution failed ... — tournament remains COMPLETED")
    # reward_result never assigned, status stays "COMPLETED" (not "REWARDS_DISTRIBUTED")
```

No retry mechanism. No system event raised. No admin alert. Failure is logged only.

---

### 3d. `PLACEMENT` scoring type — Likely incorrect mapping

**Location:** `strategies/factory.py:70`

```python
elif scoring_type == "PLACEMENT":
    # PLACEMENT uses direct ranking (no scores, just ranks)
    # Uses same logic as SCORE_BASED but ranks are inverted (lower rank = better)
    return ScoreBasedStrategy()
```

The comment says "ranks are inverted (lower rank = better)" but `ScoreBasedStrategy` sorts DESC (higher is better). For placement scores (where `1` = 1st place = best), DESC sort would put `1` after `10` — the opposite of the intended result. This is a logic error in the mapping.

---

## 4. Identified Bugs / Risks (Pre-Refactor)

| ID | Severity | Component | Description |
|---|---|---|---|
| BUG-01 | **HIGH** | `SessionFinalizer` + `RankingService` | `ranking_direction` read but not passed to strategy — silently ignored in modern flow |
| BUG-02 | **HIGH** | `RankingStrategyFactory` | `"PLACEMENT"` maps to `ScoreBasedStrategy` (DESC) — should sort ASC for rank numbers |
| BUG-03 | **MEDIUM** | `SessionFinalizer` | `aggregation_method="BEST_VALUE"` hardcoded — wrong metadata for SCORE_BASED (SUM) and TIME_BASED (MIN) |
| BUG-04 | **MEDIUM** | `TournamentFinalizer` | `extract_final_rankings()` uses `title.ilike("%final%")` — fragile title-based lookup |
| BUG-05 | **MEDIUM** | `RankingStrategyFactory` | `tournament_type_code="swiss"` raises `ValueError` — no HEAD_TO_HEAD Swiss strategy registered |
| BUG-06 | **LOW** | `GroupStageFinalizer` | `top_n_per_group=2` hardcoded — not configurable from tournament settings |
| BUG-07 | **LOW** | `StandingsCalculator` | No head-to-head tiebreaker — three-way equal-point ties resolved only by goal_diff |
| BUG-08 | **LOW** | `TournamentFinalizer` | Reward failure silently caught — no system_event, no retry, no admin alert |
| BUG-09 | **LOW** | `GroupStageFinalizer` | `print()` fallback if `tournament_config_obj` is None — should be `logger.warning()` |
| DEBT-01 | **INFO** | `SessionFinalizer` | `RankingAggregator` instantiated in `__init__` but never called — dead code |
| DEBT-02 | **INFO** | `test_dual_path_prevention.py` | 4/5 tests broken: `Semester.format` is a read-only property — fixture uses assignment |

---

## 5. Classes with Zero Dedicated Unit Tests (Refactor Prerequisites)

These must have unit tests written **before** any refactoring begins:

| Priority | Class | File | What to test |
|---|---|---|---|
| P0 | `RankingService` | `ranking/ranking_service.py` | All 6 scoring_type dispatch paths; convert_to_legacy_format ties |
| P0 | `RoundsBasedStrategy` | `strategies/rounds_based.py` | MAX aggregation, ties, missing rounds, empty participants |
| P0 | `TimeBasedStrategy` | `strategies/time_based.py` | ASC aggregation, string parsing, ties |
| P0 | `ScoreBasedStrategy` | `strategies/score_based.py` | DESC aggregation, SUM across rounds, ties |
| P1 | `SessionFinalizer` | `finalization/session_finalizer.py` | Idempotency guards, single/multi round, ranking_direction bug |
| P1 | `TournamentFinalizer` | `finalization/tournament_finalizer.py` | Title lookup, NULL-rank insertion, reward failure path |
| P1 | `StandingsCalculator` | `calculators/standings_calculator.py` | 0-0 draw, three-way tie, single player |
| P2 | `ResultValidator` | `validators/result_validator.py` | Invalid users, duplicate ranks, partial enrollment |
| P2 | `GroupStageFinalizer` | `finalization/group_stage_finalizer.py` | No sessions, incomplete matches, snapshot save |

---

## 6. Recommended Refactor Sequence

> **Do not start until P0 + P1 tests are written and green.**

1. **Fix BUG-02 first** (`PLACEMENT` → ASC) — low blast radius, high correctness impact
2. **Fix BUG-01** (`ranking_direction` forwarding to strategy) — requires strategy API change (add `ranking_direction` param to `calculate_rankings()`)
3. **Fix BUG-03** (`aggregation_method` metadata — make it dynamic per strategy)
4. **Fix BUG-04** (`extract_final_rankings` — replace title `ilike` with `tournament_phase + tournament_round == max(round)`)
5. **Fix BUG-05** (Swiss strategy — add `HeadToHeadSwissRankingStrategy` to factory)
6. **Remove DEBT-01** (`RankingAggregator` import and instantiation from `SessionFinalizer`)
7. **Fix DEBT-02** (`test_dual_path_prevention.py` — replace `Semester` real object with `SimpleNamespace`)

---

## 7. Entry Points Summary

| Who calls what | When |
|---|---|
| `ResultSubmission` endpoint | → `SessionFinalizer.finalize()` | After all IR rounds submitted |
| Admin COMPLETED status change | → `TournamentFinalizer.finalize()` | H2H / Knockout / Group+Knockout |
| Admin "finalize group stage" | → `GroupStageFinalizer.finalize()` | During GROUP_KNOCKOUT phase |
| `TournamentFinalizer.finalize()` | → `distribute_rewards_for_tournament()` | Automatically after finalization |

`SessionFinalizer` does **NOT** call `TournamentFinalizer`. The IR path produces per-session rankings; the admin must separately trigger tournament-level finalization for XP distribution.

---

*Refactoring begins next sprint. This document serves as the pre-refactor baseline.*
*Author: AI pair programmer, 2026-02-18.*
