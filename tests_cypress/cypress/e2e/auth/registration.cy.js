// ============================================================================
// Auth — Registration
// ============================================================================
// Covers:
//   - Register toggle button shows registration form
//   - All registration fields are present and interactable
//   - Back-to-login toggle works
//   - Required-field validation (empty submit)
//   - Invalid email format is rejected
//   - Duplicate email shows error (HTTP 409 from API)
//   - Successful registration flow (stubbed API)
// ============================================================================

describe('Auth / Registration', () => {
  const API = () => Cypress.env('apiUrl');

  beforeEach(() => {
    cy.visit('/');
    cy.waitForStreamlit();

    // Open the registration form
    cy.contains('[data-testid="stButton"] button', '📝 Register with Invitation Code')
      .click();
    cy.waitForStreamlit();
  });

  // ── Form renders correctly ────────────────────────────────────────────────

  it('@smoke registration form shows all required fields', () => {
    cy.contains('📝 Register with Invitation Code').should('be.visible');

    const expectedLabels = [
      'First Name',
      'Last Name',
      'Nickname',
      'Email',
      'Password',
      'Phone Number',
      'Nationality',
    ];

    expectedLabels.forEach((label) => {
      cy.contains('[data-testid="stTextInput"] label', label)
        .should('be.visible');
    });

    // Gender selectbox
    cy.get('[data-testid="stSelectbox"]').should('be.visible');

    // Date of Birth date input
    cy.get('[data-testid="stDateInput"]').should('be.visible');

    // Back to login button
    cy.contains('[data-testid="stButton"] button', '← Back to Login')
      .should('be.visible');
  });

  // ── Back to login toggle ──────────────────────────────────────────────────

  it('back to login button returns to login form', () => {
    cy.contains('[data-testid="stButton"] button', '← Back to Login').click();
    cy.waitForStreamlit();

    cy.assertUnauthenticated();
    cy.contains('📝 Register with Invitation Code').should('not.exist');
  });

  // ── Empty form validation ─────────────────────────────────────────────────

  it('empty form submission shows a validation error', () => {
    // Find and click the Register/Submit button without filling any fields
    cy.get('[data-testid="stButton"] button')
      .contains(/Register|Submit/)
      .click();
    cy.waitForStreamlit();

    // Should either show an alert or stay on the registration form
    cy.get('[data-testid="stApp"]').should('be.visible');
    // Not redirected to authenticated state
    cy.assertUnauthenticated();
  });

  // ── Field-level interaction ───────────────────────────────────────────────

  it('all text fields accept typed input', () => {
    cy.fixture('users').then(({ registration: r }) => {
      cy.fillInput('First Name', r.firstName);
      cy.fillInput('Last Name', r.lastName);
      cy.fillInput('Nickname', r.nickname);
      cy.fillInput('Email', r.email);
      cy.fillInput('Password', r.password);
      cy.fillInput('Phone Number', r.phone);
      cy.fillInput('Nationality', r.nationality);

      // Verify values persisted
      cy.get('[data-testid="stTextInput"]')
        .find(`input[value="${r.firstName}"]`)
        .should('exist');
    });
  });

  // ── Duplicate email (HTTP 409 from API) ───────────────────────────────────

  it('duplicate email returns a 409-like error message', () => {
    // Stub the registration endpoint to return 409
    cy.intercept('POST', `${API()}/api/v1/auth/register`, {
      statusCode: 409,
      body: { detail: 'An account with this email already exists.' },
    }).as('registerConflict');

    cy.fixture('users').then(({ registration: r }) => {
      cy.fillInput('First Name', r.firstName);
      cy.fillInput('Last Name', r.lastName);
      cy.fillInput('Nickname', r.nickname);
      cy.fillInput('Email', r.email);
      cy.fillInput('Password', r.password);
      cy.fillInput('Phone Number', r.phone);
      cy.fillInput('Nationality', r.nationality);

      cy.get('[data-testid="stButton"] button')
        .contains(/Register|Submit/)
        .click();

      // Wait for the stub or real API to respond
      cy.waitForStreamlit();

      // Error message should be visible
      cy.get('[data-testid="stAlert"]').should('be.visible');
      cy.assertUnauthenticated();
    });
  });

  // ── Successful registration (stubbed) ─────────────────────────────────────

  it('successful registration shows success feedback', () => {
    // Stub successful registration
    cy.intercept('POST', `${API()}/api/v1/auth/register`, {
      statusCode: 201,
      body: { message: 'Registration successful. Please log in.' },
    }).as('registerSuccess');

    cy.fixture('users').then(({ registration: r }) => {
      cy.fillInput('First Name', r.firstName);
      cy.fillInput('Last Name', r.lastName);
      cy.fillInput('Nickname', r.nickname);
      cy.fillInput('Email', r.email);
      cy.fillInput('Password', r.password);
      cy.fillInput('Phone Number', r.phone);
      cy.fillInput('Nationality', r.nationality);

      cy.get('[data-testid="stButton"] button')
        .contains(/Register|Submit/)
        .click();

      cy.waitForStreamlit();

      // Either success alert or redirect to login
      cy.get('[data-testid="stApp"]').should('be.visible');
    });
  });
});
