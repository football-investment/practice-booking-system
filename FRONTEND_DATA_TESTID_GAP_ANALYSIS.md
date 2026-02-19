# Frontend data-testid Gap Analysis
**Generated**: 2026-02-02
**Purpose**: Identify missing data-testid attributes required for 100% UI-driven Playwright E2E tests

---

## Executive Summary

**Current State**:
- ✅ **Leaderboard & Rewards UI**: Fully instrumented with data-testid attributes
- ❌ **Navigation & Workflow UI**: Almost no data-testid attributes
- **Gap**: ~95% of interactive elements (buttons, forms, inputs) lack testable identifiers

**Recommendation**: Add data-testid attributes to ALL interactive elements before implementing full UI workflow tests.

---

## Audit Results by File

### ✅ sandbox_helpers.py - GOOD (100% coverage)

**Status**: All UI rendering components have data-testid attributes

**Existing data-testid attributes**:
- `tournament-rankings` - Rankings container
- `rankings-table` - Rankings table
- `ranking-row` - Each ranking row (with data-rank, data-user-id, data-is-winner)
- `rank` - Rank column
- `player-name` - Player name column
- `final-score` - Score column
- `winner-badge` - Winner trophy icon
- `rewards-summary` - Rewards summary container
- `players-rewarded` - Players rewarded count (with data-value)
- `total-xp` - Total XP distributed (with data-value)
- `total-credits` - Total credits distributed (with data-value)
- `skill-rewards-count` - Skill rewards count (with data-value)

**Action Required**: ✅ NONE - Already fully instrumented

---

### ❌ streamlit_sandbox_v3_admin_aligned.py - CRITICAL GAPS (5% coverage)

**Status**: Only 1 data-testid out of ~20+ interactive elements

**Existing data-testid attributes**:
- `tournament-status` - Tournament status badge (with data-status attribute)

**MISSING data-testid attributes**:

#### Home Page (Screen: home)
- ❌ `btn-create-tournament` - "Create New Tournament" button
- ❌ `btn-view-history` - "View Tournament History" button

#### Tournament History (Screen: instructor_workflow, no tournament selected)
- ❌ `tournament-history-table` - Tournament list/table
- ❌ `tournament-row` - Each tournament row (should include data-tournament-id)
- ❌ `btn-view-tournament` - Button to view specific tournament

#### Query Parameter Handling
- Currently works via `?tournament_id=X` but no UI buttons to test navigation

**Action Required**:
1. Add data-testid to "Create New Tournament" button
2. Add data-testid to "View Tournament History" button
3. Add data-testid to tournament list rows with data-tournament-id attribute

---

### ❌ sandbox_workflow.py - CRITICAL GAPS (5% coverage)

**Status**: Only 1 data-testid out of ~50+ interactive elements

**Existing data-testid attributes**:
- `tournament-status` - Tournament status badge

**MISSING data-testid attributes by Workflow Step**:

#### Step 1: Review Tournament Info
- ❌ `tournament-code-display` - Tournament code value
- ❌ `tournament-name-display` - Tournament name value
- ❌ `tournament-format-display` - Format value
- ❌ `scoring-type-display` - Scoring type value
- ❌ `btn-start-enrollment` - "Enroll Players" button
- ❌ `btn-back-to-home` - "Back to Home" button

#### Step 2: Enroll Players
- ❌ `enrollment-status` - Current enrollment count display
- ❌ `player-select-multiselect` - Player selection multiselect widget
- ❌ `btn-confirm-enrollment` - "Confirm Enrollment" button
- ❌ `btn-cancel-enrollment` - "Cancel" button

#### Step 3: Start Tournament
- ❌ `enrolled-players-count` - Enrolled players count display
- ❌ `btn-start-tournament` - "Start Tournament" button
- ❌ `btn-back-to-enrollment` - "Back" button

#### Step 4: Generate Sessions
- ❌ `parallel-fields-input` - Parallel fields number input
- ❌ `session-duration-input` - Session duration input
- ❌ `break-minutes-input` - Break minutes input
- ❌ `btn-generate-sessions` - "Generate Sessions" button
- ❌ `btn-skip-generation` - "Skip" button

#### Step 5: Submit Results
- ❌ `session-list-container` - Sessions list container
- ❌ `session-row` - Each session row (with data-session-id)
- ❌ `result-input-player-{user_id}` - Result input for each player
- ❌ `btn-submit-session-results` - "Submit Results" button per session
- ❌ `btn-auto-fill-all` - "Auto-Fill ALL Remaining Rounds" button

#### Step 6: Finalize Sessions
- ❌ `finalize-status` - Finalization status display
- ❌ `btn-finalize-sessions` - "Finalize Sessions" button
- ❌ `btn-skip-finalization` - "Skip" button

#### Step 7: View Leaderboard
- ❌ `leaderboard-container` - Leaderboard display container
- ❌ `btn-complete-tournament` - "Complete Tournament" button
- ❌ `btn-back-to-results` - "Back" button

#### Step 8: Complete Tournament
- ❌ `completion-status` - Completion status display
- ❌ `btn-distribute-rewards` - "Distribute Rewards" button
- ❌ `btn-skip-completion` - "Skip" button

#### Step 7 (Rewards View - after completion)
- ❌ `rewards-container` - Rewards display (already handled by sandbox_helpers.py)
- ❌ `btn-back-to-history` - "Back to History" button
- ❌ `btn-view-leaderboard` - "View Leaderboard" button

**Action Required**: Add data-testid to ALL buttons and input fields across all 8 workflow steps

