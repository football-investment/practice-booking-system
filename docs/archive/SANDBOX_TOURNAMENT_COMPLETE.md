# Sandbox Tournament Logic - COMPLETE

**Date:** 2026-01-28
**Status:** ✅ PRODUCTION READY

## Summary

The sandbox tournament system is now **complete and production-ready** with:
- ✅ HEAD_TO_HEAD match simulation with draws support
- ✅ Configurable match probabilities
- ✅ Deterministic mode for regression testing
- ✅ Automated test suite with known baselines
- ✅ Clear sandbox-only documentation
- ✅ Verified ranking calculation consistency

## Implementation Timeline

### Phase 1: Draws Support ([SANDBOX_DRAWS_FIXED.md](SANDBOX_DRAWS_FIXED.md))
**Problem:** HEAD_TO_HEAD tournaments didn't support draws, all players had `draws=0`

**Solution:**
- Implemented round-robin match simulation
- Added 20% draw probability (configurable)
- Implemented 3-1-0 points system
- Added goal statistics tracking
- Used shared `calculate_ranks()` service

### Phase 2: Configuration & Documentation ([SANDBOX_CONFIGURATION_COMPLETE.md](SANDBOX_CONFIGURATION_COMPLETE.md))
**Requirements:**
- Make probabilities configurable (not hardcoded)
- Add explicit sandbox-only warnings
- Verify ranking calculation consistency

**Solution:**
- Added `draw_probability` parameter (0.0-1.0, default 0.20)
- Added `home_win_probability` parameter (0.0-1.0, default 0.40)
- Added comprehensive module-level warnings
- Verified both sandbox and production use same `calculate_ranks()` service
- Documented architecture and data flow

### Phase 3: Deterministic Mode & Regression Tests ([SANDBOX_DETERMINISTIC_MODE.md](SANDBOX_DETERMINISTIC_MODE.md))
**Requirements:**
- Add seeded random for reproducible results
- Create automated regression test suite
- Lock down known baselines

**Solution:**
- Added `random_seed` parameter for deterministic mode
- Created comprehensive regression test suite
- Implemented 3 test cases: baseline verification, repeatability, randomness
- Added baseline update workflow
- Documented CI/CD integration

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              SANDBOX TEST ORCHESTRATOR                   │
│         (Testing & Demonstration Only)                   │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │  execute_test()         │
         │  - random_seed (opt)    │
         │  - draw_probability     │
         │  - home_win_probability │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │ _generate_rankings()    │
         │ HEAD_TO_HEAD:           │
         │  - Simulate matches     │
         │  - Calculate W-D-L      │
         │  - Track goals          │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │ tournament_rankings     │
         │ (Database Table)        │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │ calculate_ranks()       │
         │ (SHARED SERVICE)        │
         │ - Points desc           │
         │ - Goal diff desc        │
         │ - Goals for desc        │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │ Leaderboard API         │
         │ /tournaments/{id}/      │
         │ leaderboard             │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │ Streamlit UI            │
         │ (Display)               │
         └─────────────────────────┘
