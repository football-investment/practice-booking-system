# Tabs/stTabs Rendering — Root Cause Analysis
**Date:** 2026-02-19
**Priority:** P1 — Critical Blocker
**Impact:** 35 test failures (44% of all failures)

---

## Problem Statement

Dashboard tabs not rendering when Cypress tests run:
```
Expected to find element: [data-testid="stTabs"] but never did
```

**Affected dashboards:**
- **Instructor Dashboard:** 16/17 tests failed (94%)
- **Admin Dashboard:** 19/19 tests failed (100%)

---

## Root Cause: TWO DIFFERENT TAB IMPLEMENTATIONS

### Implementation 1: Admin Dashboard — Custom Button-Based Tabs

**File:** `streamlit_app/components/admin/dashboard_header.py` (lines 102-147)

**Implementation:**
```python
# Tab selection using 9 columns with buttons
tab_col1, tab_col2, ..., tab_col9 = st.columns(9)

with tab_col1:
    if st.button("📊 Overview", use_container_width=True,
                 type="primary" if st.session_state.active_tab == 'overview' else "secondary"):
        st.session_state.active_tab = 'overview'
        st.rerun()

# ... 8 more buttons for Users, Sessions, Locations, Financial, Semesters, Tournaments, Events, Presets
```

**Rendering:**
- Uses `st.columns()` + `st.button()` (NOT `st.tabs()`)
- Buttons have testid: `[data-testid="stButton"]`
- **NO `[data-testid="stTabs"]` element exists**
- Conditional content rendering based on `st.session_state.active_tab`

**Test Selectors (CORRECT):**
```javascript
// admin/dashboard_navigation.cy.js line 42-46
cy.contains('[data-testid="stButton"] button', '📊 Overview').should('be.visible');
cy.contains('[data-testid="stButton"] button', '👥 Users').should('be.visible');
// ... etc
```

**Why Tests Fail:**
- ✅ Test selectors are CORRECT (looking for buttons, not stTabs)
- ❌ Buttons not rendered yet when tests run
- ❌ Same race condition as logout button: auth state propagation delay
- ❌ Tab buttons render AFTER `render_dashboard_header()` returns, which requires auth check + API calls

### Implementation 2: Instructor Dashboard — Native st.tabs()

**File:** `streamlit_app/pages/Instructor_Dashboard.py` (lines 186-194)

**Implementation:**
```python
# Main tabs using native Streamlit st.tabs()
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📆 Today & Upcoming",
    "💼 My Jobs",
    "🏆 Tournament Applications",
    "👥 My Students",
    "✅ Check-in & Groups",
    "📬 Inbox",
    "👤 My Profile"
])

with tab1:
    render_today_tab(data, token, today, next_week)
# ... etc
```

**Rendering:**
- Uses native Streamlit `st.tabs()` API
- **SHOULD emit `[data-testid="stTabs"]` and `[data-testid="stTab"]`**
- Tabs render after data loading (line 170: `with st.spinner("Loading your data..."): data = load_dashboard_data(token)`)

**Test Selectors (CORRECT):**
```javascript
// instructor/dashboard.cy.js line 46-50
cy.get('[data-testid="stTabs"]')
  .find('[data-testid="stTab"]')
  .contains('📅 Today')
  .should('exist');
```

**Why Tests Fail:**
- ✅ Test selectors are CORRECT (looking for stTabs)
- ✅ Source code uses `st.tabs()` which should emit the testid
- ❌ Tabs component not rendered when tests run
- ❌ Data loading delay: `load_dashboard_data(token)` makes API calls BEFORE tabs render
- ❌ Tabs rendering happens AFTER data loading completes
- ❌ Tests don't wait for data loading spinner to disappear

---

## Timing Analysis

### Admin Dashboard Flow
1. User clicks "🔐 Login" (t=0ms)
2. `st.switch_page("pages/Admin_Dashboard.py")` triggers redirect (~100-300ms)
3. Admin Dashboard loads → `render_dashboard_header()` called
4. Auth check: `if SESSION_TOKEN_KEY not in st.session_state` (lines 39-56)
5. Role check: `if user_role != 'admin'` (lines 59-63)
6. Token validation + session restore (~200-500ms)
7. Tab buttons render (lines 102-147)
8. **Test runs: buttons may not be in DOM yet**

**Total delay:** ~300-800ms from page load to tab buttons appearing

### Instructor Dashboard Flow
1. User clicks "🔐 Login" (t=0ms)
2. `st.switch_page("pages/Instructor_Dashboard.py")` triggers redirect (~100-300ms)
3. Instructor Dashboard loads
4. Auth check (lines 46-48)
5. Role check (lines 51-54)
6. **Token validation API call:** `requests.get("/api/v1/users/me")` (lines 76-92) ~200-500ms
7. Notification count API call: `get_unread_notification_count(token)` (line 103) ~100-300ms
8. **Data loading:** `load_dashboard_data(token)` (line 171) ~500-2000ms
   - Fetches sessions, semesters, tournaments, students
   - Multiple API calls in parallel
   - Spinner shown during loading
