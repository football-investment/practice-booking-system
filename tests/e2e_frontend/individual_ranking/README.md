# INDIVIDUAL_RANKING Tournament E2E Tests

**Purpose:** Validate INDIVIDUAL_RANKING tournament format

**Status:** ✅ Active

---

## Overview

This directory contains E2E tests for **INDIVIDUAL_RANKING tournaments** - individual performance-based competitions where participants compete individually (not head-to-head).

**Key Characteristics:**
- **Scoring Mode:** INDIVIDUAL
- **Match Type:** Individual performances (not 1v1)
- **Result Submission:** UI-based (100% UI-driven workflow)
- **Scoring Types:** 5 types tested (SCORE, TIME, DISTANCE, PLACEMENT, ROUNDS)
- **Round Variants:** 1-3 rounds per scoring type

---

## Files

### `test_tournament_full_ui_workflow.py`

**What it tests:**
- Complete UI workflow (NO API shortcuts)
- 15 INDIVIDUAL_RANKING configurations
- 5 scoring types × 3 round variants
- Full tournament lifecycle via Streamlit UI

**Configurations:** 15 total

| ID | Scoring Type | Rounds | Ranking Direction | Measurement Unit |
|----|-------------|--------|-------------------|------------------|
| T1_Ind_Score_1R | SCORE_BASED | 1 | DESC (Higher better) | - |
| T1_Ind_Score_2R | SCORE_BASED | 2 | DESC (Higher better) | - |
| T1_Ind_Score_3R | SCORE_BASED | 3 | DESC (Higher better) | - |
| T2_Ind_Time_1R | TIME_BASED | 1 | ASC (Lower better) | seconds |
| T2_Ind_Time_2R | TIME_BASED | 2 | ASC (Lower better) | seconds |
| T2_Ind_Time_3R | TIME_BASED | 3 | ASC (Lower better) | seconds |
| T3_Ind_Distance_1R | DISTANCE_BASED | 1 | DESC (Higher better) | meters |
| T3_Ind_Distance_2R | DISTANCE_BASED | 2 | DESC (Higher better) | meters |
| T3_Ind_Distance_3R | DISTANCE_BASED | 3 | DESC (Higher better) | meters |
| T4_Ind_Placement_1R | PLACEMENT | 1 | ASC (Lower better) | - |
| T4_Ind_Placement_2R | PLACEMENT | 2 | ASC (Lower better) | - |
| T4_Ind_Placement_3R | PLACEMENT | 3 | ASC (Lower better) | - |
| T5_Ind_Rounds_1R | ROUNDS_BASED | 1 | DESC (Higher better) | - |
| T5_Ind_Rounds_2R | ROUNDS_BASED | 2 | DESC (Higher better) | - |
| T5_Ind_Rounds_3R | ROUNDS_BASED | 3 | DESC (Higher better) | - |

---

## Running Tests

### Run All INDIVIDUAL_RANKING Tests

```bash
# By directory
pytest tests/e2e_frontend/individual_ranking/ -v

# By file
pytest tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py -v
```

### Run Specific Configuration

```bash
# SCORE_BASED, 1 round
pytest tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py::test_full_ui_workflow[T1_Ind_Score_1R] -v

# TIME_BASED, 2 rounds
pytest tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py::test_full_ui_workflow[T2_Ind_Time_2R] -v

# DISTANCE_BASED, 3 rounds
pytest tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py::test_full_ui_workflow[T3_Ind_Distance_3R] -v
```

### Run All Configurations for Specific Scoring Type

```bash
# All SCORE_BASED
pytest tests/e2e_frontend/individual_ranking/ -v -k "Score"

# All TIME_BASED
pytest tests/e2e_frontend/individual_ranking/ -v -k "Time"

# All DISTANCE_BASED
pytest tests/e2e_frontend/individual_ranking/ -v -k "Distance"
```

### Run Headless (CI)

```bash
pytest tests/e2e_frontend/individual_ranking/ -v --headed=false
```

---

## Test Workflow

### Full UI Workflow (100% UI-driven)

