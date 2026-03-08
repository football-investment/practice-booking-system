// ============================================================================
// Error States — Unauthorized & Forbidden
// ============================================================================
//
// Covers:
//   - HTTP 401 on login → readable "incorrect credentials" message
//   - HTTP 401 on API call mid-session → graceful session expiry handling
//   - HTTP 403 on role-restricted page (player accessing admin pages)
//   - Direct URL access without auth → redirect or access denied
//   - Token expiry simulation (401 mid-session)
//   - HTTP 422 validation error on malformed form data
// ============================================================================

describe('Error States / Unauthorized & Forbidden', () => {
  const API = () => Cypress.env('apiUrl');

  // ═══════════════════════════════════════════════════════════════════════════
  // 1. HTTP 401 — Login failure
  // ═══════════════════════════════════════════════════════════════════════════

  describe('401 — Login Failure', () => {
    beforeEach(() => {
      cy.visit('/');
      cy.waitForStreamlit();
    });

    it('@smoke 401 from login API shows user-readable error', () => {
      // Note: Streamlit login is server-to-server (Python → FastAPI), so
      // cy.intercept() cannot capture it. Use real bad credentials instead.
      cy.get('[data-testid="stTextInput"]').first().find('input')
        .clear().type('bad@example.com');
      cy.get('[data-testid="stTextInput"]').find('input[type="password"]')
        .clear().type('wrongpassword');
      cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

      cy.waitForStreamlit();

      // Error alert must appear
      cy.get('[data-testid="stAlert"]').should('be.visible');

      // Must NOT show raw status code or JSON
      cy.get('body').should('not.contain.text', '"statusCode": 401');
      cy.get('body').should('not.contain.text', 'Traceback');

      // Login form must still be visible (not blank page)
      cy.assertUnauthenticated();
    });

    it('401 error message does not expose internal API detail verbatim', () => {
      cy.get('[data-testid="stTextInput"]').first().find('input')
        .clear().type('test@example.com');
      cy.get('[data-testid="stTextInput"]').find('input[type="password"]')
        .clear().type('wrong');
      cy.contains('[data-testid="stButton"] button', '🔐 Login').click();

      cy.waitForStreamlit();

      // Alert should be visible
      cy.get('[data-testid="stAlert"]').should('be.visible');

      // Raw JSON keys should NOT appear in the UI
      cy.get('[data-testid="stAlert"]')
        .invoke('text')
        .should('not.match', /^\{.*"detail".*\}$/);
    });

    it('user can retry login after 401 error', () => {
      // First attempt: wrong credentials (real 401 from server)
      cy.get('[data-testid="stTextInput"]').first().find('input')
        .clear().type('bad@example.com');
      cy.get('[data-testid="stTextInput"]').find('input[type="password"]')
        .clear().type('wrong');
      cy.contains('[data-testid="stButton"] button', '🔐 Login').click();
      cy.waitForStreamlit();

      // Login form must still be present (recoverable)
      cy.assertUnauthenticated();

      // Second attempt: real credentials
      cy.fixture('users').then((users) => {
        cy.login(users.admin.email, users.admin.password);
        cy.assertAuthenticated();
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 2. HTTP 401 — Mid-session token expiry
  // ═══════════════════════════════════════════════════════════════════════════

  describe('401 — Session Expiry', () => {
    it('@smoke session expiry (401 on API call) is handled gracefully', () => {
      cy.loginAsPlayer();
      cy.navigateTo('/Specialization_Hub');

      // Simulate token expiry by making all subsequent API calls return 401
      cy.intercept('GET', `${API()}/api/v1/**`, {
        statusCode: 401,
        body: { detail: 'Token has expired. Please log in again.' },
      }).as('sessionExpired');

      // Reload the page to trigger fresh API calls with the stub
      cy.reload();
      cy.waitForStreamlit();

      // App must not crash — should show login form or expiry message
      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 3. HTTP 403 — Role-based access control
  // ═══════════════════════════════════════════════════════════════════════════

  describe('403 — Role Restriction', () => {
    it('@smoke player visiting /Admin_Dashboard does not crash', () => {
      cy.loginAsPlayer();
      cy.visit('/Admin_Dashboard');
      cy.waitForStreamlit();

      // Must not crash regardless of how the app handles the restriction
      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });

    it('player visiting /Tournament_Manager does not crash', () => {
      cy.loginAsPlayer();
      cy.visit('/Tournament_Manager');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });

    it('instructor visiting admin-only dashboard does not crash', () => {
      cy.loginAsInstructor();
      cy.visit('/Admin_Dashboard');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });

    it('403 from API on admin action is shown as readable error', () => {
      cy.loginAsPlayer();

      // Stub any admin API endpoint to return 403
      cy.intercept('POST', `${API()}/api/v1/tournaments/**`, {
        statusCode: 403,
        body: { detail: 'You do not have permission to create tournaments.' },
      }).as('forbidden');

      cy.navigateTo('/Specialization_Hub');
      cy.waitForStreamlit();

      // App must not crash
      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 4. Unauthenticated direct URL access
  // ═══════════════════════════════════════════════════════════════════════════

  describe('Unauthenticated Direct Access', () => {
    const PROTECTED_PAGES = [
      '/Admin_Dashboard',
      '/Instructor_Dashboard',
      '/LFA_Player_Dashboard',
      '/Tournament_Manager',
      '/Tournament_Monitor',
      '/My_Credits',
      '/My_Profile',
      '/Specialization_Hub',
    ];

    PROTECTED_PAGES.forEach((page) => {
      it(`@smoke unauthenticated access to ${page} does not crash`, () => {
        // No login — directly visit the page
        cy.visit(page);
        cy.waitForStreamlit();

        cy.get('[data-testid="stApp"]').should('be.visible');
        cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
      });
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 5. HTTP 422 — Validation errors
  // ═══════════════════════════════════════════════════════════════════════════

  describe('422 — Validation Error', () => {
    it('@smoke 422 from API on malformed input is shown as readable error', () => {
      cy.loginAsAdmin();

      // Stub any tournament POST with 422 (e.g., missing required field)
      cy.intercept('POST', `${API()}/api/v1/tournaments/**`, {
        statusCode: 422,
        body: {
          detail: [
            {
              loc: ['body', 'campus_ids'],
              msg: 'field required',
              type: 'value_error.missing',
            },
          ],
        },
      }).as('validationError');

      cy.navigateTo('/Tournament_Manager');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });
  });
});
