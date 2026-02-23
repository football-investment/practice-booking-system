# Sandbox Deterministic Mode & Regression Testing

**Date:** 2026-01-28
**Status:** ✅ COMPLETE

## Overview

The sandbox tournament orchestrator now supports **deterministic mode** via random seeding. This enables:
1. **Reproducible test results** - Same seed always produces same outcome
2. **Regression testing** - Detect unintended changes in match generation logic
3. **Debugging** - Replay specific tournament scenarios exactly
4. **CI/CD validation** - Automated testing with known expected outputs

## Deterministic Mode

### Usage

```python
from app.services.sandbox_test_orchestrator import SandboxTestOrchestrator

orchestrator = SandboxTestOrchestrator(db)

# Run tournament with fixed seed for reproducible results
result = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control", "stamina"],
    player_count=4,
    random_seed=42  # ✅ DETERMINISTIC: Same seed = same results
)
```

### How It Works

When `random_seed` is provided:
1. Python's `random.seed(seed_value)` is called at the start of `execute_test()`
2. All subsequent `random.random()`, `random.randint()`, etc. calls become deterministic
3. Match outcomes, goal scores, and rankings become fully reproducible

**Code location:** [app/services/sandbox_test_orchestrator.py:106-109](app/services/sandbox_test_orchestrator.py#L106-L109)

```python
# Set random seed for deterministic results if provided
if random_seed is not None:
    random.seed(random_seed)
    logger.info(f"🎲 Deterministic mode: random seed set to {random_seed}")
```

### When to Use

**Use deterministic mode for:**
- ✅ Regression tests
- ✅ Debugging specific scenarios
- ✅ CI/CD automated testing
- ✅ Comparing algorithm changes
- ✅ Reproducing bug reports

**Don't use deterministic mode for:**
- ❌ Production testing (want realistic randomness)
- ❌ Load testing (want varied scenarios)
- ❌ Demo/showcase (want varied results)

## Regression Test Suite

### Test File

Location: [tests/integration/test_sandbox_regression.py](tests/integration/test_sandbox_regression.py)

### Test Cases

#### 1. `test_deterministic_head_to_head_4_players`
**Purpose:** Verify 4-player HEAD_TO_HEAD tournament produces expected rankings

**Setup:**
- 4 players (user IDs: 4, 5, 6, 7)
- HEAD_TO_HEAD format (round-robin)
- 6 total matches
- Random seed: 42
- Draw probability: 20%
- Home win probability: 40%

**Expected Results (Baseline):**
```python
Rank 1: 9 points (3 wins, 0 draws, 0 losses)
Rank 2: 6 points (2 wins, 0 draws, 1 loss)
Rank 3: 3 points (1 win, 0 draws, 2 losses)
Rank 4: 0 points (0 wins, 0 draws, 3 losses)
```

**What it verifies:**
- Rankings are calculated correctly
- Match statistics (W-D-L) are consistent
- Points system works (3-1-0)
- Total matches count is correct (6)
- Wins equal losses across all players

#### 2. `test_deterministic_repeatability`
**Purpose:** Verify same seed produces identical results twice

**Setup:**
- Run tournament with seed=12345
- Run again with seed=12345
- Compare all rankings and statistics

**What it verifies:**
- Determinism works correctly
- No hidden state affects results
- Results are truly reproducible

#### 3. `test_different_seeds_produce_different_results`
**Purpose:** Verify different seeds produce different results

**Setup:**
- Run tournament with seed=100
- Run tournament with seed=200
- Compare rankings

**What it verifies:**
- Randomness still works
- Seeds actually affect outcomes
- System isn't accidentally deterministic without seed

### Running Tests

**Run all regression tests:**
```bash
pytest tests/integration/test_sandbox_regression.py -v
```

**Run specific test:**
```bash
pytest tests/integration/test_sandbox_regression.py::TestSandboxRegression::test_deterministic_head_to_head_4_players -v
```

**Run with output:**
```bash
pytest tests/integration/test_sandbox_regression.py -v -s
```

### Updating Baseline

If match generation logic changes (e.g., scoring algorithm, probability distribution), the expected baseline will need updating:

**Step 1: Generate new baseline**
```bash
pytest tests/integration/test_sandbox_regression.py::test_generate_regression_baseline -v -s
```

**Step 2: Copy output**
The test will print the new expected values:
```
REGRESSION BASELINE (seed=42)
====================================
Rank 1 - Player Name
    {
        "rank": 1,
        "points": 9,
        "wins": 3,
        ...
    },
```

**Step 3: Update test**
Copy the printed values into `expected_baseline` array in `test_deterministic_head_to_head_4_players`

**Step 4: Verify**
Run the test again to ensure it passes with new baseline

## Implementation Details

### Random Operations Affected

When seed is set, these operations become deterministic:

1. **Match Outcomes:**
   ```python
   rand = random.random()
   if rand < draw_probability:    # Draw
   elif rand < draw_probability + home_win_probability:  # Home win
   else:  # Away win
   ```

2. **Goal Scores:**
   ```python
   score = random.randint(0, 3)  # Draw score (0-0, 1-1, 2-2, 3-3)
   p1_score = random.randint(1, 5)  # Winner score
   p2_score = random.randint(0, p1_score - 1)  # Loser score
   ```

3. **Player Selection (if not specified):**
   ```python
   selected_users = random.sample(TEST_USER_POOL, player_count)
   ```

4. **Performance Variation (INDIVIDUAL_RANKING):**
   ```python
   noise = random.uniform(-noise_range, noise_range)
   ```

### Seed Scope

**Global scope:** The seed affects ALL `random` module operations after it's set

**Reset behavior:** Seed persists until:
- Process restarts
- `random.seed()` called again (with different seed or None)
- Test isolation (pytest fixtures)

**Best practice:** Always provide explicit seed in tests, or explicitly set to None for random behavior

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Sandbox Regression Tests

on: [push, pull_request]

jobs:
  regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run regression tests
        run: |
          pytest tests/integration/test_sandbox_regression.py -v
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running sandbox regression tests..."
pytest tests/integration/test_sandbox_regression.py -q

if [ $? -ne 0 ]; then
    echo "❌ Regression tests failed! Match logic may have changed."
    echo "   Run: pytest tests/integration/test_sandbox_regression.py::test_generate_regression_baseline -v -s"
    echo "   Then update expected baseline values."
    exit 1
fi

echo "✅ Regression tests passed"
```

## Debugging with Deterministic Mode

### Reproduce Bug Report

```python
# User reports: "Tournament 12345 had wrong rankings"

# 1. Find tournament details
tournament = db.query(Semester).filter(Semester.id == 12345).first()
player_count = len(tournament.enrollments)

# 2. Replay with same seed (if you know it)
result = orchestrator.execute_test(
    tournament_type_code=tournament.tournament_type,
    skills_to_test=get_skills_from_tournament(tournament),
    player_count=player_count,
    random_seed=42,  # Use known seed
    draw_probability=0.20,
    home_win_probability=0.40
)

# 3. Compare results
# Rankings should match exactly if seed is correct
```

### Test Algorithm Changes

```python
# Before change
result_before = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=4,
    random_seed=100
)

