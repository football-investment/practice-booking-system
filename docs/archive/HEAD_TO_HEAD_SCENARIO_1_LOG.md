# Scenario 1: Basic League Flow - Test Execution Log

**Date**: 2026-02-04
**Tester**: Claude (AI Assistant)
**Environment**: Local dev (localhost:8000)
**Database**: lfa_intern_system

---

## Test Configuration

**Tournament Name**: `[TEST_H2H_LEAGUE] Basic Happy Path`
**Format**: HEAD_TO_HEAD + League (Round Robin)
**Participants**: 4 (IDs: 2, 3, 4, 5)
**Expected Matches**: 6 (round robin: 4 × 3 / 2 = 6)
**Skills to Reward**: dribbling, passing, shooting
**Winner Count**: 3

---

## Execution Steps

### Step 1: Create HEAD_TO_HEAD League Tournament
**Status**: ⏸️ IN PROGRESS
**Timestamp**: [To be filled]

**Action**: Navigate to Streamlit sandbox, create tournament via UI

**Expected**:
- Tournament created with tournament_type_id set to League (id=1)
- Tournament state: DRAFT
- format property: "HEAD_TO_HEAD"

**Actual**:
[To be filled during testing]

**Issues Found**:
[None yet]

---

### Step 2: Generate Sessions (Matches)
**Status**: ⏸️ PENDING
**Timestamp**: [To be filled]

**Action**: Click "Generate Sessions" in sandbox

**Expected**:
- 6 sessions created (round robin pairs)
- Each participant appears in exactly 3 matches
- No duplicate pairings
- match_format = "HEAD_TO_HEAD"
- session_status = "scheduled"

**Actual**:
[To be filled]

**Validation Queries**:
```sql
-- Check session count
SELECT COUNT(*) FROM sessions WHERE semester_id = <tournament_id>;
-- Expected: 6

-- Check participant distribution
SELECT user_id, COUNT(*) as match_count
FROM session_participants
WHERE session_id IN (SELECT id FROM sessions WHERE semester_id = <tournament_id>)
GROUP BY user_id
ORDER BY user_id;
-- Expected: Each user appears 3 times

-- Check match pairings (no duplicates)
SELECT
    sp1.user_id as user_1,
    sp2.user_id as user_2
FROM session_participants sp1
JOIN session_participants sp2 ON sp1.session_id = sp2.session_id AND sp1.user_id < sp2.user_id
WHERE sp1.session_id IN (SELECT id FROM sessions WHERE semester_id = <tournament_id>)
ORDER BY user_1, user_2;
-- Expected: 6 unique pairs
```

**Issues Found**:
[None yet]

---

### Step 3: Mark Attendance (All Present)
**Status**: ⏸️ PENDING
**Timestamp**: [To be filled]

**Action**: Mark all participants as "present" for all sessions

**Expected**:
- All session_participants have attendance_status = 'present'
- Can proceed to result entry

**Actual**:
[To be filled]

**Validation Query**:
```sql
SELECT
    session_id,
    user_id,
    attendance_status
FROM session_participants
WHERE session_id IN (SELECT id FROM sessions WHERE semester_id = <tournament_id>)
ORDER BY session_id, user_id;
-- Expected: All rows have attendance_status = 'present'
```

**Issues Found**:
[None yet]

---

### Step 4: Enter Match Results (Varied Scores)
**Status**: ⏸️ PENDING
**Timestamp**: [To be filled]

**Action**: Submit results for all 6 matches via Streamlit UI

**Planned Results**:
```
Match 1: User 2 vs User 3 → 3-1 (User 2 wins)
Match 2: User 2 vs User 4 → 2-0 (User 2 wins)
Match 3: User 2 vs User 5 → 1-0 (User 2 wins)
Match 4: User 3 vs User 4 → 2-1 (User 3 wins)
Match 5: User 3 vs User 5 → 0-1 (User 5 wins)
Match 6: User 4 vs User 5 → 1-2 (User 5 wins)
```

