# Sandbox Workflow - data-testid Documentation
**File**: `sandbox_workflow.py`
**Date**: 2026-02-02
**Status**: ✅ COMPLETE - All workflow buttons have Streamlit keys that auto-generate data-testid attributes

---

## Overview

The sandbox workflow (Steps 1-7) is **fully instrumented** with Streamlit `key` parameters on all interactive buttons. Streamlit automatically converts these keys into `data-testid` attributes in the DOM.

---

## data-testid Attributes by Workflow Step

### Step 1: Create Tournament

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Back to Configuration button | `btn_back_to_config` | Auto-generated | 151 |
| Create Tournament button | `btn_create_tournament_step1` | Auto-generated | 162 |

### Step 2: Manage Sessions

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Back to Home (invalid ID) | `btn_invalid_id_home` | Auto-generated | 268 |
| Back to Step 1 button | `btn_back_to_step1` | Auto-generated | 301 |
| Continue to Attendance button | `btn_continue_to_step3` | Auto-generated | 311 |

### Step 3: Track Attendance

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Back to Sessions button | `btn_back_to_step2` | Auto-generated | 357 |
| Continue to Results button | `btn_continue_to_step4` | Auto-generated | 367 |

### Step 4: Enter Results

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Sandbox Auto-Fill toggle | `toggle_sandbox_autofill` | Auto-generated | 412 |
| Auto-Fill ALL Remaining Rounds button | `btn_auto_fill_all` | Auto-generated | 439 |
| Submit Round button (dynamic) | `btn_sandbox_submit_round_{round}_{session_id}` | Auto-generated | 565 |
| Back to Attendance button | `btn_back_to_step3` | Auto-generated | 638 |
| View Final Leaderboard button | `btn_continue_to_step5` | Auto-generated | 648 |

**Note**: Submit Round buttons are dynamically generated per round and session.
Example: `btn_sandbox_submit_round_1_123`, `btn_sandbox_submit_round_2_123`

### Step 5: View Final Leaderboard

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Back to Results button | `btn_back_to_step4` | Auto-generated | 690 |
| Distribute Rewards button | `btn_continue_to_step6` | Auto-generated | 700 |

### Step 6: Distribute Rewards

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Distribute All Rewards button | `btn_distribute_rewards` | Auto-generated | 772 |
| Back to Leaderboard button | `btn_back_to_step5` | Auto-generated | 852 |
| View in History button | `btn_view_history` | Auto-generated | 862 |

### Step 7: View Rewards (E2E Validation Step)

| Element | key | data-testid | Line |
|---------|-----|-------------|------|
| Back to History (no tournament) | `btn_back_to_history_no_tournament` | Auto-generated | 896 |
| Back to History (invalid ID) | `btn_back_to_history_invalid_id` | Auto-generated | 906 |
| Back to History button | `btn_back_to_history` | Auto-generated | 937 |
| View Leaderboard button | `btn_view_leaderboard_from_rewards` | Auto-generated | 942 |

**E2E Testing Note**: Step 7 also contains:
- `tournament-status` (data-testid + data-status attribute) - Line 921
- `tournament-rankings` (via `render_mini_leaderboard()`) - Line 925
- `rewards-summary` (via `render_rewards_table()`) - Line 929

---

## Playwright Selector Usage Examples

```python
# Step 1: Create Tournament
page.click('[data-testid="btn_create_tournament_step1"]')

# Step 2: Navigate to attendance
page.click('[data-testid="btn_continue_to_step3"]')

# Step 4: Enable auto-fill toggle
page.check('[data-testid="toggle_sandbox_autofill"]')

# Step 4: Submit round results
page.click('[data-testid="btn_sandbox_submit_round_1_123"]')

# Step 5: Go to rewards
page.click('[data-testid="btn_continue_to_step6"]')

# Step 6: Distribute rewards
page.click('[data-testid="btn_distribute_rewards"]')

# Step 7: View leaderboard
page.click('[data-testid="btn_view_leaderboard_from_rewards"]')

# Step 7: Verify tournament status
status = page.locator('[data-testid="tournament-status"]').get_attribute('data-status')
assert status == "REWARDS_DISTRIBUTED"
```

---

## Coverage Summary

| Step | Element Count | Status |
|------|---------------|--------|
| Step 1: Create Tournament | 2 buttons | ✅ Complete |
| Step 2: Manage Sessions | 3 buttons | ✅ Complete |
| Step 3: Track Attendance | 2 buttons | ✅ Complete |
| Step 4: Enter Results | 5 elements (1 toggle, 4 buttons) | ✅ Complete |
| Step 5: View Leaderboard | 2 buttons | ✅ Complete |
| Step 6: Distribute Rewards | 3 buttons | ✅ Complete |
| Step 7: View Rewards | 4 buttons + 3 data elements | ✅ Complete |

**Total**: 20+ unique data-testid attributes (excluding dynamic submit buttons)

---

## Dynamic Elements

### Submit Round Buttons (Step 4)
Pattern: `btn_sandbox_submit_round_{round_number}_{session_id}`

Example keys for session ID 123 with 3 rounds:
- `btn_sandbox_submit_round_1_123`
- `btn_sandbox_submit_round_2_123`
- `btn_sandbox_submit_round_3_123`

Playwright can locate these dynamically:
```python
# Get current round from UI
current_round = 1
session_id = 123

# Click submit button for current round
page.click(f'[data-testid="btn_sandbox_submit_round_{current_round}_{session_id}"]')
```

---

## Implementation Status

✅ **COMPLETE** - No modifications needed. All workflow buttons already have Streamlit keys that auto-generate data-testid attributes.

**Phase 1 (P0) Status**: ✅ COMPLETE
- Tournament Creation Form: ✅ 28+ attributes
- Sandbox Workflow Steps 1-7: ✅ 20+ attributes

**Next Steps**: Phase 2 (P1) - Home page navigation and history table (5 attributes)
