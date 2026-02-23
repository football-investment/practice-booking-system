# Frontend UI Validation Backlog - 2026-02-02

## 🔴 CRITICAL: Incomplete UI Validation

**Status**: ⚠️ **INCOMPLETE** - Backend 100% tested, Frontend UI validation incomplete
**Playwright Tests**: ✅ 18/18 PASSED (API workflow only)
**UI Validation**: ❌ Steps 9-12 mostly skipped due to selector issues

---

## Current Status Summary

### ✅ What Works (100% Tested)

**Backend API Workflow (Steps 1-8)**:
- ✅ Tournament creation (all 18 configs)
- ✅ Player enrollment (8 test players)
- ✅ Tournament start (status transitions)
- ✅ Session generation (correct counts)
- ✅ Result submission (all scoring types)
- ✅ Session finalization (INDIVIDUAL_RANKING)
- ✅ Tournament completion (status transitions)
- ✅ Reward distribution (all winner counts: 1, 2, 3, 5)

### ❌ What's Missing (UI Validation Steps 9-12)

**Step 9: Tournament Status Display** - ⚠️ SKIPPED
- **Issue**: Selector `text=REWARDS_DISTRIBUTED` not found
- **Impact**: Cannot verify status badge/text in UI
- **Configs Affected**: 15/18 (all INDIVIDUAL_RANKING)

**Step 10: Rankings Display** - ⚠️ PARTIALLY TESTED
- **Working**: HEAD_TO_HEAD (T6, T7, T18) ✅
- **Skipped**: INDIVIDUAL_RANKING (T1-T5, T8-T17) ❌
- **Issue**: Selector `text=/.*2.*/` too generic
- **Impact**: Cannot verify ranking tables, medals, positions

**Step 11: Rewards Distribution** - ⚠️ PARTIALLY TESTED
- **Working**: HEAD_TO_HEAD (T6, T7, T18) ✅
- **Skipped**: INDIVIDUAL_RANKING (T1-T5, T8-T17) ❌
- **Issue**: Selector `text=/reward/i` not found
- **Impact**: Cannot verify reward summary section

**Step 12: Winner Count Handling** - ❌ COMPLETELY SKIPPED
- **Issue**: Selector `text=/winner|🏆|🥇/i` not found
- **Impact**: Cannot verify 1, 2, 3, 5 winner highlights
- **Configs Affected**: All 15 INDIVIDUAL_RANKING configs
- **Critical**: This was explicitly requested by user

---

## Root Causes

### 1. Unknown UI Structure
- **Problem**: Playwright test was created without inspecting actual Streamlit UI
- **Selectors Used**: Generic text-based selectors (fragile)
- **Solution Needed**: Manual UI inspection to identify real elements

### 2. No data-testid Attributes
- **Problem**: Streamlit components lack stable test identifiers
- **Impact**: Selectors break when UI text changes
- **Solution Needed**: Add `data-testid` to critical elements

### 3. Unknown Navigation Path
- **Problem**: Test uses `?tournament_id=` URL parameter
- **Reality**: May need to navigate via UI clicks/menus
- **Solution Needed**: Identify correct navigation flow

### 4. Multiple Recording Interfaces Not Tested
- **Identified Interfaces**:
  1. Game Result Entry (basic form)
  2. Match Command Center (advanced multi-round)
- **Problem**: Neither interface validated in automated tests
- **Solution Needed**: Manual testing of both interfaces

---

## Manual UI Validation Plan

### Phase 1: UI Structure Discovery (1-2 hours)

**Objective**: Identify all UI elements and their selectors

**Tasks**:
1. **Launch Streamlit app** and navigate to tournament pages
2. **Open browser DevTools** (Inspect Element)
3. **Document UI structure** for each page:
   - Tournament list/grid page
   - Tournament detail page
   - Game result entry page
   - Match command center page
