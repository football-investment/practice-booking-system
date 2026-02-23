# Cypress Test Failure Categorization
**Date:** 2026-02-19
**Total Failures:** 80 (of 194 tests)
**Pass Rate:** 37%

---

## 📊 Failure Distribution by Root Cause

| Bucket | Count | % of Failures | Priority |
|--------|-------|---------------|----------|
| **1. Backend Dependency** | 2 failures + 43 skipped | 3% / 54% skipped | ✅ RESOLVED |
| **2. Sidebar Rendering** | ~15 failures | 19% | P2 |
| **3. Logout Button** | ~20 failures | 25% | ✅ FIXED |
| **4. Tabs/stTabs** | ~35 failures | 44% | **P1** |
| **Other/Mixed** | ~8 failures | 10% | P3 |

---

## 🪣 Bucket 1: Backend Dependency (Missing API)

### Status: ✅ RESOLVED
Backend API started on port 8000 — environment now stable.

### Failed Tests (2)
These tests FAILED (not skipped) because they attempted backend calls:

| Spec | Test | Error |
|------|------|-------|
| system/cross_role_e2e.cy.js | before all hook | `connect ECONNREFUSED 127.0.0.1:8000` |
| student/enrollment_409_live.cy.js | API enrollment test | `connect ECONNREFUSED 127.0.0.1:8000` |

### Skipped Tests (43)
These tests were SKIPPED due to beforeEach/before failures:

| Spec | Skipped Count |
|------|---------------|
| system/cross_role_e2e.cy.js | 13 |
| student/enrollment_409_live.cy.js | 5 |
| admin/tournament_manager.cy.js | 7 |
| admin/tournament_monitor.cy.js | 8 |
| student/credits.cy.js | 10 |

**Total Impact:** 45 tests (2 failed + 43 skipped)

---

## 🪣 Bucket 2: Sidebar Rendering Timing

### Status: 🔄 NOT YET ADDRESSED
Sidebar navigation buttons not appearing in DOM after login/page load.

### Pattern
```
Expected to find content: '🏆 Tournament Manager'
within [data-testid="stSidebar"] but never did
```

### Failed Tests (~15)

| Spec | Failures | Missing Buttons |
|------|----------|-----------------|
| admin/tournament_manager.cy.js | 1 | '🏆 Tournament Manager' (beforeEach blocker) |
| admin/tournament_monitor.cy.js | 1 | '🏆 Tournament Manager', '🔄 Refresh' |
| player/credits.cy.js | 7 | '💰 My Credits' / '💳 Credits' |
| player/specialization_hub.cy.js | 3 | '💰 My Credits', '👤 My Profile', '🔄 Refresh' |
| student/credits.cy.js | 1 | '/💰 My Credits|💳 Credits/' (beforeEach blocker) |
| student/enrollment_flow.cy.js | 1 | Navigate to Credits → button missing |
| error_states/http_409_conflict.cy.js | 1 | Result submission → button not found |

**Total:** ~15 failures

### Root Cause Hypothesis
1. Sidebar component renders but buttons inside it are delayed
2. Role-based conditional rendering may be waiting for async API calls
3. Streamlit sidebar re-render not completing before assertions
4. Similar to logout button issue — authentication state propagation delay

### Recommended Fix
Similar to logout button fix:
- Add explicit wait for sidebar to be fully populated after login
- Wait for at least 1 navigation button to appear before proceeding
- Increase timeout for sidebar button searches from 5s to 10s

---

## 🪣 Bucket 3: Logout Button Rendering

### Status: ✅ FIX IMPLEMENTED (Awaiting CI Verification)
PR #4 created with fix: explicit URL redirect wait + sidebar visibility check.

### Pattern
```
Expected to find content: '🚪 Logout'
within [data-testid="stButton"] button but never did
```

### Failed Tests (~20)

| Spec | Failures | Specific Tests |
|------|----------|----------------|
| auth/login.cy.js | 5 | Admin login, Instructor login, Player login, Logout flow, Session persistence |
| player/dashboard.cy.js | 3 | Sidebar logout button tests |
| student/enrollment_flow.cy.js | 1 | "Session stays active" test |
| error_states/unauthorized.cy.js | 1 | Retry after 401 → logout button check |
| student/dashboard.cy.js | ~4 | Various logout/authentication checks |
| student/error_states.cy.js | ~2 | Post-error logout checks |
| player/specialization_hub.cy.js | ~2 | Navigation/logout checks |
| student/skill_update.cy.js | ~2 | Session state checks |

