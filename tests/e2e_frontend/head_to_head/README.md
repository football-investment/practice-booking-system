# HEAD_TO_HEAD Tournament E2E Tests

**Purpose:** Validate HEAD_TO_HEAD tournament format (1v1 matches)

**Status:** ✅ Active

---

## Overview

This directory contains E2E tests for **HEAD_TO_HEAD tournaments** - 1v1 match-based competitions with League and Knockout formats.

**Key Characteristics:**
- **Scoring Mode:** HEAD_TO_HEAD (1 vs 1 matches)
- **Result Submission:** API-based (headless-ready)
- **Formats Tested:** League (Round Robin)
- **Formats TODO:** Knockout (multi-phase workflow needed)

---

## Files

### `test_tournament_head_to_head.py`

**What it tests:**
- Tournament creation with HEAD_TO_HEAD scoring mode
- Session generation for 1v1 matches
- Result submission via API (POST `/sessions/{id}/head-to-head-results`)
- Ranking calculation via API
- Reward distribution
- Full lifecycle validation

**Configurations:**
- **H1_League_Basic:** 4 players, 6 matches (4×3/2)
- **H2_League_Medium:** 6 players, 15 matches (6×5/2)
- **H3_League_Large:** 8 players, 28 matches (8×7/2)

**Status:**
- ✅ League: 3 configurations active
- ⚠️ Knockout: Disabled (multi-phase workflow needed)
- ⚠️ Group+Knockout: Disabled (2-phase workflow needed)

---

## Running Tests

### Run All HEAD_TO_HEAD Tests

```bash
# By marker
pytest -m h2h -v

# By directory
pytest tests/e2e_frontend/head_to_head/ -v

# By file
pytest tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py -v
```

### Run Specific Configuration

```bash
# 4 players league
pytest tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py::test_head_to_head_tournament_e2e[H1_League_Basic] -v

# 6 players league
pytest tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py::test_head_to_head_tournament_e2e[H2_League_Medium] -v

# 8 players league
pytest tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py::test_head_to_head_tournament_e2e[H3_League_Large] -v
```

### Run Headless (CI)

```bash
HEADED=0 pytest -m h2h -v
```

### Run with Visual Browser

```bash
HEADED=1 pytest -m h2h -v
```

---

## Test Workflow

### League Format (Round Robin)

1. **Create Tournament** - HEAD_TO_HEAD League via UI
2. **Enroll Players** - 4/6/8 players via UI
3. **Start Tournament** - Mark as IN_PROGRESS
4. **Generate Sessions** - Create all 1v1 matches
5. **Submit Results via API** - All matches (not UI)
6. **Finalize Sessions** - Mark all complete
7. **Calculate Rankings** - Via API
8. **Complete Tournament** - Mark as COMPLETED
9. **Distribute Rewards** - Skill rewards + XP
10. **Verify State** - Database validation

---

## Key Differences from INDIVIDUAL

| Aspect | HEAD_TO_HEAD | INDIVIDUAL_RANKING |
|--------|--------------|-------------------|
| **Match Type** | 1v1 matches | Individual performances |
| **Result Format** | Participant1 vs Participant2 scores | Single participant score |
| **Session Generation** | Pairings algorithm | All participants in same session |
| **Ranking** | Win/loss/draw + head-to-head | Aggregate score/time/distance |
| **Result Submission** | API-based (this test) | UI-based |

---

## Architecture

### Isolation

**File Comment (line 18):**
> "ISOLATION: Does NOT interfere with INDIVIDUAL test suite."

**How:**
- Separate test file
- Separate configurations (`HEAD_TO_HEAD_CONFIGS`)
- Different result submission method (API vs UI)
- Imports shared workflows selectively (skips `submit_results_via_ui`)

### Shared Workflows

**Imports from:** `tests/e2e_frontend/shared/shared_tournament_workflow.py`

**Uses:**
- `get_random_participants` ✅
- `navigate_to_home` ✅
- `click_create_new_tournament` ✅
- `enroll_players_via_ui` ✅
- `start_tournament_via_ui` ✅
- `generate_sessions_via_ui` ✅
- ~~`submit_results_via_ui`~~ ❌ **NOT IMPORTED** (uses API instead)

**Custom Logic:**
- `get_tournament_sessions_via_api()` - Fetch session pairings
- `submit_head_to_head_result_via_api()` - API result submission

---

## Test Configurations

### H1_League_Basic (4 players)

```python
{
    "id": "H1_League_Basic",
    "name": "HEAD_TO_HEAD League (4 players)",
    "tournament_format": "league",
    "scoring_mode": "HEAD_TO_HEAD",
    "max_players": 4,  # 6 matches (4×3/2)
    "winner_count": 3,
    "skills_to_test": ["dribbling", "passing", "shooting"],
}
```

**Total Matches:** 6 (round-robin)

---

### H2_League_Medium (6 players)

