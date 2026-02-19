// ============================================================================
// Cypress Custom Commands — LFA Education Center
// ============================================================================
//
// All Streamlit-aware helpers live here.
//
// Streamlit DOM notes:
//   - Buttons:     [data-testid="stButton"] button
//   - Text inputs: [data-testid="stTextInput"] input
//   - Password:    [data-testid="stTextInput"] input[type="password"]
//   - Select:      [data-testid="stSelectbox"] select (or [role="combobox"])
//   - Tabs:        [data-testid="stTabs"] + [data-testid="stTab"]
//   - Sidebar:     [data-testid="stSidebar"]
//   - Spinner:     [data-testid="stSpinner"]  (wait for it to disappear)
//   - Alert/info:  [data-testid="stAlert"]
//   - Metric:      [data-testid="stMetric"]
//
// After every Streamlit interaction, the React tree re-renders.
// Always waitForStreamlit() before asserting on post-action state.
// ============================================================================


// ── Streamlit boot wait ──────────────────────────────────────────────────────

/**
 * Wait until Streamlit has fully rendered the page (spinner gone, app visible).
 * Must be called after every cy.visit() and after interactions that trigger
 * a full rerender (e.g. login, tab switch).
 */
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

  // 3. Brief stabilisation pause (Streamlit batches state updates)
  cy.wait(500);
});


// ── Authentication commands ──────────────────────────────────────────────────

/**
 * Login via the LFA Home page login form.
 *
 * @param {string} email
 * @param {string} password
 *
 * Usage:
 *   cy.login('admin@lfa.com', 'password123')
 */
Cypress.Commands.add('login', (email, password) => {
  cy.visit('/');
  cy.waitForStreamlit();

  // Email field (labelled "Email", placeholder "admin@lfa.com")
  cy.get('[data-testid="stTextInput"]')
    .first()
    .find('input')
    .clear()
    .type(email, { delay: 30 });

  // Password field (type="password")
  cy.get('[data-testid="stTextInput"]')
    .find('input[type="password"]')
    .clear()
    .type(password, { delay: 30 });

  // Login button
  cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

  // FIX: Wait for redirect to dashboard (URL changes from / to /Admin_Dashboard etc)
  // Streamlit st.switch_page() triggers navigation - must wait for it to complete
  cy.url({ timeout: 10000 }).should('not.equal', Cypress.config().baseUrl + '/');

  // Wait for new page to fully render
  cy.waitForStreamlit({ timeout: 10000 });

  // Ensure sidebar is visible on dashboard page
  cy.get('[data-testid="stSidebar"]', { timeout: 5000 }).should('be.visible');
});

/**
 * Login as admin using credentials from cypress.config env.
 */
Cypress.Commands.add('loginAsAdmin', () => {
  cy.login(Cypress.env('adminEmail'), Cypress.env('adminPassword'));
});

/**
 * Login as instructor using credentials from cypress.config env.
 */
Cypress.Commands.add('loginAsInstructor', () => {
  cy.login(Cypress.env('instructorEmail'), Cypress.env('instructorPassword'));
});

/**
 * Login as player using credentials from cypress.config env.
 */
Cypress.Commands.add('loginAsPlayer', () => {
  cy.login(Cypress.env('playerEmail'), Cypress.env('playerPassword'));
});

/**
 * Click the Logout button wherever it appears in the sidebar.
 */
Cypress.Commands.add('logout', () => {
  // Click Logout button — search whole page because sidebar may be CSS-collapsed
  cy.contains('[data-testid="stButton"] button', '🚪 Logout').click();
  cy.waitForStreamlit();
  // After logout, the login form should reappear
  cy.contains('🔐 Login').should('be.visible');
});


// ── Navigation commands ──────────────────────────────────────────────────────

/**
 * Navigate to a Streamlit page by its URL path.
 * Streamlit multi-page URLs use the filename without .py, underscores preserved.
 *
 * @param {string} pagePath  e.g. '/Admin_Dashboard', '/Tournament_Manager'
 */
Cypress.Commands.add('navigateTo', (pagePath) => {
  cy.visit(pagePath);
  cy.waitForStreamlit();
});

/**
 * Click a sidebar navigation button by its visible text.
 *
 * @param {string} buttonText  e.g. '🏆 Tournament Manager'
 */
