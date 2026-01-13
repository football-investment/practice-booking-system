# 🎮 Tournament Game Types - Complete Specification

**Document Version**: 1.0
**Last Updated**: 2026-01-12
**Status**: ✅ Implemented

---

## 📋 Overview

This document defines all available **game types** for tournament matches in the LFA Internship System. Each game type represents a distinct match format with specific rules, scoring systems, and use cases.

**Key Feature**: All game types support **fixed durations** of **1, 3, or 5 minutes**.

---

## 🎯 Game Type Catalog

### 1️⃣ **League Match**

**Display Name**: ⚽ League Match
**Category**: LEAGUE
**Scoring System**: TABLE_BASED (win=3, draw=1, loss=0)
**Ranking Method**: POINTS

#### Description
All participants play against each other in a round-robin format. Points are awarded based on match results: 3 for a win, 1 for a draw, 0 for a loss. Matches can have fixed durations of 1, 3, or 5 minutes.

#### Use Case
- Long-term competitions with multiple rounds
- Season-long tournaments
- Everyone plays everyone format

#### Business Rules
- ✅ Result entry required
- ✅ Draws allowed
- ⏱️ Fixed game times: 1, 3, or 5 minutes

#### Example
```
Premier League format
- 20 players
- Each plays each other once
- Ranked by total points
```

---

### 2️⃣ **King of the Court**

**Display Name**: 🏆 King of the Court
**Category**: SPECIAL
**Scoring System**: WIN_STREAK
**Ranking Method**: SURVIVAL

#### Description
Players compete in a challenge format with 1v1, 1v2, or 1v3 setups. Each round has a fixed duration (1, 3, or 5 minutes). The winner stays on the court while losers rotate out. The goal is to remain on the court as long as possible.

#### Use Case
- Short, intense challenge competitions
- Quick rotation tournaments
- Individual skill showcases

#### Business Rules
- ✅ Result entry required
- ❌ Draws NOT allowed (winner must be determined)
- ⏱️ Fixed game times: 1, 3, or 5 minutes

#### Example
```
1v1 King of the Court
- Player A beats Player B (stays)
- Player A beats Player C (stays)
- Player A beats Player D (stays)
→ Player A has 3-game win streak
```

---

### 3️⃣ **Group Stage + Placement Matches**

**Display Name**: 🏆 Group Stage + Placement
**Category**: GROUP_STAGE
**Scoring System**: GROUP_TABLE
**Ranking Method**: POINTS_ADVANCE

#### Description
Tournament split into groups where each group plays a round-robin format. After the group stage, placement matches determine final rankings (e.g., 1st-4th, 5th-8th). Each game has a fixed duration of 1, 3, or 5 minutes.

#### Use Case
- Tournaments requiring fair group competition
- Multi-stage tournaments with placement brackets
- Ensures every participant has multiple matches

#### Business Rules
- ✅ Result entry required
- ✅ Draws allowed (in group stage)
- ⏱️ Fixed game times: 1, 3, or 5 minutes

#### Example
```
16-player tournament
- 4 groups of 4 players
- Group stage: Round-robin (3 games each)
- Placement: 1st place finishers compete for 1-4
              2nd place finishers compete for 5-8
              etc.
```

---

### 4️⃣ **Elimination Bracket**

**Display Name**: 🔥 Elimination Bracket
**Category**: KNOCKOUT
**Scoring System**: WIN_LOSS
**Ranking Method**: ADVANCE

#### Description
Single or double elimination bracket format. The loser is eliminated, and the winner advances to the next round. Each game has a fixed duration of 1, 3, or 5 minutes. Used for tournaments where the final winner is determined through knockout rounds.

#### Use Case
- Direct knockout tournaments
- Championship finals
- Quick elimination formats

#### Business Rules
- ✅ Result entry required
- ❌ Draws NOT allowed (overtime/tiebreaker if needed)
- ⏱️ Fixed game times: 1, 3, or 5 minutes

#### Example
```
8-player single elimination
- Quarterfinals: 8→4 winners
- Semifinals: 4→2 winners
- Final: 2→1 champion
```

---

## 🔧 Implementation Details

### Code Location
```
streamlit_app/components/admin/tournaments_tab.py
- Lines 28-33: GAME_TYPE_OPTIONS
- Lines 39-106: GAME_TYPE_DEFINITIONS
```

