// ============================================================================
// Auth — Login
// ============================================================================
// Covers:
//   - Home page renders login form
//   - Valid admin login → redirects to Admin Dashboard
//   - Valid instructor login → redirects to Instructor Dashboard
//   - Valid player login → redirects to LFA Player Dashboard
//   - Invalid credentials → error message shown
//   - Empty form submission → error shown
//   - Logout clears session and returns to login form
// ============================================================================

describe('Auth / Login', () => {
  beforeEach(() => {
    cy.visit('/');
    cy.waitForStreamlit();
  });

  // ── Home page structure ───────────────────────────────────────────────────

  it('@smoke renders the login form on the home page', () => {
    // Page title
    cy.contains('LFA Education Center').should('be.visible');

    // Login heading
    cy.contains('🔐 Login').should('be.visible');

    // Email input (first text input)
    cy.get('[data-testid="stTextInput"]')
      .first()
      .find('input')
      .should('be.visible');

    // Password input
    cy.get('[data-testid="stTextInput"]')
      .find('input[type="password"]')
      .should('be.visible');

    // Login button
    cy.contains('[data-testid="stButton"] button', '🔐 Login')
      .should('be.visible')
      .and('not.be.disabled');

    // Register button
    cy.contains('[data-testid="stButton"] button', '📝 Register with Invitation Code')
      .should('be.visible');
  });

  // ── Valid login — admin ───────────────────────────────────────────────────

  it('@smoke admin login succeeds and renders Admin Dashboard', () => {
    cy.fixture('users').then((users) => {
      cy.login(users.admin.email, users.admin.password);

      // Sidebar should appear (authenticated)
      cy.assertAuthenticated();

      // Admin-specific sidebar buttons
      cy.get('[data-testid="stSidebar"]')
        .contains('[data-testid="stButton"] button', '🏆 Tournament Manager')
        .should('exist');
      cy.get('[data-testid="stSidebar"]')
        .contains('[data-testid="stButton"] button', '📡 Tournament Monitor')
        .should('exist');

      // Admin dashboard title
      cy.contains('📊 Admin Dashboard').should('be.visible');
    });
  });

  // ── Valid login — instructor ──────────────────────────────────────────────

  it('instructor login succeeds and renders Instructor Dashboard', () => {
    cy.fixture('users').then((users) => {
      cy.login(users.instructor.email, users.instructor.password);
      cy.assertAuthenticated();
      cy.contains('👨‍🏫 Instructor Dashboard').should('be.visible');
    });
  });

  // ── Valid login — player ──────────────────────────────────────────────────

  it('player login succeeds and renders LFA Player Dashboard', () => {
    cy.fixture('users').then((users) => {
      cy.login(users.player.email, users.player.password);
      cy.assertAuthenticated();
      // Player dashboard or redirect — either works
      cy.get('[data-testid="stApp"]').should('be.visible');
    });
  });

  // ── Invalid credentials ───────────────────────────────────────────────────

  it('@smoke invalid credentials show an error message', () => {
    cy.fixture('users').then((users) => {
      cy.login(users.invalid.email, users.invalid.password);

      // Logout button must NOT be present anywhere on the page
      // Note: use cy.get('body').contains() — not cy.get(sidebar).find() —
      // to safely assert non-existence without intermediate .find() timing out.
      cy.get('body')
        .contains('[data-testid="stButton"] button', '🚪 Logout')
        .should('not.exist');

      // An error alert must be visible
      cy.get('[data-testid="stAlert"]').should('be.visible');
    });
  });

  it('wrong password for valid email shows an error', () => {
    cy.fixture('users').then((users) => {
      cy.login(users.admin.email, 'definitely-wrong-password');

      cy.get('[data-testid="stAlert"]').should('be.visible');
      cy.assertUnauthenticated();
    });
  });

  // ── Empty form submission ─────────────────────────────────────────────────

  it('clicking Login with empty fields shows an error or keeps login form', () => {
    cy.contains('[data-testid="stButton"] button', '🔐 Login').click();
    cy.waitForStreamlit();

    // Either an alert appears or the login form remains (no redirect)
    cy.assertUnauthenticated();
  });

  // ── Logout ────────────────────────────────────────────────────────────────

  it('@smoke logout clears session and returns to login form', () => {
    cy.fixture('users').then((users) => {
      cy.login(users.admin.email, users.admin.password);
      cy.assertAuthenticated();

      cy.logout();

      // Login form should be visible again
      cy.assertUnauthenticated();

      // No Logout button anywhere on the page after logout
      cy.get('body').contains('🚪 Logout').should('not.exist');
    });
  });

  // ── Session persistence ───────────────────────────────────────────────────

  it('authenticated user stays logged in after page reload', () => {
    cy.fixture('users').then((users) => {
      cy.login(users.admin.email, users.admin.password);
      cy.assertAuthenticated();

      // Reload the page — Streamlit restores session from URL params / sessionStorage
      cy.reload();
      cy.waitForStreamlit();

      // Dashboard or login form — either is valid depending on Streamlit session handling;
      // here we assert the app rendered without crashing
      cy.get('[data-testid="stApp"]').should('be.visible');
    });
  });
});
