# HEAD_TO_HEAD Manual Validation Plan

**Status**: 🧪 TESTING PHASE
**Goal**: Validate implementation is stable and human-playable before E2E tests
**Date**: 2026-02-04

---

## Test Scenarios

### Scenario 1: Basic League Flow (Happy Path)
**Goal**: Validate complete league workflow with clean data

**Steps**:
1. ✅ Create HEAD_TO_HEAD League tournament
   - 4 participants (round robin = 6 matches)
   - Skills: dribbling, passing, shooting
   - Winner count: 3
2. ✅ Generate sessions (should create 6 matches)
3. ✅ Mark all participants as present (attendance)
4. ✅ Enter results for all 6 matches (varied scores, no ties)
5. ✅ Calculate rankings (verify points system: Win=3)
6. ✅ Distribute rewards (verify top 3 get skill boosts)

**Expected Rankings** (example):
- Participant A: 3 wins, 0 ties, 0 losses = 9 points → Rank 1
- Participant B: 2 wins, 0 ties, 1 loss = 6 points → Rank 2
- Participant C: 1 win, 0 ties, 2 losses = 3 points → Rank 3
- Participant D: 0 wins, 0 ties, 3 losses = 0 points → Rank 4

**Validation Checks**:
- [ ] All 6 sessions created correctly
- [ ] Each participant plays 3 matches
- [ ] Results stored in session.game_results
- [ ] Rankings calculated correctly
- [ ] Rewards distributed to top 3
- [ ] XP transactions created
- [ ] Skill rewards created

---

### Scenario 2: League with Ties
**Goal**: Test tie handling and tiebreaker logic

**Steps**:
1. ✅ Create HEAD_TO_HEAD League tournament (4 participants)
2. ✅ Generate sessions
3. ✅ Enter results with MULTIPLE ties:
   - Match 1: A vs B → 2-2 (tie)
   - Match 2: C vs D → 1-1 (tie)
   - Match 3: A vs C → 3-1 (A wins)
   - Match 4: B vs D → 2-0 (B wins)
   - Match 5: A vs D → 1-1 (tie)
   - Match 6: B vs C → 0-0 (tie)
4. ✅ Calculate rankings
5. ✅ Verify tiebreaker logic (goal difference, goals scored)

**Expected Rankings**:
- A: 1 win, 2 ties, 0 losses = 5 points, +2 GD → Rank 1
- B: 1 win, 2 ties, 0 losses = 5 points, +2 GD → Rank 1 (tied)
- C: 0 wins, 2 ties, 1 loss = 2 points, -2 GD → Rank 3
- D: 0 wins, 2 ties, 1 loss = 2 points, -2 GD → Rank 3 (tied)

**Validation Checks**:
- [ ] Tie results stored correctly (winner_user_id = null)
- [ ] Both participants get 1 point for tie
- [ ] Goal difference calculated correctly
- [ ] Tied ranks handled properly (same rank number)
- [ ] Rewards distributed to tied participants (if in top N)

---

### Scenario 3: Attendance Edge Cases
**Goal**: Test validation when participants are not present

**Steps**:
1. ✅ Create HEAD_TO_HEAD League tournament (4 participants)
2. ✅ Generate sessions
3. ❌ **DO NOT mark attendance for one participant**
4. ❌ Try to submit result for match with absent participant
5. ✅ Verify API returns error (400 Bad Request)
6. ✅ Mark all participants present
7. ✅ Submit results successfully

**Validation Checks**:
- [ ] API blocks result submission if participant not present
- [ ] Error message is clear and actionable
- [ ] After marking present, submission works

---

### Scenario 4: Result Modification
**Goal**: Test editing submitted results (before finalization)

**Steps**:
1. ✅ Create tournament and submit initial results
2. ✅ Calculate rankings (initial)
3. ✅ Modify one match result (change score)
4. ✅ Re-calculate rankings
5. ✅ Verify rankings updated correctly
6. ✅ Verify old rankings removed (idempotency)

**Validation Checks**:
- [ ] Can re-submit result for same match
- [ ] New result overwrites old result
- [ ] Re-calculating rankings overwrites old rankings
- [ ] No duplicate ranking records
- [ ] Reward distribution can be re-run after ranking change

---

### Scenario 5: Incomplete Matches
**Goal**: Test ranking calculation with missing results

**Steps**:
1. ✅ Create tournament with 6 matches
2. ✅ Submit results for only 4 matches
3. ❌ Try to calculate rankings
4. ✅ Verify API returns error (400 Bad Request: "4 matches missing results")
5. ✅ Submit remaining 2 results
6. ✅ Calculate rankings successfully

**Validation Checks**:
- [ ] API blocks ranking calculation if any match incomplete
- [ ] Error message specifies how many matches missing
- [ ] After completing all matches, calculation works

---