### Data Structure
```python
GAME_TYPE_DEFINITIONS = {
    "Game Type Name": {
        "display_name": "🏆 Display Name",
        "category": "LEAGUE|KNOCKOUT|GROUP_STAGE|SPECIAL|FRIENDLY",
        "description": "Full description...",
        "scoring_system": "TABLE_BASED|WIN_LOSS|WIN_STREAK|CUSTOM",
        "ranking_method": "POINTS|ADVANCE|SURVIVAL|SCORE",
        "use_case": "When to use this game type",
        "requires_result": True|False,
        "allows_draw": True|False,
        "fixed_game_times": [1, 3, 5]  # minutes
    }
}
```

### Database Storage
```sql
-- sessions table
SELECT id, title, game_type FROM sessions
WHERE is_tournament_game = true;

-- Column: game_type (VARCHAR 100)
```

---

## 📊 Category Breakdown

| Category | Game Types | Count |
|----------|-----------|-------|
| **LEAGUE** | League Match | 1 |
| **SPECIAL** | King of the Court | 1 |
| **GROUP_STAGE** | Group Stage + Placement Matches | 1 |
| **KNOCKOUT** | Elimination Bracket | 1 |
| **Total** | | **4** |

---

## ✅ Usage in UI

### Admin Dashboard
1. Navigate to: **Admin Dashboard → Tournaments → Manage Games**
2. Click **"Add New Game"**
3. Select **Game Type** from dropdown:
   - League Match
   - King of the Court
   - Group Stage + Placement Matches
   - Elimination Bracket
4. Set game time: 1, 3, or 5 minutes
5. Create game

### Game Type Visibility
- ✅ Admin: Can select and create games with any type
- ✅ Instructor: Sees game type when managing tournament
- ✅ Player: Sees game type when viewing tournament schedule

---

## 🚀 Adding New Game Types

### Step-by-Step Guide

1. **Add to OPTIONS list**
```python
GAME_TYPE_OPTIONS = [
    "League Match",
    "King of the Court",
    "Group Stage + Placement Matches",
    "Elimination Bracket",
    "NEW_GAME_TYPE_NAME"  # ← Add here
]
```

2. **Add to DEFINITIONS dictionary**
```python
GAME_TYPE_DEFINITIONS = {
    # ... existing definitions ...

    "NEW_GAME_TYPE_NAME": {
        "display_name": "🎯 Display Name",
        "category": "CATEGORY",
        "description": "Full description of the game type...",
        "scoring_system": "SCORING_SYSTEM",
        "ranking_method": "RANKING_METHOD",
        "use_case": "When to use this type",
        "requires_result": True,
        "allows_draw": False,
        "fixed_game_times": [1, 3, 5]
    }
}
```

3. **Test in UI**
   - Restart Streamlit
   - Navigate to Admin Dashboard → Tournaments → Manage Games
   - Verify new type appears in dropdown
   - Create test game with new type
   - Verify it saves correctly

---

## 📝 Validation Rules

### Fixed Game Times
All game types **MUST** support fixed durations:
- ✅ 1 minute
- ✅ 3 minutes
- ✅ 5 minutes

### Result Entry
- `requires_result: True` → Instructor **MUST** enter results after game
- `requires_result: False` → Results optional (e.g., friendly matches)

### Draw Rules
- `allows_draw: True` → Match can end in a tie
- `allows_draw: False` → Winner must be determined (overtime/tiebreaker)

---

## 🔄 Future Enhancements

### Planned Features
- [ ] Custom game duration input (not just 1/3/5)
- [ ] Automatic bracket generation for Elimination Bracket
- [ ] Group assignment UI for Group Stage format
- [ ] Win streak leaderboard for King of the Court
- [ ] Multi-round league support

### Under Consideration
- [ ] Swiss System format
- [ ] Double Elimination Bracket
- [ ] Team-based formats (2v2, 3v3)
- [ ] Time-based challenges (e.g., score as many in X minutes)

---

## 📚 Related Documentation

- [Tournament Workflow](./tournament_game.md)
- [Game Result Entry](../../streamlit_app/components/tournaments/game_result_entry.py)
- [Database Schema](../../alembic/versions/2025_12_31_1600-add_tournament_game_fields.py)

---

**Document Maintenance**:
- Update this document when adding/modifying game types
- Keep code examples synchronized with actual implementation
- Version control all changes
