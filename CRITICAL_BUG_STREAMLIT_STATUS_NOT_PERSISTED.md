# CRITICAL BUG: Streamlit Sandbox Tournament Status Not Persisted to Database

**Date**: 2026-02-02
**Severity**: P0 - CRITICAL
**Status**: IDENTIFIED - NEEDS FIX

## Summary

The Streamlit sandbox workflow (`streamlit_sandbox_v3_admin_aligned.py`) creates tournaments but **does NOT persist status transitions** to the database. Tournament status changes are only reflected in Streamlit's session state, not in the actual backend database.

## Evidence from E2E Test

### Test Execution
```bash
pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow -v -s
```

### Results
- **Tournament ID**: 758
- **Database Status**: `DRAFT` (never changed from initial creation)
- **UI Session State**: `IN_PROGRESS` (only in Streamlit memory)
- **Expected Status**: `REWARDS_DISTRIBUTED`
- **Status History**: Empty (no transitions recorded)

### Terminal Output
```
📊 Database status for tournament 758: DRAFT
⚠️  No status history found - tournament never progressed!
Tournament Status: IN_PROGRESS
```

## Root Cause Analysis

The Streamlit sandbox workflow implements the following steps:

1. ✅ **Create Tournament** - Database call WORKS (creates semester with status=DRAFT)
2. ❌ **Start Workflow** - Only updates session_state, no backend API call
3. ❌ **Generate Sessions** - Creates sessions but doesn't update tournament status
4. ❌ **Submit Results** - Only updates session_state
5. ❌ **View Leaderboard** - Only updates session_state
6. ❌ **Complete Tournament** - No backend call to transition DRAFT → COMPLETED
7. ❌ **Distribute Rewards** - No backend call to transition COMPLETED → REWARDS_DISTRIBUTED

## Database Queries

### Tournament Status
```sql
SELECT id, name, status FROM semesters WHERE id = 758;
```
Result:
```
 id  |        name         | status
-----+---------------------+--------
 758 | UI-E2E-T1_UI-232253 | DRAFT
```

### Status History
```sql
SELECT old_status, new_status, created_at
FROM tournament_status_history
WHERE tournament_id = 758
ORDER BY created_at;
```
Result: **0 rows** (no transitions recorded)

## Business Impact

### Critical Business Requirements NOT Met
1. **Reward Distribution Tracking**: System cannot verify if rewards were actually distributed
2. **Tournament Lifecycle Auditing**: No audit trail of status transitions
3. **Data Integrity**: Database state inconsistent with UI state
4. **Report Correctness**: Reports and analytics will show tournaments stuck in DRAFT
5. **Payment Verification**: Cannot verify tournament completed before processing refunds

### User-Facing Impact
- Tournament history shows wrong status
- Analytics dashboards show incorrect tournament states
- Reward distribution cannot be verified
- Payment flows may break (refunds, enrollment checks)

## Required Fix

The Streamlit sandbox must call the actual backend API endpoints for status transitions:

### Current (BROKEN)
```python
# streamlit_sandbox_v3_admin_aligned.py
st.session_state["tournament_status"] = "IN_PROGRESS"  # Only in memory!
```

### Required (CORRECT)
```python
# Call backend API to properly transition status
response = requests.post(
    f"{API_BASE_URL}/tournaments/{tournament_id}/start",
    headers={"Authorization": f"Bearer {token}"}
)
# Backend updates database AND records status history
```

### Endpoints Needed
1. `POST /tournaments/{id}/start` - DRAFT → IN_PROGRESS
2. `POST /tournaments/{id}/complete` - IN_PROGRESS → COMPLETED
3. `POST /tournaments/{id}/distribute-rewards` - COMPLETED → REWARDS_DISTRIBUTED

## Verification Steps

After fix, run E2E test and verify:

```bash
# 1. Run E2E test
pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py -v -s

# 2. Check database status
psql -d lfa_intern_system -c "SELECT id, name, status FROM semesters WHERE name LIKE 'UI-E2E%' ORDER BY id DESC LIMIT 1;"

# Expected: status = 'REWARDS_DISTRIBUTED'

# 3. Check status history
psql -d lfa_intern_system -c "SELECT old_status, new_status, created_at FROM tournament_status_history WHERE tournament_id = (SELECT id FROM semesters WHERE name LIKE 'UI-E2E%' ORDER BY id DESC LIMIT 1);"

# Expected: Multiple rows showing DRAFT → IN_PROGRESS → COMPLETED → REWARDS_DISTRIBUTED
```

## Related Files

- **Bug Location**: `streamlit_sandbox_v3_admin_aligned.py`
- **Test File**: `tests/e2e_frontend/test_tournament_full_ui_workflow.py`
- **Backend API**: `app/api/api_v1/endpoints/tournaments/lifecycle.py`
- **Database Table**: `semesters` (tournament_status column)
- **Audit Table**: `tournament_status_history`

## Acceptance Criteria

- [ ] Tournament status persists to database after each workflow step
- [ ] Status transitions recorded in `tournament_status_history` table
- [ ] E2E test passes with status = REWARDS_DISTRIBUTED
- [ ] Database query shows correct final status
- [ ] All 18 Playwright E2E tests pass

## Priority Justification

**P0 CRITICAL** because:
1. Breaks tournament lifecycle tracking (core business logic)
2. Prevents reward distribution verification (financial impact)
3. Corrupts audit trail (compliance risk)
4. Affects ALL tournaments created via sandbox workflow
5. Blocks E2E test validation
