# UI Testing Contract - Streamlit Frontend
## 2026-02-02

---

## Philosophy

**Contract-First Testing**: UI elements must have **stable, semantic test identifiers** that represent backend state, not visual appearance.

**Principles**:
- ❌ NO text-based selectors (`text=REWARDS_DISTRIBUTED`)
- ❌ NO CSS class-based selectors (`.status-badge`)
- ❌ NO visual assumptions (color, position)
- ✅ YES `data-testid` attributes
- ✅ YES semantic identifiers (`tournament-status`, not `badge-123`)
- ✅ YES deterministic DOM truth

---

## Required UI Elements for E2E Testing

### Step 9: Tournament Status Display

**Purpose**: Verify backend `tournament_status` field is correctly displayed

**DOM Truth**:
```html
<div data-testid="tournament-status" data-status="REWARDS_DISTRIBUTED">
  <!-- Visual content (badge, icon, text) can vary -->
  <!-- Test reads data-status attribute, not visual content -->
</div>
```

**Contract**:
- **Attribute**: `data-testid="tournament-status"`
- **State Attribute**: `data-status="{tournament_status}"` (enum value from backend)
- **Valid Values**: `DRAFT`, `REGISTRATION_OPEN`, `IN_PROGRESS`, `COMPLETED`, `REWARDS_DISTRIBUTED`, `CANCELLED`
- **Location**: Tournament detail page/section
- **Requirement**: MUST exist when tournament data is loaded

**Playwright Selector**:
```python
status_element = page.locator('[data-testid="tournament-status"]')
status_value = status_element.get_attribute('data-status')
assert status_value == "REWARDS_DISTRIBUTED"
```

---

### Step 10: Rankings Display

**Purpose**: Verify tournament rankings table is displayed with correct data

**DOM Truth**:
```html
<div data-testid="tournament-rankings">
  <table data-testid="rankings-table">
    <tbody>
      <tr data-testid="ranking-row" data-user-id="4" data-rank="1" data-is-winner="true">
        <td data-testid="rank">1</td>
        <td data-testid="player-name">Junior Intern</td>
        <td data-testid="final-score">100.0</td>
      </tr>
      <tr data-testid="ranking-row" data-user-id="5" data-rank="2" data-is-winner="false">
        <!-- ... -->
      </tr>
    </tbody>
  </table>
</div>
```

**Contract**:
- **Container**: `data-testid="tournament-rankings"`
- **Table**: `data-testid="rankings-table"`
- **Row**: `data-testid="ranking-row"`
  - `data-user-id="{user_id}"` - Backend user ID
  - `data-rank="{rank}"` - Final rank (1, 2, 3, ...)
  - `data-is-winner="{true|false}"` - Boolean, derived from `winner_count`
- **Cells**: `data-testid="rank"`, `data-testid="player-name"`, `data-testid="final-score"`
- **Location**: Tournament detail page, visible after COMPLETED status
- **Requirement**: MUST exist when tournament has rankings

**Playwright Selector**:
```python
rankings_container = page.locator('[data-testid="tournament-rankings"]')
expect(rankings_container).to_be_visible()

# Verify 8 players
rows = page.locator('[data-testid="ranking-row"]')
expect(rows).to_have_count(8)

# Verify winners based on winner_count
winners = page.locator('[data-testid="ranking-row"][data-is-winner="true"]')
expect(winners).to_have_count(expected_winner_count)
```

---

### Step 11: Rewards Distribution Summary

**Purpose**: Verify rewards were distributed and summary is displayed

**DOM Truth**:
```html
<div data-testid="rewards-summary">
  <div data-testid="total-credits" data-value="8000">
    Total Credits: 8000
  </div>
  <div data-testid="total-xp" data-value="4000">
    Total XP: 4000
  </div>
  <div data-testid="players-rewarded" data-value="8">
    Players Rewarded: 8
  </div>
  <div data-testid="skill-rewards-count" data-value="3">
    Skill Rewards: 3
  </div>
</div>
```

**Contract**:
- **Container**: `data-testid="rewards-summary"`
- **Total Credits**: `data-testid="total-credits"`, `data-value="{amount}"`
- **Total XP**: `data-testid="total-xp"`, `data-value="{amount}"`
- **Players Rewarded**: `data-testid="players-rewarded"`, `data-value="{count}"`
- **Skill Rewards**: `data-testid="skill-rewards-count"`, `data-value="{count}"`
- **Location**: Tournament detail page, visible after REWARDS_DISTRIBUTED status
- **Requirement**: MUST exist when rewards have been distributed