```python
{
    "id": "H2_League_Medium",
    "name": "HEAD_TO_HEAD League (6 players)",
    "tournament_format": "league",
    "scoring_mode": "HEAD_TO_HEAD",
    "max_players": 6,  # 15 matches (6×5/2)
    "winner_count": 2,
    "skills_to_test": ["dribbling", "passing"],
}
```

**Total Matches:** 15 (round-robin)

---

### H3_League_Large (8 players)

```python
{
    "id": "H3_League_Large",
    "name": "HEAD_TO_HEAD League (8 players)",
    "tournament_format": "league",
    "scoring_mode": "HEAD_TO_HEAD",
    "max_players": 8,  # 28 matches (8×7/2)
    "winner_count": 3,
    "skills_to_test": ["shooting"],
}
```

**Total Matches:** 28 (round-robin)

---

## Disabled Configurations

### Knockout (DISABLED)

**Reason:** Multi-phase workflow required

**Current Issue:**
```
participant_user_ids is NULL for rounds 2+ until previous round completes
```

**Workflow Needed:**
1. Submit QF results
2. Backend assigns SF participants → `/complete`
3. Submit SF results
4. Backend assigns Final participants → `/complete`
5. Submit Final results → `/complete`

**TODO:** Implement multi-phase workflow for complete Knockout E2E coverage

---

### Group + Knockout (DISABLED)

**Reason:** 2-phase workflow required

**Workflow Needed:**
1. Submit group stage results
2. Complete group stage → qualifiers determined
3. Backend populates knockout sessions with qualifiers
4. Submit knockout results
5. Complete tournament

**TODO:** Implement full 2-phase workflow for complete Group+Knockout E2E coverage

---

## Result Submission (API-Based)

### Why API Instead of UI?

**Reasons:**
1. **Headless CI compatibility** - No UI interaction needed
2. **Speed** - Faster than clicking through UI forms
3. **Reliability** - No Playwright/Streamlit interaction issues
4. **Determinism** - API responses are consistent

### API Endpoint

```python
POST /api/v1/sessions/{session_id}/head-to-head-results

Request Body:
{
    "participant1_id": int,
    "participant2_id": int,
    "participant1_score": int,
    "participant2_score": int,
    "status": "completed"
}
```

---

## Troubleshooting

### Test Fails at Session Generation

**Symptom:** No sessions created or `participant_user_ids` is NULL

**Check:**
1. Tournament type is `league` (not knockout)
2. Enrolled player count matches `max_players`
3. Session generation API call succeeded

### Test Fails at Result Submission

**Symptom:** API returns 400/500 error

**Check:**
1. Session ID valid
2. Participant IDs match enrolled players
3. Scores are valid integers
4. Session not already completed

### Test Fails at Ranking Calculation

**Symptom:** Rankings incorrect or API fails

**Check:**
1. All matches submitted
2. Win/loss/draw logic correct
3. Head-to-head tiebreaker working

---

## Adding New Configurations

### Steps

1. **Add configuration to `HEAD_TO_HEAD_CONFIGS`:**
```python
{
    "id": "H4_League_10",
    "name": "HEAD_TO_HEAD League (10 players)",
    "tournament_format": "league",
    "scoring_mode": "HEAD_TO_HEAD",
    "max_players": 10,  # 45 matches
    "winner_count": 3,
    "skills_to_test": ["dribbling"],
}
```

2. **Test runs automatically** via parametrization

3. **Validate:**
```bash
pytest tests/e2e_frontend/head_to_head/test_tournament_head_to_head.py::test_head_to_head_tournament_e2e[H4_League_10] -v
```

---

## Markers

```python
@pytest.mark.h2h  # Applied to ALL tests in file via pytestmark
```

**Usage:**
```bash
pytest -m h2h -v
```

---

## Related Documentation

- [TEST_SUITE_ARCHITECTURE.md](../../../TEST_SUITE_ARCHITECTURE.md) - Overall test architecture
- [NAVIGATION_GUIDE.md](../../NAVIGATION_GUIDE.md) - Test navigation
- [shared/shared_tournament_workflow.py](../shared/shared_tournament_workflow.py) - Shared helpers

---

## Future Work

### P1 - High Priority

1. **Knockout Multi-Phase Workflow**
   - Implement round-by-round completion
   - Handle `participant_user_ids` NULL for later rounds
   - Enable H4-H5 configurations

2. **Group+Knockout Hybrid**
   - Implement 2-phase workflow
   - Enable H6-H7 configurations

### P2 - Medium Priority

3. **UI-Based Result Submission**
   - Alternative test with UI forms
   - Validate Streamlit form workflow

4. **Error Recovery Tests**
   - Test invalid scores
   - Test duplicate submissions
   - Test mid-tournament cancellation

---

**Author:** Claude Code (Sonnet 4.5)
**Date:** 2026-02-08
**Status:** Active (League), TODO (Knockout)
