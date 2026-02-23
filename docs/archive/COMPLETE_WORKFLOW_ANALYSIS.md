# TELJES INSTRUCTOR WORKFLOW ELEMZÉS

## 🎯 Cél
A **teljes Create New Tournament workflow** backend + frontend elemzése,
elejétől (Home screen) a végéig (Results megjelenítése).

---

## 1. BACKEND API ENDPOINTS - Teljes Flow

### 1.1 **Quick Test Mode** (Auto-complete)

#### API Call Sequence:
```
POST /api/v1/sandbox/run-test
```

**Input Payload**:
```json
{
  "tournament_type": "league|knockout|hybrid",
  "skills_to_test": ["passing", "dribbling", ...],
  "player_count": 4-16,
  "test_config": {
    "performance_variation": "LOW|MEDIUM|HIGH",
    "ranking_distribution": "NORMAL|TOP_HEAVY|BOTTOM_HEAVY",
    "game_preset_id": null | int,
    "game_config_overrides": null | {}
  }
}
```

**Backend Process** (`SandboxTestOrchestrator.execute_test()`):
1. **Create Tournament** (`_create_tournament()`)
   - Creates Tournament record (DRAFT status)
   - Creates TournamentRewardConfig (P1)
   - Creates TournamentConfiguration (P2)
   - Creates GameConfiguration (P3) if preset provided

2. **Enroll Participants** (`_enroll_participants()`)
   - Selects `player_count` users from TEST_USER_POOL
   - Creates UserLicense records
   - Creates SemesterEnrollment records
   - Creates TournamentEnrollment records

3. **Snapshot Skills Before** (`_snapshot_skills_before()`)
   - Reads current skill values for all enrolled users
   - Stores in memory for later comparison

4. **Generate Rankings** (`_generate_rankings()`)
   - Creates synthetic match results
   - Creates TournamentRanking records (rank 1..N)
   - Sets final_placement for each user

5. **Transition to COMPLETED** (`_transition_to_completed()`)
   - Updates Tournament.status = "COMPLETED"
   - Updates Tournament.end_date = now

6. **Distribute Rewards** (`_distribute_rewards()`)
   - Calls `tournament_reward_orchestrator.distribute_rewards_v2()`
   - Calculates XP based on:
     - Placement bonuses
     - Skill mappings
     - Participation bonuses
   - Applies XP to user skills
   - Creates TournamentReward records
   - Creates UserBadge records (if achievements earned)
   - Updates Tournament.status = "REWARDS_DISTRIBUTED"

7. **Calculate Verdict** (`_calculate_verdict()`)
   - Compares skills_before vs skills_after
   - Identifies top/bottom performers
   - Generates insights
   - Returns verdict: "WORKING" | "DEGRADED" | "NOT_WORKING"

**Output Payload**:
```json
{
  "verdict": "WORKING",
  "test_run_id": "sandbox-2026-01-29-20-15-42-1234",
  "tournament": {
    "id": 175,
    "name": "SANDBOX-TEST-LEAGUE-2026-01-29",
    "type": "LEAGUE",
    "status": "REWARDS_DISTRIBUTED",
    "player_count": 8,
    "skills_tested": ["passing", "dribbling"]
  },
  "execution_summary": {
    "duration_seconds": 2.45,
    "steps_completed": ["CREATE", "ENROLL", "RANK", "COMPLETE", "REWARD", "VERDICT"]
  },
  "skill_progression": {
    "user_4": {"passing": {"before": 65.0, "after": 68.5, "delta": +3.5}},
    ...
  },
  "top_performers": [...],
  "bottom_performers": [...],
  "insights": [...],
  "export_data": {"pdf_ready": true, "export_url": "/api/v1/sandbox/export-pdf/..."}
}
```

---

### 1.2 **Instructor Workflow Mode** (Step-by-step)

**DOES NOT USE `/api/v1/sandbox/run-test`**

Instead uses **standard tournament lifecycle endpoints**:

