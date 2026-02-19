# Frontend Manual Validation Guide
## Tournament E2E - All 7 Configurations
### 2026-02-02

## Overview

This guide provides step-by-step instructions for **manually validating** all 7 tournament configuration variations through the **Streamlit frontend UI**.

Each configuration must complete the full user journey from creation to reward distribution verification.

---

## Prerequisites

### 1. Backend Running
```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  ./venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify:** http://localhost:8000/docs should load

### 2. Streamlit Frontend Running
```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8501
```

**Verify:** http://localhost:8501 should load

### 3. Test User Login
- **Email:** `admin@lfa.com`
- **Password:** `admin123`

### 4. Test Players
Have 8 players with `LFA_FOOTBALL_PLAYER` licenses:
- User IDs: 4, 5, 6, 7, 13, 14, 15, 16
- Emails: `junior.intern@lfa.com`, etc.

---

## Test Configuration Matrix

| Test ID | Format | Scoring Type | Tournament Type | Expected Sessions | Finalization |
|---------|--------|--------------|-----------------|-------------------|--------------|
| **T1** | INDIVIDUAL_RANKING | ROUNDS_BASED | N/A | 1 | ✅ YES |
| **T2** | INDIVIDUAL_RANKING | TIME_BASED | N/A | 1 | ✅ YES |
| **T3** | INDIVIDUAL_RANKING | SCORE_BASED | N/A | 1 | ✅ YES |
| **T4** | INDIVIDUAL_RANKING | DISTANCE_BASED | N/A | 1 | ✅ YES |
| **T5** | INDIVIDUAL_RANKING | PLACEMENT | N/A | 1 | ✅ YES |
| **T6** | HEAD_TO_HEAD | N/A | League (Round Robin) | 28 | ❌ NO |
| **T7** | HEAD_TO_HEAD | N/A | Single Elimination | 8 | ❌ NO |

---

## Test Workflow Template

### For INDIVIDUAL_RANKING (T1-T5)

#### Step 1: Create Tournament ✅
1. Navigate to **Admin Dashboard** or **Tournament Creation** page
2. Click **"Create New Tournament"**
3. Fill in tournament details:
   - **Code:** `MANUAL-T{X}-{YYYYMMDD}` (e.g., `MANUAL-T1-20260202`)
   - **Name:** Descriptive name (e.g., `Manual Test: INDIVIDUAL_RANKING + ROUNDS_BASED`)
   - **Start Date:** Tomorrow's date
   - **End Date:** 7 days from start
   - **Age Group:** PRO
   - **Specialization:** PLAYER
   - **Format:** INDIVIDUAL_RANKING
   - **Scoring Type:** (See test configuration)
   - **Ranking Direction:** (ASC for TIME_BASED, DESC for others, N/A for PLACEMENT)
   - **Measurement Unit:** (seconds for TIME_BASED, points for SCORE_BASED, meters for DISTANCE_BASED, none for PLACEMENT/ROUNDS_BASED)
   - **Max Players:** 8
   - **Assignment Type:** OPEN_ASSIGNMENT
   - **Location:** Budapest, LFA Academy
   - **Status:** DRAFT

4. **Verify:**
   - ✅ Tournament appears in tournament list
   - ✅ Status shows "DRAFT"
   - ✅ All fields saved correctly

**Screenshot:** `T{X}_01_tournament_created.png`

---

#### Step 2: Enroll Players ✅
1. Navigate to tournament detail page
2. Click **"Enroll Players"** or **"Manage Enrollments"**
3. Select 8 players:
   - `junior.intern@lfa.com`
   - (7 other LFA_FOOTBALL_PLAYER users)
4. For each player:
   - Click **"Enroll"**
   - Verify enrollment status: APPROVED
   - Verify payment: Verified
5. **Verify:**
   - ✅ 8 players enrolled
   - ✅ Enrollment count shows "8/8"
   - ✅ All enrollments show APPROVED status

**Screenshot:** `T{X}_02_players_enrolled.png`

---

#### Step 3: Start Tournament ✅
1. On tournament detail page, click **"Start Tournament"**
2. Confirm action in modal dialog
3. **Verify:**
   - ✅ Status changes to "IN_PROGRESS"
   - ✅ "Generate Sessions" button becomes available
   - ✅ Enrolled players list is locked (no more enrollments)

**Screenshot:** `T{X}_03_tournament_started.png`

---

#### Step 4: Generate Sessions ✅
1. Click **"Generate Sessions"**
2. Fill in session generation form:
   - **Parallel Fields:** 1
   - **Session Duration:** 90 minutes
   - **Break Between Sessions:** 15 minutes
   - **Number of Rounds:** 1
3. Click **"Generate"**
4. **Verify:**
   - ✅ 1 session created
   - ✅ Session shows all 8 participants
   - ✅ Session has correct game type (Individual Ranking Competition)
   - ✅ Session date/time displayed correctly

**Screenshot:** `T{X}_04_sessions_generated.png`

---

#### Step 5: Submit Results ✅
1. Navigate to session detail page
2. Click **"Submit Results"** or **"Enter Scores"**
3. For each player, enter:
   - **Score:** (varies by scoring type)
     - ROUNDS_BASED: 100, 95, 90, 85, 80, 75, 70, 65
     - TIME_BASED: 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5 (seconds)
     - SCORE_BASED: 95, 90, 85, 80, 75, 70, 65, 60
     - DISTANCE_BASED: 50.0, 48.0, 46.0, 44.0, 42.0, 40.0, 38.0, 36.0 (meters)
     - PLACEMENT: 0 (no scores, only ranks)
   - **Rank:** 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th
4. Click **"Submit Results"**
5. **Verify:**
   - ✅ Results saved successfully
   - ✅ Session shows "Results Submitted" status
   - ✅ Results appear in session detail view

**Screenshot:** `T{X}_05_results_submitted.png`

---

#### Step 6: Finalize Session ✅
1. On session detail page, click **"Finalize Session"**
2. Confirm finalization
3. **Verify:**
   - ✅ Session status changes to "Finalized"
   - ✅ Rankings calculated and displayed
   - ✅ Derived rankings match expected order (based on scores/times)
   - ✅ Performance rankings calculated
   - ✅ Tournament rankings table updated

**Screenshot:** `T{X}_06_session_finalized.png`

---

#### Step 7: Complete Tournament ✅
1. Navigate to tournament detail page
2. Click **"Complete Tournament"**
3. Confirm completion
4. **Verify:**
   - ✅ Status changes to "COMPLETED"
   - ✅ Final rankings visible
   - ✅ All sessions marked as finalized
   - ✅ "Distribute Rewards" button becomes available

**Screenshot:** `T{X}_07_tournament_completed.png`

---

#### Step 8: Distribute Rewards ✅
1. Click **"Distribute Rewards"**
2. Review reward distribution preview (if available)
3. Confirm distribution
4. **Verify:**
   - ✅ Status changes to "REWARDS_DISTRIBUTED"
   - ✅ Success message displayed
   - ✅ Reward distribution summary shows:
     - Total credits distributed
     - Total XP distributed
     - Number of players rewarded

**Screenshot:** `T{X}_08_rewards_distributed.png`

---

#### Step 9: Verify Player Rewards ✅
1. Navigate to each player's profile (or credits page)
2. Check:
   - **Credit Balance:** Increased by reward amount
   - **XP Balance:** Increased by XP amount
   - **Transaction History:** Shows reward entry with tournament name
3. **Verify:**
   - ✅ All 8 players received rewards
   - ✅ Reward amounts match tournament configuration
   - ✅ Transaction timestamps match distribution time
   - ✅ No duplicate reward entries (idempotency check)

**Screenshot:** `T{X}_09_player_rewards_verified.png`

---

#### Step 10: Test Idempotency (Optional) ⚠️
1. Try to click **"Distribute Rewards"** again
2. **Expected Result:**
   - ❌ Button disabled OR
   - ❌ Error message: "Rewards already distributed"
3. **Verify:**
   - ✅ System prevents duplicate distribution
   - ✅ Player balances remain unchanged

**Screenshot:** `T{X}_10_idempotency_test.png`

---

### For HEAD_TO_HEAD (T6-T7)

#### Steps 1-3: Same as INDIVIDUAL_RANKING ✅
- Create tournament with **Format: HEAD_TO_HEAD**
- Select **Tournament Type:**
  - T6: League (Round Robin)
  - T7: Single Elimination (Knockout)
- Enroll 8 players
- Start tournament

---

#### Step 4: Generate Sessions ✅
1. Click **"Generate Sessions"**
2. **Expected Session Count:**
   - **T6 (League):** 28 sessions (8 players × 7 opponents)
   - **T7 (Single Elimination):** 8 sessions (quarter-finals, semi-finals, finals)
3. **Verify:**
   - ✅ Correct number of sessions generated
   - ✅ Match pairings are valid (no self-matches)
   - ✅ Bracket structure correct (for T7)

**Screenshot:** `T{X}_04_sessions_generated.png`

---

#### Step 5: Submit Results ✅
1. For each session:
   - Navigate to session detail
   - Enter score and rank for each participant
   - Submit results
2. **Verify:**
   - ✅ All sessions show "Results Submitted"
   - ✅ Scores saved correctly

**Screenshot:** `T{X}_05_all_results_submitted.png`

---

#### Step 6: SKIP Finalization ⏭️
**HEAD_TO_HEAD tournaments do NOT require finalization step.**

Jump directly to Step 7 (Complete Tournament).

---

#### Step 7-10: Same as INDIVIDUAL_RANKING ✅
- Complete tournament
- Distribute rewards
- Verify player rewards
- Test idempotency

---

## Success Criteria Per Configuration

### T1: INDIVIDUAL_RANKING + ROUNDS_BASED ✅
- ✅ 10 steps completed successfully
- ✅ Finalization calculates rankings based on best round performance
- ✅ Rewards distributed correctly

### T2: INDIVIDUAL_RANKING + TIME_BASED ✅
- ✅ 10 steps completed successfully
- ✅ Finalization ranks players by fastest time (ASC order)
- ✅ Measurement unit displayed as "seconds"
- ✅ Rewards distributed correctly

### T3: INDIVIDUAL_RANKING + SCORE_BASED ✅
- ✅ 10 steps completed successfully
- ✅ Finalization ranks players by highest score (DESC order)
- ✅ Measurement unit displayed as "points"
- ✅ Rewards distributed correctly

### T4: INDIVIDUAL_RANKING + DISTANCE_BASED ✅
- ✅ 10 steps completed successfully
- ✅ Finalization ranks players by longest distance (DESC order)
- ✅ Measurement unit displayed as "meters"
- ✅ Rewards distributed correctly

### T5: INDIVIDUAL_RANKING + PLACEMENT ✅
- ✅ 10 steps completed successfully
- ✅ Finalization uses direct ranking (no scores)
- ✅ No measurement unit displayed
- ✅ Rewards distributed correctly

### T6: HEAD_TO_HEAD + League ✅
- ✅ 9 steps completed (skip finalization)
- ✅ 28 sessions generated (round-robin)
- ✅ All match results submitted
- ✅ Rewards distributed correctly

### T7: HEAD_TO_HEAD + Single Elimination ✅
- ✅ 9 steps completed (skip finalization)
- ✅ 8 sessions generated (knockout bracket)
- ✅ All match results submitted
- ✅ Rewards distributed correctly

---

## Common Issues & Troubleshooting

### Issue 1: Tournament Creation Fails
**Symptom:** Error message on submit
**Cause:** Missing TournamentConfiguration object
**Solution:** Verify backend fix is applied (POST /semesters creates TournamentConfiguration)

### Issue 2: Session Generation Shows No Sessions
**Symptom:** Generate succeeds but no sessions visible
**Cause:** Frontend not fetching sessions correctly
**Solution:** Refresh page or check API response

### Issue 3: Finalization Fails with "Rounds Remaining"
**Symptom:** Error: "Cannot finalize: 1 rounds remaining"
**Cause:** Results not properly saved to rounds_data
**Solution:** Verify result submission populates rounds_data field

### Issue 4: Finalization Fails with "Unknown scoring_type: PLACEMENT"
**Symptom:** 400 error on finalization
**Cause:** PLACEMENT not supported in ranking strategies
**Solution:** Verify PLACEMENT support added to factory.py

### Issue 5: Rewards Already Distributed
**Symptom:** Error on step 8
**Cause:** Tournament already completed in previous test
**Solution:** Create new tournament with unique code

### Issue 6: Player Not Found for Enrollment
**Symptom:** Cannot enroll specific player
**Cause:** Player missing LFA_FOOTBALL_PLAYER license
**Solution:** Check user_licenses table, create license if needed

---

## Test Data Tracking Sheet

Use this table to track progress:

| Test ID | Tournament ID | Code | Status | Start Time | End Time | Duration | Screenshots | Notes |
|---------|---------------|------|--------|------------|----------|----------|-------------|-------|
| T1 | | | ⏳ | | | | 0/10 | |
| T2 | | | ⏳ | | | | 0/10 | |
| T3 | | | ⏳ | | | | 0/10 | |
| T4 | | | ⏳ | | | | 0/10 | |
| T5 | | | ⏳ | | | | 0/10 | |
| T6 | | | ⏳ | | | | 0/9 | |
| T7 | | | ⏳ | | | | 0/9 | |

**Legend:**
- ⏳ Not Started
- 🔄 In Progress
- ✅ Passed
- ❌ Failed

---

## Screenshot Naming Convention

Save screenshots in `tests/e2e_frontend/manual_validation/` directory:

```
T{test_id}_{step_number}_{description}.png

