# 🚨 CRITICAL: Test Configuration & UI Issues

**Discovered**: 2026-02-03
**Status**: BLOCKING ALL E2E TESTS

---

## Issue #1: Missing UI `data-testid` for Participant Toggles

### Problem

E2E tests **CANNOT select participants** because Streamlit toggle switches have NO `data-testid` attributes!

**File**: `streamlit_sandbox_v3_admin_aligned.py` line 646-650

```python
# Toggle switch (on/off button)
toggle_key = f"participant_{user_id}"
is_selected = st.toggle(
    "",
    value=st.session_state.participant_toggles.get(user_id, False),
    key=toggle_key  # ❌ Only has 'key', no data-testid!
)
```

### Impact

- ❌ Playwright CANNOT find toggles
- ❌ E2E tests cannot enroll participants
- ❌ All tournaments run with **0 participants selected**
- ❌ Backend uses hardcoded TEST_USER_POOL instead

### Fix Required

```python
is_selected = st.toggle(
    "",
    value=st.session_state.participant_toggles.get(user_id, False),
    key=toggle_key,
    help=f"Select user {user_id}",
    kwargs={"data-testid": f"participant-toggle-{user_id}"}  # ✅ ADD THIS
)
```

**Then update E2E test selector**:
```python
toggle = page.locator(f'[data-testid="participant-toggle-{user_id}"]')
```

---

## Issue #2: Redundant League/Knockout in INDIVIDUAL Mode

### Problem

E2E test configs have **30 configurations**, but only **15 are unique**!

**Why?** `tournament_format="league"` vs `"knockout"` is **MEANINGLESS** in INDIVIDUAL_RANKING mode!

### Backend Behavior

**File**: `app/services/tournament/session_generation/session_generator.py` line 124-148

```python
if tournament.format == "INDIVIDUAL_RANKING":
    # ✅ Uses individual_ranking_generator
    # ❌ tournament_type (league/knockout) is IGNORED!
    sessions = self.individual_ranking_generator.generate(
        tournament=tournament,
        tournament_type=None,  # <-- NULL!
        player_count=player_count,
        ...
    )
else:
    # HEAD_TO_HEAD: league/knockout matters here
    if tournament_type.code == "league":
        sessions = self.league_generator.generate(...)
    elif tournament_type.code == "knockout":
        sessions = self.knockout_generator.generate(...)
```

**Key insight**:
- **INDIVIDUAL_RANKING**: `tournament_type = NULL`, uses `individual_ranking_generator`
- **HEAD_TO_HEAD**: `tournament_type` matters (league/knockout/swiss)

### Current Test Matrix (WRONG)

| Scoring Type | Formats | Rounds | Total Configs |
|--------------|---------|--------|---------------|
| SCORE_BASED | League + Knockout | 1, 2, 3 | **6** configs |
| TIME_BASED | League + Knockout | 1, 2, 3 | **6** configs |
| DISTANCE_BASED | League + Knockout | 1, 2, 3 | **6** configs |
| PLACEMENT | League + Knockout | 1, 2, 3 | **6** configs |
| ROUNDS_BASED | League + Knockout | 1, 2, 3 | **6** configs |
| **TOTAL** | | | **30** configs |

### Reality (Backend Behavior)

**INDIVIDUAL mode doesn't use tournament_type!**

Actual unique configurations:
- 5 scoring types × 3 rounds = **15 unique configs**
- League vs Knockout = **DUPLICATE TESTS** (waste of time!)

### Examples

These TWO configs are **IDENTICAL** in backend behavior:

```python
# Config 1
{
    "id": "T1_League_Ind_Score_1R",
    "tournament_format": "league",  # ← IGNORED!
    "scoring_mode": "INDIVIDUAL",
    "scoring_type": "SCORE_BASED",
    "number_of_rounds": 1,
}

# Config 2
{
    "id": "T2_Knockout_Ind_Score_1R",
    "tournament_format": "knockout",  # ← IGNORED!
    "scoring_mode": "INDIVIDUAL",
    "scoring_type": "SCORE_BASED",
    "number_of_rounds": 1,
}
```

**Both call**:
```python
individual_ranking_generator.generate(
    tournament=tournament,
    tournament_type=None,  # <-- Same!
    ...
)
```

### Impact

- ❌ **50% redundant tests** (15 duplicate configs)
- ❌ **Wasted time**: ~1.5 hours for 15 identical tests
- ❌ **False confidence**: Thinking we test 30 configs, but only 15 unique
- ❌ **Confusing naming**: "League INDIVIDUAL" makes no semantic sense

