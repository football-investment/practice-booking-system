# HEAD_TO_HEAD Manual Result Entry - Design Document

**Status**: 🚧 DESIGN PHASE
**Priority**: P0 - Production Blocker
**Created**: 2026-02-04

---

## Problem Statement

HEAD_TO_HEAD tournaments currently have **no manual result entry UI** (sandbox_workflow.py:638), blocking:
- Instructors from recording match results
- Tournament finalization
- Reward distribution
- Full E2E test validation

**Current State**: Production gap - users cannot complete HEAD_TO_HEAD tournament workflows.

---

## User Flow Requirements

### League Format (Round Robin)

**Match Structure**:
- All participants play against each other
- Each match: 2 participants (Team A vs Team B)
- Multiple sessions (one per match pairing)

**Result Entry Flow**:
1. Instructor navigates to "Enter Results" step
2. Sees list of ALL matches (sessions) for the league
3. For EACH match:
   - Match title: "Match X: [Player A] vs [Player B]"
   - Score entry fields:
     - Player A score: `number_input` (0-99)
     - Player B score: `number_input` (0-99)
   - Result status indicator:
     - ⚪ Not submitted
     - ✅ Submitted
4. Submit button per match OR bulk submit for all matches
5. After all matches submitted → "Continue to Finalization"

**Winner Logic**:
- Higher score = Winner
- Equal scores = Tie (both get tie points)
- Points system: Win = 3 points, Tie = 1 point, Loss = 0 points

**Edge Cases**:
- What if instructor enters same score for both? → Tie
- What if instructor leaves score blank? → Validation error
- What if instructor tries to finalize without all matches? → Block with error
- Can instructor edit submitted results? → Yes, before finalization

---

### Knockout Format (Single Elimination)

**Match Structure**:
- Bracket-style elimination
- Round 1: All participants (must be power of 2: 4, 8, 16, etc.)
- Round 2: Winners from Round 1
- Round 3: Winners from Round 2 (if applicable)
- Final: Last 2 winners

**Result Entry Flow**:
1. Instructor navigates to "Enter Results" step
2. Sees matches organized by **rounds**:
   - **Round 1 (Quarterfinals)**: 4 matches (8 participants)
   - **Round 2 (Semifinals)**: 2 matches (4 participants)
   - **Round 3 (Final)**: 1 match (2 participants)
3. For EACH match:
   - Match title: "Round X - Match Y: [Player A] vs [Player B]"
   - Score entry fields (same as league)
   - Winner selection:
     - Radio buttons: "Player A wins" | "Player B wins" | "Tie → Replay"
4. **Critical**: Subsequent rounds only visible after previous round finalized
5. After final match submitted → "Continue to Finalization"

**Winner Logic**:
- Higher score = Winner advances to next round
- Tie = Replay match (instructor must re-enter or use tiebreaker rule)
- Tiebreaker options:
  - Re-enter scores
  - Sudden death (1 additional goal)
  - Penalty shootout (separate score entry)

**Edge Cases**:
- What if tie in knockout? → Must have tiebreaker or replay
- What if instructor enters Round 2 before Round 1 complete? → Block
- What if participant drops out mid-tournament? → Forfeit (opponent auto-advances)
- Can instructor edit knockout results? → Yes, but may invalidate subsequent rounds

---

## Database Schema Integration

### Existing Tables

**`sessions`**:
- `id`: Session ID
- `semester_id`: Tournament ID
- `session_status`: 'scheduled' | 'completed' | 'cancelled'
- `game_results`: JSONB - stores match results
- `match_format`: 'INDIVIDUAL_RANKING' | 'HEAD_TO_HEAD'

**`session_participants`**:
- `session_id`: FK to sessions
- `user_id`: FK to users
- `attendance_status`: 'present' | 'absent'
- `performance_notes`: Text

**`tournament_rankings`**:
- `tournament_id`: FK to semesters
- `user_id`: FK to users
- `rank`: Integer (1, 2, 3, ...)
- `total_points`: Integer (for league: win/tie/loss points)

### Proposed `game_results` JSONB Schema

#### League Format:
```json
{
  "match_format": "HEAD_TO_HEAD",
  "tournament_type": "league",
  "participants": [
    {
      "user_id": 4,
      "score": 3,
      "result": "win"  // "win" | "tie" | "loss"
    },
    {
      "user_id": 5,
      "score": 1,
      "result": "loss"
    }
  ],
  "winner_user_id": 4,  // null if tie
  "match_status": "completed",
  "submitted_at": "2026-02-04T10:30:00Z",
  "submitted_by": 1  // instructor user_id
}
```

#### Knockout Format:
```json
{
  "match_format": "HEAD_TO_HEAD",
  "tournament_type": "knockout",
  "round_number": 1,  // 1 = Round 1, 2 = Semifinals, 3 = Final
  "match_number": 1,  // Match order within round
  "participants": [
    {
      "user_id": 4,
      "score": 2,
      "result": "win"
    },
    {
      "user_id": 5,
      "score": 1,
      "result": "loss"
    }
  ],
  "winner_user_id": 4,
  "match_status": "completed",
  "advances_to_round": 2,  // Winner advances to round 2
  "advances_to_match": 1,  // Winner goes to match 1 in round 2
  "submitted_at": "2026-02-04T10:30:00Z",
  "submitted_by": 1
}
```

