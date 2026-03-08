// ============================================================================
// Cypress E2E Support — global configuration and hooks
// ============================================================================
// This file is loaded automatically before every spec.
// Import custom commands, third-party plugins, and global hooks here.
// ============================================================================

import './commands';

// ── @cypress/grep ────────────────────────────────────────────────────────────
// Tag-based test filtering.  Usage: CYPRESS_grepTags=@smoke npx cypress run
try {
  require('@cypress/grep')();
} catch {
  // Not installed yet — skip silently.
}

// ── Uncaught exception handling ──────────────────────────────────────────────
// Streamlit's React internals occasionally throw ResizeObserver loop errors
// and hydration warnings that are benign and should not fail tests.
Cypress.on('uncaught:exception', (err) => {
  // Allow genuine application errors to bubble up, suppress framework noise.
  const knownNoise = [
    'ResizeObserver loop limit exceeded',
    'ResizeObserver loop completed',
    'hydration',
    'Minified React error',
    'Non-Error promise rejection',
    'Script error',
  ];
  if (knownNoise.some(msg => err.message?.includes(msg))) {
    return false; // suppress
  }
  // Let all other errors fail the test as expected.
  return true;
});

// ── Global before each ───────────────────────────────────────────────────────
// Clear Streamlit session storage between tests to prevent state leakage.
beforeEach(() => {
  // Streamlit persists session state in sessionStorage under various keys.
  // Clearing it ensures each test starts from a clean auth state.
  cy.clearAllSessionStorage();
  cy.clearAllCookies();
  cy.clearAllLocalStorage();
});