### Fix Options

#### Option A: Remove Redundant Configs (Recommended)

**Reduce from 30 to 15 configs**:

```python
ALL_TEST_CONFIGS = [
    # INDIVIDUAL + SCORE_BASED (3 configs: 3 round variants)
    {
        "id": "T1_Ind_Score_1R",
        "name": "INDIVIDUAL + SCORE_BASED (1 Round)",
        "tournament_format": "INDIVIDUAL_RANKING",  # ✅ Explicit!
        "scoring_mode": "INDIVIDUAL",
        "scoring_type": "SCORE_BASED",
        "number_of_rounds": 1,
        ...
    },
    {
        "id": "T1_Ind_Score_2R",
        "tournament_format": "INDIVIDUAL_RANKING",
        "number_of_rounds": 2,
        ...
    },
    {
        "id": "T1_Ind_Score_3R",
        "tournament_format": "INDIVIDUAL_RANKING",
        "number_of_rounds": 3,
        ...
    },
    # Repeat for TIME_BASED, DISTANCE_BASED, PLACEMENT, ROUNDS_BASED
]
```

**Result**: 5 scoring types × 3 rounds = **15 configs** (50% time savings!)

#### Option B: Keep Both, Add HEAD_TO_HEAD Tests Later

Keep redundant configs for now, but:
1. Document that League/Knockout are redundant in INDIVIDUAL mode
2. Add note that these will be differentiated when HEAD_TO_HEAD is implemented
3. In Phase 2, add TRUE league/knockout tests with HEAD_TO_HEAD mode

**Result**: Keep 30 configs, but acknowledge 15 are duplicates

#### Option C: Make League/Knockout Actually Different

Modify backend to make tournament_type meaningful even in INDIVIDUAL mode:
- **League**: Multiple sessions, all players compete in each session
- **Knockout**: Progressive elimination (but still INDIVIDUAL scoring)

**Result**: More complex implementation, questionable value

---

## Issue #3: UI Form Doesn't Set `tournament.format` Correctly

### Investigation Needed

Check `streamlit_sandbox_v3_admin_aligned.py`:
1. Does form send `tournament_format` field?
2. Does it send "league"/"knockout" or "INDIVIDUAL_RANKING"?
3. Does backend API accept and use this field?

**Hypothesis**: The UI might be setting `tournament_type` instead of `tournament.format`, causing confusion.

---

## Recommended Actions

### Immediate (Blocking)

1. ✅ **Add `data-testid` to participant toggles**
   - File: `streamlit_sandbox_v3_admin_aligned.py`
   - Add `data-testid="participant-toggle-{user_id}"` to each toggle
   - Update E2E test selectors

2. ✅ **Fix test configs (Option A)**
   - Remove redundant league/knockout variants
   - Reduce from 30 to 15 configs
   - Update documentation
   - **Time saved**: ~1.5 hours per test run!

3. ✅ **Update test names**
   - Remove confusing "League"/"Knockout" prefix
   - Use clear naming: "T1_Ind_Score_1R" not "T1_League_Ind_Score_1R"

### Short-Term

4. ⏳ **Audit UI → Backend flow**
   - Verify `tournament_format` vs `tournament_type` usage
   - Ensure UI sends correct field for INDIVIDUAL mode
   - Add validation: Reject league/knockout when mode=INDIVIDUAL

5. ⏳ **Add backend validation**
   - If `scoring_mode == "INDIVIDUAL"`, force `tournament.format = "INDIVIDUAL_RANKING"`
   - Ignore `tournament_type` field
   - Return error if both are inconsistent

### Long-Term (Phase 2)

6. ⏳ **Implement HEAD_TO_HEAD mode**
   - Add league/knockout tests for HEAD_TO_HEAD
   - Test TRUE head-to-head matchups
   - Validate pairing logic

---

## Summary

| Issue | Severity | Impact | Status |
|-------|----------|--------|--------|
| Missing data-testid | 🔴 CRITICAL | E2E tests can't select participants | ⏳ Fix required |
| Redundant configs | 🟠 HIGH | 50% wasted test time (1.5hrs) | ⏳ Fix recommended |
| UI format confusion | 🟡 MEDIUM | Unclear what backend receives | ⏳ Investigation needed |

**Estimated Fix Time**: 30-60 minutes
**Time Savings**: ~1.5 hours per test run (50% reduction)

---

**Created**: 2026-02-03
**Priority**: P0 (Blocking)
**Next Steps**: Fix data-testid, then remove redundant configs
