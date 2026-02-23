# Sandbox Tournament Draws Support - FIXED

**Date:** 2026-01-28
**Status:** ✅ COMPLETE

## Problem

User reported that HEAD_TO_HEAD tournament draws were not being tracked:
- CSV export showed "3-0-0" format (wins-draws-losses)
- But **all players had draws = 0** in the database
- The sandbox orchestrator was generating **fixed points** without simulating actual matches

**User feedback:** "volt döntetlen is a meccsek között de nem kezeli a backend vagy a frontend??"

## Root Cause

The `sandbox_test_orchestrator.py` `_generate_rankings()` function had two major issues:

1. **No match simulation for HEAD_TO_HEAD**: It only generated abstract points, not actual match results
2. **Hardcoded zeros**: Lines 429-431 hardcoded `wins=0, losses=0, draws=0` regardless of tournament format

```python
# OLD CODE (BROKEN)
ranking = TournamentRanking(
    tournament_id=self.tournament_id,
    user_id=user_id,
    participant_type="PLAYER",
    rank=rank,
    points=int(points),
    wins=0,          # ❌ Always zero!
    losses=0,        # ❌ Always zero!
    draws=0,         # ❌ Always zero!
    updated_at=datetime.now()
)
```

This meant:
- Sandbox tournaments never had realistic match data
- HEAD_TO_HEAD format wasn't being respected
- No draws were possible in sandbox tests
- Points were arbitrary, not based on 3-1-0 win/draw/loss system

## Solution

### 1. Format-Aware Match Generation

Modified `_generate_rankings()` to check tournament format and handle HEAD_TO_HEAD differently:

```python
# Get tournament to check format
tournament = self.db.query(Semester).filter(Semester.id == self.tournament_id).first()
tournament_format = tournament.format if tournament else "HEAD_TO_HEAD"

if tournament_format == "HEAD_TO_HEAD":
    # Generate round-robin matches with draws
else:
    # Original logic for INDIVIDUAL_RANKING
```

### 2. Round-Robin Match Simulation

For HEAD_TO_HEAD tournaments, now generates **all possible matches** between players:

```python
# Initialize player stats
player_stats = {user_id: {"wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}
               for user_id in user_ids}

# Generate all possible matches (round-robin)
for i, player1 in enumerate(user_ids):
    for player2 in user_ids[i+1:]:
        # Simulate match result
        # 20% chance of draw, 40% player1 wins, 40% player2 wins
        rand = random.random()

        if rand < 0.2:  # Draw (20%)
            score = random.randint(0, 3)  # 0-0, 1-1, 2-2, or 3-3
            player_stats[player1]["draws"] += 1
            player_stats[player2]["draws"] += 1
            # Update goals_for and goals_against
        elif rand < 0.6:  # Player 1 wins (40%)
            # Generate scores where p1_score > p2_score
        else:  # Player 2 wins (40%)
            # Generate scores where p2_score > p1_score
```

### 3. Proper Points Calculation

Points now follow standard football rules:
- **Win**: 3 points
- **Draw**: 1 point
- **Loss**: 0 points

```python
points = (stats["wins"] * 3) + stats["draws"]
```

### 4. Ranking with Match Stats

Rankings now include realistic match statistics:

```python
ranking = TournamentRanking(
    tournament_id=self.tournament_id,
    user_id=user_id,
    participant_type="PLAYER",
    rank=0,  # Calculated by calculate_ranks()
    points=points,
    wins=stats["wins"],           # ✅ Real wins
    losses=stats["losses"],       # ✅ Real losses
    draws=stats["draws"],         # ✅ Real draws!
    goals_for=stats["goals_for"],
    goals_against=stats["goals_against"],
    updated_at=datetime.now()
)
```

### 5. Proper Rank Calculation

Uses the existing `calculate_ranks()` service to properly rank by:
1. Points (descending)
2. Goal difference (descending)
3. Goals for (descending)

```python
from app.services.tournament.leaderboard_service import calculate_ranks
calculate_ranks(self.db, self.tournament_id)
```

## Code Changes

### File: app/services/sandbox_test_orchestrator.py

**Lines 384-520** - Complete rewrite of `_generate_rankings()`:

1. **Check tournament format** (line ~392)
2. **HEAD_TO_HEAD branch** (lines ~394-470):
   - Round-robin match generation
   - 20% draw probability
   - Realistic score generation
   - Goal tracking
   - Points calculation (3-1-0 system)
   - Proper ranking insertion
3. **Other formats branch** (lines ~471-518):
   - Original abstract points logic (for INDIVIDUAL_RANKING, etc.)