```

## API Reference

### SandboxTestOrchestrator.execute_test()

```python
def execute_test(
    tournament_type_code: str,          # "league", "knockout", etc.
    skills_to_test: List[str],          # ["ball_control", "stamina"]
    skill_weights: Optional[Dict[str, float]] = None,  # {"ball_control": 2.0}
    player_count: int = 16,             # 4-16 players
    campus_id: int = 1,
    performance_variation: str = "MEDIUM",  # LOW/MEDIUM/HIGH (INDIVIDUAL_RANKING)
    ranking_distribution: str = "NORMAL",   # NORMAL/TOP_HEAVY/BOTTOM_HEAVY
    user_ids: Optional[List[int]] = None,   # Specific users (default: random)
    instructor_ids: Optional[List[int]] = None,
    skip_lifecycle: bool = False,       # Skip rankings/rewards (workflow mode)
    draw_probability: float = 0.20,     # 0.0-1.0 (20% draws)
    home_win_probability: float = 0.40, # 0.0-1.0 (40% home wins)
    random_seed: Optional[int] = None   # Deterministic mode (e.g., 42)
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tournament_type_code` | str | required | Tournament type: "league", "knockout", etc. |
| `skills_to_test` | List[str] | required | Skills to test and reward |
| `skill_weights` | Dict[str, float] | None | Weight multipliers per skill (1.0 default) |
| `player_count` | int | 16 | Number of players (4-16) |
| `campus_id` | int | 1 | Campus ID for tournament location |
| `draw_probability` | float | 0.20 | Probability of draws (0.0-1.0) |
| `home_win_probability` | float | 0.40 | Probability of home team winning |
| `random_seed` | int | None | Seed for deterministic results |

### Return Value

```python
{
    "verdict": "WORKING",  # WORKING / NEEDS_TUNING / NOT_WORKING
    "test_run_id": "sandbox-2026-01-28-19-15-00-1234",
    "tournament": {
        "id": 165,
        "name": "SANDBOX-TEST-LEAGUE-2026-01-28",
        "type": "LEAGUE",
        "status": "REWARDS_DISTRIBUTED",
        "player_count": 4,
        "skills_tested": ["ball_control", "stamina"]
    },
    "execution_summary": {
        "duration_seconds": 2.34,
        "steps_completed": [...]
    },
    "skill_progression": {...},
    "top_performers": [...],
    "bottom_performers": [...],
    "insights": [...],
    "export_data": {...}
}
```

## Usage Examples

### Basic Usage

```python
from app.services.sandbox_test_orchestrator import SandboxTestOrchestrator

orchestrator = SandboxTestOrchestrator(db)

result = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control", "stamina"],
    player_count=4
)

print(f"Tournament {result['tournament']['id']}: {result['verdict']}")
```

### Configured Probabilities

```python
# Simulate home field advantage (60% home wins, 30% away wins, 10% draws)
result = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=8,
    draw_probability=0.10,      # 10% draws
    home_win_probability=0.60   # 60% home wins, 30% away wins
)
```

### Deterministic Testing

```python
# Run twice with same seed - results will be identical
result1 = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=4,
    user_ids=[4, 5, 6, 7],  # Fixed users
    random_seed=42           # Fixed seed
)

result2 = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=4,
    user_ids=[4, 5, 6, 7],
    random_seed=42           # Same seed
)

# Verify identical
assert result1["tournament"]["id"] != result2["tournament"]["id"]  # Different IDs
# But rankings will be identical
```

### Regression Testing

```python
# In pytest
def test_tournament_regression(db):
    orchestrator = SandboxTestOrchestrator(db)

    result = orchestrator.execute_test(
        tournament_type_code="league",
        skills_to_test=["ball_control"],
        player_count=4,
        user_ids=[4, 5, 6, 7],
        random_seed=42  # Known baseline
    )

    # Verify against known baseline
    rankings = get_rankings(db, result["tournament"]["id"])
    assert rankings[0].points == 9  # Expected with seed=42
    assert rankings[1].points == 6
    assert rankings[2].points == 3
    assert rankings[3].points == 0
```

## Test Suite

### Running Tests

```bash
# Run all regression tests
pytest tests/integration/test_sandbox_regression.py -v

# Run specific test
pytest tests/integration/test_sandbox_regression.py::TestSandboxRegression::test_deterministic_head_to_head_4_players -v

