# HEAD_TO_HEAD Playwright Test Suite - Implementation Plan

**Status**: 🚧 IN PROGRESS
**Goal**: Create CI-ready, headless, reprodukálható HEAD_TO_HEAD test coverage
**Date**: 2026-02-04

---

## Test Suite Architecture

### File Structure
```
tests/e2e_frontend/
├── test_tournament_full_ui_workflow.py     # INDIVIDUAL (15/15 PASS)
├── test_tournament_head_to_head.py         # HEAD_TO_HEAD (NEW - to be created)
├── shared_tournament_workflow.py           # Shared helpers
└── streamlit_helpers.py                    # Streamlit UI helpers
```

### Test Isolation
- ✅ Separate test file for HEAD_TO_HEAD
- ✅ Marker: `@pytest.mark.h2h`
- ✅ Run independently: `pytest -m h2h`
- ✅ No interference with INDIVIDUAL suite

---

## HEAD_TO_HEAD Config Matrix

### League Configs (3 variants)
```python
{
    "id": "H1_League_Basic",
    "name": "HEAD_TO_HEAD League (4 players)",
    "tournament_format": "league",
    "scoring_mode": "HEAD_TO_HEAD",
    "skills_to_test": ["dribbling", "passing", "shooting"],
    "winner_count": 3,
    "max_players": 4,  # 6 matches (4×3/2)
}

{
    "id": "H2_League_Medium",
    "name": "HEAD_TO_HEAD League (6 players)",
    "tournament_format": "league",
    "scoring_mode": "HEAD_TO_HEAD",
    "skills_to_test": ["dribbling", "passing"],
    "winner_count": 2,
    "max_players": 6,  # 15 matches (6×5/2)
}

{
    "id": "H3_League_Large",
    "name": "HEAD_TO_HEAD League (8 players)",
    "tournament_format": "league",
    "scoring_mode": "HEAD_TO_HEAD",
    "skills_to_test": ["shooting"],
    "winner_count": 3,
    "max_players": 8,  # 28 matches (8×7/2)
}
```

### Knockout Configs (3 variants)
```python
{
    "id": "H4_Knockout_4",
    "name": "HEAD_TO_HEAD Knockout (4 players)",
    "tournament_format": "knockout",
    "scoring_mode": "HEAD_TO_HEAD",
    "skills_to_test": ["dribbling", "passing", "shooting"],
    "winner_count": 2,
    "max_players": 4,  # 3 matches (2+1)
}

{
    "id": "H5_Knockout_8",
    "name": "HEAD_TO_HEAD Knockout (8 players)",
    "tournament_format": "knockout",
    "scoring_mode": "HEAD_TO_HEAD",
    "skills_to_test": ["dribbling", "passing"],
    "winner_count": 3,
    "max_players": 8,  # 7 matches (4+2+1)
}

{
    "id": "H6_Knockout_16",
    "name": "HEAD_TO_HEAD Knockout (16 players)",
    "tournament_format": "knockout",
    "scoring_mode": "HEAD_TO_HEAD",
    "skills_to_test": ["shooting"],
    "winner_count": 3,
    "max_players": 16,  # 15 matches (8+4+2+1)
}
```

**Total Configs**: 6 (3 League + 3 Knockout)

---

## Test Workflow (Per Config)

### Phase 1: Setup
1. Get random participants (from ALL_STUDENT_IDS)
2. Create tournament via sandbox API
3. Enroll participants via API
4. Generate sessions via API

### Phase 2: Result Submission (CURRENT BLOCKER)
**Problem**: Manual UI for HEAD_TO_HEAD not ready
**Options**:
- **A**: Use API directly (POST /sessions/{id}/head-to-head-results)
- **B**: SKIP result submission, test only setup
- **C**: Wait for manual UI, then use Playwright

**Decision**: **Option A** - Use API directly for now
- Pro: Tests can run immediately, validate full workflow
- Pro: API is the source of truth, UI is just interface
- Con: Doesn't validate Streamlit UI (but that's not critical for CI)

### Phase 3: Ranking & Rewards
1. Calculate rankings via API (POST /tournaments/{id}/calculate-rankings)
2. Distribute rewards via API
3. Verify database state (rankings, xp_transactions, skill_rewards)