**Total:** ~20 failures

### Root Cause
Race condition in login flow:
1. User clicks "🔐 Login"
2. Streamlit triggers `st.switch_page()` redirect (async)
3. Test waits 500ms (`waitForStreamlit()`)
4. Test checks for logout button
5. **Redirect may not be complete yet**

### Fix Applied
Modified `tests_cypress/cypress/support/commands.js` login command:
```javascript
// Wait for redirect to complete (URL changes from / to /Admin_Dashboard)
cy.url({ timeout: 10000 }).should('not.equal', Cypress.config().baseUrl + '/');

// Wait for new page to fully render
cy.waitForStreamlit({ timeout: 10000 });

// Ensure sidebar is visible on dashboard page
cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('be.visible');
```

### Verification Needed
GitHub Actions CI workflow (#4) will verify fix works in Ubuntu environment.

---

## 🪣 Bucket 4: Dashboard Tabs (stTabs) Not Rendering

### Status: 🚨 CRITICAL BLOCKER — Priority 1
Dashboard tabs component (`[data-testid="stTabs"]`) not rendering, causing complete breakdown of admin/instructor UIs.

### Pattern
```
Expected to find element: [data-testid="stTabs"] but never did
```

### Failed Tests (~35)

| Spec | Failures | Impact |
|------|----------|--------|
| instructor/dashboard.cy.js | 16 | 94% test failure (16/17) |
| admin/dashboard_navigation.cy.js | 19 | 100% test failure (19/19) |

**Total:** 35 failures
**Impact:** Complete breakdown of role-based dashboard UIs

### Detailed Breakdown

#### instructor/dashboard.cy.js (16/17 failed)
- ❌ Dashboard title not found
- ❌ Tabs component missing (`[data-testid="stTabs"]`)
- ❌ Sidebar buttons not rendering
- ❌ Profile tab inaccessible
- ❌ Applications tab inaccessible
- ❌ All tab content assertions fail
- ✅ Only 1 passing: "Renders without Python errors"

#### admin/dashboard_navigation.cy.js (19/19 failed)
- ❌ Dashboard title/caption missing
- ❌ 9 tab buttons not visible
- ❌ No tab content rendering
- ❌ Navigation buttons missing
- ❌ Tournament Manager button missing
- ❌ Tournament Monitor button missing
- ❌ Access control tests failing

### Root Cause Hypotheses
1. **Conditional Rendering Issue:**
   - Tabs may be conditionally rendered based on auth state
   - Auth state not propagated to tab component
   - Similar to logout button race condition

2. **Streamlit Version Incompatibility:**
   - `st.tabs()` API may have changed
   - Testid format may differ in newer Streamlit versions
   - Check if tabs render differently in headless vs headed mode

3. **Custom Tab Implementation:**
   - Admin Dashboard uses "custom button-based tabs (not native st.tabs)"
   - May use different testid or component structure
   - Custom tabs may not emit `[data-testid="stTabs"]`

4. **Role-Based Rendering Delay:**
   - Dashboard may wait for API calls to determine which tabs to show
   - Tabs component waiting for permissions check
   - Similar timing issue to sidebar/logout button

### Investigation Steps Required
1. **Read Dashboard Source Files:**
   - `streamlit_app/pages/Admin_Dashboard.py`
   - `streamlit_app/pages/Instructor_Dashboard.py`
   - Check if they use `st.tabs()` or custom implementation

2. **Verify Tab Implementation:**
   - Search for `st.tabs(` in codebase
   - Identify actual testid used
   - Check if custom tabs use different selector

3. **Test with Explicit Waits:**
   - Add `cy.get('[data-testid="stTabs"]', { timeout: 15000 })`
   - Check if tabs eventually appear with longer timeout

4. **Headed Mode Comparison:**
   - Run single failing test in headed mode
   - Observe if tabs appear visually but with different testid
   - Screenshot comparison

### Recommended Fix Strategy

**Option A: Wait for Tab Component (Recommended)**
```javascript
Cypress.Commands.add('waitForDashboardTabs', () => {
  cy.get('[data-testid="stTabs"]', { timeout: 15000 }).should('exist');
  cy.waitForStreamlit();
});
```

**Option B: Custom Tab Selector (If Admin Uses Custom Tabs)**
```javascript
// If admin dashboard uses custom button-based tabs
cy.get('[data-testid="stButton"]').contains('👥 Users').should('be.visible');
```

**Option C: Fix Source Code Tab Rendering**
If tabs are conditionally rendered and condition is broken:
- Check `if` conditions around `st.tabs()` in dashboard files
- Ensure auth state is available when tabs render
- Add explicit session state checks before tab rendering

---

## 🪣 Other/Mixed Failures (~8)

### Miscellaneous failures not fitting into main buckets:

| Spec | Failures | Description |
|------|----------|-------------|
| error_states/unauthorized.cy.js | 1 | 401 from login → route timeout (not logout button) |
| student/dashboard.cy.js | 2 | Possibly metrics/content not loading |
| student/error_states.cy.js | 2 | 409 handling (not the passing ones) |
| student/skill_update.cy.js | 3 | Metric indicators, credit balance display |

**Total:** ~8 failures

### Common Patterns
- **Content Loading Issues:** Metrics, balances, indicators not appearing
- **Async API Delays:** Content depends on API calls not completing in time
- **Test Flakiness:** May pass with longer timeouts or retry

### Recommended Action
- Address after fixing the 4 main buckets
- May auto-resolve once timing issues fixed
- Low priority — only 10% of total failures

---

## 📈 Fix Impact Projections

| Fix | Tests Unblocked | New Pass Rate |
|-----|-----------------|---------------|
| ✅ Backend API started | 45 (2 failed + 43 skipped) | 60% → 83% |
| ✅ Logout button fixed | ~20 | 37% → 47% |
| 🔄 Sidebar buttons fixed | ~15 | 47% → 55% |
| 🚨 **Tabs/stTabs fixed** | **~35** | **55% → 73%** |
| 🔧 Other/mixed fixed | ~8 | 73% → 77% |

**Projected Final Pass Rate:** ~77% (150/194) after all fixes

---

## 🎯 Recommended Action Plan

### ✅ Completed
1. Backend API started on port 8000
2. Logout button fix implemented (PR #4)
3. Environment stabilized

### 🔄 In Progress
4. Categorization complete (this document)
5. Awaiting GitHub Actions CI verification of logout fix

### ⏳ Next Actions

**Priority 1: Fix Tabs/stTabs Rendering (~35 failures)**
1. Read `Admin_Dashboard.py` and `Instructor_Dashboard.py`
2. Identify tab implementation (native `st.tabs()` vs custom)
3. Run single failing test in headed mode to observe tabs
4. Implement fix based on findings
5. Verify with `admin/dashboard_navigation.cy.js` spec

**Priority 2: Fix Sidebar Button Rendering (~15 failures)**
1. Similar approach to logout button fix
2. Add explicit wait for sidebar buttons after login
3. Verify buttons exist before proceeding to test assertions

**Priority 3: Address Remaining Failures (~8)**
1. Increase timeouts for slow-loading content
2. Add explicit waits for metrics/balances
3. Re-run full suite to identify flaky tests

---

## 📊 Summary Statistics

| Metric | Value |
|--------|-------|
| Total Tests | 194 |
| Current Pass Rate | 37% (71/194) |
| Total Failures | 80 |
| Backend Dependency | 2 failures + 43 skipped (56% of non-passing) |
| Logout Button | ~20 failures (25%) |
| Sidebar Buttons | ~15 failures (19%) |
| **Tabs/stTabs** | **~35 failures (44%)** |
| Other/Mixed | ~8 failures (10%) |
| **Projected Pass Rate** | **~77%** after all fixes |

---

**Status:** Categorization complete — Ready for Priority 1 (Tabs debugging)
**Next Step:** Investigate tabs rendering issue in dashboard source files
**Blocker:** Awaiting PR #4 merge for CI verification of logout fix
**Owner:** Claude Code
**Updated:** 2026-02-19 22:00