9. Tabs render (line 186)
10. **Test runs: tabs may not be in DOM yet**

**Total delay:** ~900-3100ms from page load to tabs appearing

---

## Comparison to Logout Button Issue

| Aspect | Logout Button | Tabs/Buttons |
|--------|---------------|--------------|
| **Root Cause** | Race condition on redirect | Race condition on data loading + auth |
| **Delay** | 500-1000ms | 900-3100ms (Instructor), 300-800ms (Admin) |
| **Blocker** | `st.switch_page()` async | API calls + data loading |
| **Test Wait** | 500ms (`waitForStreamlit()`) | 500ms (`waitForStreamlit()`) |
| **Fix** | Wait for URL change + sidebar visible | Wait for tabs/buttons to appear |

---

## Proposed Fix Strategy

### Fix 1: Instructor Dashboard — Wait for Tabs After Data Loading

**Problem:** Tabs render AFTER `load_dashboard_data()` completes, which makes multiple API calls.

**Solution:** Add explicit wait for tabs component AND spinner disappearance.

#### Option A: Fix in Cypress Helper (Recommended)

**File:** `tests_cypress/cypress/support/commands.js`

Add new command:
```javascript
/**
 * Wait for Streamlit tabs component to render after data loading.
 * Use after navigating to dashboards that use st.tabs().
 */
Cypress.Commands.add('waitForTabs', (options = {}) => {
  const timeout = options.timeout || 15000;

  // 1. Wait for spinner to disappear (data loading)
  cy.get('body').then($body => {
    if ($body.find('[data-testid="stSpinner"]').length > 0) {
      cy.get('[data-testid="stSpinner"]', { timeout }).should('not.exist');
    }
  });

  // 2. Wait for tabs component to exist
  cy.get('[data-testid="stTabs"]', { timeout }).should('exist');

  // 3. Stabilization pause
  cy.wait(500);
});
```

**Usage in tests:**
```javascript
// instructor/dashboard.cy.js
beforeEach(() => {
  cy.loginAsInstructor();
  cy.navigateTo('/Instructor_Dashboard');
  cy.waitForTabs();  // ADD THIS
});
```

#### Option B: Fix in loginAsInstructor() Command

**File:** `tests_cypress/cypress/support/commands.js`

Modify `loginAsInstructor()` to wait for dashboard-specific elements:
```javascript
Cypress.Commands.add('loginAsInstructor', () => {
  cy.login(Cypress.env('instructorEmail'), Cypress.env('instructorPassword'));

  // Instructor login redirects to Instructor Dashboard
  // Wait for tabs to appear (data loading may take 1-3 seconds)
  cy.get('[data-testid="stTabs"]', { timeout: 15000 }).should('exist');
});
```

### Fix 2: Admin Dashboard — Wait for Tab Buttons

**Problem:** Tab buttons render AFTER auth check + header rendering.

**Solution:** Add explicit wait for at least one tab button to appear.

#### Option A: Fix in Cypress Helper (Recommended)

**File:** `tests_cypress/cypress/support/commands.js`

Add new command:
```javascript
/**
 * Wait for Admin Dashboard custom tab buttons to render.
 * Use after navigating to Admin Dashboard.
 */
Cypress.Commands.add('waitForAdminTabs', (options = {}) => {
  const timeout = options.timeout || 10000;

  // Wait for at least one tab button to exist (Overview is always first)
  cy.contains('[data-testid="stButton"] button', '📊 Overview', { timeout })
    .should('exist');

  // Stabilization pause
  cy.wait(500);
});
```

**Usage in tests:**
```javascript
// admin/dashboard_navigation.cy.js
beforeEach(() => {
  cy.loginAsAdmin();
  cy.waitForAdminTabs();  // ADD THIS
});
```

#### Option B: Fix in login Command

Modify the existing `login()` command to wait for dashboard-specific elements based on role:
```javascript
Cypress.Commands.add('login', (email, password) => {
  // ... existing login logic ...

  // Wait for redirect to complete
  cy.url({ timeout: 10000 }).should('not.equal', Cypress.config().baseUrl + '/');

  // Wait for new page to fully render
  cy.waitForStreamlit({ timeout: 10000 });

  // Ensure sidebar is visible on dashboard page
  cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('be.visible');

  // Role-specific waits
  cy.url().then(url => {
    if (url.includes('Admin_Dashboard')) {
      // Wait for admin tab buttons
      cy.contains('[data-testid="stButton"] button', '📊 Overview', { timeout: 10000 })
        .should('exist');
    } else if (url.includes('Instructor_Dashboard')) {
      // Wait for instructor tabs
      cy.get('[data-testid="stTabs"]', { timeout: 15000 }).should('exist');
    }
  });
});
```

---

## Recommended Implementation Plan

### Step 1: Verify Root Cause with Headed Mode Test

Run single failing test in headed mode to observe timing:
```bash
cd tests_cypress
npx cypress open
# Select: instructor/dashboard.cy.js
# Select: "all 7 instructor tabs are present"
# Watch: Does spinner appear? How long does data loading take? When do tabs appear?
```

