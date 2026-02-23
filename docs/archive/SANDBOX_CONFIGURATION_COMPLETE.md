# Sandbox Configuration & Documentation - COMPLETE

**Date:** 2026-01-28
**Status:** ✅ COMPLETE

## Summary

Successfully configured the sandbox test orchestrator with:
1. ✅ Configurable draw/win probabilities
2. ✅ Clear sandbox-only documentation
3. ✅ Verified ranking calculation consistency between sandbox and production

## Changes Made

### 1. Configurable Match Probabilities

**File:** [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py)

**Parameters added to `execute_test()`:**
```python
draw_probability: float = 0.20       # 20% chance of draws (0.0-1.0)
home_win_probability: float = 0.40   # 40% chance of first player winning
```

**Updated `_generate_rankings()` signature:**
```python
def _generate_rankings(
    self,
    user_ids: List[int],
    performance_variation: str,
    ranking_distribution: str,
    draw_probability: float = 0.20,      # NEW
    home_win_probability: float = 0.40  # NEW
) -> None:
```

**Usage example:**
```python
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control", "stamina"],
    player_count=8,
    draw_probability=0.25,      # 25% draws
    home_win_probability=0.50   # 50% home wins, 25% away wins
)
```

**Validation:**
- Probabilities validated to be between 0.0 and 1.0
- Invalid values log warnings and fall back to defaults
- Away win probability calculated as: `1 - draw_probability - home_win_probability`

**Logging:**
```
🎲 Simulating HEAD_TO_HEAD matches for 8 players
   Match probabilities: draw=20%, home_win=40%, away_win=40%
```

### 2. Sandbox-Only Documentation

**Module-level docstring:**
```python
"""
Sandbox Test Orchestrator

⚠️ SANDBOX / TESTING ENVIRONMENT ONLY ⚠️

This module is designed EXCLUSIVELY for sandbox testing and demonstration purposes.
It simulates tournament matches and generates synthetic results to test the reward
distribution system, skill progression, and tournament mechanics.

🚫 DO NOT USE IN PRODUCTION:
- This code simulates match results with random probabilities
- Production tournaments MUST use real match data from actual games
- Real tournaments should use session management and attendance tracking
- Production ranking calculations should come from real match outcomes
...
"""
```

**Function-level documentation:**
```python
def execute_test(...):
    """
    Execute complete sandbox test

    ⚠️ SANDBOX ONLY: This is a simulation environment for testing tournament mechanics.
    Production tournaments should use real match data from actual games.
    ...
    """

def _generate_rankings(...):
    """
    Generate synthetic tournament rankings with real match results for HEAD_TO_HEAD

    ⚠️ SANDBOX ONLY: This method simulates match results for testing purposes.
    Production tournaments should calculate rankings from real match data.
    ...
    """
```

### 3. Ranking Calculation Verification

**Confirmed consistency:** Both sandbox and production use the SAME ranking calculation service.

#### Sandbox Flow:
1. `SandboxTestOrchestrator._generate_rankings()` simulates matches
2. Writes to `tournament_rankings` table
3. Calls `calculate_ranks(db, tournament_id)` from `leaderboard_service.py`
4. Ranks calculated by: points (desc) → goal difference (desc) → goals for (desc)

#### Production Flow:
1. Real matches recorded in `sessions` table with attendance
2. Match results API (`match_results.py`) updates `tournament_rankings`
3. Calls SAME `calculate_ranks(db, tournament_id)` service
4. Same ranking algorithm applied

#### API Endpoint (Shared):
- `/tournaments/{id}/leaderboard` reads from `tournament_rankings` table
- Format-agnostic (works for both sandbox and production)
- Streamlit UI calls this endpoint
- No distinction between sandbox and production leaderboards