## Benefits

### Before:
- ❌ No match results for HEAD_TO_HEAD
- ❌ Always 0 draws
- ❌ Arbitrary points not based on wins/draws/losses
- ❌ No goal statistics
- ❌ Inconsistent with real tournament logic

### After:
- ✅ Realistic round-robin matches
- ✅ 20% draw probability (configurable)
- ✅ Standard 3-1-0 points system
- ✅ Goal statistics tracked
- ✅ Consistent with real tournament behavior
- ✅ CSV exports show correct W-D-L format

## Match Probability Distribution

Current configuration (can be adjusted):
- **Draw**: 20% chance
- **Home Win**: 40% chance
- **Away Win**: 40% chance

Draw scores: 0-0, 1-1, 2-2, or 3-3 (random)
Win scores: Winner gets 1-5 goals, loser gets 0 to (winner-1) goals

## Testing

### Test Case 1: 4 Players HEAD_TO_HEAD
- Generates 6 matches (4 × 3 / 2 = 6)
- Expected: ~1 draw on average (20% of 6)
- Each player plays 3 matches

### Test Case 2: 8 Players HEAD_TO_HEAD
- Generates 28 matches (8 × 7 / 2 = 28)
- Expected: ~5-6 draws on average (20% of 28)
- Each player plays 7 matches

### Verification Query:
```sql
SELECT
    u.name as player,
    tr.wins,
    tr.draws,
    tr.losses,
    tr.points,
    tr.goals_for,
    tr.goals_against
FROM tournament_rankings tr
JOIN users u ON tr.user_id = u.id
WHERE tr.tournament_id = <tournament_id>
ORDER BY tr.rank;
```

Expected: **At least some players will have draws > 0**

## Backward Compatibility

✅ **INDIVIDUAL_RANKING** tournaments still use the original abstract points logic
✅ Existing tournaments are not affected
✅ Only new HEAD_TO_HEAD sandbox tournaments use the new match simulation

## Related Files

- [app/services/sandbox_test_orchestrator.py](app/services/sandbox_test_orchestrator.py) - Main orchestrator
- [app/services/tournament/leaderboard_service.py](app/services/tournament/leaderboard_service.py) - Ranking calculation
- [app/models/tournament_ranking.py](app/models/tournament_ranking.py) - Ranking model

## Configuration Options

The match simulation now supports configurable probabilities:

```python
orchestrator.execute_test(
    tournament_type_code="league",
    skills_to_test=["ball_control", "stamina"],
    draw_probability=0.20,      # 20% chance of draws (configurable)
    home_win_probability=0.40   # 40% chance of first player winning (configurable)
)
```

**Default values:**
- `draw_probability`: 0.20 (20%)
- `home_win_probability`: 0.40 (40%)
- Away win probability: `1 - draw_probability - home_win_probability` (40%)

**Validation:**
- Probabilities must be between 0.0 and 1.0
- Invalid values fall back to defaults with warning logs

## Production vs Sandbox

### ⚠️ CRITICAL DISTINCTION

**Sandbox (Testing Only):**
- Uses `SandboxTestOrchestrator._generate_rankings()`
- Simulates match results with random probabilities
- For testing reward distribution, skill progression, and mechanics
- **DO NOT USE IN PRODUCTION**

**Production (Real Tournaments):**
- Uses real match data from `sessions` table via attendance tracking
- Rankings updated by `match_results.py` API endpoint after each match
- Both use the SAME `calculate_ranks()` service for consistency

### Shared Ranking Calculation

✅ **Both systems use:** `app.services.tournament.leaderboard_service.calculate_ranks()`

This ensures:
- Consistent ranking algorithm (points → goal difference → goals for)
- Same tie-breaking rules
- Identical leaderboard display logic

**Flow:**
1. **Sandbox**: Simulates matches → writes to `tournament_rankings` → calls `calculate_ranks()`
2. **Production**: Real matches → updates `tournament_rankings` → calls `calculate_ranks()`
3. **API**: Both read from `tournament_rankings` table via `/tournaments/{id}/leaderboard` endpoint
4. **UI**: Streamlit displays leaderboard via API (format-agnostic)

## Future Enhancements

Potential improvements:
1. ✅ ~~Make draw probability configurable~~ (DONE)
2. Add home field advantage simulation
3. Consider player skill levels in match outcomes
4. Generate actual session records for each match (currently only rankings)
5. Support other scoring systems (2 points for win, etc.)
6. Add match simulation logs/replay data