# <Make your changes to match generation logic>

# After change
result_after = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=4,
    random_seed=100  # SAME SEED
)

# Compare results to understand impact
compare_rankings(result_before, result_after)
```

## Limitations

### What's NOT Deterministic

1. **Tournament ID** - Auto-incremented by database
2. **Timestamps** - Uses `datetime.now()`
3. **Test run ID** - Includes timestamp
4. **User selection** (if `user_ids` not provided) - Uses random sample

### To Make Fully Deterministic

```python
result = orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control"],
    player_count=4,
    user_ids=[4, 5, 6, 7],  # ✅ Fixed user IDs
    campus_id=1,
    random_seed=42  # ✅ Fixed seed
)
```

### External Factors

- Database state (existing tournaments, user data)
- System time (if used in calculations)
- Environment variables
- Database transaction isolation level

## Benefits

1. **Confidence** - Detect unintended changes immediately
2. **Speed** - No need for manual testing after code changes
3. **Documentation** - Tests serve as specification
4. **Debugging** - Reproduce exact scenarios
5. **Refactoring** - Safe to refactor with test coverage

## Example Test Output

```
======================== test session starts =========================
tests/integration/test_sandbox_regression.py::TestSandboxRegression::test_deterministic_head_to_head_4_players

🎲 Deterministic mode: random seed set to 42
🏆 Generating rankings: variation=MEDIUM, distribution=NORMAL
🎲 Simulating HEAD_TO_HEAD matches for 4 players
   Match probabilities: draw=20%, home_win=40%, away_win=40%
✅ HEAD_TO_HEAD rankings with match results created for 4 players

✅ Regression test passed with seed=42
   Tournament ID: 165
   Total matches: 6
   Leaderboard verified against baseline

PASSED                                                          [100%]

======================== 1 passed in 2.34s ==========================
```

## Related Documentation

- [SANDBOX_CONFIGURATION_COMPLETE.md](SANDBOX_CONFIGURATION_COMPLETE.md) - Configuration options
- [SANDBOX_DRAWS_FIXED.md](SANDBOX_DRAWS_FIXED.md) - Draw implementation details
- [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py) - Implementation
- [tests/integration/test_sandbox_regression.py](tests/integration/test_sandbox_regression.py) - Test suite

## Future Enhancements

1. Add more baseline scenarios (8 players, 16 players, different formats)
2. Test skill progression determinism
3. Test reward distribution determinism
4. Add performance benchmarks (ensure simulation doesn't slow down)
5. Test edge cases (all draws, all wins, etc.)
