# INDIVIDUAL Tournament Complete Flow Documentation

**Date**: 2026-01-31
**Status**: ✅ VERIFIED & WORKING
**Test Tournament**: #211 (successful end-to-end)

---

## Flow Overview

INDIVIDUAL tournaments use a **round-based incremental workflow** where each round is submitted separately, then aggregated at the end.

```
┌─────────────────────────────────────────────────────────────┐
│                  COMPLETE WORKFLOW                           │
└─────────────────────────────────────────────────────────────┘

Step 1: Create Tournament
  └─ tournament_type_id = NULL ✅
  └─ game_preset_id = NULL ✅
  └─ format = "INDIVIDUAL_RANKING" ✅
  └─ scoring_type = SCORE_BASED / TIME_BASED / DISTANCE_BASED

Step 2: Generate Sessions
  └─ POST /tournaments/{id}/generate-sessions
  └─ Creates 1 session with rounds_data structure
  └─ Session stores: total_rounds, completed_rounds=0, round_results={}

Step 3: Track Attendance
  └─ Mark which players attended
  └─ Session status: PENDING → IN_PROGRESS

Step 4: Score Entry (Round-by-Round)
  ├─ Round 1 Entry
  │   └─ POST /sessions/{sid}/rounds/1/submit-results
  │   └─ Updates: rounds_data.round_results["1"] = {user_id: value}
  ├─ Round 2 Entry
  │   └─ POST /sessions/{sid}/rounds/2/submit-results
  │   └─ Updates: rounds_data.round_results["2"] = {user_id: value}
  └─ ... (continue for all rounds)

Step 5: Finalize Session
  └─ POST /sessions/{sid}/finalize
  └─ Aggregates all rounds (finds BEST value per player)
  └─ Calculates final rankings
  └─ Stores in: session.game_results

Step 6: Complete Tournament
  └─ All sessions finalized
  └─ Tournament rankings calculated
  └─ Rewards distributed
```

---

## Data Structures

### Session Model (During Entry)

**Field**: `rounds_data` (JSONB)

**Structure**:
```json
{
  "total_rounds": 3,
  "completed_rounds": 2,
  "round_results": {
    "1": {
      "123": "12.5s",
      "456": "13.2s",
      "789": "14.0s"
    },
    "2": {
      "123": "12.0s",
      "456": "13.8s",
      "789": "13.5s"
    }
  }
}
```

**Key Points**:
- `total_rounds`: Configured at session creation (from tournament config)
- `completed_rounds`: Auto-calculated from `len(round_results.keys())`
- `round_results`: Dict of dicts
  - Outer key: round_number (as string "1", "2", "3")
  - Inner key: user_id (as string)
  - Value: measured result (string with unit, e.g., "12.5s", "150 points")

---

### Session Model (After Finalization)

**Field**: `game_results` (JSONB)

**Structure**:
```json
{
  "recorded_at": "2026-01-31T18:00:00Z",
  "tournament_format": "INDIVIDUAL_RANKING",
  "scoring_type": "SCORE_BASED",
  "ranking_direction": "DESC",
  "total_rounds": 3,
  "aggregation_method": "BEST_VALUE",
  "rounds_data": {
    "total_rounds": 3,
    "completed_rounds": 3,
    "round_results": {...}
  },
  "derived_rankings": [
    {
      "user_id": 123,
      "rank": 1,
      "final_value": 12.0,
      "best_round": 2,
      "all_rounds": ["12.5s", "12.0s", "12.3s"]
    },
    {
      "user_id": 456,
      "rank": 2,
      "final_value": 13.2,
      "best_round": 1,
      "all_rounds": ["13.2s", "13.8s", "14.0s"]
    }
  ],
  "performance_rankings": [...],
  "wins_rankings": [...]
}
```

**Aggregation Logic**:
- **BEST_VALUE**: Takes the best (min for TIME, max for SCORE/DISTANCE) across all rounds
- **Ranking Direction**:
  - TIME_BASED: ASC (lower is better)
  - SCORE_BASED: DESC (higher is better)
  - DISTANCE_BASED: DESC (further is better)

---

## API Endpoints

### 1. Session Generation
```
POST /api/v1/tournaments/{tournament_id}/generate-sessions

Request:
{
  "parallel_fields": 1,
  "session_duration_minutes": 90,
  "break_minutes": 15,
  "number_of_rounds": 3
}

Response: 200 OK
{
  "success": true,
  "message": "Successfully generated 1 tournament sessions for 8 enrolled players",
  "tournament_id": 211,
  "sessions_generated_count": 1,
  "sessions": [...]
}
```

