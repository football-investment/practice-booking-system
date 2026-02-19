# Manual Test Guide - Scenario 1: Basic League Flow

**Tester**: User (Zoltan)
**Environment**: Streamlit Sandbox at http://localhost:8501
**Backend**: http://localhost:8000
**Database**: lfa_intern_system

---

## Prerequisites

1. ✅ Backend running: `http://localhost:8000`
2. ✅ Streamlit running: Open new terminal and run:
   ```bash
   cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
   streamlit run streamlit_sandbox_v3_admin_aligned.py
   ```
3. ✅ Browser open to: `http://localhost:8501`

---

## Step-by-Step Instructions

### Step 1: Create Tournament

**Action**:
1. In Streamlit sidebar, select **"Step 1: Tournament Creation"**
2. Fill in tournament details:
   - **Name**: `[TEST_H2H_LEAGUE] Basic Happy Path`
   - **Age Group**: AMATEUR (required)
   - **Scoring Mode**: Select **"HEAD_TO_HEAD"** from dropdown
   - **Tournament Format**: Select **"League (Round Robin)"**
   - **Skills to Test**: Check boxes for:
     - ✅ dribbling
     - ✅ passing
     - ✅ shooting
   - **Number of Winners**: `3`
   - **Max Players**: `4`
   - **Enrollment Cost**: `0` (free for testing)
3. Click **"Create Tournament"**

**Expected Result**:
- Green success message: "Tournament created successfully"
- Tournament ID displayed (note this number)
- Tournament appears in sidebar

**📝 Document**:
- Tournament ID: `_______`
- Any errors or warnings: `_______`
- Screenshot: (optional)

---

### Step 2: Enroll Participants

**Action**:
1. Navigate to **"Step 2: Player Enrollment"**
2. Select tournament from dropdown: `[TEST_H2H_LEAGUE] Basic Happy Path`
3. Enroll exactly 4 participants:
   - User ID: `2` (junior.intern@lfa.com)
   - User ID: `3` (senior.intern@lfa.com)
   - User ID: `4` (master.intern@lfa.com)
   - User ID: `5` (elite.intern@lfa.com)
4. For each participant, click **"Enroll Player"**

**Expected Result**:
- Success message for each enrollment
- 4 participants shown in enrollment list
- Can proceed to session generation

**📝 Document**:
- All 4 participants enrolled: `YES / NO`
- Any enrollment errors: `_______`

---

### Step 3: Generate Sessions (Matches)

**Action**:
1. Navigate to **"Step 3: Session Generation"**
2. Click **"Generate Sessions"**

**Expected Result**:
- Success message: "6 sessions generated"
- Sessions displayed in list below:
  ```
  Session 1: User 2 vs User 3
  Session 2: User 2 vs User 4
  Session 3: User 2 vs User 5
  Session 4: User 3 vs User 4
  Session 5: User 3 vs User 5
  Session 6: User 4 vs User 5
  ```
- Each participant appears in exactly 3 matches
- No duplicate pairings

**📝 Document**:
- Number of sessions created: `_______`
- All pairings correct: `YES / NO`
- Any duplicate pairings: `_______`
- Session IDs: `_______, _______, _______, _______, _______, _______`

**🔍 Database Validation** (optional):
```sql
-- Check session count
SELECT COUNT(*) FROM sessions WHERE semester_id = <tournament_id>;
-- Expected: 6

-- List all sessions with participants
SELECT
    s.id,
    sp1.user_id as user_1,
    sp2.user_id as user_2
FROM sessions s
JOIN session_participants sp1 ON s.id = sp1.session_id
JOIN session_participants sp2 ON s.id = sp2.session_id AND sp1.user_id < sp2.user_id
WHERE s.semester_id = <tournament_id>
ORDER BY s.id;
```

---

### Step 4: Mark Attendance

**Action**:
1. Navigate to **"Step 4: Mark Attendance"**
2. For EACH of the 6 sessions:
   - Expand the session card
   - For BOTH participants:
     - Mark attendance as **"Present"**
   - Click **"Update Attendance"**