### Phase 4: Validation
1. Query database for tournament state
2. Verify session count matches expected
3. Verify all results submitted
4. Verify rankings correct
5. Verify rewards distributed

---

## Implementation Strategy

### Step 1: Create API-based Result Submission Helper
```python
def submit_head_to_head_results_via_api(
    tournament_id: int,
    sessions: List[Dict],
    api_client
):
    """
    Submit HEAD_TO_HEAD match results via API (not UI)

    For each session:
    - Get participants
    - Generate random scores (0-5)
    - Call POST /sessions/{session_id}/head-to-head-results
    """
    for session in sessions:
        session_id = session['id']
        participants = session['participants']

        # Generate random scores
        score_1 = random.randint(0, 5)
        score_2 = random.randint(0, 5)

        api_client.patch(
            f"/api/v1/sessions/{session_id}/head-to-head-results",
            data={
                "results": [
                    {"user_id": participants[0]['id'], "score": score_1},
                    {"user_id": participants[1]['id'], "score": score_2}
                ]
            }
        )
```

### Step 2: Create Ranking Calculation Helper
```python
def calculate_rankings_via_api(tournament_id: int, api_client):
    """Call POST /tournaments/{id}/calculate-rankings"""
    response = api_client.post(
        f"/api/v1/tournaments/{tournament_id}/calculate-rankings"
    )
    return response.json()
```

### Step 3: Create HEAD_TO_HEAD Test Function
```python
@pytest.mark.h2h
@pytest.mark.parametrize("config", HEAD_TO_HEAD_CONFIGS, ids=lambda c: c["id"])
def test_head_to_head_tournament_workflow(page: Page, config: dict):
    """
    Complete HEAD_TO_HEAD tournament workflow test

    Uses API for result submission (not UI) to enable headless testing
    """
    # Phase 1: Setup (via sandbox API)
    participants = get_random_participants(config['max_players'])
    tournament_id = create_tournament_via_api(config)
    enroll_participants_via_api(tournament_id, participants)
    sessions = generate_sessions_via_api(tournament_id)

    # Phase 2: Results (via API - not UI)
    submit_head_to_head_results_via_api(tournament_id, sessions, api_client)

    # Phase 3: Rankings & Rewards (via API)
    rankings = calculate_rankings_via_api(tournament_id, api_client)
    distribute_rewards_via_api(tournament_id, api_client)

    # Phase 4: Validation (database queries)
    verify_tournament_state(tournament_id, config, rankings)
    verify_rewards(tournament_id, config, rankings)
```

---

## Expected Test Results

### Success Criteria (Per Config)
- ✅ Tournament created with correct tournament_type_id
- ✅ All sessions generated (correct count for format)
- ✅ All results submitted successfully
- ✅ Rankings calculated correctly
- ✅ Rewards distributed to top N
- ✅ No crashes or errors

### Failure Scenarios to Handle
- ❌ Tie in knockout (need tiebreaker - not yet implemented)
- ❌ Missing tournament_type_id
- ❌ Invalid participant count (not power of 2 for knockout)

---

## CI Integration

### GitHub Actions Workflow
```yaml
- name: Run HEAD_TO_HEAD Tests
  run: |
    pytest -m h2h -v --tb=short
```

### Expected Runtime
- League 4: ~5 seconds
- League 6: ~10 seconds
- League 8: ~20 seconds
- Knockout 4: ~3 seconds
- Knockout 8: ~5 seconds
- Knockout 16: ~10 seconds
**Total**: ~53 seconds for 6 configs

---

## Next Steps

1. ✅ Create `submit_head_to_head_results_via_api()` helper
2. ✅ Create `calculate_rankings_via_api()` helper
3. ✅ Update `test_tournament_head_to_head.py` to use API-based flow
4. ✅ Run full config matrix (6 configs)
5. ✅ Fix any P0/P1 issues
6. ✅ Document results
7. ⏸️ Manual UI playthrough (optional, after headless PASS)

---

**Status**: Ready to implement API-based HEAD_TO_HEAD test suite
**Blocker**: None (API endpoints exist and validated)
**ETA**: ~30 minutes for implementation + test run