**What it does**:
- Calls `IndividualRankingGenerator.generate()`
- Creates 1 session with `rounds_data` initialized
- Sets `session.tournament_phase = "INDIVIDUAL_RANKING"`
- Sets `session.rounds_data = {"total_rounds": 3, "completed_rounds": 0, "round_results": {}}`

---

### 2. Get Sessions
```
GET /api/v1/tournaments/{tournament_id}/sessions

Response: 200 OK
[
  {
    "id": 1412,
    "title": "LFA Sandbox Tournament",
    "description": "3 rounds - All players compete - highest score wins",
    "match_format": "INDIVIDUAL_RANKING",
    "scoring_type": "SCORE_BASED",
    "rounds_data": {
      "total_rounds": 3,
      "completed_rounds": 0,
      "round_results": {}
    },
    "participant_user_ids": [6, 4, 16, 13, 5, 7, 14, 15],
    "structure_config": {
      "number_of_rounds": 3,
      "scoring_method": "SCORE_BASED",
      "expected_participants": 8
    }
  }
]
```

---

### 3. Submit Round Results
```
POST /api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds/{round_number}/submit-results

Request:
{
  "results": {
    "123": "150",
    "456": "145",
    "789": "140"
  }
}

Response: 200 OK
{
  "success": true,
  "message": "Round 1 results submitted successfully",
  "round_number": 1,
  "completed_rounds": 1,
  "total_rounds": 3
}
```

**What it does** (submission.py:343-431):
1. Validates session is `INDIVIDUAL_RANKING` format
2. Validates round_number is between 1 and total_rounds
3. Validates instructor authorization
4. Updates `rounds_data.round_results[str(round_number)]` = results
5. Recalculates `completed_rounds = len(round_results.keys())`
6. **Idempotent**: Can resubmit same round to overwrite

---

### 4. Get Round Status
```
GET /api/v1/tournaments/{tournament_id}/sessions/{session_id}/rounds

Response: 200 OK
{
  "total_rounds": 3,
  "completed_rounds": 2,
  "pending_rounds": [3],
  "round_results": {
    "1": {...},
    "2": {...}
  },
  "is_complete": false
}
```

**What it does** (round_management.py:73-123):
- Returns current state of rounds_data
- Identifies which rounds are pending
- Shows which rounds have been completed

---

### 5. Finalize Session
```
POST /api/v1/tournaments/{tournament_id}/sessions/{session_id}/finalize

Response: 200 OK
{
  "success": true,
  "message": "Session finalized successfully",
  "rankings": [
    {"user_id": 123, "rank": 1, "final_value": 150},
    {"user_id": 456, "rank": 2, "final_value": 145}
  ]
}
```

**What it does** (finalization.py + SessionFinalizer):
1. Validates all rounds completed (`completed_rounds == total_rounds`)
2. Calls `RankingAggregator.aggregate_rankings()`
   - Extracts all user results across rounds
   - Finds BEST value per user (min for TIME, max for SCORE/DISTANCE)
   - Sorts by final value (ASC for TIME, DESC for SCORE/DISTANCE)
   - Assigns ranks (1, 2, 3, ...)
3. Saves to `session.game_results` (full structure above)
4. Updates `tournament_rankings` table
5. Returns final rankings

---

## Streamlit UI Flow

### Step 4: Score Entry

**File**: `streamlit_app/components/tournaments/instructor/match_command_center.py`

**Flow**:
1. Detects `match_format == "INDIVIDUAL_RANKING"`
2. Calls `render_rounds_based_entry(match, num_rounds)`
3. Renders separate card for each round (Round 1, Round 2, Round 3)
4. Each card has:
   - Input fields for each participant
   - Submit button for that specific round
   - Status indicator (✅ submitted, ⏳ pending)

**Helper**: `match_command_center_helpers.py:86-97`
```python
def submit_round_results(match_id, round_number, results):
    response = requests.post(
        f"{API_BASE}/tournaments/{tournament_id}/sessions/{match_id}/rounds/{round_number}/submit-results",
        json={"results": results}
    )
    return response.json()
```

---

## Key Architectural Points

### ✅ Round-Based (NOT Match-Based)
- INDIVIDUAL tournaments do NOT have separate "matches"
- The **session IS the match**
- Multiple rounds within a single session
- Each round submitted independently

### ✅ Incremental Workflow
- Cannot skip rounds (Round 2 before Round 1)
- Can resubmit rounds for corrections
- UI guides instructor through rounds sequentially

### ✅ Idempotent Submissions
- Resubmitting Round 1 overwrites previous Round 1 data
- Useful for correcting data entry errors
- No duplicate round entries possible