---

## Reward Distribution Integration

### Current Reward Orchestrator Assumptions

**File**: `app/services/tournament/tournament_reward_orchestrator.py`

**Current Logic** (lines 401-406):
```python
# Get all rankings
rankings = db.query(TournamentRanking).filter(
    TournamentRanking.tournament_id == tournament_id
).all()

if not rankings:
    raise ValueError(f"No rankings found for tournament {tournament_id}")
```

**Problem**: HEAD_TO_HEAD tournaments need rankings calculated from match results.

### Proposed Ranking Calculation Logic

#### League Format:
1. Read all session results for tournament
2. Calculate points per participant:
   - Win = 3 points
   - Tie = 1 point
   - Loss = 0 points
3. Aggregate total points per user
4. Rank by total points (DESC)
5. Tiebreaker: Head-to-head record → Goal difference → Goals scored
6. Insert into `tournament_rankings` table

#### Knockout Format:
1. Identify final match winner → Rank 1
2. Identify final match loser → Rank 2
3. Identify semifinal losers → Rank 3 (tie)
4. Identify quarterfinal losers → Rank 5 (tie)
5. Insert into `tournament_rankings` table

**API Endpoint** (new):
```
POST /api/v1/tournaments/{tournament_id}/calculate-rankings
```

**Business Logic**:
- Called automatically after all sessions finalized
- Idempotent (can be called multiple times)
- Updates `tournament_rankings` table

---

## Skill Rewards Integration

### Current Skill System

**Skills**: dribbling, passing, shooting, defending, fitness, teamwork, leadership, etc.

**Reward Logic**:
- Top N winners (configured per tournament) get skill rewards
- Skills selected by tournament creator (e.g., ["dribbling", "passing", "shooting"])
- Reward amount: Based on rank (1st place = highest reward)

### HEAD_TO_HEAD Skill Attribution

**Challenge**: HEAD_TO_HEAD matches don't have individual skill tracking like INDIVIDUAL tournaments.

**Proposed Solution**:
1. **Skill rewards based on final rank** (same as INDIVIDUAL)
2. **No per-match skill tracking** (matches are team-based)
3. **Skills to reward** selected at tournament creation
4. **Distribution**: Top N winners get equal skill boosts to selected skills

**Example**:
- Tournament: HEAD_TO_HEAD League
- Skills to reward: ["dribbling", "passing", "shooting"]
- Winner count: 3
- Results:
  - Rank 1: +50 dribbling, +50 passing, +50 shooting
  - Rank 2: +30 dribbling, +30 passing, +30 shooting
  - Rank 3: +10 dribbling, +10 passing, +10 shooting

---

## Edge Cases & Validation Rules

### Universal Rules
1. ✅ All participants must have `attendance_status = 'present'` to submit results
2. ✅ Scores must be non-negative integers
3. ✅ Both participants must have scores entered (no null/blank)
4. ✅ Cannot finalize tournament until all matches submitted
5. ✅ Cannot distribute rewards until tournament finalized

### League-Specific Rules
1. ✅ All matches must be completed before finalization
2. ✅ Ties are allowed (equal scores)
3. ✅ No minimum/maximum score requirements

### Knockout-Specific Rules
1. ✅ Ties require tiebreaker or replay
2. ✅ Cannot advance to next round until current round complete
3. ✅ Bracket must be balanced (power of 2 participants)
4. ✅ Forfeit handling: Opponent auto-advances (no score required)

### Result Editing Rules
1. ✅ Can edit results before finalization
2. ✅ Cannot edit after finalization (data integrity)
3. ✅ Editing knockout results may invalidate subsequent rounds (warn instructor)

---

## UI/UX Design (Streamlit)

### Layout Structure

```
Step 4: Enter Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tournament: [Tournament Name]
Format: [League / Knockout]
Total Matches: [X]
Completed: [Y / X] ✅ [Progress Bar]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[IF LEAGUE]
  📋 All Matches (Round Robin)

  Match 1: Player A vs Player B
  ┌─────────────────────────────────────┐
  │ Player A Score: [___] (0-99)        │
  │ Player B Score: [___] (0-99)        │
  │ Status: ⚪ Not Submitted             │
  │ [Submit Match Results] 🟢           │
  └─────────────────────────────────────┘

  Match 2: Player C vs Player D
  ┌─────────────────────────────────────┐
  │ Player C Score: [3] ✅               │
  │ Player D Score: [1] ✅               │
  │ Status: ✅ Submitted                 │
  │ Winner: Player C                    │
  │ [Edit Results] 🔄                   │
  └─────────────────────────────────────┘

  [Continue to Finalization] (Disabled until all matches submitted)

[IF KNOCKOUT]
  🏆 Round 1: Quarterfinals (4 matches)

  Match 1: Player A vs Player B
  ┌─────────────────────────────────────┐
  │ Player A Score: [___] (0-99)        │
  │ Player B Score: [___] (0-99)        │
  │ Winner Advances: [○ A  ○ B  ○ Tie] │
  │ Status: ⚪ Not Submitted             │
  │ [Submit Match Results] 🟢           │
  └─────────────────────────────────────┘

  [... 3 more matches ...]

  🏆 Round 2: Semifinals (2 matches)
  ⚠️  Complete Round 1 first to unlock

  🏆 Round 3: Final (1 match)
  ⚠️  Complete Round 2 first to unlock

  [Continue to Finalization] (Disabled until all rounds complete)
```

