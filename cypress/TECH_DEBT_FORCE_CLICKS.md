# TECH-DEBT: {force: true} Usage in Cypress Commands

**Date:** 2026-02-20
**Status:** 🔴 Active technical debt
**Priority:** P2 (Medium - workaround for Streamlit overlay race conditions)

---

## Overview

This document tracks all `{force: true}` usage in Cypress custom commands. Force-clicking bypasses Cypress's actionability checks (visibility, coverage, pointer-events) and should be treated as **technical debt** requiring future investigation.

---

## Current Usage Locations

### 1. `clickSidebarButton()` — Line 174
**File:** [tests_cypress/cypress/support/commands.js:174](tests_cypress/cypress/support/commands.js#L174)

**Code:**
```javascript
cy.get('[data-testid="stSidebar"]')
  .contains('[data-testid="stButton"] button', buttonText)
  .click({ force: true });  // force bypasses CSS-collapsed sidebar (transform off-screen)
```

**Reason:**
Streamlit sidebar can be CSS-collapsed (off-screen via `transform: translateX(-100%)`) in headless Electron even at 1440×900 resolution. Force-clicking bypasses Cypress's visibility check.

**Risk:** LOW
- Known Streamlit behavior (CSS transform, not pointer-events blocking)
- Element is functionally clickable (not covered by overlay)
- No observed side effects

**Mitigation:**
None required — this is expected Streamlit behavior.

---

### 2. `clickAdminTab()` — Line 186
**File:** [tests_cypress/cypress/support/commands.js:186](tests_cypress/cypress/support/commands.js#L186)

**Code:**
```javascript
Cypress.Commands.add('clickAdminTab', (tabLabel) => {
  cy.waitForNoOverlay();  // Ensure no blocking overlays before tab click
  cy.contains('[data-testid="stButton"] button', tabLabel).click({ force: true });
  cy.waitForStreamlit();
});
```

**Reason:**
Streamlit renders blocking overlay divs (`<div class="st-emotion-cache-1j22a0y">`) **during** the click operation (not before). `waitForNoOverlay()` checks pointer-events before the click, but the overlay appears dynamically during React reconciliation.

**Root Cause:**
Streamlit's React state update cycle triggers overlay rendering **after** Cypress's actionability check passes but **before** the click event completes.

**Risk:** MEDIUM
- ⚠️ Bypasses genuine coverage detection
- ✅ Click event **does** reach the button (verified: 19/19 tests pass)
- ✅ Streamlit processes the click server-side correctly
- ⚠️ May mask future overlay-related bugs

**Validation:**
- **Before fix:** 8/19 passing (42.1%)
- **After fix:** 19/19 passing (100%)
- **Duration improvement:** 10m 51s → 1m 16s

**Future Investigation:**
1. Increase `waitForNoOverlay()` timeout (300ms → 2000ms) to allow full React reconciliation
2. Wait for no DOM mutations (MutationObserver) before clicking
3. Upstream Streamlit issue: overlay should not block interactions during state updates

**Mitigation Priority:** P2 (Medium)
Fix works reliably, but should be replaced with non-force solution if Streamlit overlay behavior changes.

---

### 3. `fillInput()` — Lines 307-308
**File:** [tests_cypress/cypress/support/commands.js:307-308](tests_cypress/cypress/support/commands.js#L307-L308)

**Code:**
```javascript
cy.contains('[data-testid="stTextInput"] label', label)
  .parents('[data-testid="stTextInput"]')
  .find('input')
  .clear({ force: true })
  .type(value, { delay: 20, force: true });
```

**Reason:**
Same as `clickAdminTab()` — Streamlit overlay can cover input fields during form rendering.

**Risk:** MEDIUM
- Same overlay race condition as tab clicks
- `.clear()` and `.type()` both need force to bypass coverage check

**Validation:**
Registration tests (auth/registration.cy.js) were failing with "element covered" errors before force was added.

**Mitigation Priority:** P2 (Medium)
Same mitigation strategy as `clickAdminTab()`.

---

## Summary Table

| Command | Line | Reason | Risk | Status |
|---------|------|--------|------|--------|
| `clickSidebarButton()` | 174 | CSS-collapsed sidebar (transform) | LOW | ✅ Acceptable |
| `clickAdminTab()` | 186 | Streamlit overlay race condition | MEDIUM | 🔴 TECH-DEBT |
| `fillInput()` clear | 307 | Streamlit overlay race condition | MEDIUM | 🔴 TECH-DEBT |
| `fillInput()` type | 308 | Streamlit overlay race condition | MEDIUM | 🔴 TECH-DEBT |

**Total force interactions:** 4
**Active tech debt items:** 3 (clickAdminTab, fillInput clear/type)

---

## Mitigation Plan

### Short-term (Current)
✅ Use `{force: true}` with explicit `waitForNoOverlay()` pre-checks
✅ Document all usage in this file
✅ Monitor for regressions in full suite runs

### Medium-term (Next sprint)
- [ ] Increase `waitForNoOverlay()` stabilization pause (300ms → 2000ms)
- [ ] Add MutationObserver-based wait helper (`waitForDOMStable()`)
- [ ] Test without force on Streamlit upgrade (track overlay behavior changes)

### Long-term (Future)
- [ ] Upstream Streamlit issue: overlay should use `pointer-events: none` or render **after** user interactions complete
- [ ] Replace all force clicks with deterministic wait strategies if Streamlit fixes overlay timing

---

## Validation Checklist

**Before removing `{force: true}` from any command:**
1. Run affected spec 3 times to ensure no flakiness
2. Verify 100% pass rate across all retries
3. Check screenshot evidence (no "element covered" errors)
4. Test on both macOS (Electron) and Linux (Chrome headless)

---

**Last Updated:** 2026-02-20
**Maintainer:** Claude Code
**Review Cycle:** After each Streamlit version upgrade