3. Verify all 12 attendance records (6 sessions × 2 participants) are "Present"

**Expected Result**:
- All participants show green "Present" status
- Can proceed to result entry

**📝 Document**:
- All attendance marked: `YES / NO`
- Any attendance marking errors: `_______`

**🔍 Database Validation** (optional):
```sql
SELECT
    session_id,
    user_id,
    attendance_status
FROM session_participants
WHERE session_id IN (SELECT id FROM sessions WHERE semester_id = <tournament_id>)
ORDER BY session_id, user_id;
-- Expected: All 12 rows have attendance_status = 'present'
```

---

### Step 5: Enter Match Results

**Action**:
1. Navigate to **"Step 5: Enter Results"**
2. For EACH of the 6 sessions, enter the following scores:

**Match 1: User 2 vs User 3**
- User 2 score: `3`
- User 3 score: `1`
- Expected winner: User 2
- Click **"Submit Match Result"**

**Match 2: User 2 vs User 4**
- User 2 score: `2`
- User 4 score: `0`
- Expected winner: User 2
- Click **"Submit Match Result"**

**Match 3: User 2 vs User 5**
- User 2 score: `1`
- User 5 score: `0`
- Expected winner: User 2
- Click **"Submit Match Result"**

**Match 4: User 3 vs User 4**
- User 3 score: `2`
- User 4 score: `1`
- Expected winner: User 3
- Click **"Submit Match Result"**

**Match 5: User 3 vs User 5**
- User 3 score: `0`
- User 5 score: `1`
- Expected winner: User 5
- Click **"Submit Match Result"**

**Match 6: User 4 vs User 5**
- User 4 score: `1`
- User 5 score: `2`
- Expected winner: User 5
- Click **"Submit Match Result"**

**Expected Result After Each Submission**:
- Green success message: "Match result submitted"
- Page reloads and shows submitted result with winner indicator
- Result displayed:
  ```
  🏆 [Winner Name]: X (win)
  ❌ [Loser Name]: Y (loss)
  ```

**📝 Document for Each Match**:
| Match | User 1 | Score 1 | User 2 | Score 2 | Winner | Success? | Errors |
|-------|--------|---------|--------|---------|--------|----------|--------|
| 1     | 2      | 3       | 3      | 1       | User 2 | YES/NO   |        |
| 2     | 2      | 2       | 4      | 0       | User 2 | YES/NO   |        |
| 3     | 2      | 1       | 5      | 0       | User 2 | YES/NO   |        |
| 4     | 3      | 2       | 4      | 1       | User 3 | YES/NO   |        |
| 5     | 3      | 0       | 5      | 1       | User 5 | YES/NO   |        |
| 6     | 4      | 1       | 5      | 2       | User 5 | YES/NO   |        |

**🔍 Database Validation** (optional):
```sql
SELECT
    s.id,
    s.session_status,
    s.game_results::json->'winner_user_id' as winner,
    s.game_results::json->'participants' as participants
FROM sessions s
WHERE s.semester_id = <tournament_id>
ORDER BY s.id;
-- Expected: All sessions have session_status = 'completed' and game_results populated
```

---

### Step 6: Calculate Rankings

**Action**:
1. Open a new terminal (keep Streamlit open)
2. Run the following curl command:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tournaments/<tournament_id>/calculate-rankings \
     -H "Content-Type: application/json" \
     -H "Cookie: session=<your_session_cookie>"
   ```
   **OR** use the API directly via Python/Postman

**Expected Result**:
- API returns 200 OK
- Response body shows calculated rankings:
  ```json
  {
    "tournament_id": <tournament_id>,
    "tournament_format": "HEAD_TO_HEAD",
    "rankings_count": 4,
    "rankings": [
      {"user_id": 2, "rank": 1, "points": 9, "wins": 3, "ties": 0, "losses": 0, "goal_difference": 5},
      {"user_id": 5, "rank": 2, "points": 6, "wins": 2, "ties": 0, "losses": 1, "goal_difference": 1},
      {"user_id": 3, "rank": 3, "points": 3, "wins": 1, "ties": 0, "losses": 2, "goal_difference": 1},
      {"user_id": 4, "rank": 4, "points": 0, "wins": 0, "ties": 0, "losses": 3, "goal_difference": -7}
    ]
  }
  ```

**📝 Document**:
- API response status: `_______`
- Rankings calculated correctly: `YES / NO`
- User 2 (Rank 1, 9 points): `YES / NO`
- User 5 (Rank 2, 6 points): `YES / NO`
- User 3 (Rank 3, 3 points): `YES / NO`
- User 4 (Rank 4, 0 points): `YES / NO`
- Any errors: `_______`

**🔍 Database Validation**:
```sql
SELECT
    user_id,
    rank,
    total_points,
    total_score