#### Step 0: Configuration (Hidden from UI - happens on "Create Tournament" click)

##### API: `POST /api/v1/tournaments/`
**Location**: `app/api/api_v1/endpoints/tournaments/lifecycle.py:167`

**Input**:
```json
{
  "name": "Test Tournament 2026-01-29",
  "tournament_type_id": 1,
  "semester_id": 1,
  "campus": "offline",
  "location": "Budapest",
  "date_start": "2026-02-01T10:00:00",
  "date_end": "2026-02-01T18:00:00",
  "enrollment_deadline": "2026-01-31T23:59:59",
  "min_participants": 4,
  "max_participants": 16,
  "reward_config": {
    "placement_bonuses": [...],
    "skill_mappings": [...]
  },
  "tournament_config": {
    "rounds": 2,
    "groups": 2,
    "advancement_rules": {...}
  },
  "game_config": {
    "game_preset_id": 1,
    "overrides": {...}
  }
}
```

**Backend**:
- Creates Tournament (status=DRAFT)
- Creates TournamentRewardConfig (P1)
- Creates TournamentConfiguration (P2)
- Creates GameConfiguration (P3)

**Output**:
```json
{
  "id": 176,
  "name": "Test Tournament 2026-01-29",
  "status": "DRAFT",
  "tournament_type": {...},
  "reward_config": {...},
  "tournament_config": {...},
  "game_config": {...}
}
```

---

#### Step 1: Create Tournament
**User sees**: Tournament created confirmation
**Backend**: Already created in Step 0
**No API call** - tournament ID stored in `st.session_state.tournament_id`

---

#### Step 2: Track Attendance

##### API: `GET /api/v1/tournaments/{tournament_id}/`
**Purpose**: Fetch tournament details to show enrollment status

**Output**:
```json
{
  "id": 176,
  "name": "Test Tournament",
  "status": "DRAFT",
  "enrollments": [
    {"user_id": 4, "user": {"name": "John Doe", "email": "john@test.com"}},
    ...
  ],
  "current_participant_count": 8,
  "min_participants": 4,
  "max_participants": 16
}
```

**Instructor Actions**:
- Views enrolled participants
- Clicks "Start Tournament" when ready

##### API: `PATCH /api/v1/tournaments/{tournament_id}/status`
**Location**: `app/api/api_v1/endpoints/tournaments/lifecycle.py:258`

**Input**:
```json
{
  "status": "IN_PROGRESS",
  "transition_reason": "Instructor started tournament"
}
```

**Backend**:
- Validates status transition (DRAFT → IN_PROGRESS)
- Updates Tournament.status = "IN_PROGRESS"
- Updates Tournament.start_date = now
- Creates StatusHistory record

**Output**:
```json
{
  "success": true,
  "tournament_id": 176,
  "old_status": "DRAFT",
  "new_status": "IN_PROGRESS",
  "transitioned_at": "2026-01-29T20:30:00"
}
```

---

#### Step 3: Enter Results

##### API: `GET /api/v1/tournaments/{tournament_id}/sessions`
**Purpose**: Fetch all sessions (matches) for the tournament

**Output**:
```json
{
  "sessions": [
    {
      "id": 1001,
      "date_start": "2026-02-01T10:00:00",
      "participants": [{"user_id": 4, "name": "John"}, {"user_id": 5, "name": "Jane"}],
      "result": null,  // Not yet entered
      "status": "PENDING"
    },
    ...
  ]
}
```

**Instructor Actions**:
- Selects a session
- Enters match results (winner, scores, etc.)

##### API: `POST /api/v1/tournaments/{tournament_id}/sessions/{session_id}/submit-results`
**Location**: `app/api/api_v1/endpoints/tournaments/match_results.py:103`

**Input**:
```json
{
  "winner_id": 4,
  "score_team_a": 10,
  "score_team_b": 7,
  "match_duration_minutes": 45,
  "notes": "Great match"
}
```