**Playwright Selector**:
```python
rewards_summary = page.locator('[data-testid="rewards-summary"]')
expect(rewards_summary).to_be_visible()

total_credits = page.locator('[data-testid="total-credits"]').get_attribute('data-value')
assert int(total_credits) > 0

players_rewarded = page.locator('[data-testid="players-rewarded"]').get_attribute('data-value')
assert int(players_rewarded) == 8
```

---

### Step 12: Winner Count Handling

**Purpose**: Verify correct number of winners are visually distinguished based on `winner_count`

**DOM Truth**:
```html
<!-- Each ranking row has data-is-winner attribute -->
<tr data-testid="ranking-row" data-user-id="4" data-rank="1" data-is-winner="true">
  <td data-testid="rank">
    <span data-testid="winner-badge">🏆</span> 1
  </td>
  <!-- ... -->
</tr>
<tr data-testid="ranking-row" data-user-id="5" data-rank="2" data-is-winner="true">
  <!-- Winner badge present if rank <= winner_count -->
</tr>
<tr data-testid="ranking-row" data-user-id="6" data-rank="3" data-is-winner="false">
  <!-- No winner badge if rank > winner_count -->
</tr>
```

**Contract**:
- **Winner Indicator**: `data-is-winner="true"` on ranking row
- **Winner Badge**: `data-testid="winner-badge"` (optional visual element)
- **Logic**: `rank <= tournament.winner_count` → `data-is-winner="true"`
- **Location**: Within ranking rows
- **Requirement**: MUST correctly reflect backend `winner_count` configuration

**Test Scenarios**:
| Config | Winner Count | Expected Behavior |
|--------|--------------|-------------------|
| T3, T13 | 1 | Only rank 1 has `data-is-winner="true"` |
| T10, T14 | 2 | Ranks 1-2 have `data-is-winner="true"` |
| T1, T4, T5, T8, T9, T15, T16, T17 | 3 | Ranks 1-3 have `data-is-winner="true"` |
| T2, T11, T12 | 5 | Ranks 1-5 have `data-is-winner="true"` |

**Playwright Selector**:
```python
# Count winners
winners = page.locator('[data-testid="ranking-row"][data-is-winner="true"]')
expect(winners).to_have_count(expected_winner_count)

# Verify non-winners
non_winners = page.locator('[data-testid="ranking-row"][data-is-winner="false"]')
expect(non_winners).to_have_count(8 - expected_winner_count)

# Verify specific ranks
for rank in range(1, expected_winner_count + 1):
    winner_row = page.locator(f'[data-testid="ranking-row"][data-rank="{rank}"]')
    is_winner = winner_row.get_attribute('data-is-winner')
    assert is_winner == "true", f"Rank {rank} should be winner"
```

---

## Implementation Plan

### Phase 1: Add `data-testid` Attributes to Streamlit Components

**Files to Modify**:
1. **Tournament Detail Page Component** (primary)
   - Location: Likely in `streamlit_sandbox_v3_admin_aligned.py` or separate component file
   - Elements: Status badge, rankings table, rewards summary

**Code Changes Required**:

#### 1. Tournament Status
```python
# BEFORE (hypothetical)
st.write(f"Status: {tournament.tournament_status}")

# AFTER
status_html = f'''
<div data-testid="tournament-status" data-status="{tournament.tournament_status}">
    Status: {tournament.tournament_status}
</div>
'''
st.markdown(status_html, unsafe_allow_html=True)
```

#### 2. Rankings Table
```python
# BEFORE (hypothetical)
st.dataframe(rankings_df)

# AFTER - Use st.html or custom HTML rendering
rankings_html = '<div data-testid="tournament-rankings">'
rankings_html += '<table data-testid="rankings-table"><tbody>'

for idx, row in rankings_df.iterrows():
    is_winner = "true" if row['rank'] <= winner_count else "false"
    rankings_html += f'''
    <tr data-testid="ranking-row"
        data-user-id="{row['user_id']}"
        data-rank="{row['rank']}"
        data-is-winner="{is_winner}">
        <td data-testid="rank">
            {f'<span data-testid="winner-badge">🏆</span> ' if is_winner == "true" else ''}
            {row['rank']}
        </td>
        <td data-testid="player-name">{row['name']}</td>
        <td data-testid="final-score">{row['final_score']}</td>
    </tr>
    '''

rankings_html += '</tbody></table></div>'
st.markdown(rankings_html, unsafe_allow_html=True)
```