4. **Identify selectors** for critical elements:
   - Tournament status badges/text
   - Ranking tables (headers, rows, medals)
   - Reward summary sections
   - Winner highlights/badges
   - Navigation buttons/links
5. **Take screenshots** of each UI state
6. **Document HTML structure** in markdown

**Deliverable**: `UI_STRUCTURE_DOCUMENTATION.md` with:
- Screenshots of all pages
- HTML snippets for critical elements
- Proposed `data-testid` attributes
- Navigation flow diagram

---

### Phase 2: Test All 18 Configurations Manually (3-4 hours)

**Objective**: Verify every tournament config displays correctly in UI

**Test Matrix**: 18 configurations × 4 validation points = 72 manual checks

#### Tournament IDs to Test

| Config | Tournament ID | Winner Count | Priority |
|--------|---------------|--------------|----------|
| **1-Round INDIVIDUAL_RANKING** | | | |
| T1 | 438 (new run: 466+) | 3 | HIGH |
| T2 | 439 (new run: 467+) | 5 | HIGH |
| T3 | 440 (new run: 468+) | 1 | CRITICAL (edge case) |
| T4 | 441 (new run: 469+) | 3 | MEDIUM |
| T5 | 442 (new run: 470+) | 3 | MEDIUM |
| **HEAD_TO_HEAD** | | | |
| T6 | 443 (new run: 471+) | N/A | LOW (already passed) |
| T7 | 444 (new run: 472+) | N/A | LOW (already passed) |
| **2-Round INDIVIDUAL_RANKING** | | | |
| T8 | 456 (new run: 473+) | 3 | HIGH |
| T10 | 457* (new run: 474+) | 2 | CRITICAL (edge case) |
| T12 | 458* (new run: 475+) | 5 | HIGH |
| T14 | 459* (new run: 476+) | 1 | CRITICAL (edge case) |
| T16 | 460* (new run: 477+) | 3 | MEDIUM |
| **3-Round INDIVIDUAL_RANKING** | | | |
| T9 | 461* (new run: 478+) | 3 | HIGH |
| T11 | 462* (new run: 479+) | 5 | HIGH |
| T13 | 463* (new run: 480+) | 1 | CRITICAL (edge case) |
| T15 | 464* (new run: 481+) | 2 | CRITICAL (edge case) |
| T17 | 465* (new run: 482+) | 3 | MEDIUM |
| **Group+Knockout** | | | |
| T18 | 455 (new run: 483+) | N/A | LOW (already passed) |

*Tournament IDs may vary based on current database state

#### Validation Checklist (For Each Tournament)

**✅ Step 9: Tournament Status**
- [ ] Navigate to tournament detail page
- [ ] Verify status badge shows "REWARDS_DISTRIBUTED"
- [ ] Check status color coding (green/success)
- [ ] Screenshot status display

**✅ Step 10: Rankings Display**
- [ ] Verify ranking table is visible
- [ ] Check medal icons for top 3 (🥇🥈🥉)
- [ ] Verify rank numbers (1-8)
- [ ] Check score/time/distance values with correct units
- [ ] Verify ranking order (ASC vs DESC)
- [ ] Screenshot rankings table

**✅ Step 11: Rewards Distribution**
- [ ] Verify reward summary section exists
- [ ] Check credit reward amounts
- [ ] Check XP reward amounts
- [ ] Check skill reward items (if applicable)
- [ ] Verify reward recipient count matches winner_count
- [ ] Screenshot reward summary

**✅ Step 12: Winner Count Handling**
- [ ] Verify exactly N winners highlighted (N = winner_count)
- [ ] Check winner badge/icon (🏆, gold border, background color)
- [ ] Verify non-winners are clearly distinguished
- [ ] Compare 1-winner vs 5-winner display
- [ ] Screenshot winner highlights

---

### Phase 3: Recording Interface Validation (2-3 hours)

**Objective**: Verify both recording interfaces work for all 18 configs

#### Interface 1: Game Result Entry

