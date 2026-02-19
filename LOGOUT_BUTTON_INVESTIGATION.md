# Logout Button Rendering Investigation
**Date:** 2026-02-19
**Priority:** P1 — Critical Blocker
**Impact:** ~20 test failures

---

## Problem Statement

Tests fail with:
```
Expected to find content: '🚪 Logout'
within [data-testid="stButton"] button but never did
```

**Affected tests:** ~20 across auth, player, student suites

---

## Current Implementation Analysis

### Login Flow Architecture

1. **Home.py (🏠_Home.py):**
   - Lines 27-35: Sidebar HIDDEN when not authenticated
   - Lines 38-57: Successful login triggers IMMEDIATE redirect:
     ```python
     if SESSION_TOKEN_KEY in st.session_state:
         # Auto-redirect based on role
         if role == 'admin':
             st.switch_page("pages/Admin_Dashboard.py")
         elif role == 'instructor':
             st.switch_page("pages/Instructor_Dashboard.py")
         else:
             st.switch_page("pages/Student_Dashboard.py")
     ```

2. **Logout Button Location:**
   - NOT on Home.py
   - EXISTS on all dashboard pages in sidebar
   - Format: `st.button("🚪 Logout", use_container_width=True)`

3. **Test Implementation (commands.js):**
   - Line 59-80: `cy.login()` helper
     - Fills email/password
     - Clicks "🔐 Login"
     - Calls `waitForStreamlit()` (waits 500ms)
   - Line 243-249: `cy.assertAuthenticated()`
     - Expects sidebar to exist
     - Expects logout button: `cy.contains('[data-testid="stButton"] button', '🚪 Logout')`

---

## Root Cause Hypothesis

### Primary Suspect: Race Condition on Redirect

**Timeline:**
1. User clicks "🔐 Login" (t=0ms)
2. API call completes (~100-500ms)
3. Session state updated
4. `st.rerun()` triggered (line 101 in Home.py)
5. **REDIRECT STARTS** (line 43-57)
6. Test waits 500ms (`waitForStreamlit()`)
7. **Test checks for logout button**
8. **REDIRECT MAY NOT BE COMPLETE YET**

**Problem:**
- `cy.waitForStreamlit()` waits 500ms after login button click
- But Streamlit redirect (`st.switch_page()`) happens DURING rerun
- New page may not be fully rendered when test asserts
- Logout button is on NEW page, not Home.py

### Secondary Factors

1. **No URL Change Detection:**
   - Test doesn't wait for URL to change from `/` to `/Admin_Dashboard`
   - Test doesn't verify new page loaded

2. **Streamlit Rerun Timing:**
   - `st.rerun()` triggers React reconciliation
   - `st.switch_page()` triggers navigation
   - Both are async — 500ms may not be enough

3. **Sidebar Rendering Timing:**
   - Sidebar component may render after main content
   - Logout button inside sidebar may lag

---

## Test Evidence from Logs

### Passing Tests
- `auth/registration.cy.js`: 100% pass (no login assertions)
- `error_states/unauthorized.cy.js`: Tests that DON'T check logout button pass

### Failing Tests
- `auth/login.cy.js`: "admin login" → logout button not found (5 failures)
- `player/dashboard.cy.js`: "sidebar Logout button present" (3 failures)
- `student/enrollment_flow.cy.js`: "session stays active" → logout check fails

**Pattern:** ALL failures involve checking logout button immediately after login

---

## Proposed Fix Strategy

### Option A: Wait for URL Change (Recommended)
Add explicit wait for redirect completion:

```javascript
Cypress.Commands.add('login', (email, password) => {
  const initialUrl = cy.url();

  cy.visit('/');
  cy.waitForStreamlit();

  // Login form interaction
  cy.get('[data-testid="stTextInput"]')
    .first()
    .find('input')
    .clear()
    .type(email, { delay: 30 });

  cy.get('[data-testid="stTextInput"]')
    .find('input[type="password"]')
    .clear()
    .type(password, { delay: 30 });

  cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

  // WAIT FOR REDIRECT TO COMPLETE
  cy.url().should('not.equal', initialUrl);

  // WAIT FOR NEW PAGE TO RENDER
  cy.waitForStreamlit({ timeout: 10000 });

  // EXPLICIT WAIT FOR SIDEBAR TO BE VISIBLE
  cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('be.visible');
});
```