FROM tournament_rankings
WHERE tournament_id = <tournament_id>
ORDER BY rank;
-- Expected: 4 records matching above rankings
```

---

### Step 7: Distribute Rewards

**Action**:
1. Navigate to **"Step 6: Distribute Rewards"** in Streamlit
2. Click **"Distribute Rewards"**

**Expected Result**:
- Success message: "Rewards distributed successfully"
- Reward summary displayed:
  ```
  User 2 (Rank 1):
  - XP: +100
  - Skills: dribbling +50, passing +50, shooting +50

  User 5 (Rank 2):
  - XP: +60
  - Skills: dribbling +30, passing +30, shooting +30

  User 3 (Rank 3):
  - XP: +30
  - Skills: dribbling +10, passing +10, shooting +10

  User 4 (Rank 4):
  - No rewards (below winner_count threshold)
  ```

**📝 Document**:
- Rewards distributed: `YES / NO`
- User 2 received rewards: `YES / NO`
- User 5 received rewards: `YES / NO`
- User 3 received rewards: `YES / NO`
- User 4 received no rewards: `YES / NO`
- Any errors: `_______`

**🔍 Database Validation**:
```sql
-- XP transactions
SELECT user_id, xp_amount
FROM xp_transactions
WHERE source_type = 'TOURNAMENT' AND source_id = <tournament_id>
ORDER BY user_id;
-- Expected: 3 records (Users 2, 3, 5)

-- Skill rewards
SELECT user_id, skill_name, skill_value_change
FROM skill_rewards
WHERE source_type = 'TOURNAMENT' AND source_id = <tournament_id>
ORDER BY user_id, skill_name;
-- Expected: 9 records (3 users × 3 skills)
```

---

## Final Validation Checklist

After completing all steps, verify:

- [ ] All 6 sessions created correctly
- [ ] Each participant played exactly 3 matches
- [ ] No duplicate pairings
- [ ] All 12 attendance records marked "present"
- [ ] All 6 match results submitted successfully
- [ ] All results show correct winner
- [ ] Rankings calculated correctly:
  - [ ] User 2: Rank 1, 9 points, +5 GD
  - [ ] User 5: Rank 2, 6 points, +1 GD
  - [ ] User 3: Rank 3, 3 points, +1 GD
  - [ ] User 4: Rank 4, 0 points, -7 GD
- [ ] Rewards distributed to top 3 only
- [ ] User 4 received no rewards
- [ ] No errors or crashes occurred
- [ ] All UI elements displayed correctly
- [ ] Database state is consistent

---

## Test Result

**Overall Outcome**: `PASS / FAIL`

**Issues Found**:
1. _______
2. _______
3. _______

**Blockers**: `_______`

**Duration**: `_______ minutes`

**Notes**:
_______

---

## Next Steps

If Scenario 1 **PASSES**:
- ✅ Update `HEAD_TO_HEAD_SCENARIO_1_LOG.md` with results
- ✅ Mark Scenario 1 as PASS in validation plan
- ➡️ Proceed to Scenario 2: League with Ties

If Scenario 1 **FAILS**:
- ❌ Document all issues in validation plan
- ❌ Prioritize blockers (P0 = must fix before continuing)
- ❌ Fix issues and re-run Scenario 1
- ❌ Do NOT proceed to other scenarios until Scenario 1 PASSES