1. **Navigate to Home** - Load Streamlit app
2. **Click "Create New Tournament"** - UI button click
3. **Fill Tournament Creation Form** - UI form inputs
4. **Enroll Players** - UI enrollment workflow
5. **Start Tournament** - Mark as IN_PROGRESS via UI
6. **Generate Sessions** - UI button click
7. **Submit Results via UI** - UI form submissions (NOT API)
8. **Finalize Sessions** - UI button click
9. **Complete Tournament** - UI button click
10. **Distribute Rewards** - UI button click
11. **Verify Final State** - Database + UI validation

**Note:** This is the ONLY test suite that validates 100% UI workflow. Other suites use API shortcuts.

---

## Key Differences from HEAD_TO_HEAD

| Aspect | INDIVIDUAL_RANKING | HEAD_TO_HEAD |
|--------|-------------------|--------------|
| **Match Type** | Individual performances | 1v1 matches |
| **Participants per Session** | All participants | 2 participants |
| **Result Format** | Single score per participant | Participant1 vs Participant2 |
| **Ranking** | Aggregate score/time/distance | Win/loss/draw |
| **Result Submission** | UI-based (forms) | API-based |
| **Session Generation** | One session (or one per round) | Pairings algorithm |

---

## Architecture

### Critical Insight (Line 97-109)

**File Comment:**
> "CRITICAL INSIGHT: In INDIVIDUAL_RANKING mode, tournament_format (league/knockout)
> is IGNORED by the backend! The backend uses individual_ranking_generator which
> doesn't differentiate between league/knockout."

**Implication:**
- League/Knockout variants were REMOVED as redundant
- Only scoring type and round count matter
- Saved 50% test time by removing duplicate configs

### Shared Workflows

**Provides shared functions to:** `tests/e2e_frontend/shared/shared_tournament_workflow.py`

**Exports:**
- `get_random_participants()` - Random player selection
- `wait_for_streamlit_load()` - Streamlit ready check
- `navigate_to_home()` - Home page navigation
- `click_create_new_tournament()` - Button click
- `fill_tournament_creation_form()` - Form filling
- `enroll_players_via_ui()` - UI enrollment
- `start_tournament_via_ui()` - Start workflow
- `generate_sessions_via_ui()` - Generate sessions
- **`submit_results_via_ui()`** ← **KEY**: UI result submission
- `finalize_sessions_via_ui()` - Finalize
- `complete_tournament_via_ui()` - Complete
- `distribute_rewards_via_ui()` - Rewards
- `verify_final_tournament_state()` - Validation
- `verify_skill_rewards()` - Reward verification

**Used by:**
- `tests/e2e_frontend/head_to_head/` (partial - skips `submit_results_via_ui`)
- Other E2E tests

---

## Scoring Types

### 1. SCORE_BASED

**Description:** Higher score is better (e.g., points in game)

**Ranking:** DESC (descending)

**Example:** Football shooting accuracy (10 shots scored)

**Configurations:** T1_Ind_Score_1R, T1_Ind_Score_2R, T1_Ind_Score_3R

---

### 2. TIME_BASED

**Description:** Lower time is better (e.g., sprint time)

**Ranking:** ASC (ascending)

**Measurement Unit:** seconds

**Example:** 100m sprint time (12.5 seconds)

**Configurations:** T2_Ind_Time_1R, T2_Ind_Time_2R, T2_Ind_Time_3R

---

### 3. DISTANCE_BASED

**Description:** Higher distance is better (e.g., long jump)

**Ranking:** DESC (descending)

**Measurement Unit:** meters

**Example:** Long jump distance (7.2 meters)

**Configurations:** T3_Ind_Distance_1R, T3_Ind_Distance_2R, T3_Ind_Distance_3R

---

### 4. PLACEMENT

**Description:** Lower placement is better (1st place = 1)

**Ranking:** ASC (ascending)

**Example:** Race finishing position (1st, 2nd, 3rd)

**Configurations:** T4_Ind_Placement_1R, T4_Ind_Placement_2R, T4_Ind_Placement_3R

---

