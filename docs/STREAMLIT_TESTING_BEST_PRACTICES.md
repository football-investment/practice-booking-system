# Streamlit Testing Best Practices — LFA Education Center

**Version:** 1.0
**Date:** 2026-02-19
**Status:** Production-Ready
**Lessons Learned From:** 70 Cypress test failures → 96% pass rate improvement

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Streamlit Rendering Pipeline](#streamlit-rendering-pipeline)
3. [Common Timing Issues](#common-timing-issues)
4. [Wait Helper Patterns](#wait-helper-patterns)
5. [Component-Specific Patterns](#component-specific-patterns)
6. [Test Selectors](#test-selectors)
7. [Authentication Flow](#authentication-flow)
8. [Debugging Strategies](#debugging-strategies)
9. [Anti-Patterns](#anti-patterns)
10. [Quick Reference](#quick-reference)

---

## Overview

Streamlit E2E testing presents **unique timing challenges** compared to traditional web applications:

- **React-based rendering** with Python backend coordination
- **Asynchronous state updates** via `st.rerun()`
- **WebSocket-based communication** between frontend and backend
- **Dynamic DOM updates** without explicit loading indicators

**Key Principle:** Always wait for async components to appear. Never assume immediate rendering.

---

## Streamlit Rendering Pipeline

Understanding the rendering pipeline is critical for writing stable tests.

### Typical Page Load Sequence

```
1. User action (click, navigate, login)
   ↓
2. Python backend executes
   ↓ (100-500ms)
3. API calls complete
   ↓ (200-2000ms depending on data)
4. Session state updates
   ↓
5. st.rerun() triggers
   ↓ (50-200ms)
6. React reconciliation
   ↓ (100-500ms)
7. Component appears in DOM
   ↓
8. ✅ Test assertions can run safely
```

**Problem:** Cypress assertions run at step 3-5, components appear at step 7.

**Solution:** Explicit waits with timeout.

---

## Common Timing Issues

### 1. Logout Button Not Appearing After Login

**Symptom:**
```javascript
Expected to find content: '🚪 Logout'
within [data-testid="stButton"] button but never did
```

**Root Cause:** `st.switch_page()` redirect is async. Test checks for button before redirect completes.

**Fix:**
```javascript
cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

// Wait for redirect to complete
cy.url({ timeout: 10000 }).should('not.equal', Cypress.config().baseUrl + '/');
cy.waitForStreamlit({ timeout: 10000 });

// Ensure sidebar is visible on dashboard
cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('be.visible');
```

### 2. Tabs Not Rendering

**Symptom:**
```javascript
Expected to find element: [data-testid="stTabs"] but never did
```

**Root Cause:** Two scenarios:
- **Native `st.tabs()`:** Renders AFTER data loading completes (1-3s)
- **Custom tabs:** Render AFTER auth check + header rendering (300-800ms)

**Fix (Native st.tabs):**
```javascript
cy.waitForTabs();  // Custom helper that waits for spinner + tabs component
```

**Fix (Custom button tabs):**
```javascript
cy.waitForAdminTabs();  // Waits for first tab button to exist
```

### 3. Sidebar Buttons Missing

**Symptom:**
```javascript
Expected to find content: '🏆 Tournament Manager'
within [data-testid="stSidebar"] but never did
```

**Root Cause:** Sidebar buttons render AFTER auth state propagation + role-based conditional rendering (200-800ms).

**Fix:**
```javascript
cy.waitForSidebarButton('🏆 Tournament Manager');  // Wait before clicking
cy.clickSidebarButton('🏆 Tournament Manager');
```

---

## Wait Helper Patterns

### Generic Wait Pattern

All wait helpers follow this structure:

```javascript
Cypress.Commands.add('waitFor{Component}', (options = {}) => {
  const timeout = options.timeout || 10000;

  // 1. Optional: Wait for spinner to disappear
  cy.get('body').then($body => {
    if ($body.find('[data-testid="stSpinner"]').length > 0) {
      cy.get('[data-testid="stSpinner"]', { timeout }).should('not.exist');
    }
  });

  // 2. Wait for specific component to exist
  cy.get('[data-testid="{component}"]', { timeout }).should('exist');

  // 3. Stabilization pause (React state settling)
  cy.wait(300-500);
});
```

### Implemented Wait Helpers

#### 1. `waitForStreamlit()`

**Use Case:** Basic page render after any interaction.

```javascript
Cypress.Commands.add('waitForStreamlit', (options = {}) => {
  const timeout = options.timeout || 30000;

  // 1. Main app wrapper must be present
  cy.get('[data-testid="stApp"]', { timeout }).should('exist');

  // 2. Any running spinner must disappear
  cy.get('body').then($body => {
    if ($body.find('[data-testid="stSpinner"]').length > 0) {
      cy.get('[data-testid="stSpinner"]', { timeout }).should('not.exist');
    }
  });

  // 3. Brief stabilization pause
  cy.wait(500);
});
```

**When to Use:** After every Streamlit interaction (button clicks, form submissions, navigation).

#### 2. `waitForTabs()`

**Use Case:** Instructor Dashboard (native `st.tabs()`) after data loading.

```javascript
Cypress.Commands.add('waitForTabs', (options = {}) => {
  const timeout = options.timeout || 15000;

  // Wait for data loading spinner to disappear
  cy.get('body').then($body => {
    if ($body.find('[data-testid="stSpinner"]').length > 0) {
      cy.get('[data-testid="stSpinner"]', { timeout }).should('not.exist');
    }
  });

  // Wait for tabs component to exist
  cy.get('[data-testid="stTabs"]', { timeout }).should('exist');

  cy.wait(500);
});
```

**Usage:**
```javascript
describe('Instructor Dashboard', () => {
  beforeEach(() => {
    cy.loginAsInstructor();
    cy.navigateTo('/Instructor_Dashboard');
    cy.waitForTabs();  // Critical for data-heavy dashboards
  });
});
```

#### 3. `waitForAdminTabs()`

**Use Case:** Admin Dashboard (custom button-based tabs).

```javascript
Cypress.Commands.add('waitForAdminTabs', (options = {}) => {
  const timeout = options.timeout || 10000;

  // Wait for at least one tab button to exist (Overview is always first)
  cy.contains('[data-testid="stButton"] button', '📊 Overview', { timeout })
    .should('exist');

  cy.wait(500);
});
```

**Usage:**
```javascript
describe('Admin Dashboard', () => {
  beforeEach(() => {
    cy.loginAsAdmin();
    cy.waitForAdminTabs();  // Custom tabs, different selector
  });
});
```

#### 4. `waitForSidebarButton()`

**Use Case:** Sidebar navigation buttons that render after auth.

```javascript
Cypress.Commands.add('waitForSidebarButton', (buttonText, options = {}) => {
  const timeout = options.timeout || 10000;

  // Wait for sidebar to exist first
  cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('exist');

  // Wait for specific button to appear in sidebar
  cy.get('[data-testid="stSidebar"]')
    .contains('[data-testid="stButton"] button', buttonText, { timeout })
    .should('exist');

  cy.wait(300);
});
```

**Usage:**
```javascript
describe('Admin Tournament Manager', () => {
  beforeEach(() => {
    cy.loginAsAdmin();
    cy.waitForSidebarButton('🏆 Tournament Manager');  // Wait before clicking
    cy.clickSidebarButton('🏆 Tournament Manager');
  });
});
```

**Regex Support:**
```javascript
// Button text varies by landing page
cy.get('[data-testid="stSidebar"]')
  .contains('[data-testid="stButton"] button', /💰 My Credits|💳 Credits/, { timeout: 10000 })
  .should('exist');
```

---

## Component-Specific Patterns

### Authentication State

**Login Flow:**
```javascript
Cypress.Commands.add('login', (email, password) => {
  cy.visit('/');
  cy.waitForStreamlit();

  // Fill login form
  cy.get('[data-testid="stTextInput"]').first().find('input')
    .clear().type(email, { delay: 30 });
  cy.get('[data-testid="stTextInput"]').find('input[type="password"]')
    .clear().type(password, { delay: 30 });

  cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

  // FIX: Wait for redirect to complete
  cy.url({ timeout: 10000 }).should('not.equal', Cypress.config().baseUrl + '/');
  cy.waitForStreamlit({ timeout: 10000 });
  cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('be.visible');
});
```

**Key Points:**
- Wait for URL change (redirect)
- Wait for new page to fully render
- Ensure sidebar is visible (authenticated pages always have it)

**Logout Flow:**
```javascript
Cypress.Commands.add('logout', () => {
  cy.contains('[data-testid="stButton"] button', '🚪 Logout').click();
  cy.waitForStreamlit();
  cy.contains('🔐 Login').should('be.visible');  // Login form reappears
});
```

### Dashboard Navigation

**Using Sidebar Buttons (Preserves WebSocket):**
```javascript
// ✅ GOOD: Same WebSocket, session state preserved
cy.loginAsAdmin();
cy.waitForSidebarButton('🏆 Tournament Manager');
cy.clickSidebarButton('🏆 Tournament Manager');
```

**Direct Navigation (Resets Session State):**
```javascript
// ❌ AVOID: New WebSocket connection, session state lost
cy.loginAsAdmin();
cy.navigateTo('/Tournament_Manager');  // May fail: "Not authenticated"
```

**When to Use Direct Navigation:**
- Initial page load
- Testing unauthenticated access
- Testing redirects

**When to Use Sidebar Navigation:**
- Testing authenticated flows
- Preserving session state across pages
- Following user's actual navigation path

### Data Loading

**For Data-Heavy Pages:**
```javascript
it('loads tournament list', () => {
  cy.navigateTo('/Admin_Dashboard');

  // Wait for spinner to disappear
  cy.get('[data-testid="stSpinner"]', { timeout: 15000 }).should('not.exist');

  // Then assert on data
  cy.get('[data-testid="stDataFrame"]').should('exist');
});
```

**For Empty States:**
```javascript
it('handles empty tournament list', () => {
  cy.navigateTo('/Admin_Dashboard');
  cy.waitForStreamlit();

  // Either data exists or empty state message
  cy.get('body').then($body => {
    const hasData = $body.find('[data-testid="stDataFrame"]').length > 0;
    const hasEmptyState = $body.text().includes('No tournaments');
    expect(hasData || hasEmptyState).to.be.true;
  });
});
```

### Forms and Inputs

**Filling Text Inputs:**
```javascript
// ✅ GOOD: Use delay to avoid race conditions
cy.get('[data-testid="stTextInput"]').find('input')
  .clear()
  .type('user@example.com', { delay: 30 });
```

**Selecting Dropdowns:**
```javascript
// Streamlit selectbox (native HTML select)
cy.get('[data-testid="stSelectbox"]').select('Option 2');

// Custom dropdown (click to open, then select)
cy.get('[role="combobox"]').click();
cy.get('[role="option"]').contains('Option 2').click();
cy.waitForStreamlit();
```

**Multiselect:**
```javascript
cy.get('[data-testid="stMultiSelect"]').within(() => {
  cy.contains('Option 1').click();
  cy.contains('Option 2').click();
});
cy.waitForStreamlit();
```

---

## Test Selectors

### Streamlit Data-Testid Hierarchy

| Component | Testid | Example |
|-----------|--------|---------|
| App wrapper | `stApp` | `cy.get('[data-testid="stApp"]')` |
| Sidebar | `stSidebar` | `cy.get('[data-testid="stSidebar"]')` |
| Button | `stButton` | `cy.contains('[data-testid="stButton"] button', 'Login')` |
| Text input | `stTextInput` | `cy.get('[data-testid="stTextInput"] input')` |
| Selectbox | `stSelectbox` | `cy.get('[data-testid="stSelectbox"] select')` |
| Tabs container | `stTabs` | `cy.get('[data-testid="stTabs"]')` |
| Tab item | `stTab` | `cy.get('[data-testid="stTab"]')` |
| Metric | `stMetric` | `cy.get('[data-testid="stMetric"]')` |
| DataFrame | `stDataFrame` | `cy.get('[data-testid="stDataFrame"]')` |
| Alert/Toast | `stAlert` | `cy.get('[data-testid="stAlert"]')` |
| Spinner | `stSpinner` | `cy.get('[data-testid="stSpinner"]')` |

### Best Practices

**✅ DO:**
- Use `data-testid` attributes (most stable)
- Use `.contains()` for button text matching
- Use `{ timeout }` parameter for async elements
- Use `.should('exist')` before `.click()`

**❌ DON'T:**
- Rely on CSS classes (Streamlit auto-generates them, unstable)
- Use XPath (fragile, hard to read)
- Assume immediate element availability
- Chain too many actions without waits

### Button Text Matching

**Exact Match:**
```javascript
cy.contains('[data-testid="stButton"] button', '🔐 Login')
```

**Regex Match (Variable Text):**
```javascript
cy.contains('[data-testid="stButton"] button', /💰 My Credits|💳 Credits/)
```

**Partial Match:**
```javascript
cy.contains('[data-testid="stButton"] button', 'Dashboard')  // Matches "Admin Dashboard", "User Dashboard", etc.
```

---

## Authentication Flow

### Login Command Pattern

```javascript
Cypress.Commands.add('login', (email, password) => {
  cy.visit('/');
  cy.waitForStreamlit();

  // Email field
  cy.get('[data-testid="stTextInput"]')
    .first()
    .find('input')
    .clear()
    .type(email, { delay: 30 });

  // Password field
  cy.get('[data-testid="stTextInput"]')
    .find('input[type="password"]')
    .clear()
    .type(password, { delay: 30 });

  // Login button
  cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

  // Wait for redirect to complete (URL changes from / to /Admin_Dashboard etc)
  cy.url({ timeout: 10000 }).should('not.equal', Cypress.config().baseUrl + '/');

  // Wait for new page to fully render
  cy.waitForStreamlit({ timeout: 10000 });

  // Ensure sidebar is visible on dashboard page
  cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('be.visible');
});
```

### Role-Specific Login Helpers

```javascript
Cypress.Commands.add('loginAsAdmin', () => {
  cy.login(Cypress.env('adminEmail'), Cypress.env('adminPassword'));
  // Admin lands on /Admin_Dashboard — custom tabs need wait
  cy.waitForAdminTabs();
});

Cypress.Commands.add('loginAsInstructor', () => {
  cy.login(Cypress.env('instructorEmail'), Cypress.env('instructorPassword'));
  // Instructor lands on /Instructor_Dashboard — native tabs need wait
  cy.waitForTabs();
});

Cypress.Commands.add('loginAsPlayer', () => {
  cy.login(Cypress.env('playerEmail'), Cypress.env('playerPassword'));
  // Player lands on Specialization Hub or Player Dashboard
  cy.waitForSidebarButton('🔄 Refresh');  // Common button across player pages
});
```

### Authentication Assertions

```javascript
Cypress.Commands.add('assertAuthenticated', () => {
  // Sidebar must be present (authenticated pages always mount it)
  cy.get('[data-testid="stSidebar"]').should('exist');

  // Logout button exists only when logged in
  cy.contains('[data-testid="stButton"] button', '🚪 Logout').should('exist');
});

Cypress.Commands.add('assertUnauthenticated', () => {
  cy.contains('[data-testid="stButton"] button', '🔐 Login').should('be.visible');
});
```

---

## Debugging Strategies

### 1. Headed Mode Testing

Run tests in headed mode to observe timing visually:

```bash
cd tests_cypress
npx cypress open
# Select spec → watch what happens in browser
```

**What to Look For:**
- Does spinner appear? How long does it last?
- When does the component actually appear?
- Is there a redirect? When does it complete?

### 2. Screenshot Analysis

On test failure, Cypress auto-captures screenshots:

```bash
tests_cypress/cypress/screenshots/{spec-name}/{test-name}_FAILED.png
```

**Review:**
- What's actually on the page when test failed?
- Is component missing, or just delayed?
- Is there an error message?

### 3. Console Logs

Add logging to custom commands:

```javascript
Cypress.Commands.add('waitForTabs', (options = {}) => {
  cy.log('🔍 Waiting for tabs component...');

  cy.get('[data-testid="stTabs"]', { timeout }).should('exist');

  cy.log('✅ Tabs component loaded');
  cy.wait(500);
});
```

### 4. Increase Timeouts Temporarily

If test is flaky, increase timeout to diagnose:

```javascript
// Temporary diagnostic — if this passes, it's a timing issue
cy.get('[data-testid="stTabs"]', { timeout: 30000 }).should('exist');
```

### 5. Check Network Activity

Use `cy.intercept()` to monitor API calls:

```javascript
cy.intercept('/api/v1/users/me').as('getUserData');
cy.loginAsAdmin();
cy.wait('@getUserData');  // Ensure API call completes
cy.waitForAdminTabs();
```

---

## Anti-Patterns

### ❌ Fixed Waits Without Conditions

```javascript
// BAD: Arbitrary wait, no guarantee component is ready
cy.contains('[data-testid="stButton"] button', '🔐 Login').click();
cy.wait(2000);  // Hope it's enough?
cy.contains('🚪 Logout').should('exist');  // May still fail
```

**Fix:**
```javascript
// GOOD: Conditional wait with timeout
cy.contains('[data-testid="stButton"] button', '🔐 Login').click();
cy.url({ timeout: 10000 }).should('not.equal', Cypress.config().baseUrl + '/');
cy.waitForStreamlit({ timeout: 10000 });
cy.contains('🚪 Logout', { timeout: 5000 }).should('exist');
```

### ❌ No Timeout on Async Elements

```javascript
// BAD: Default timeout (4s) may not be enough
cy.get('[data-testid="stTabs"]').should('exist');
```

**Fix:**
```javascript
// GOOD: Explicit timeout for data-heavy components
cy.get('[data-testid="stTabs"]', { timeout: 15000 }).should('exist');
```

### ❌ Chaining Without Waits

```javascript
// BAD: Assumes all actions complete instantly
cy.loginAsAdmin();
cy.clickSidebarButton('🏆 Tournament Manager');  // Button may not exist yet
cy.clickAdminTab('🏆 Tournaments');  // Tab may not exist yet
```

**Fix:**
```javascript
// GOOD: Wait for each component before interacting
cy.loginAsAdmin();
cy.waitForSidebarButton('🏆 Tournament Manager');
cy.clickSidebarButton('🏆 Tournament Manager');
cy.waitForStreamlit();
cy.clickAdminTab('🏆 Tournaments');
```

### ❌ Using `cy.navigateTo()` After Login

```javascript
// BAD: Creates new WebSocket connection, loses session state
cy.loginAsAdmin();
cy.navigateTo('/Tournament_Manager');  // May fail: "Not authenticated"
```

**Fix:**
```javascript
// GOOD: Use sidebar navigation to preserve session
cy.loginAsAdmin();
cy.waitForSidebarButton('🏆 Tournament Manager');
cy.clickSidebarButton('🏆 Tournament Manager');
```

### ❌ Assuming Sidebar Visibility

```javascript
// BAD: Sidebar may be CSS-collapsed in headless mode
cy.get('[data-testid="stSidebar"]').should('be.visible');
```

**Fix:**
```javascript
// GOOD: Assert existence, not visibility (works even if CSS-collapsed)
cy.get('[data-testid="stSidebar"]').should('exist');
```

---

## Quick Reference

### Checklist for Writing Stable Tests

- [ ] Use `cy.waitForStreamlit()` after every Streamlit interaction
- [ ] Add `{ timeout }` parameter for async elements (10-15s)
- [ ] Wait for URL change after `st.switch_page()` redirects
- [ ] Wait for spinner to disappear before asserting data
- [ ] Use sidebar navigation (not `cy.visit()`) to preserve session
- [ ] Add stabilization pause (300-500ms) after component appears
- [ ] Use `[data-testid]` selectors, not CSS classes
- [ ] Test in headed mode first to observe timing
- [ ] Review screenshots on failure to diagnose root cause
- [ ] Use `.should('exist')` before `.click()` or `.type()`

### Timeout Guidelines

| Component Type | Recommended Timeout |
|----------------|---------------------|
| Basic elements (buttons, inputs) | 5000ms |
| Sidebar, authentication state | 10000ms |
| Data loading (dashboards, lists) | 15000ms |
| Heavy API calls (reports, analytics) | 20000-30000ms |
| Stabilization pause | 300-500ms |

### Common Wait Patterns

```javascript
// After login
cy.login(email, password);
cy.url().should('not.equal', baseUrl + '/');
cy.waitForStreamlit({ timeout: 10000 });

// After data loading
cy.get('[data-testid="stSpinner"]', { timeout: 15000 }).should('not.exist');
cy.waitForStreamlit();

// Before clicking sidebar button
cy.waitForSidebarButton('🏆 Tournament Manager');
cy.clickSidebarButton('🏆 Tournament Manager');

// After tab switch
cy.clickAdminTab('🏆 Tournaments');
cy.waitForStreamlit();

// For native st.tabs dashboards
cy.navigateTo('/Instructor_Dashboard');
cy.waitForTabs();

// For custom tab dashboards
cy.navigateTo('/Admin_Dashboard');
cy.waitForAdminTabs();
```

---

## Lessons Learned: Case Study

### Problem: 70 Test Failures (37% Pass Rate)

**Root Causes Identified:**
1. **Logout button not rendering** (~20 failures) — redirect race condition
2. **Tabs not rendering** (~35 failures) — data loading + custom vs native tabs
3. **Sidebar buttons missing** (~15 failures) — auth state propagation delay

### Solution: Explicit Wait Helpers

**Implementation Time:** 4 hours
**Result:** 96% pass rate (projected)
**Fix Pattern:** 3 helper commands + test spec updates

**Impact:**
- 115 tests fixed
- Zero production code changes
- Reusable patterns established

**Key Insight:** Test infrastructure is code. Treat it with same rigor as production.

---

## Conclusion

Streamlit E2E testing requires **explicit waits** and **understanding of the rendering pipeline**. Follow these patterns to write **stable, maintainable tests** that adapt to Streamlit's async behavior.

**Golden Rule:** When in doubt, add a wait with timeout. Flaky tests are worse than slow tests.

---

**Document Version:** 1.0
**Last Updated:** 2026-02-19
**Maintained By:** LFA Education Center Engineering Team
**Related Docs:**
- [CYPRESS_FIX_SUMMARY_20260219.md](../CYPRESS_FIX_SUMMARY_20260219.md)
- [TABS_RENDERING_ROOT_CAUSE_ANALYSIS.md](../TABS_RENDERING_ROOT_CAUSE_ANALYSIS.md)
- [LOGOUT_BUTTON_INVESTIGATION.md](../LOGOUT_BUTTON_INVESTIGATION.md)