**Backend**:
- Validates session exists and is PENDING
- Creates MatchResult record
- Updates Session.result_id
- Updates Session.status = "COMPLETED"
- Updates tournament standings/rankings

**Output**:
```json
{
  "success": true,
  "session_id": 1001,
  "result_id": 501,
  "winner": {"id": 4, "name": "John Doe"},
  "standings_updated": true
}
```

**Repeat** for all sessions.

---

#### Step 4: View Leaderboard

##### API: `GET /api/v1/tournaments/{tournament_id}/leaderboard`
**Location**: `app/api/api_v1/endpoints/tournaments/instructor.py:297`

**Output**:
```json
{
  "tournament_id": 176,
  "leaderboard": [
    {
      "rank": 1,
      "user_id": 4,
      "user_name": "John Doe",
      "wins": 3,
      "losses": 0,
      "points": 9,
      "goal_diff": +12
    },
    ...
  ],
  "final_standings": null  // Not finalized yet
}
```

**Instructor Actions**:
- Reviews standings
- Clicks "Finalize Tournament"

##### API: `POST /api/v1/tournaments/{tournament_id}/finalize-tournament`
**Location**: `app/api/api_v1/endpoints/tournaments/match_results.py:632`

**Backend**:
- Validates all sessions completed
- Calculates final rankings
- Creates TournamentRanking records
- Updates Tournament.status = "COMPLETED"
- Updates Tournament.end_date = now
- Stores final_standings JSON

**Output**:
```json
{
  "success": true,
  "tournament_id": 176,
  "status": "COMPLETED",
  "final_standings": [
    {"rank": 1, "user_id": 4, "user_name": "John Doe", "points": 9},
    ...
  ]
}
```

---

#### Step 5: Distribute Rewards

##### API: `POST /api/v1/tournaments/{tournament_id}/distribute-rewards-v2`
**Location**: `app/api/api_v1/endpoints/tournaments/rewards_v2.py:32`

**Backend** (`tournament_reward_orchestrator.distribute_rewards_v2()`):
1. Fetches Tournament, TournamentRewardConfig, GameConfiguration
2. For each ranked user:
   - Calculates placement bonus (from reward_config)
   - Calculates skill XP (from skill_mappings × game_config)
   - Applies XP to user skills
   - Creates TournamentReward record
3. Checks for badge achievements
4. Creates UserBadge records if earned
5. Updates Tournament.status = "REWARDS_DISTRIBUTED"

**Output**:
```json
{
  "success": true,
  "tournament_id": 176,
  "rewards_distributed": 8,
  "total_xp_awarded": 450,
  "badges_awarded": 2,
  "distribution_summary": {
    "user_4": {"placement_bonus": 50, "skill_xp": 35, "total": 85, "badges": ["Gold Winner"]},
    ...
  }
}
```

---

#### Step 6: View Results

##### API: `GET /api/v1/tournaments/{tournament_id}/`
**Purpose**: Fetch complete tournament with final results

**Output**:
```json
{
  "id": 176,
  "name": "Test Tournament",
  "status": "REWARDS_DISTRIBUTED",
  "final_standings": [...],
  "reward_distribution": {...},
  "badges_awarded": [...],
  "skill_progression": {
    "user_4": {"passing": {"before": 65.0, "after": 68.5, "delta": +3.5}},
    ...
  }
}
```

---

## 2. FRONTEND UI INTERACTIONS - Session State Flow

### 2.1 Screen Navigation

**Streamlit uses**:
- `st.session_state.screen` - Current screen name
- `st.session_state.workflow_step` - Current step in instructor workflow (1-6)
- `st.session_state.tournament_config` - Tournament configuration
- `st.session_state.tournament_id` - Created tournament ID
- `st.session_state.tournament_result` - Tournament results data
- `st.session_state.test_mode` - "quick" | "instructor"