**Benefits:**
- Guarantees redirect completed before assertions
- Explicit sidebar visibility check
- More stable timing

**Drawbacks:**
- Adds ~1-2s per login
- More complex logic

### Option B: Increase Wait Time (Quick Fix)
```javascript
Cypress.Commands.add('waitForStreamlit', (options = {}) => {
  const timeout = options.timeout || 30000;

  cy.get('[data-testid="stApp"]', { timeout }).should('exist');

  cy.get('body').then($body => {
    if ($body.find('[data-testid="stSpinner"]').length > 0) {
      cy.get('[data-testid="stSpinner"]', { timeout }).should('not.exist');
    }
  });

  // INCREASE from 500ms to 2000ms
  cy.wait(2000);
});
```

**Benefits:**
- Simple one-line change
- May fix issue without complex logic

**Drawbacks:**
- Slower tests overall
- Doesn't guarantee redirect completion
- Band-aid solution

### Option C: Wait for Logout Button Explicitly
```javascript
Cypress.Commands.add('assertAuthenticated', () => {
  cy.get('[data-testid="stSidebar"]').should('exist');

  // WAIT UP TO 10s FOR LOGOUT BUTTON
  cy.contains('[data-testid="stButton"] button', '🚪 Logout', { timeout: 10000 })
    .should('exist');
});
```

**Benefits:**
- Minimal code change
- Focused on specific problem

**Drawbacks:**
- Doesn't fix underlying race condition
- Other elements may still fail

---

## Verification Plan

### Step 1: Headed Mode Test
Run single failing test in headed mode to observe:
```bash
cd tests_cypress
npx cypress open
# Select: auth/login.cy.js
# Select: "@smoke admin login succeeds"
# Watch what happens after login button click
```

**Observations to make:**
- Does URL change from `/` to `/Admin_Dashboard`?
- How long does redirect take?
- When does logout button appear?
- Is sidebar visible immediately or delayed?

### Step 2: Add Debug Logging
Temporarily add to `commands.js`:
```javascript
Cypress.Commands.add('login', (email, password) => {
  cy.visit('/');
  cy.waitForStreamlit();

  cy.log('Current URL before login:', cy.url());

  // ... login form interaction ...

  cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

  cy.url().then(url => cy.log('URL immediately after click:', url));

  cy.waitForStreamlit();

  cy.url().then(url => cy.log('URL after waitForStreamlit:', url));

  cy.get('[data-testid="stSidebar"]').should('exist').then(() => {
    cy.log('Sidebar exists');
  });

  cy.contains('[data-testid="stButton"] button', '🚪 Logout').should('exist').then(() => {
    cy.log('Logout button found');
  });
});
```

### Step 3: Implement Fix
Based on headed mode observations, implement Option A (wait for URL change).

### Step 4: Validate Fix
```bash
# Run only auth/login.cy.js
npx cypress run --spec "cypress/e2e/auth/login.cy.js"

# Expected: All 9 tests pass
```

### Step 5: Full Regression
```bash
# Run full suite with backend running
npx cypress run

# Track improvement in pass rate
```

---

## Environment Baseline (Current State)

### Confirmed Working
- ✅ Backend API: Running on port 8000 (HTTP 200)
- ✅ Streamlit: Running on port 8501 (HTTP 200)
- ✅ Clean restart: Cache cleared

### Test Configuration
- Browser: Electron 106 (headless)
- Node: v23.7.0
- Cypress: 12.17.4
- Retry: 3 attempts per test

---

## Success Criteria

1. **Immediate:** Single test passes consistently
   - `auth/login.cy.js` → "admin login" → 3/3 retries pass

2. **Short-term:** Auth suite stable
   - `auth/login.cy.js` → 9/9 tests pass
   - No retry needed

3. **Long-term:** All logout-dependent tests pass
   - Player dashboard suite: 8/8 pass
   - Student enrollment: 9/9 pass
   - Overall: +20 tests fixed

---

## Next Actions

1. ✅ Environment stabilized (backend + streamlit running)
2. 🔄 **IN PROGRESS:** Run headed mode test to observe timing
3. ⏳ Implement Option A (URL change wait)
4. ⏳ Validate fix with single spec
5. ⏳ Full suite regression test

---

**Status:** Investigation complete — Ready for headed mode validation
**Owner:** Claude Code
**Target:** Fix within 2 hours
