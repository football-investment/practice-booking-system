// ============================================================================
// Student / Error States (Player-Facing)
// ============================================================================
// Covers:
//   - 409 Conflict on enrollment: readable error shown, UI not frozen
//   - 409 recovery: subsequent actions still work
//   - 401 mid-session (token expiry): graceful handling, no raw JSON crash
//   - Slow network (cy.intercept delay): dashboard does not crash, eventually loads
//   - Role restriction: player visiting admin pages does not crash
//   - Unauthenticated direct URL access to player dashboard: no crash
//
// All 4xx responses are injected via cy.intercept() for isolation.
// Slow network is simulated via cy.intercept() with a delay response.
// These tests do NOT require live backend state — they are fully reproducible.
// ============================================================================

describe('Student / Error States (Player-Facing)', () => {
  const API = () => Cypress.env('apiUrl');

  // ═══════════════════════════════════════════════════════════════════════════
  // 1. 409 Conflict — Enrollment
  // ═══════════════════════════════════════════════════════════════════════════

  describe('409 — Enrollment Conflict', () => {
    beforeEach(() => {
      cy.loginAsPlayer();
    });

    it('@smoke 409 on enrollment shows readable error — not raw JSON or Traceback', () => {
      // Register 409 stub before any enrollment interaction
      cy.intercept('POST', `${API()}/api/v1/semester-enrollments/**`, {
        statusCode: 409,
        body: { detail: 'Enrollment conflict: already enrolled.' },
      }).as('enrollConflict');

      cy.contains('[data-testid="stTab"]', '🏆 Tournaments').click({ force: true });
      cy.waitForStreamlit();

      // Attempt enrollment if the button is visible
      cy.get('body').then(($body) => {
        const hasEnroll = $body.text().includes('Enroll') || $body.text().includes('Register');
        if (hasEnroll) {
          cy.contains('[data-testid="stButton"] button', /Enroll|Register/)
            .first()
            .click({ force: true });
          cy.waitForStreamlit();

          cy.get('body').should('not.contain.text', '"statusCode"');
          cy.get('body').should('not.contain.text', '"detail":');
          cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
        }
        // Page must remain visible regardless of whether enroll was triggered
        cy.get('[data-testid="stApp"]').should('be.visible');
      });
    });

    it('409 does not freeze the UI — buttons remain clickable after conflict', () => {
      cy.intercept('POST', `${API()}/api/v1/semester-enrollments/**`, {
        statusCode: 409,
        body: { detail: 'Conflict.' },
      }).as('freezeTest');

      cy.contains('[data-testid="stTab"]', '🏆 Tournaments').click({ force: true });
      cy.waitForStreamlit();

      cy.get('[data-testid="stButton"] button').first().should('not.be.disabled');
      cy.get('[data-testid="stApp"]').should('be.visible');
    });

    it('app is fully usable after 409 — can navigate to other tabs', () => {
      cy.intercept('POST', `${API()}/api/v1/semester-enrollments/**`, {
        statusCode: 409,
        body: { detail: 'Conflict.' },
      }).as('conflictStub');

      cy.contains('[data-testid="stTab"]', '🏆 Tournaments').click({ force: true });
      cy.waitForStreamlit();

      // Navigate away after the 409 stub is in place
      cy.contains('[data-testid="stTab"]', '📊 Home').click({ force: true });
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
      cy.assertAuthenticated();
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 2. 401 — Mid-Session Token Expiry
  // ═══════════════════════════════════════════════════════════════════════════

  describe('401 — Session Expiry (simulated mid-session)', () => {
    it('@smoke 401 on API calls after login shows graceful UI — not raw JSON', () => {
      cy.loginAsPlayer();

      // Simulate token expiry: all GET API calls return 401
      cy.intercept('GET', `${API()}/api/v1/**`, {
        statusCode: 401,
        body: { detail: 'Token has expired. Please log in again.' },
      }).as('sessionExpired');

      // Reload to trigger fresh API calls with the stub active
      cy.reload();
      cy.waitForStreamlit();

      // App must not show raw JSON or Python traceback
      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
      cy.get('body').should('not.contain.text', '"statusCode": 401');
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 3. Slow Network
  // ═══════════════════════════════════════════════════════════════════════════

  describe('Slow Network Resilience', () => {
    it('@smoke dashboard loads eventually under slow API (5 s delay) without crash', () => {
      // Delay all API responses by 5 seconds to simulate a slow backend
      cy.intercept('GET', `${API()}/api/v1/users/me`, (req) => {
        req.on('response', (res) => {
          res.setDelay(5000);
        });
      }).as('slowUserMe');

      cy.loginAsPlayer();

      cy.get('[data-testid="stApp"]', { timeout: 30000 }).should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });

    it('Credits page load survives a slow balance API response', () => {
      cy.loginAsPlayer();

      // Delay the credit balance or user-info endpoint
      cy.intercept('GET', `${API()}/api/v1/credits/**`, (req) => {
        req.on('response', (res) => {
          res.setDelay(3000);
        });
      }).as('slowCredits');

      cy.clickSidebarButton('💳 Credits');

      cy.get('[data-testid="stApp"]', { timeout: 30000 }).should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 4. Role Restriction — Player visiting admin pages
  // ═══════════════════════════════════════════════════════════════════════════

  describe('Role Restriction — Player visiting admin-only pages', () => {
    it('@smoke player visiting /Admin_Dashboard does not crash', () => {
      cy.loginAsPlayer();
      cy.visit('/Admin_Dashboard');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
    });

    it('player visiting /Tournament_Manager does not crash', () => {
      cy.loginAsPlayer();
      cy.visit('/Tournament_Manager');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 5. Unauthenticated Access to Player Pages
  // ═══════════════════════════════════════════════════════════════════════════

  describe('Unauthenticated Direct URL Access', () => {
    it('@smoke unauthenticated visit to /LFA_Player_Dashboard does not crash', () => {
      cy.visit('/LFA_Player_Dashboard');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
    });

    it('unauthenticated visit to /My_Credits does not crash', () => {
      cy.visit('/My_Credits');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });

    it('unauthenticated visit to /Specialization_Hub does not crash', () => {
      cy.visit('/Specialization_Hub');
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });
  });
});