#### 3. Rewards Summary
```python
# BEFORE (hypothetical)
st.metric("Total Credits", total_credits)
st.metric("Total XP", total_xp)

# AFTER
rewards_html = f'''
<div data-testid="rewards-summary">
    <div data-testid="total-credits" data-value="{total_credits}">
        Total Credits: {total_credits}
    </div>
    <div data-testid="total-xp" data-value="{total_xp}">
        Total XP: {total_xp}
    </div>
    <div data-testid="players-rewarded" data-value="{players_rewarded}">
        Players Rewarded: {players_rewarded}
    </div>
    <div data-testid="skill-rewards-count" data-value="{skill_rewards_count}">
        Skill Rewards: {skill_rewards_count}
    </div>
</div>
'''
st.markdown(rewards_html, unsafe_allow_html=True)
```

### Phase 2: Update Playwright Test Functions

**File**: `tests/e2e_frontend/test_tournament_playwright.py`

#### Updated Step 9: Status Verification
```python
def verify_tournament_status_in_ui(page: Page, tournament_id: int, expected_status: str):
    """Verify tournament status is displayed correctly in Streamlit UI"""
    page.goto(f"{STREAMLIT_URL}?tournament_id={tournament_id}")
    wait_for_streamlit_load(page)

    # Contract-based validation
    status_element = page.locator('[data-testid="tournament-status"]')
    page.wait_for_selector('[data-testid="tournament-status"]', timeout=10000)

    status_value = status_element.get_attribute('data-status')
    assert status_value == expected_status, f"Expected {expected_status}, got {status_value}"
```

#### Updated Step 10: Rankings Verification
```python
def verify_rankings_displayed(page: Page, tournament_id: int, config: dict):
    """Verify rankings are displayed correctly"""
    # Wait for rankings container
    rankings_container = page.locator('[data-testid="tournament-rankings"]')
    page.wait_for_selector('[data-testid="tournament-rankings"]', timeout=10000)
    expect(rankings_container).to_be_visible()

    # Verify table exists
    table = page.locator('[data-testid="rankings-table"]')
    expect(table).to_be_visible()

    # Verify 8 players
    rows = page.locator('[data-testid="ranking-row"]')
    expect(rows).to_have_count(8)
```

#### Updated Step 11: Rewards Verification
```python
def verify_rewards_distributed(page: Page, tournament_id: int, config: dict):
    """Verify rewards distribution summary is displayed"""
    # Wait for rewards summary
    rewards_summary = page.locator('[data-testid="rewards-summary"]')
    page.wait_for_selector('[data-testid="rewards-summary"]', timeout=10000)
    expect(rewards_summary).to_be_visible()

    # Verify credits distributed
    total_credits = page.locator('[data-testid="total-credits"]')
    expect(total_credits).to_be_visible()
    credits_value = total_credits.get_attribute('data-value')
    assert int(credits_value) > 0, "No credits distributed"

    # Verify players rewarded
    players_rewarded = page.locator('[data-testid="players-rewarded"]')
    players_count = players_rewarded.get_attribute('data-value')
    assert int(players_count) == 8, f"Expected 8 players rewarded, got {players_count}"
```

#### Updated Step 12: Winner Count Verification
```python
def verify_winner_count_handling(page: Page, tournament_id: int, expected_winner_count: int):
    """Verify correct number of winners are marked"""
    # Count winners via data-is-winner attribute
    winners = page.locator('[data-testid="ranking-row"][data-is-winner="true"]')
    expect(winners).to_have_count(expected_winner_count)

    # Count non-winners
    non_winners = page.locator('[data-testid="ranking-row"][data-is-winner="false"]')
    expect(non_winners).to_have_count(8 - expected_winner_count)

    # Verify specific ranks are winners
    for rank in range(1, expected_winner_count + 1):
        winner_row = page.locator(f'[data-testid="ranking-row"][data-rank="{rank}"]')
        is_winner = winner_row.get_attribute('data-is-winner')
        assert is_winner == "true", f"Rank {rank} should be marked as winner"

    # Verify ranks beyond winner_count are NOT winners
    for rank in range(expected_winner_count + 1, 9):
        non_winner_row = page.locator(f'[data-testid="ranking-row"][data-rank="{rank}"]')
        is_winner = non_winner_row.get_attribute('data-is-winner')
        assert is_winner == "false", f"Rank {rank} should NOT be marked as winner"
```