### Scenario 6: Reward Distribution with Ranking Changes
**Goal**: Test reward idempotency and re-distribution

**Steps**:
1. ✅ Complete league, calculate rankings, distribute rewards
2. ✅ Verify participant 1 (Rank 1) received rewards
3. ✅ Modify results to change rankings (participant 2 becomes Rank 1)
4. ✅ Re-calculate rankings
5. ✅ Re-distribute rewards
6. ✅ Verify:
   - Old rewards removed or marked invalid
   - New rewards distributed to new top N
   - No duplicate rewards

**Validation Checks**:
- [ ] Can re-run reward distribution
- [ ] Old rewards handled correctly (removed or invalidated)
- [ ] New rewards distributed to correct participants
- [ ] Total reward count matches expected (not duplicated)

---

### Scenario 7: Large League (8 participants)
**Goal**: Test with maximum participants (8 = 28 matches)

**Steps**:
1. ✅ Create tournament with 8 participants
2. ✅ Generate sessions (should create 28 matches)
3. ✅ Mark all 16 attendance records (8 participants × 2 per match)
4. ✅ Submit results for ALL 28 matches (time-consuming but critical)
5. ✅ Calculate rankings
6. ✅ Verify correct point totals and ranking order

**Validation Checks**:
- [ ] All 28 sessions created
- [ ] Each participant plays 7 matches
- [ ] No duplicate match pairings
- [ ] Rankings calculated correctly for all 8 participants
- [ ] Performance acceptable (< 5 seconds for ranking calculation)

---

### Scenario 8: Zero Scores
**Goal**: Test edge case where all scores are 0

**Steps**:
1. ✅ Create tournament
2. ✅ Enter results with all zeros:
   - Match 1: A vs B → 0-0 (tie)
   - Match 2: C vs D → 0-0 (tie)
   - etc.
3. ✅ Calculate rankings
4. ✅ Verify all participants tied with 0 goals scored/conceded

**Validation Checks**:
- [ ] Zero scores handled correctly
- [ ] All participants receive tie points (1 point per match)
- [ ] Goal difference all zero
- [ ] Tiebreaker does not crash (all tied)

---

### Scenario 9: One-Sided Matches
**Goal**: Test extreme score differences

**Steps**:
1. ✅ Create tournament
2. ✅ Enter extreme results:
   - Match 1: A vs B → 99-0 (max score difference)
   - Match 2: C vs D → 50-1
   - Match 3: A vs C → 30-0
3. ✅ Calculate rankings
4. ✅ Verify goal difference handles large numbers

**Validation Checks**:
- [ ] Large scores stored correctly
- [ ] Goal difference calculation accurate
- [ ] No integer overflow
- [ ] Ranking logic works with extreme values

---

### Scenario 10: Try to Break the Flow
**Goal**: Adversarial testing - try to cause errors

**Attack Vectors**:
1. ❌ Submit result with invalid user_id (not in session)
2. ❌ Submit result with negative score (-5)
3. ❌ Submit result with score > 99 (100)
4. ❌ Submit result with only 1 participant
5. ❌ Submit result with 3 participants
6. ❌ Calculate rankings before any results submitted
7. ❌ Distribute rewards before rankings calculated
8. ❌ Delete tournament mid-flow
9. ❌ Modify tournament type after sessions generated
10. ❌ Submit result for non-tournament session

**Validation Checks**:
- [ ] All invalid inputs return 400 Bad Request
- [ ] Error messages are descriptive
- [ ] System does not crash or corrupt data
- [ ] Valid operations still work after failed attempts

---

### Scenario 11: Tournament Lifecycle State Validation
**Goal**: Test state transitions and blocking rules

**Steps**:
1. ✅ Create tournament (state: DRAFT)
2. ❌ Try to submit results before starting tournament
3. ❌ Try to calculate rankings before completing tournament
4. ✅ Start tournament (state: IN_PROGRESS)
5. ✅ Submit results
6. ❌ Try to distribute rewards before finalizing
7. ✅ Complete tournament (state: COMPLETED)
8. ✅ Calculate rankings
9. ✅ Distribute rewards
10. ❌ Try to modify results after tournament completed

**Validation Checks**:
- [ ] Cannot submit results in DRAFT state
- [ ] Cannot calculate rankings in IN_PROGRESS state (before all results)
- [ ] Cannot distribute rewards before rankings calculated
- [ ] Cannot modify results after tournament COMPLETED (or requires unlock)
- [ ] State transitions follow correct flow

---

### Scenario 12: Concurrent Result Submission
**Goal**: Test race conditions and data integrity

**Steps**:
1. ✅ Create tournament with 2 matches
2. ✅ Open two browser tabs for same match
3. ✅ Submit different results from both tabs simultaneously
4. ✅ Verify only one result persisted (last write wins or first write locks)
5. ✅ No data corruption