**Code references:**
- Sandbox: [app/services/sandbox_test_orchestrator.py:519-520](app/services/sandbox_test_orchestrator.py#L519-L520)
- Production: [app/api/api_v1/endpoints/tournaments/match_results.py:1186-1206](app/api/api_v1/endpoints/tournaments/match_results.py#L1186-L1206)
- Shared service: [app/services/tournament/leaderboard_service.py:100-160](app/services/tournament/leaderboard_service.py#L100-L160)
- API endpoint: [app/api/api_v1/endpoints/tournaments/instructor.py:297-390](app/api/api_v1/endpoints/tournaments/instructor.py#L297-L390)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    TOURNAMENT RANKINGS                       │
│                  (tournament_rankings table)                 │
│                                                              │
│  Fields: user_id, points, wins, draws, losses,              │
│          goals_for, goals_against, rank                      │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             │                                │
    ┌────────▼────────┐              ┌───────▼────────┐
    │   SANDBOX       │              │   PRODUCTION   │
    │   (Simulated)   │              │   (Real Games) │
    └────────┬────────┘              └───────┬────────┘
             │                                │
             │                                │
    ┌────────▼────────┐              ┌───────▼────────┐
    │ Sandbox         │              │ Match Results  │
    │ Orchestrator    │              │ API            │
    │ - Simulates     │              │ - Real match   │
    │   matches       │              │   data         │
    │ - Random        │              │ - Attendance   │
    │   probabilities │              │   tracking     │
    └────────┬────────┘              └───────┬────────┘
             │                                │
             │        ┌───────────────┐       │
             └────────►  SHARED       ◄───────┘
                      │  calculate_   │
                      │  ranks()      │
                      │  service      │
                      └───────┬───────┘
                              │
                      ┌───────▼───────┐
                      │  Leaderboard  │
                      │  API Endpoint │
                      │  (Read-only)  │
                      └───────┬───────┘
                              │
                      ┌───────▼───────┐
                      │  Streamlit UI │
                      │  (Display)    │
                      └───────────────┘
```

## Key Distinctions

### What's SANDBOX-ONLY:
- ❌ Match result simulation with random probabilities
- ❌ Synthetic player performance generation
- ❌ Abstract points distribution (INDIVIDUAL_RANKING)
- ❌ Automated tournament lifecycle (no manual intervention)

### What's SHARED:
- ✅ `calculate_ranks()` service
- ✅ `tournament_rankings` table structure
- ✅ Leaderboard API endpoint
- ✅ Points system (3-1-0)
- ✅ Ranking algorithm (points → GD → GF)
- ✅ Streamlit UI display logic

### What's PRODUCTION-ONLY:
- ✅ Real match data from sessions
- ✅ Attendance tracking
- ✅ Manual session management
- ✅ Instructor verification
- ✅ Real player performance

## Testing

### Verify Configuration Works:
```python
# Test with custom probabilities
result = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=4,
    draw_probability=0.30,      # 30% draws
    home_win_probability=0.35   # 35% home wins, 35% away wins
)

# Check logs for:
# "🎲 Simulating HEAD_TO_HEAD matches for 4 players"
# "   Match probabilities: draw=30%, home_win=35%, away_win=35%"
```

### Verify Draws Are Generated:
```sql
SELECT
    u.name,
    tr.wins,
    tr.draws,  -- Should be > 0 for some players
    tr.losses,
    tr.points
FROM tournament_rankings tr
JOIN users u ON tr.user_id = u.id
WHERE tr.tournament_id = <sandbox_tournament_id>
ORDER BY tr.rank;
```

Expected: At least some players should have `draws > 0` with default 20% probability.

### Verify Ranking Consistency:
1. Create sandbox tournament
2. Create production tournament with same players
3. Compare ranking algorithms (should be identical)
4. Verify leaderboard display matches

## Related Documentation

- [SANDBOX_DRAWS_FIXED.md](SANDBOX_DRAWS_FIXED.md) - Original draws implementation
- [DRAFT_STATUS_HANDLING_FIXED.md](DRAFT_STATUS_HANDLING_FIXED.md) - History Browser DRAFT handling
- [SKILL_WEIGHTS_FIXED.md](SKILL_WEIGHTS_FIXED.md) - Skill weights configuration

## Benefits

1. **Flexibility:** Adjust match probabilities for different testing scenarios
2. **Clarity:** Clear documentation prevents production misuse
3. **Consistency:** Shared ranking logic ensures identical behavior
4. **Safety:** Explicit warnings prevent accidental production use
5. **Testability:** Configurable probabilities enable edge case testing

## Future Enhancements

1. Add preset probability profiles (e.g., "BALANCED", "HOME_ADVANTAGE", "HIGH_DRAWS")
2. Support player-specific win probabilities based on skill ratings
3. Add match simulation replay/visualization
4. Generate session records for each simulated match
5. Support alternative scoring systems (2-1-0, bonus points, etc.)