Cypress.Commands.add('clickSidebarButton', (buttonText) => {
  cy.get('[data-testid="stSidebar"]')
    .contains('[data-testid="stButton"] button', buttonText)
    .click({ force: true });  // force bypasses CSS-collapsed sidebar (transform off-screen)
  cy.waitForStreamlit();
});

/**
 * Click an Admin Dashboard tab button by label.
 * The admin uses custom button-based tabs (not native st.tabs).
 *
 * @param {string} tabLabel  e.g. '👥 Users', '🏆 Tournaments'
 */
Cypress.Commands.add('clickAdminTab', (tabLabel) => {
  cy.contains('[data-testid="stButton"] button', tabLabel).click();
  cy.waitForStreamlit();
});


// ── Streamlit widget helpers ─────────────────────────────────────────────────

/**
 * Fill a Streamlit text input identified by its visible label.
 *
 * @param {string} label  Exact label text, e.g. 'Email'
 * @param {string} value  Text to type
 */
Cypress.Commands.add('fillInput', (label, value) => {
  cy.contains('[data-testid="stTextInput"] label', label)
    .parents('[data-testid="stTextInput"]')
    .find('input')
    .clear()
    .type(value, { delay: 20 });
});

/**
 * Assert that a Streamlit alert/toast matches expected text.
 *
 * @param {string|RegExp} text  Expected message content
 * @param {'success'|'error'|'warning'|'info'} type  Optional alert type
 */
Cypress.Commands.add('assertAlert', (text, type = null) => {
  const selector = type
    ? `[data-testid="stAlert"][data-baseweb="${type}"]`
    : '[data-testid="stAlert"]';
  cy.get(selector).should('contain.text', text);
});

/**
 * Assert a Streamlit metric value.
 *
 * @param {string} label  Metric label, e.g. 'Current Balance'
 * @param {string|RegExp} value  Expected value text or regex
 */
Cypress.Commands.add('assertMetric', (label, value) => {
  cy.contains('[data-testid="stMetric"]', label)
    .find('[data-testid="stMetricValue"]')
    .should(value instanceof RegExp ? 'match' : 'contain.text', value);
});


// ── API intercept helpers ────────────────────────────────────────────────────

/**
 * Stub the enrollment endpoint to return HTTP 409 Conflict.
 * Used in error-state tests to simulate a double-enrollment race.
 *
 * @param {string} apiUrl  Backend base URL from env
 */
Cypress.Commands.add('stub409Enrollment', (apiUrl) => {
  cy.intercept('POST', `${apiUrl}/api/v1/semester-enrollments/**`, {
    statusCode: 409,
    body: {
      detail: 'Enrollment conflict: user is already enrolled in this tournament.',
    },
  }).as('enrollConflict');
});

/**
 * Stub the login endpoint to return HTTP 401 Unauthorized.
 *
 * @param {string} apiUrl  Backend base URL from env
 */
Cypress.Commands.add('stub401Login', (apiUrl) => {
  cy.intercept('POST', `${apiUrl}/api/v1/auth/login`, {
    statusCode: 401,
    body: { detail: 'Incorrect email or password.' },
  }).as('loginFailed');
});


// ── Assertion helpers ────────────────────────────────────────────────────────

/**
 * Assert the current page URL includes the given path fragment.
 *
 * @param {string} fragment  e.g. 'Admin_Dashboard'
 */
Cypress.Commands.add('assertOnPage', (fragment) => {
  cy.url().should('include', fragment);
});

/**
 * Assert the user is authenticated.
 *
 * Streamlit's sidebar can be collapsed (off-screen) in headless Electron even
 * at 1440×900 — so we never assert sidebar *visibility*.  Instead we assert
 * that the Logout button exists somewhere in the DOM (it is only rendered in
 * authenticated state), which works regardless of sidebar collapsed/expanded.
 */
Cypress.Commands.add('assertAuthenticated', () => {
  // The sidebar element must be present (authenticated pages always mount it)
  cy.get('[data-testid="stSidebar"]').should('exist');
  // Logout button exists only when logged in — search whole page, not inside
  // sidebar, to avoid failing when sidebar is CSS-collapsed (translateX).
  cy.contains('[data-testid="stButton"] button', '🚪 Logout').should('exist');
});

/**
 * Assert that the login form is visible (user is NOT authenticated).
 */
Cypress.Commands.add('assertUnauthenticated', () => {
  cy.contains('[data-testid="stButton"] button', '🔐 Login').should('be.visible');
});