### Streamlit Components

**Score Input**:
```python
st.number_input(
    f"{participant_a_name} Score",
    min_value=0,
    max_value=99,
    step=1,
    key=f"score_{session_id}_{participant_a_id}"
)
```

**Winner Selection (Knockout)**:
```python
winner = st.radio(
    "Winner",
    options=[participant_a_name, participant_b_name, "Tie → Tiebreaker"],
    key=f"winner_{session_id}"
)
```

**Submit Button**:
```python
if st.button(f"Submit Match {match_number} Results", key=f"submit_{session_id}"):
    # Validate scores
    # Call API: POST /api/v1/sessions/{session_id}/submit-results
    # Show success message
    st.rerun()
```

---

## Implementation Plan

### Phase 1: Backend - League Support (P0)
1. ✅ Create `submit_head_to_head_result()` API endpoint
2. ✅ Validate score input (both participants, non-negative)
3. ✅ Update `session.game_results` JSONB with match data
4. ✅ Update `session.session_status` to 'completed'
5. ✅ Create `calculate_league_rankings()` function
6. ✅ Insert/update `tournament_rankings` table

### Phase 2: Frontend - League UI (P0)
1. ✅ Render all league matches with score inputs
2. ✅ Submit button per match (API call)
3. ✅ Show submitted/not submitted status
4. ✅ Enable "Continue to Finalization" when all matches complete
5. ✅ Add edit functionality for submitted results

### Phase 3: Backend - Knockout Support (P1)
1. ✅ Create `calculate_knockout_bracket()` function
2. ✅ Validate round progression (can't skip rounds)
3. ✅ Handle tiebreaker logic
4. ✅ Create `calculate_knockout_rankings()` function
5. ✅ Update bracket advancement logic

### Phase 4: Frontend - Knockout UI (P1)
1. ✅ Render matches grouped by rounds
2. ✅ Lock subsequent rounds until previous complete
3. ✅ Winner selection radio buttons
4. ✅ Show bracket progression visually
5. ✅ Handle tiebreaker/replay flow

### Phase 5: Reward Distribution (P1)
1. ✅ Update reward orchestrator to support HEAD_TO_HEAD
2. ✅ Read rankings from `tournament_rankings` table
3. ✅ Distribute XP, credits, and skill rewards
4. ✅ Test with both league and knockout formats

### Phase 6: E2E Testing (P2)
1. ✅ Add full config matrix to HEAD_TO_HEAD test suite
2. ✅ Run all 18+ config combinations
3. ✅ Validate reward distribution
4. ✅ Verify skill tracking integration

---

## Open Questions

1. **Tiebreaker Rule for Knockout**:
   - Automatic replay with re-entry?
   - Sudden death (first to score)?
   - Penalty shootout?
   - → **Decision needed from Product/User**

2. **Skill Attribution Accuracy**:
   - Should HEAD_TO_HEAD track per-match skills?
   - Or only final ranking-based rewards?
   - → **Current proposal**: Ranking-based only (simpler)

3. **Forfeits & No-Shows**:
   - What if participant doesn't show up?
   - Auto-forfeit or manual instructor action?
   - → **Proposed**: Manual forfeit button per match

4. **Match Scheduling**:
   - Are all matches in a tournament on the same day?
   - Or spread across multiple sessions?
   - → **Assumption**: All matches in one session for now

5. **XP/Credit Distribution Logic**:
   - Same as INDIVIDUAL (rank-based)?
   - Or match-win-based (XP per win)?
   - → **Current proposal**: Same as INDIVIDUAL (rank-based)

---

## Success Criteria

✅ **Phase 1+2 Complete**:
- Instructor can enter league match results via UI
- All matches show submitted status
- Rankings calculated correctly
- Reward distribution works

✅ **Phase 3+4 Complete**:
- Instructor can enter knockout match results
- Bracket progression enforced
- Winners advance correctly
- Final rankings match bracket results

✅ **Full E2E Tests Pass**:
- HEAD_TO_HEAD test suite runs 18+ configs
- All tests PASS (not SKIP)
- No regression in INDIVIDUAL suite

---

**Next Step**: Review this design with user, get approval on:
1. Tiebreaker rules (knockout)
2. Skill attribution logic
3. Forfeit handling
4. XP/credit distribution

Once approved → Begin Phase 1 implementation.