Examples:
T1_01_tournament_created.png
T1_02_players_enrolled.png
T1_03_tournament_started.png
...
T1_10_idempotency_test.png
```

---

## Final Validation Checklist

Before marking test as PASSED, verify:

- ✅ All steps completed without errors
- ✅ All screenshots captured
- ✅ Player rewards verified in database
- ✅ No duplicate reward transactions
- ✅ Tournament status = REWARDS_DISTRIBUTED
- ✅ Backend logs show no errors
- ✅ Frontend shows correct data throughout workflow

---

## Appendix: Quick Reference

### API Endpoints for Verification

```bash
# Get tournament details
GET http://localhost:8000/api/v1/semesters/{tournament_id}

# Get tournament sessions
GET http://localhost:8000/api/v1/tournaments/{tournament_id}/sessions

# Get session results
GET http://localhost:8000/api/v1/sessions/{session_id}/results

# Get tournament rankings
GET http://localhost:8000/api/v1/tournaments/{tournament_id}/rankings

# Get player credits
GET http://localhost:8000/api/v1/users/{user_id}/credits
```

### Database Verification Queries

```sql
-- Check tournament status
SELECT id, code, name, tournament_status, format
FROM semesters
WHERE id = {tournament_id};

-- Check session results
SELECT id, semester_id, rounds_data, game_results
FROM sessions
WHERE semester_id = {tournament_id};

-- Check tournament rankings
SELECT * FROM tournament_rankings
WHERE tournament_id = {tournament_id}
ORDER BY final_rank;

-- Check credit transactions
SELECT * FROM credit_transactions
WHERE idempotency_key LIKE '%tournament_{tournament_id}%'
ORDER BY created_at DESC;

-- Check XP transactions
SELECT * FROM xp_transactions
WHERE idempotency_key LIKE '%tournament_{tournament_id}%'
ORDER BY created_at DESC;
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-02
**Author:** Claude Code
**Status:** Ready for Manual Testing