**Screens**:
- `"home"` - Home screen with 2 buttons
- `"history"` - Tournament History Browser
- `"configuration"` - Tournament configuration form
- `"progress"` - Quick test running (auto-complete)
- `"results"` - Results display
- `"instructor_workflow"` - Step-by-step workflow (uses workflow_step 1-6)

---

### 2.2 Complete Flow - Quick Test Mode

#### Flow Diagram:
```
HOME
  ↓ (Click "➕ New Tournament")
  st.session_state.screen = "configuration"
  ↓
CONFIGURATION
  ↓ (Fill form, select "Quick Test", click "✅ Create Tournament")
  st.session_state.test_mode = "quick"
  st.session_state.tournament_config = {...}
  st.session_state.screen = "progress"
  ↓ (Auto-runs)
PROGRESS
  ↓ API: POST /api/v1/sandbox/run-test
  ↓ (Response received)
  st.session_state.tournament_result = response
  st.session_state.tournament_id = response.tournament.id
  st.session_state.screen = "results"
  ↓
RESULTS
  - Shows verdict, skill progression, top/bottom performers
  - Click "📊 View Tournament History" → screen = "history"
  - Click "🏠 New Tournament" → screen = "configuration"
```

**Code Locations**:
- Line 3053-3054: Click "New Tournament" → screen = "configuration"
- Line 1106-1112: Save config → test_mode → screen = "progress" or "instructor_workflow"
- Line 1140: Quick test completes → screen = "results"
- Line 3008-3013: From results, click "New Tournament" → screen = "configuration"

---

### 2.3 Complete Flow - Instructor Workflow Mode

#### Flow Diagram:
```
HOME
  ↓ (Click "➕ New Tournament")
  st.session_state.screen = "configuration"
  ↓
CONFIGURATION
  ↓ (Fill form, select "Instructor Workflow", click "✅ Create Tournament")
  st.session_state.test_mode = "instructor"
  st.session_state.tournament_config = {...}
  ↓ API: POST /api/v1/tournaments/ (creates tournament)
  st.session_state.tournament_id = response.id
  st.session_state.screen = "instructor_workflow"
  st.session_state.workflow_step = 1
  ↓
INSTRUCTOR WORKFLOW - Step 1: Create Tournament
  - Shows "Tournament Created" confirmation
  - Click "Continue" → workflow_step = 2
  ↓
Step 2: Track Attendance
  ↓ API: GET /api/v1/tournaments/{id}/ (fetch enrollments)
  - Shows enrolled participants list
  - Click "Start Tournament" →
    ↓ API: PATCH /api/v1/tournaments/{id}/status (DRAFT → IN_PROGRESS)
    workflow_step = 3
  ↓
Step 3: Enter Results
  ↓ API: GET /api/v1/tournaments/{id}/sessions (fetch all matches)
  - Shows match list
  - For each match:
    - Select match
    - Enter results
    ↓ API: POST /api/v1/tournaments/{id}/sessions/{sid}/submit-results
  - Click "Continue" → workflow_step = 4
  ↓
Step 4: View Leaderboard
  ↓ API: GET /api/v1/tournaments/{id}/leaderboard
  - Shows current standings
  - Click "Finalize Tournament" →
    ↓ API: POST /api/v1/tournaments/{id}/finalize-tournament
    workflow_step = 5
  ↓
Step 5: Distribute Rewards
  - Shows reward configuration
  - Click "Distribute Rewards" →
    ↓ API: POST /api/v1/tournaments/{id}/distribute-rewards-v2
    workflow_step = 6
  ↓
Step 6: View Results
  ↓ API: GET /api/v1/tournaments/{id}/ (fetch complete results)
  - Shows final standings, rewards, skill progression
  - Click "📊 View Tournament History" → screen = "history"
  - Click "🏠 New Tournament" → screen = "configuration"
```