### 5. ROUNDS_BASED

**Description:** More rounds passed is better

**Ranking:** DESC (descending)

**Example:** Obstacle course - how many obstacles cleared

**Configurations:** T5_Ind_Rounds_1R, T5_Ind_Rounds_2R, T5_Ind_Rounds_3R

---

## Round Variants

### 1 Round

**Total Sessions:** 1

**Ranking:** Based on single performance

**Example:** Single race, one attempt

---

### 2 Rounds

**Total Sessions:** 2

**Ranking:** Aggregate of 2 performances

**Example:** Two heats, average or total

---

### 3 Rounds

**Total Sessions:** 3

**Ranking:** Aggregate of 3 performances

**Example:** Three attempts, best or average

---

## Random Participant Selection

### Purpose

**File Comment (line 54-92):**
> "Select random NUMBER of random participants from the full student pool"

**Benefits:**
- Different participant count each run (4-8 players)
- Different users selected
- Catches edge cases (small/medium/full tournaments)

### Player Pool

```python
ALL_STUDENT_IDS = [4, 5, 6, 7, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]  # 14 students
```

**Range:** 4-8 participants per test (configurable)

---

## Troubleshooting

### Test Fails at Form Submission

**Symptom:** UI form doesn't submit

**Check:**
1. Streamlit rerun completed
2. Form button visible
3. Input fields filled correctly
4. No JavaScript errors

### Test Fails at Result Submission

**Symptom:** Results not saved

**Check:**
1. Session exists
2. Participant enrolled
3. Result format matches scoring type
4. Streamlit form_submit_button callback executed

### Test Fails at Ranking Calculation

**Symptom:** Rankings incorrect

**Check:**
1. Ranking direction correct (ASC vs DESC)
2. Multi-round aggregation correct
3. Tiebreaker logic applied

---

## Adding New Configurations

### Steps

1. **Add configuration to `ALL_TEST_CONFIGS`:**
```python
{
    "id": "T6_Ind_Custom_1R",
    "name": "INDIVIDUAL + CUSTOM (1 Round)",
    "tournament_format": "INDIVIDUAL_RANKING",
    "scoring_mode": "INDIVIDUAL",
    "scoring_type": "CUSTOM_TYPE",
    "ranking_direction": "DESC (Higher is better)",
    "measurement_unit": "units",
    "number_of_rounds": 1,
    "winner_count": 3,
    "max_players": 8,
}
```

2. **Test runs automatically** via parametrization

3. **Validate:**
```bash
pytest tests/e2e_frontend/individual_ranking/test_tournament_full_ui_workflow.py::test_full_ui_workflow[T6_Ind_Custom_1R] -v
```

---

## Markers

**No specific marker** - Use directory or file path to filter

**Usage:**
```bash
# By directory
pytest tests/e2e_frontend/individual_ranking/ -v

# By config ID
pytest tests/e2e_frontend/individual_ranking/ -v -k "T1_Ind_Score"
```

---

## Related Documentation

- [TEST_SUITE_ARCHITECTURE.md](../../../TEST_SUITE_ARCHITECTURE.md) - Overall test architecture
- [NAVIGATION_GUIDE.md](../../NAVIGATION_GUIDE.md) - Test navigation
- [shared/shared_tournament_workflow.py](../shared/shared_tournament_workflow.py) - Shared helpers

---

## Future Work

### P1 - High Priority

1. **Add Pytest Marker**
   - `@pytest.mark.individual_ranking`
   - Enable `pytest -m individual_ranking`

2. **File Rename**
   - `test_tournament_full_ui_workflow.py` → `test_individual_ranking_full_ui_workflow.py`
   - Improves clarity

### P2 - Medium Priority

3. **API-Based Result Submission**
   - Alternative test with API (faster)
   - Compare UI vs API behavior

4. **Error Recovery Tests**
   - Test invalid scores
   - Test duplicate round submissions
   - Test mid-tournament cancellation

---

**Author:** Claude Code (Sonnet 4.5)
**Date:** 2026-02-08
**Status:** Active (15 configurations)
