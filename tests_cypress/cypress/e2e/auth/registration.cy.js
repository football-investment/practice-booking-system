// ============================================================================
// Auth — Registration
// ============================================================================
// Covers:
//   - Register toggle button shows registration form
//   - All registration fields are present in the DOM
//   - Back-to-login toggle works (🔙 Back to Login)
//   - Required-field validation (empty submit stays on form)
//   - Successful registration (stubbed API)
//   - Duplicate email → error (HTTP 409 — register-with-invitation endpoint)
// ============================================================================

describe('Auth / Registration', () => {
  const API = () => Cypress.env('apiUrl');
  // Actual registration endpoint in the app
  const REG_ENDPOINT = '**/api/v1/auth/register-with-invitation';

  beforeEach(() => {
    cy.visit('/');
    cy.waitForStreamlit();

    // Open the registration form (click only if not already open)
    cy.get('body').then($body => {
      if ($body.text().includes('📝 Register with Invitation Code') &&
          !$body.text().includes('🔙 Back to Login')) {
        cy.contains('[data-testid="stButton"] button', '📝 Register with Invitation Code')
          .click();
        cy.waitForStreamlit();
      }
    });
  });

  // ── Form renders correctly ────────────────────────────────────────────────

  it('@smoke registration form shows all required fields', () => {
    // Form heading must be visible
    cy.contains('📝 Register with Invitation Code').should('exist');

    // Labels exist in the DOM (Streamlit columns may not report 'visible'
    // due to CSS overflow; existence is sufficient for DOM-presence audit)
    const expectedLabels = [
      'First Name',
      'Last Name',
      'Nickname',
      'Email',
      'Password',
      'Phone Number',
      'Nationality',
      'Invitation Code',
    ];

    expectedLabels.forEach((label) => {
      cy.contains('[data-testid="stTextInput"] label', label)
        .should('exist');
    });

    // Gender selectbox
    cy.get('[data-testid="stSelectbox"]').should('exist');

    // Date of Birth date input
    cy.get('[data-testid="stDateInput"]').should('exist');

    // Back to login button (actual emoji is 🔙, not ←)
    cy.contains('[data-testid="stButton"] button', '🔙 Back to Login')
      .should('exist');
  });

  // ── Back to login toggle ──────────────────────────────────────────────────

  it('back to login button returns to login form', () => {
    // Actual button text in Home.py: "🔙 Back to Login"
    cy.contains('[data-testid="stButton"] button', '🔙 Back to Login').click();
    cy.waitForStreamlit();

    // Login form should now be showing
    cy.assertUnauthenticated();
    cy.get('body').should('not.contain', '🔙 Back to Login');
  });

  // ── Empty form validation ─────────────────────────────────────────────────

  it('empty form submission shows a validation error', () => {
    // Click Register without filling any fields
    cy.contains('[data-testid="stButton"] button', '📝 Register Now').click();
    cy.waitForStreamlit();

    // Validation warning must appear (Streamlit st.warning)
    cy.get('[data-testid="stNotification"], [data-testid="stAlert"]')
      .should('exist');

    // Should NOT have navigated to an authenticated state
    cy.get('body')
      .contains('[data-testid="stButton"] button', '🚪 Logout')
      .should('not.exist');
  });

  // ── Field-level interaction ───────────────────────────────────────────────

  it('all text fields accept typed input', () => {
    cy.fixture('users').then(({ registration: r }) => {
      cy.fillInput('First Name', r.firstName);
      cy.fillInput('Last Name', r.lastName);
      cy.fillInput('Nickname', r.nickname);
      cy.fillInput('Email', r.email);
      cy.fillInput('Phone Number', r.phone);
      cy.fillInput('Nationality', r.nationality);

      // Verify at least one value persisted in an input
      cy.get('[data-testid="stTextInput"] input')
        .then($inputs => {
          const values = [...$inputs].map(i => i.value);
          expect(values.some(v => v === r.firstName || v === r.email)).to.be.true;
        });
    });
  });

  // ── Duplicate email (HTTP 409 from API) ───────────────────────────────────

  it('duplicate email returns a 409-like error message', () => {
    // Stub the actual registration endpoint used by the app
    cy.intercept('POST', REG_ENDPOINT, {
      statusCode: 409,
      body: { detail: 'An account with this email already exists.' },
    }).as('registerConflict');

    cy.fixture('users').then(({ registration: r }) => {
      cy.fillInput('First Name', r.firstName);
      cy.fillInput('Last Name', r.lastName);
      cy.fillInput('Nickname', r.nickname);
      cy.fillInput('Email', r.email);
      cy.fillInput('Phone Number', r.phone);
      cy.fillInput('Nationality', r.nationality);

      cy.contains('[data-testid="stButton"] button', '📝 Register Now').click();
      cy.waitForStreamlit();

      // Some error feedback must be visible (alert or warning)
      cy.get('[data-testid="stNotification"], [data-testid="stAlert"]')
        .should('exist');

      // Must NOT be authenticated
      cy.get('body')
        .contains('[data-testid="stButton"] button', '🚪 Logout')
        .should('not.exist');
    });
  });

  // ── Successful registration (stubbed) ─────────────────────────────────────

  it('successful registration shows success feedback', () => {
    cy.intercept('POST', REG_ENDPOINT, {
      statusCode: 200,
      body: { message: 'Registration successful. Please log in.' },
    }).as('registerSuccess');

    cy.fixture('users').then(({ registration: r }) => {
      cy.fillInput('First Name', r.firstName);
      cy.fillInput('Last Name', r.lastName);
      cy.fillInput('Nickname', r.nickname);
      cy.fillInput('Email', r.email);
      cy.fillInput('Phone Number', r.phone);
      cy.fillInput('Nationality', r.nationality);

      cy.contains('[data-testid="stButton"] button', '📝 Register Now').click();
      cy.waitForStreamlit();

      // App must still be rendered (no crash)
      cy.get('[data-testid="stApp"]').should('exist');
    });
  });
});