**File**: `streamlit_app/components/tournaments/game_result_entry.py`

**Test Scenarios**:
1. **Single-round INDIVIDUAL_RANKING** (T1-T5)
   - [ ] Form displays correctly
   - [ ] All 8 participants listed
   - [ ] Score input field works (0-100)
   - [ ] Rank input field works (1-8)
   - [ ] Notes field optional
   - [ ] Submit button functional
   - [ ] Success message appears
   - [ ] Results saved correctly

2. **HEAD_TO_HEAD** (T6, T7, T18)
   - [ ] Form displays for match results
   - [ ] Win/loss/draw input works
   - [ ] Score input works
   - [ ] Submit saves correctly

#### Interface 2: Match Command Center

**File**: `streamlit_app/components/tournaments/instructor/match_command_center_screens.py`

**Test Scenarios**:
1. **Attendance Marking**
   - [ ] Participant list shows all 8 players
   - [ ] "Present" button works
   - [ ] "Absent" button works
   - [ ] Status updates correctly

2. **Round-by-Round Entry (Multi-Round)**
   - [ ] T8-T17: 2-round and 3-round configs
   - [ ] Progress indicator shows current round
   - [ ] Round 1 result entry works
   - [ ] Submit round 1, progress updates
   - [ ] Round 2 result entry works
   - [ ] Submit round 2, progress updates
   - [ ] (If 3 rounds) Round 3 entry works
   - [ ] All rounds completed message

3. **Finalization Button**
   - [ ] INDIVIDUAL_RANKING: Button appears after all rounds
   - [ ] HEAD_TO_HEAD: Button does NOT appear
   - [ ] Finalize button functional
   - [ ] Rankings calculated correctly

4. **Scoring Type Rendering**
   - [ ] **ROUNDS_BASED**: Round number input
   - [ ] **TIME_BASED**: Time input (seconds)
   - [ ] **SCORE_BASED**: Score input (points)
   - [ ] **DISTANCE_BASED**: Distance input (meters)
   - [ ] **PLACEMENT**: Rank input only (no score)
   - [ ] Correct units displayed
   - [ ] Validation works (no negative values)

---

### Phase 4: Winner Count Variation Testing (1-2 hours)

**Objective**: Verify UI correctly handles 1, 2, 3, 5 winners

**Critical Test Cases**:

| Winner Count | Config IDs | Test Scenarios |
|--------------|-----------|----------------|
| **1 Winner** | T3, T13, T14 | - Only 1st place highlighted<br>- Single winner badge<br>- Other 7 players normal styling<br>- Reward summary shows 1 recipient |
| **2 Winners** | T10, T15 | - 1st and 2nd place highlighted<br>- Two winner badges<br>- Other 6 players normal styling<br>- Reward summary shows 2 recipients |
| **3 Winners** | T1, T4, T5, T8, T9, T16, T17 | - Top 3 highlighted (🥇🥈🥉)<br>- Three winner badges<br>- Other 5 players normal styling<br>- Reward summary shows 3 recipients |
| **5 Winners** | T2, T11, T12 | - Top 5 highlighted<br>- Five winner badges<br>- Other 3 players normal styling<br>- Reward summary shows 5 recipients |

**UI Elements to Check**:
1. **Winner Highlights**: Background color, border, or icon
2. **Non-Winner Styling**: Clear visual distinction
3. **Reward Summary**: Correct recipient count
4. **Ranking Table**: Winner indicator column/icon

---

### Phase 5: Add data-testid Attributes (1-2 hours)

**Objective**: Make UI automation-friendly for future test runs

**Files to Modify** (Streamlit components):

1. **Tournament Detail Page** (`streamlit_app/pages/Tournament_Detail.py` or equivalent)
   ```python
   # Add data-testid to status badge
   st.markdown(f'<div data-testid="tournament-status">{tournament_status}</div>', unsafe_allow_html=True)

   # Add data-testid to ranking table
   st.dataframe(rankings_df, key="rankings-table", use_container_width=True)
   # Wrapper with data-testid:
   st.markdown('<div data-testid="rankings-section">', unsafe_allow_html=True)
   st.dataframe(rankings_df)
   st.markdown('</div>', unsafe_allow_html=True)
   ```