### Phase 3: Verify Streamlit App Running

**Before running tests**, ensure Streamlit is running:

```bash
# Terminal 1: Backend
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8501
```

### Phase 4: Re-run STRICT Mode Tests

**After implementing data-testid attributes:**

```bash
pytest tests/e2e_frontend/test_tournament_playwright.py::test_tournament_complete_workflow_with_ui_validation -v --tb=short
```

**Expected Result**: 18/18 PASSED in headless mode

---

## Validation Criteria

### Contract Compliance

For each test configuration:
- ✅ `data-testid="tournament-status"` exists
- ✅ `data-status` attribute matches backend `tournament_status`
- ✅ `data-testid="tournament-rankings"` exists
- ✅ 8 `data-testid="ranking-row"` elements present
- ✅ `data-is-winner` correctly reflects `rank <= winner_count`
- ✅ `data-testid="rewards-summary"` exists
- ✅ Reward counts match backend distribution

### Deterministic Truth

**Not Acceptable**:
- ❌ "Status badge is green"
- ❌ "Text contains 'Rewards Distributed'"
- ❌ "Winner has gold border"

**Acceptable**:
- ✅ `data-status="REWARDS_DISTRIBUTED"`
- ✅ `data-is-winner="true"` for ranks 1-3
- ✅ `data-value="8000"` for total credits

---

## Next Steps

### Step 1: Identify Streamlit Component Files
- [ ] Find where tournament detail page is rendered
- [ ] Locate status display code
- [ ] Locate rankings table rendering
- [ ] Locate rewards summary rendering

### Step 2: Implement `data-testid` Attributes
- [ ] Add `data-testid` to status element
- [ ] Add `data-testid` to rankings table and rows
- [ ] Add `data-testid` to rewards summary
- [ ] Add `data-is-winner` logic based on `winner_count`

### Step 3: Update Playwright Tests
- [ ] Update `verify_tournament_status_in_ui` to use `[data-testid="tournament-status"]`
- [ ] Update `verify_rankings_displayed` to use `[data-testid="tournament-rankings"]`
- [ ] Update `verify_rewards_distributed` to use `[data-testid="rewards-summary"]`
- [ ] Update `verify_winner_count_handling` to use `[data-is-winner]`

### Step 4: Test Locally
- [ ] Start Streamlit app
- [ ] Manually verify `data-testid` attributes in browser DevTools
- [ ] Run single test config to validate selectors work

### Step 5: Full STRICT Mode Run
- [ ] Run all 18 tests in headless mode
- [ ] Goal: 18/18 PASSED
- [ ] Document results

### Step 6: ONLY AFTER 100% PASS
- [ ] Manual/headed validation
- [ ] Screenshot winner count variations
- [ ] Visual verification

---

## Benefits of Contract-First Approach

1. **Deterministic**: Test reads data attributes, not visual/text assumptions
2. **Maintainable**: UI styling can change without breaking tests
3. **Semantic**: `data-testid` names describe purpose, not implementation
4. **Backend Truth**: Data attributes directly reflect backend state
5. **Stable**: No brittle text matching or CSS class dependencies

---

## Anti-Patterns to Avoid

❌ **Text Matching**:
```python
page.wait_for_selector("text=REWARDS_DISTRIBUTED")  # WRONG
```

❌ **CSS Classes**:
```python
page.locator(".status-badge.success")  # WRONG - styling can change
```

❌ **Visual Checks**:
```python
expect(element).to_have_css("background-color", "green")  # WRONG
```

✅ **Contract-Based**:
```python
status = page.locator('[data-testid="tournament-status"]').get_attribute('data-status')
assert status == "REWARDS_DISTRIBUTED"  # RIGHT
```

---

**Document**: UI Testing Contract
**Date**: 2026-02-02
**Status**: ✅ DEFINED - Ready for Implementation
**Next**: Implement `data-testid` attributes in Streamlit components
**Philosophy**: Contract-First, Deterministic, Backend Truth
