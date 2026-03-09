/**
 * Custom Cypress commands for FastAPI Jinja2 web routes (localhost:8000).
 *
 * These are separate from the Streamlit commands in commands.js.
 * Import in web specs via:  import '../support/web_commands'
 * Or auto-import via e2e.js when baseUrl points to port 8000.
 */

// ── Login / logout ─────────────────────────────────────────────────────────

/**
 * Login via the FastAPI /login form.
 * Clears cookies first so each test starts unauthenticated.
 */
Cypress.Commands.add('webLogin', (email, password) => {
  cy.clearAllCookies();
  cy.visit('/login');
  cy.get('input[name="email"]').type(email);
  cy.get('input[name="password"]').type(password);
  cy.get('button[type="submit"]').click();
});

/**
 * Login using a named role from cypress env (set in cypress.config.js).
 * Roles: 'admin' | 'instructor' | 'student' | 'fresh'
 */
Cypress.Commands.add('webLoginAs', (role) => {
  const map = {
    admin:      { email: Cypress.env('webAdminEmail'),      password: Cypress.env('webAdminPassword') },
    instructor: { email: Cypress.env('webInstructorEmail'), password: Cypress.env('webInstructorPassword') },
    student:    { email: Cypress.env('webStudentEmail'),     password: Cypress.env('webStudentPassword') },
    fresh:      { email: Cypress.env('webFreshEmail'),       password: Cypress.env('webFreshPassword') },
  };
  const creds = map[role];
  if (!creds) throw new Error(`Unknown web role: "${role}". Use admin|instructor|student|fresh.`);
  cy.webLogin(creds.email, creds.password);
});

// ── Navigation assertions ──────────────────────────────────────────────────

/** Assert that the current URL contains the given path fragment. */
Cypress.Commands.add('assertWebPath', (fragment) => {
  cy.url().should('include', fragment);
});

/** Assert that the page contains a visible element with the given text. */
Cypress.Commands.add('assertPageContains', (text) => {
  cy.contains(text).should('be.visible');
});

/** Assert that a form error message is visible on the page. */
Cypress.Commands.add('assertFormError', (text) => {
  cy.get('[class*="error"], [class*="alert"], [class*="danger"], .flash, #error')
    .should('be.visible')
    .and('contain', text);
});

// ── DB reset ──────────────────────────────────────────────────────────────

/**
 * Reset the database to the given scenario before a suite.
 * Call in before() or beforeEach() at the top of each spec.
 * Scenarios: 'baseline' | 'student_no_dob' | 'student_with_credits' | 'session_ready'
 */
Cypress.Commands.add('resetDb', (scenario = 'baseline') => {
  cy.task('resetDb', scenario);
});

// ── API helpers ───────────────────────────────────────────────────────────

/**
 * Get a session ID for the given title prefix from the DB via API.
 * Requires admin auth.  Used in session flow specs to get dynamic session IDs.
 */
Cypress.Commands.add('getSessionIdByTitle', (titleFragment) => {
  cy.request({
    method: 'GET',
    url: `${Cypress.env('apiUrl')}/api/v1/sessions/`,
    qs: { limit: 50 },
    headers: { Authorization: 'Bearer test-csrf-bypass' },
    failOnStatusCode: false,
  }).then((resp) => {
    if (resp.status !== 200) return cy.wrap(null);
    const session = resp.body.sessions?.find((s) => s.title?.includes(titleFragment));
    return cy.wrap(session?.id ?? null);
  });
});