2. **Reward Summary Section**
   ```python
   st.markdown('<div data-testid="reward-summary">', unsafe_allow_html=True)
   st.write(f"Total Winners: {winner_count}")
   st.write(f"Credit Rewards: {total_credits}")
   st.write(f"XP Rewards: {total_xp}")
   st.markdown('</div>', unsafe_allow_html=True)
   ```

3. **Winner Highlights**
   ```python
   # For each player in ranking
   if rank <= winner_count:
       st.markdown(f'<div data-testid="winner-{user_id}" class="winner-highlight">...'
                   , unsafe_allow_html=True)
   else:
       st.markdown(f'<div data-testid="player-{user_id}">...', unsafe_allow_html=True)
   ```

4. **Game Result Entry Form**
   ```python
   with st.form(key="result-entry-form", data-testid="game-result-entry"):
       # Form fields
       submit = st.form_submit_button("Submit Results", data-testid="submit-results-btn")
   ```

5. **Match Command Center**
   ```python
   st.markdown('<div data-testid="match-command-center">', unsafe_allow_html=True)

   # Attendance section
   st.markdown('<div data-testid="attendance-section">', unsafe_allow_html=True)
   # Attendance buttons
   st.markdown('</div>', unsafe_allow_html=True)

   # Round entry section
   st.markdown(f'<div data-testid="round-{current_round}-entry">', unsafe_allow_html=True)
   # Round input fields
   st.markdown('</div>', unsafe_allow_html=True)

   # Finalize button (conditional)
   if supports_finalization and all_rounds_complete:
       st.button("Finalize Session", key="finalize-btn", data-testid="finalize-session-btn")
   ```

**Proposed data-testid Convention**:
- Tournament status: `tournament-status`
- Ranking section: `rankings-section`
- Ranking table: `rankings-table`
- Reward summary: `reward-summary`
- Winner highlight: `winner-{user_id}`
- Player row: `player-{user_id}`
- Result entry form: `game-result-entry`
- Submit button: `submit-results-btn`
- Command center: `match-command-center`
- Attendance section: `attendance-section`
- Round entry: `round-{N}-entry`
- Finalize button: `finalize-session-btn`

---

## Updated Playwright Test (After UI Discovery)

Once Phase 1 is complete, update the Playwright test with correct selectors:

```python
def verify_tournament_status_in_ui(page: Page, tournament_id: int, expected_status: str):
    """Verify tournament status using data-testid"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    # Use data-testid instead of text selector
    status_element = page.locator('[data-testid="tournament-status"]')
    expect(status_element).to_contain_text(expected_status)


def verify_rankings_displayed(page: Page, tournament_id: int, config: dict):
    """Verify rankings using data-testid"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    if config["format"] == "INDIVIDUAL_RANKING":
        # Check rankings section exists
        rankings_section = page.locator('[data-testid="rankings-section"]')
        expect(rankings_section).to_be_visible()

        # Check top 3 ranks
        for rank in [1, 2, 3]:
            rank_element = page.locator(f'[data-testid="rank-{rank}"]')
            expect(rank_element).to_be_visible()


def verify_winner_count_handling(page: Page, tournament_id: int, winner_count: int):
    """Verify winner count using data-testid"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    # Check exactly winner_count winners are highlighted
    for i in range(1, winner_count + 1):
        winner_element = page.locator(f'[data-testid^="winner-"]').nth(i - 1)
        expect(winner_element).to_be_visible()

    # Verify reward summary shows correct count
    reward_summary = page.locator('[data-testid="reward-summary"]')
    expect(reward_summary).to_contain_text(f"Winners: {winner_count}")
```