### ✅ Aggregation at Finalization
- Raw round data preserved in `rounds_data`
- Aggregated rankings calculated during finalization
- Uses `BEST_VALUE` aggregation method

### ✅ No Bulk Entry
- No endpoint to submit all rounds at once
- Enforces round-by-round workflow
- Reduces data entry errors

---

## Storage Flow

```
Session Creation:
  rounds_data = {
    "total_rounds": 3,
    "completed_rounds": 0,
    "round_results": {}
  }
  ↓

After Round 1 Submission:
  rounds_data = {
    "total_rounds": 3,
    "completed_rounds": 1,
    "round_results": {
      "1": {"123": "12.5s", "456": "13.2s"}
    }
  }
  ↓

After Round 2 Submission:
  rounds_data = {
    "total_rounds": 3,
    "completed_rounds": 2,
    "round_results": {
      "1": {"123": "12.5s", "456": "13.2s"},
      "2": {"123": "12.0s", "456": "13.8s"}
    }
  }
  ↓

After Round 3 Submission:
  rounds_data = {
    "total_rounds": 3,
    "completed_rounds": 3,
    "round_results": {
      "1": {"123": "12.5s", "456": "13.2s"},
      "2": {"123": "12.0s", "456": "13.8s"},
      "3": {"123": "12.3s", "456": "14.0s"}
    }
  }
  ↓

After Finalization:
  game_results = {
    "recorded_at": "...",
    "tournament_format": "INDIVIDUAL_RANKING",
    "aggregation_method": "BEST_VALUE",
    "derived_rankings": [
      {"user_id": 123, "rank": 1, "final_value": 12.0, "best_round": 2},
      {"user_id": 456, "rank": 2, "final_value": 13.2, "best_round": 1}
    ]
  }
```

---

## Example: 100m Sprint (TIME_BASED)

**Configuration**:
- scoring_type: TIME_BASED
- ranking_direction: ASC (lower is better)
- number_of_rounds: 3 (3 attempts)
- measurement_unit: "seconds"

**Round Entry**:
```
Round 1:
  User 123 → 12.5s
  User 456 → 13.2s

Round 2:
  User 123 → 12.0s ← BEST
  User 456 → 13.8s

Round 3:
  User 123 → 12.3s
  User 456 → 13.0s ← BEST
```

**Final Rankings** (after aggregation):
```
Rank 1: User 123 (12.0s from Round 2)
Rank 2: User 456 (13.0s from Round 3)
```

---

## Testing Reference

**Test File**: `tests/tournament_types/test_multi_round_api.sh`
**Lines**: 290-326

**Complete Workflow Test**:
1. Create INDIVIDUAL tournament
2. Generate sessions
3. Submit Round 1 results
4. Submit Round 2 results
5. Submit Round 3 results
6. Finalize session
7. Verify rankings

---

## Related Files

**API Endpoints**:
- `app/api/api_v1/endpoints/tournaments/results/submission.py` (round submission)
- `app/api/api_v1/endpoints/tournaments/results/round_management.py` (round status)
- `app/api/api_v1/endpoints/tournaments/results/finalization.py` (finalize session)
- `app/api/api_v1/endpoints/tournaments/generate_sessions.py` (session generation + GET)

**Services**:
- `app/services/tournament/results/finalization/session_finalizer.py` (aggregation logic)
- `app/services/tournament/results/finalization/ranking_aggregator.py` (best value calculation)
- `app/services/tournament/session_generation/formats/individual_ranking_generator.py` (session creation)

**Streamlit UI**:
- `streamlit_app/components/tournaments/instructor/match_command_center.py` (main workflow)
- `streamlit_app/components/tournaments/instructor/match_command_center_screens.py` (round UI)
- `streamlit_app/components/tournaments/instructor/match_command_center_helpers.py` (API helpers)

**Models**:
- `app/models/session.py` (rounds_data, game_results storage)
- `app/models/semester.py` (tournament configuration)

---

## Summary

**INDIVIDUAL tournaments use a round-based incremental workflow**:
1. ✅ Sessions generated with `rounds_data` structure
2. ✅ Each round submitted separately via API
3. ✅ Round results stored in `rounds_data.round_results[round_number]`
4. ✅ Finalization aggregates all rounds (BEST value)
5. ✅ Final rankings stored in `session.game_results`
6. ✅ UI guides instructor through rounds sequentially

**No separate match-level logic** - the session IS the match with multiple rounds.

**Step 4 (Score Entry) handles EVERYTHING** - all round submissions happen in this step.