**Code Locations**:
- Line 1201-1211: Render step based on `workflow_step`
- Line 1262: "Create Tournament" button click
- Line 1468-1474: Jump to step 6 or 2 based on auto-complete check
- Line 1563-1568: Step 1 → Step 3 or Step 2
- Line 1598: Start Tournament → Step 2
- Line 1624: All results entered → Step 3
- Line 1778: Navigate to Enter Results → Step 3
- Line 1860: Finalize → Step 4
- Line 2036: Return to Track Attendance → Step 2
- Line 2111/2123: Jump to Step 3
- Line 2127: Jump to Step 5
- Line 2206: Complete → Step 6
- Line 2385: Auto-complete detected → Step 6
- Line 2539: Reset → Step 1

---

## 3. STATE LIFECYCLE TRANSITIONS

### Tournament Status Flow:
```
DRAFT
  ↓ Instructor clicks "Start Tournament"
  ↓ API: PATCH /tournaments/{id}/status → IN_PROGRESS
IN_PROGRESS
  ↓ All matches completed, instructor clicks "Finalize"
  ↓ API: POST /tournaments/{id}/finalize-tournament
COMPLETED
  ↓ Instructor clicks "Distribute Rewards"
  ↓ API: POST /tournaments/{id}/distribute-rewards-v2
REWARDS_DISTRIBUTED
```

### Session Lifecycle:
```
Tournament created → Sessions generated
Session.status = PENDING
  ↓ Instructor submits result
  ↓ API: POST /sessions/{id}/submit-results
Session.status = COMPLETED
Session.result_id = <result_id>
```

---

## 4. KEY DATA STRUCTURES

### Tournament Record (P0):
```python
{
  "id": int,
  "name": str,
  "status": "DRAFT" | "IN_PROGRESS" | "COMPLETED" | "REWARDS_DISTRIBUTED",
  "tournament_type_id": int,
  "semester_id": int,
  "campus": str,
  "location": str,
  "date_start": datetime,
  "date_end": datetime,
  "enrollment_deadline": datetime,
  "min_participants": int,
  "max_participants": int,
  "instructor_id": int | None,
  "created_at": datetime
}
```

### TournamentRewardConfig (P1):
```python
{
  "id": int,
  "tournament_id": int,
  "placement_bonuses": [
    {"rank": 1, "xp": 50},
    {"rank": 2, "xp": 30},
    ...
  ],
  "skill_mappings": [
    {"skill": "passing", "weight": 1.0, "enabled": true},
    ...
  ],
  "participation_bonus": int
}
```

### TournamentConfiguration (P2):
```python
{
  "id": int,
  "tournament_id": int,
  "rounds": int,
  "groups": int,
  "advancement_rules": {...}
}
```

### GameConfiguration (P3):
```python
{
  "id": int,
  "tournament_id": int,
  "game_preset_id": int | None,
  "duration_minutes": int,
  "max_score": int,
  "skill_weights": {...}
}
```

---

## 5. CRITICAL BUG FIX LOCATIONS

### 🐛 Fixed: `reward_config = None` crash

**Lines Fixed**:
- `streamlit_sandbox_v3_admin_aligned.py:3194`
- `streamlit_sandbox_v3_admin_aligned.py:3239`

**Pattern**:
```python
# BEFORE (CRASHES):
skills = [s['skill'] for s in tournament.get('reward_config', {}).get('skill_mappings', [])]
# When reward_config IS None, .get('reward_config', {}) returns None (not {})
# Then None.get('skill_mappings') → AttributeError

# AFTER (SAFE):
skills = [s['skill'] for s in (tournament.get('reward_config') or {}).get('skill_mappings', [])]
# (None or {}) = {} → {}.get('skill_mappings') = [] → safe
```

**Why This Happens**:
- Quick test mode: reward_config created in-memory, never None
- Instructor mode: reward_config stored in DB, can be NULL
- History browser: Loads tournaments from DB, NULL → None in Python

---

## 6. MISSING PIECE: Continue Tournament from History

**Current Behavior**:
- Click "Continue Setup" (DRAFT) → tries to load `reward_config`
- Click "Continue Tournament" (IN_PROGRESS) → tries to load `reward_config`
- **CRASHES** if reward_config is None