**Validation Checks**:
- [ ] No duplicate result records
- [ ] Only one result stored per session
- [ ] No partial writes or corrupted JSONB
- [ ] Consistent state after concurrent writes

---

### Scenario 13: Missing Tournament Configuration
**Goal**: Test validation when tournament_type_id is NULL

**Steps**:
1. ✅ Create tournament with tournament_type_id = NULL (force via DB)
2. ❌ Try to calculate rankings
3. ✅ Verify API returns 400 with clear error ("missing tournament_type")

**Validation Checks**:
- [ ] API validates tournament_type_id exists
- [ ] Error message is actionable
- [ ] Does not crash with NPE

---

### Scenario 14: Partial Attendance (Mixed)
**Goal**: Test when some participants marked present, others absent

**Steps**:
1. ✅ Create tournament with 4 participants (6 matches)
2. ✅ Mark 3 participants as present, 1 as absent
3. ❌ Try to submit results for matches involving absent participant
4. ✅ Verify validation blocks submission
5. ✅ Submit results for matches with only present participants
6. ✅ Verify partial results stored correctly

**Validation Checks**:
- [ ] Can submit results for matches with both participants present
- [ ] Cannot submit results if any participant absent
- [ ] Partial completion state tracked correctly

---

## Testing Environment Setup

**Database**: `lfa_intern_system`
**API**: `http://localhost:8000`
**Streamlit**: Sandbox Admin UI

**Test Users** (from database):
- junior.intern@lfa.com (ID: 2)
- senior.intern@lfa.com (ID: 3)
- master.intern@lfa.com (ID: 4)
- elite.intern@lfa.com (ID: 5)
- User 6, 7, 8, 9 (for 8-participant tests)

**Test Tournament Prefix**: `[TEST_H2H_LEAGUE]` (for easy cleanup)

---

## Validation Checklist

### API Validation
- [ ] POST /sessions/{id}/head-to-head-results
  - [ ] Returns 200 on success
  - [ ] Returns 400 on validation error
  - [ ] Returns 403 on unauthorized
  - [ ] Returns 404 on invalid session_id
- [ ] POST /tournaments/{id}/calculate-rankings
  - [ ] Returns 200 with rankings array
  - [ ] Returns 400 if results incomplete
  - [ ] Idempotent (can call multiple times)
- [ ] GET /tournaments/{id}/rankings
  - [ ] Returns empty array if not calculated
  - [ ] Returns sorted rankings after calculation

### Database Validation
- [ ] session.game_results JSONB structure correct
- [ ] session.session_status updated to 'completed'
- [ ] tournament_rankings table populated
- [ ] No duplicate ranking records
- [ ] Rankings match expected logic

### UI Validation
- [ ] Match entry form displays correctly
- [ ] Score inputs accept 0-99
- [ ] Result preview shows correct winner/tie
- [ ] Submit button works
- [ ] Success message displays
- [ ] Page reloads and shows submitted result
- [ ] Can edit result (re-submit)

### Reward Validation
- [ ] XP transactions created for top N
- [ ] Skill rewards created for selected skills
- [ ] Credit transactions created (if applicable)
- [ ] Reward amounts match tournament configuration

---

## Test Execution Log

**Tester**: Claude (AI Assistant)
**Date**: 2026-02-04
**Environment**: Local dev

### Scenario 1: Basic League Flow
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 2: League with Ties
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 3: Attendance Edge Cases
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 4: Result Modification
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 5: Incomplete Matches
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 6: Reward Distribution
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 7: Large League (8 participants)
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 8: Zero Scores
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 9: One-Sided Matches
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

### Scenario 10: Try to Break the Flow
**Status**: ⏸️ NOT STARTED
**Notes**: [To be filled during testing]

---

## Issues Found

**Priority**: P0 (Blocker) | P1 (Critical) | P2 (Important) | P3 (Minor)

| # | Priority | Description | Scenario | Status |
|---|----------|-------------|----------|--------|
| - | - | - | - | - |

---

## Final Assessment

**Overall Status**: ⏸️ TESTING IN PROGRESS

**Scenarios Passed**: 0 / 14
**Scenarios Failed**: 0 / 14
**Blockers Found**: 0

**Coverage Analysis**:
- ✅ Happy path (Scenario 1)
- ✅ Edge cases (Scenarios 2, 8, 9)
- ✅ Validation (Scenarios 3, 5, 10, 11, 13, 14)
- ✅ Idempotency (Scenarios 4, 6)
- ✅ Performance (Scenario 7)
- ✅ Concurrency (Scenario 12)

**Ready for E2E Tests**: ❌ NO (not tested yet)
**Ready for Config Matrix**: ❌ NO (not tested yet)
**Ready for Production**: ❌ NO (not tested yet)

---

**Next Step**: Begin Scenario 1 testing