**Expected Final Standings**:
- User 2: 3 wins, 0 ties, 0 losses = 9 points, +5 GD (6 scored, 1 conceded) → Rank 1
- User 3: 1 win, 0 ties, 2 losses = 3 points, +1 GD (3 scored, 2 conceded) → Rank 2
- User 5: 2 wins, 0 ties, 1 loss = 6 points, +1 GD (3 scored, 2 conceded) → Rank 3
- User 4: 0 wins, 0 ties, 3 losses = 0 points, -7 GD (2 scored, 9 conceded) → Rank 4

**Actual Results**:
[To be filled for each match]

**Validation Checks**:
- [ ] All 6 sessions have game_results JSONB populated
- [ ] session_status updated to 'completed' for all
- [ ] game_results structure matches design:
  ```json
  {
    "match_format": "HEAD_TO_HEAD",
    "tournament_type": "league",
    "participants": [
      {"user_id": X, "score": Y, "result": "win/tie/loss"},
      {"user_id": Z, "score": W, "result": "loss/tie/win"}
    ],
    "winner_user_id": X (or null for tie),
    "match_status": "completed",
    "submitted_at": "ISO timestamp",
    "submitted_by": instructor_user_id
  }
  ```

**Validation Query**:
```sql
SELECT
    id,
    semester_id,
    session_status,
    game_results::text
FROM sessions
WHERE semester_id = <tournament_id>
ORDER BY id;
```

**Issues Found**:
[None yet]

---

### Step 5: Calculate Rankings
**Status**: ⏸️ PENDING
**Timestamp**: [To be filled]

**Action**: Call POST /api/v1/tournaments/<tournament_id>/calculate-rankings

**Expected**:
- API returns 200 OK
- 4 ranking records created in tournament_rankings table
- Rankings match expected standings:
  - User 2: Rank 1, 9 points
  - User 5: Rank 2, 6 points
  - User 3: Rank 3, 3 points
  - User 4: Rank 4, 0 points

**Actual**:
[To be filled]

**Validation Query**:
```sql
SELECT
    user_id,
    rank,
    total_points,
    total_score
FROM tournament_rankings
WHERE tournament_id = <tournament_id>
ORDER BY rank;
```

**Issues Found**:
[None yet]

---

### Step 6: Distribute Rewards
**Status**: ⏸️ PENDING
**Timestamp**: [To be filled]

**Action**: Call reward distribution endpoint (existing flow)

**Expected**:
- XP transactions created for top 3 (Users 2, 5, 3)
- Skill rewards created for dribbling, passing, shooting
- User 2 (Rank 1) gets highest skill boost
- User 5 (Rank 2) gets medium skill boost
- User 3 (Rank 3) gets lowest skill boost
- User 4 (Rank 4) gets no rewards

**Actual**:
[To be filled]

**Validation Queries**:
```sql
-- XP transactions
SELECT
    user_id,
    xp_amount,
    source_type,
    source_id
FROM xp_transactions
WHERE source_type = 'TOURNAMENT' AND source_id = <tournament_id>
ORDER BY user_id;

-- Skill rewards
SELECT
    user_id,
    skill_name,
    skill_value_change
FROM skill_rewards
WHERE source_type = 'TOURNAMENT' AND source_id = <tournament_id>
ORDER BY user_id, skill_name;

-- Credit transactions (if applicable)
SELECT
    user_id,
    amount,
    transaction_type
FROM credit_transactions
WHERE tournament_id = <tournament_id>
ORDER BY user_id;
```

**Issues Found**:
[None yet]

---

## Final Validation Checklist

- [ ] All 6 sessions created correctly
- [ ] Each participant plays exactly 3 matches
- [ ] No duplicate pairings
- [ ] All results stored in session.game_results
- [ ] session_status = 'completed' for all sessions
- [ ] Rankings calculated correctly (User 2 → Rank 1, 9 points)
- [ ] Tiebreaker not needed (clear winner)
- [ ] Rewards distributed to top 3
- [ ] XP transactions created (3 records)
- [ ] Skill rewards created (3 users × 3 skills = 9 records)
- [ ] User 4 (Rank 4) received no rewards
- [ ] No data corruption or crashes
- [ ] All API calls returned expected status codes

---

## Test Result

**Status**: ⏸️ IN PROGRESS

**Duration**: [To be filled]

**Outcome**: [PASS / FAIL]

**Issues Found**: [Count: 0]

**Blockers**: [Count: 0]

---

## Notes

[Any observations, unexpected behavior, or insights gained during testing]