---

### ❌ streamlit_preset_forms.py - CRITICAL GAPS (0% coverage)

**Status**: NO data-testid attributes whatsoever

**MISSING data-testid attributes**:

#### Tournament Creation Form
- ❌ `tournament-code-input` - Tournament code text input
- ❌ `tournament-name-input` - Tournament name text input
- ❌ `age-group-select` - Age group selectbox
- ❌ `specialization-select` - Specialization type selectbox
- ❌ `format-select` - Tournament format selectbox (INDIVIDUAL_RANKING vs HEAD_TO_HEAD)
- ❌ `scoring-type-select` - Scoring type selectbox (ROUNDS_BASED, TIME_BASED, etc.)
- ❌ `measurement-unit-input` - Measurement unit input
- ❌ `ranking-direction-select` - Ranking direction select (ASC/DESC)
- ❌ `tournament-type-select` - Tournament type selectbox (for HEAD_TO_HEAD)
- ❌ `number-of-rounds-input` - Number of rounds input
- ❌ `max-players-input` - Max players input
- ❌ `winner-count-input` - Winner count input (for INDIVIDUAL_RANKING)
- ❌ `location-city-input` - Location city input
- ❌ `location-venue-input` - Location venue input
- ❌ `start-date-input` - Start date picker
- ❌ `end-date-input` - End date picker
- ❌ `enrollment-cost-input` - Enrollment cost input
- ❌ `btn-create-tournament` - "Create Tournament" button
- ❌ `btn-cancel-creation` - "Cancel" button

**Action Required**: Add data-testid to ALL form fields and buttons

---

## Priority Matrix

### P0 - CRITICAL (Blocks all UI testing)
1. **streamlit_preset_forms.py** - Tournament creation form (ALL fields)
2. **sandbox_workflow.py Steps 2-8** - Enrollment through completion buttons

### P1 - HIGH (Blocks navigation testing)
3. **streamlit_sandbox_v3_admin_aligned.py** - Home page navigation buttons
4. **sandbox_workflow.py Step 1** - Review info and navigation

### P2 - MEDIUM (Nice to have for comprehensive testing)
5. **streamlit_sandbox_v3_admin_aligned.py** - Tournament history table rows

---

## Recommended Implementation Order

### Phase 1: Enable Basic Workflow (P0)
1. Add data-testid to streamlit_preset_forms.py form inputs (15 attributes)
2. Add data-testid to sandbox_workflow.py Step 2 enrollment buttons (3 attributes)
3. Add data-testid to sandbox_workflow.py Step 3 start button (1 attribute)
4. Add data-testid to sandbox_workflow.py Step 4 session generation (4 attributes)
5. Add data-testid to sandbox_workflow.py Step 5 results submission (5 attributes)
6. Add data-testid to sandbox_workflow.py Step 6 finalization (2 attributes)
7. Add data-testid to sandbox_workflow.py Step 8 completion/rewards (2 attributes)

**Total**: ~32 data-testid additions

### Phase 2: Enable Navigation (P1)
8. Add data-testid to home page buttons (2 attributes)
9. Add data-testid to workflow Step 1 navigation (3 attributes)

**Total**: ~5 data-testid additions

### Phase 3: Full Coverage (P2)
10. Add data-testid to tournament history table (2 attributes)

**Total**: ~2 data-testid additions

---

## Technical Notes

### Streamlit data-testid Best Practices

1. **Buttons**: Use `key` parameter in st.button()
   ```python
   if st.button("Create Tournament", key="btn-create-tournament"):
   ```
   Streamlit automatically adds `data-testid="stButton"` but key creates unique identifier

2. **Text Inputs**: Use `key` parameter in st.text_input()
   ```python
   code = st.text_input("Tournament Code", key="tournament-code-input")
   ```

3. **Selectboxes**: Use `key` parameter in st.selectbox()
   ```python
   format_val = st.selectbox("Format", options=["INDIVIDUAL_RANKING", "HEAD_TO_HEAD"], key="format-select")
   ```

4. **Custom HTML**: Use unsafe_allow_html
   ```python
   st.markdown(f'<div data-testid="custom-element" data-value="{value}">Content</div>', unsafe_allow_html=True)
   ```

### Playwright Selector Syntax

```python
# By Streamlit key (becomes data-test-id in DOM)
page.locator('[data-testid="btn-create-tournament"]')

# By custom data-testid
page.locator('[data-testid="tournament-status"]')

# With additional attribute filters
page.locator('[data-testid="ranking-row"][data-rank="1"]')
```

---

## Estimated Implementation Effort

- **Phase 1 (P0)**: ~2-3 hours (32 additions across 2 files)
- **Phase 2 (P1)**: ~30 minutes (5 additions)
- **Phase 3 (P2)**: ~15 minutes (2 additions)

**Total**: ~3-4 hours for complete data-testid instrumentation

---

## Conclusion

**Current State**: The frontend is NOT ready for 100% UI-driven Playwright tests. Only the final results view (leaderboard & rewards) has proper data-testid coverage.

**Required Work**: Add ~39 data-testid attributes across 3 files to enable full E2E UI testing.

**Recommendation**: Implement Phase 1 (P0) first to unblock basic workflow testing, then proceed with Phases 2-3 for complete coverage.

**Next Steps**:
1. Review and approve this gap analysis
2. Prioritize which phases to implement
3. Begin systematic data-testid addition following best practices
4. Test each addition with Playwright as implemented
5. Update `test_tournament_full_ui_workflow.py` progressively as attributes are added