---

## Priority Order

### 🔴 CRITICAL (Do First)
1. **Phase 1: UI Structure Discovery** (1-2 hours)
   - Required for all other phases
   - Blocking: Cannot write tests without knowing UI

2. **Phase 4: Winner Count Variation Testing** (1-2 hours)
   - Explicitly requested by user
   - Critical edge cases: 1 winner, 2 winners

### 🟠 HIGH (Do Next)
3. **Phase 2: Manual Validation of Priority Configs** (1-2 hours)
   - Test CRITICAL and HIGH priority configs first
   - Focus on: T3, T10, T14, T15 (1-2 winner edge cases)
   - Multi-round configs: T8, T9, T11, T12

4. **Phase 3: Recording Interface Validation** (2-3 hours)
   - User explicitly mentioned "többféle rögzítő felület"
   - Multi-round interface critical for T8-T17

### 🟡 MEDIUM (Do After)
5. **Phase 5: Add data-testid Attributes** (1-2 hours)
   - Enables future automation
   - Not blocking for manual validation

6. **Phase 2: Complete Manual Validation** (1-2 hours)
   - Test remaining MEDIUM/LOW priority configs
   - HEAD_TO_HEAD configs (already passing)

---

## Estimated Time

| Phase | Duration | Priority |
|-------|----------|----------|
| Phase 1: UI Discovery | 1-2 hours | CRITICAL |
| Phase 4: Winner Count Testing | 1-2 hours | CRITICAL |
| Phase 2: Manual Validation (Priority) | 1-2 hours | HIGH |
| Phase 3: Recording Interfaces | 2-3 hours | HIGH |
| Phase 5: data-testid Attributes | 1-2 hours | MEDIUM |
| Phase 2: Complete Validation | 1-2 hours | MEDIUM |
| **TOTAL** | **8-13 hours** | |

---

## Success Criteria

### Minimum Viable (MVP)
- [ ] UI structure documented
- [ ] All 4 winner count variations (1, 2, 3, 5) validated manually
- [ ] Both recording interfaces tested for at least 5 configs each
- [ ] Screenshots collected for all critical UI states

### Complete (Full Coverage)
- [ ] All 18 configs validated manually (72 checks)
- [ ] Both recording interfaces tested for all 18 configs
- [ ] data-testid attributes added to all critical elements
- [ ] Playwright test updated with correct selectors
- [ ] Re-run Playwright tests: Steps 9-12 all PASS

### Ideal (Production-Ready)
- [ ] Automated Playwright tests: 18/18 PASSED (Steps 1-12)
- [ ] No manual validation required
- [ ] Screenshot regression tests in place
- [ ] Performance benchmarks documented

---

## Deliverables

1. **UI_STRUCTURE_DOCUMENTATION.md** - UI element documentation with screenshots
2. **MANUAL_VALIDATION_RESULTS.md** - Results of all 72 manual checks
3. **RECORDING_INTERFACE_TEST_REPORT.md** - Both interfaces tested
4. **WINNER_COUNT_VALIDATION_REPORT.md** - 1, 2, 3, 5 winner scenarios
5. **Updated Playwright test** - With correct selectors using data-testid
6. **Frontend code changes** - data-testid attributes added

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Streamlit UI different than expected** | High | Phase 1 discovery will reveal actual structure |
| **data-testid not supported in Streamlit** | Medium | Use stable CSS selectors or IDs as fallback |
| **Recording interfaces not accessible** | High | Check user permissions, navigation flow |
| **Winner highlights not visually distinct** | Medium | Document current state, recommend UI improvements |
| **Multi-round UI buggy** | High | File bugs, provide detailed reproduction steps |

---

**Document Created**: 2026-02-02
**Status**: ⚠️ INCOMPLETE - Manual validation required
**Next Action**: Begin Phase 1 (UI Structure Discovery)
**Owner**: User (manual validation) + Claude Code (automation improvements)