# Generate new baseline
pytest tests/integration/test_sandbox_regression.py::test_generate_regression_baseline -v -s
```

### Test Coverage

| Test | Purpose | Seed | Players | Matches |
|------|---------|------|---------|---------|
| `test_deterministic_head_to_head_4_players` | Baseline verification | 42 | 4 | 6 |
| `test_deterministic_repeatability` | Repeatability check | 12345 | 4 | 6 |
| `test_different_seeds_produce_different_results` | Randomness check | 100, 200 | 4 | 6 |

## Production vs Sandbox

### ⚠️ CRITICAL: DO NOT USE IN PRODUCTION

**Sandbox (Testing Only):**
```python
# ❌ TESTING ONLY - Simulated matches
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=4
)
```

**Production (Real Tournaments):**
```python
# ✅ PRODUCTION - Real match data
# 1. Create tournament via API
POST /api/v1/tournaments/generate

# 2. Players enroll
POST /api/v1/semester-enrollments

# 3. Generate sessions
POST /api/v1/tournaments/{id}/sessions/generate

# 4. Record real match results
POST /api/v1/sessions/{id}/match-result

# 5. Rankings auto-update via calculate_ranks()
# Same service as sandbox!

# 6. Display leaderboard
GET /api/v1/tournaments/{id}/leaderboard
```

### Shared Components

Both sandbox and production use:
- ✅ `calculate_ranks()` service
- ✅ `tournament_rankings` table
- ✅ Leaderboard API endpoint
- ✅ 3-1-0 points system
- ✅ Same ranking algorithm

## Documentation Files

| File | Purpose |
|------|---------|
| [SANDBOX_DRAWS_FIXED.md](SANDBOX_DRAWS_FIXED.md) | Initial draws implementation |
| [SANDBOX_CONFIGURATION_COMPLETE.md](SANDBOX_CONFIGURATION_COMPLETE.md) | Configuration & consistency verification |
| [SANDBOX_DETERMINISTIC_MODE.md](SANDBOX_DETERMINISTIC_MODE.md) | Deterministic mode & regression testing |
| **SANDBOX_TOURNAMENT_COMPLETE.md** | **This file - Complete reference** |

## Code Files

| File | Purpose | Lines |
|------|---------|-------|
| [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py) | Main orchestrator | ~550 |
| [app/services/tournament/leaderboard_service.py](app/services/tournament/leaderboard_service.py) | Shared ranking logic | ~200 |
| [tests/integration/test_sandbox_regression.py](tests/integration/test_sandbox_regression.py) | Regression test suite | ~300 |

## Key Features

### 1. Match Simulation
- Round-robin generation for HEAD_TO_HEAD
- Configurable draw/win probabilities
- Realistic goal statistics (0-5 goals per team)
- Draw scores: 0-0, 1-1, 2-2, 3-3

### 2. Points System
- Win: 3 points
- Draw: 1 point
- Loss: 0 points
- Standard football rules

### 3. Ranking Algorithm
1. Total points (descending)
2. Goal difference (descending)
3. Goals for (descending)
4. User ID (tiebreaker)

### 4. Deterministic Mode
- Set `random_seed` parameter
- All random operations become reproducible
- Perfect for regression testing
- CI/CD integration ready

### 5. Configuration
- Adjust draw probability (0-100%)
- Adjust win/loss distribution
- Skill-specific weights
- Player count (4-16)

## Success Criteria

✅ **All criteria met:**
- [x] Draws are generated and tracked correctly
- [x] Probabilities are configurable
- [x] Clear sandbox-only documentation
- [x] Ranking calculation verified consistent with production
- [x] Deterministic mode implemented
- [x] Regression test suite created
- [x] Known baseline locked down
- [x] CI/CD integration documented

## Sign-Off

**Sandbox tournament logic is COMPLETE and ready for:**
- ✅ Testing reward distribution formulas
- ✅ Demonstrating tournament mechanics
- ✅ Running automated integration tests
- ✅ Debugging tournament workflows
- ✅ Regression testing after code changes

**NOT ready for (by design):**
- ❌ Production tournaments with real users
- ❌ Live competitions
- ❌ Official rankings

**For production tournaments, use the real tournament workflow via API and Streamlit UI.**

---

**Status:** ✅ COMPLETE - No further work required
**Last Updated:** 2026-01-28
**Maintainer:** Development Team