**Fix Applied** (lines 3194, 3239):
```python
"skills_to_test": [
    s['skill']
    for s in (tournament_detail.get('reward_config') or {}).get('skill_mappings', [])
    if s.get('enabled', True)
]
```

**What Happens Next**:
1. User selects DRAFT tournament from history
2. Clicks "Continue Setup"
3. Frontend reconstructs tournament_config from tournament_detail
4. Sets `st.session_state.screen = "instructor_workflow"`
5. Sets `st.session_state.workflow_step = 1` (or appropriate step)
6. Workflow continues as normal

---

## 7. AUTO-COMPLETE DETECTION

**Logic** (line 1468):
```python
tournament_result = response.get("tournament_result") or {}
final_standings = tournament_result.get("final_standings")

if final_standings:
    # Tournament auto-completed (Quick Test mode)
    st.session_state.workflow_step = 6  # Jump to results
else:
    # Tournament needs manual workflow
    st.session_state.workflow_step = 2  # Start at Track Attendance
```

**When `final_standings` exists**:
- Tournament was created via Quick Test (`/api/v1/sandbox/run-test`)
- All lifecycle steps already completed
- Jump directly to Step 6 (View Results)

**When `final_standings` is None**:
- Tournament created via Instructor Workflow (`POST /api/v1/tournaments/`)
- Needs manual step-by-step progression
- Start at Step 2 (Track Attendance)

---

## 8. SUMMARY - Complete Flow Map

### Quick Test Mode:
```
1. Home → Click "New Tournament"
2. Configuration → Select "Quick Test", fill form, click "Create"
3. API: POST /api/v1/sandbox/run-test
   - Backend creates tournament, enrolls users, runs matches, distributes rewards
   - Returns complete result with verdict
4. Progress → Auto-waits for API response
5. Results → Shows complete results
6. Done → Can go to History or create New Tournament
```

### Instructor Workflow Mode:
```
1. Home → Click "New Tournament"
2. Configuration → Select "Instructor Workflow", fill form, click "Create"
3. API: POST /api/v1/tournaments/ → Creates DRAFT tournament
4. Step 1 (Create) → Confirmation → Continue
5. Step 2 (Track Attendance) → View enrollments → Start Tournament
   - API: PATCH status → IN_PROGRESS
6. Step 3 (Enter Results) → Submit each match result
   - API: POST submit-results (for each session)
7. Step 4 (View Leaderboard) → Review standings → Finalize
   - API: POST finalize-tournament → COMPLETED
8. Step 5 (Distribute Rewards) → Click "Distribute"
   - API: POST distribute-rewards-v2 → REWARDS_DISTRIBUTED
9. Step 6 (View Results) → Complete results
10. Done → Can go to History or create New Tournament
```

### Continue from History:
```
1. Home → Click "📚 Open History"
2. History Browser → Select tournament → Click "Continue Setup" or "Continue Tournament"
3. Frontend loads tournament_detail → reconstructs state
4. Sets screen = "instructor_workflow"
5. Sets workflow_step based on tournament status:
   - DRAFT → Step 2 (Track Attendance)
   - IN_PROGRESS → Step 3 (Enter Results)
   - COMPLETED → Step 5 (Distribute Rewards)
   - REWARDS_DISTRIBUTED → Step 6 (View Results)
6. Workflow continues from that step
```

---

## ✅ CONCLUSION

**Complete workflow analyzed**:
- ✅ Backend API endpoints identified (Quick Test vs Instructor)
- ✅ Frontend UI interactions mapped (session_state flow)
- ✅ State lifecycle transitions documented (DRAFT → REWARDS_DISTRIBUTED)
- ✅ Critical bug fix locations documented (reward_config None handling)
- ✅ Auto-complete detection logic explained
- ✅ Continue from History flow documented

**Next Step**: Create E2E Playwright tests covering the complete flow.