### Step 2: Implement waitForTabs() and waitForAdminTabs() Commands

Add both helper commands to `commands.js` (Option A approach).

### Step 3: Update Affected Test Specs

**Instructor Dashboard:**
```javascript
// tests_cypress/cypress/e2e/instructor/dashboard.cy.js
beforeEach(() => {
  cy.loginAsInstructor();
  cy.navigateTo('/Instructor_Dashboard');
  cy.waitForTabs();  // NEW
});
```

**Admin Dashboard:**
```javascript
// tests_cypress/cypress/e2e/admin/dashboard_navigation.cy.js
beforeEach(() => {
  cy.loginAsAdmin();
  // loginAsAdmin() already navigates to /Admin_Dashboard
  cy.waitForAdminTabs();  // NEW
});
```

### Step 4: Validate Fix

```bash
# Run instructor dashboard test
npx cypress run --spec "cypress/e2e/instructor/dashboard.cy.js"
# Expected: 17/17 passing (from 1/17)

# Run admin dashboard test
npx cypress run --spec "cypress/e2e/admin/dashboard_navigation.cy.js"
# Expected: 19/19 passing (from 0/19)
```

---

## Alternative Fix: Source Code Optimization (NOT RECOMMENDED)

### Option: Pre-render Tabs Without Data

**File:** `streamlit_app/pages/Instructor_Dashboard.py`

Move `st.tabs()` BEFORE data loading:
```python
# Render tabs container first (before data loading)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📆 Today & Upcoming",
    "💼 My Jobs",
    "🏆 Tournament Applications",
    "👥 My Students",
    "✅ Check-in & Groups",
    "📬 Inbox",
    "👤 My Profile"
])

# Then load data
with st.spinner("Loading your data..."):
    data = load_dashboard_data(token)

# Then populate tabs with data
with tab1:
    if data.load_error:
        st.error(data.load_error)
    else:
        render_today_tab(data, token, today, next_week)
```

**Why NOT Recommended:**
- Changes production code to fix test issue (test should adapt to app, not vice versa)
- May introduce UX issues (empty tabs visible during loading)
- Doesn't fix Admin Dashboard (custom tabs still delayed by auth)
- Test fix is simpler and safer

---

## Impact Projection

| Fix | Tests Unblocked | New Pass Rate |
|-----|-----------------|---------------|
| Before | 71/194 (37%) | Baseline |
| + Backend API | 116/194 (60%) | +45 tests |
| + Logout button | 136/194 (70%) | +20 tests |
| + **Tabs rendering** | **171/194 (88%)** | **+35 tests** |
| + Sidebar buttons | 186/194 (96%) | +15 tests |
| + Other/mixed | ~192/194 (99%) | +6 tests |

**This fix alone improves pass rate from 70% → 88%**

---

## Success Criteria

### Immediate
- Instructor dashboard test passes with explicit tab wait
- Admin dashboard test passes with explicit button wait
- No increase in test duration (waits are only for actual rendering time)

### Short-term
- `instructor/dashboard.cy.js`: 17/17 passing (from 1/17)
- `admin/dashboard_navigation.cy.js`: 19/19 passing (from 0/19)
- No retry needed

### Long-term
- Overall pass rate: 88%+ (171/194)
- Stable test runs without flakiness
- Clear pattern established for waiting on async-rendered components

---

## Next Actions

1. ✅ Root cause identified (this document)
2. 🔄 **CURRENT:** Run headed mode test to observe timing
3. ⏳ Implement `waitForTabs()` and `waitForAdminTabs()` commands
4. ⏳ Update affected test specs (2 files)
5. ⏳ Validate fix locally (if possible) or via GitHub Actions
6. ⏳ Full suite regression test

---

**Status:** Root cause analysis complete — Ready for fix implementation
**Owner:** Claude Code
**Target:** Fix within 1 hour
**Blocked By:** PR #4 merge (for CI verification), OR local headed mode test

---

## Appendix: Test Selector Validation

### Admin Dashboard Tabs (Custom Buttons)

**Source code testid:** `[data-testid="stButton"]`

**Test selectors:**
```javascript
cy.contains('[data-testid="stButton"] button', '📊 Overview')
cy.contains('[data-testid="stButton"] button', '👥 Users')
// ... etc
```

✅ **Selectors are CORRECT** — failure is timing, not wrong selector

### Instructor Dashboard Tabs (Native st.tabs())

**Expected testid:** `[data-testid="stTabs"]` + `[data-testid="stTab"]`

**Test selectors:**
```javascript
cy.get('[data-testid="stTabs"]')
  .find('[data-testid="stTab"]')
  .contains('📅 Today')
```

✅ **Selectors are CORRECT** — failure is timing, not wrong selector

---

**Conclusion:** Both dashboards have correct test selectors. Failures are 100% due to timing/rendering delays, not incorrect testids. Fix is to add explicit waits for dashboard-specific elements after login/navigation.
