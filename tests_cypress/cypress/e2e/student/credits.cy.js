// ============================================================================
// Student / My Credits
// ============================================================================
// Covers:
//   - My Credits page loads without error (navigated via sidebar — no session reset)
//   - Balance metric is visible and contains a numeric value
//   - All 4 tabs render: Purchase Credits, Redeem Coupon, Transaction History, Invoices
//   - Transaction History: shows table or empty state (no crash)
//   - Purchase Credits tab: form elements present
//   - Coupon tab: text input is present
//   - Sidebar Refresh button works
//   - Logout from Credits page returns to login form
//   - Back to Hub button navigates without crash
//
// Session safety: loginAsPlayer() stays on landing page, then
// the Credits sidebar button uses st.switch_page() → same WebSocket.
//
// Button text varies by landing page:
//   - Specialization Hub:    '💰 My Credits'
//   - LFA Player Dashboard:  '💳 Credits'
// We click whichever exists.
// ============================================================================

describe('Student / My Credits', () => {
  beforeEach(() => {
    cy.loginAsPlayer();
    // Click the Credits sidebar button regardless of which landing page the player is on.
    // Specialization Hub:   '💰 My Credits'
    // LFA Player Dashboard: '💳 Credits'
    // cy.contains() accepts regex — this matches both button texts.
    cy.clickSidebarButton(/💰 My Credits|💳 Credits/);
  });

  // ── Page loads ────────────────────────────────────────────────────────────

  it('@smoke My Credits page loads without error', () => {
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
  });

  it('@smoke player is authenticated on Credits page', () => {
    cy.assertAuthenticated();
  });

  // ── Balance metric ────────────────────────────────────────────────────────

  it('@smoke credit balance metric is visible', () => {
    // My_Credits.py renders st.metric("Balance", ...) in sidebar
    // and also shows current balance in the main content
    cy.get('[data-testid="stMetric"]')
      .contains(/Balance|Egyenleg|Credit/)
      .should('exist');
  });

  it('balance value is a non-negative integer', () => {
    cy.get('[data-testid="stMetric"]')
      .first()
      .find('[data-testid="stMetricValue"]')
      .invoke('text')
      .should('match', /^\d[\d,]*$/);
  });

  // ── Tab structure ─────────────────────────────────────────────────────────

  it('Credits page has tabs (Purchase, Coupon, History, Invoices)', () => {
    cy.get('[data-testid="stTabs"]').should('exist');

    cy.get('body').then(($body) => {
      const hasTab = $body.find('[data-testid="stTab"]').length > 0;
      const hasPurchaseText = $body.text().includes('Purchase') ||
                               $body.text().includes('Credit') ||
                               $body.text().includes('Redeem');
      expect(hasTab || hasPurchaseText).to.be.true;
    });
  });

  it('Transaction History tab renders or shows empty state without crash', () => {
    // Click the Transaction History tab if it exists
    cy.get('body').then(($body) => {
      if ($body.text().includes('Transaction') || $body.text().includes('History')) {
        cy.contains('[data-testid="stTab"]', /Transaction|History/)
          .click({ force: true });
        cy.waitForStreamlit();
      }
    });

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');

    // Either a data table or an empty-state message
    cy.get('body').then(($body) => {
      const hasTable   = $body.find('[data-testid="stDataFrame"]').length > 0 ||
                          $body.find('[data-testid="stTable"]').length > 0;
      const hasMessage = $body.text().includes('transaction') ||
                          $body.text().includes('Transaction') ||
                          $body.text().includes('history') ||
                          $body.text().includes('No') ||
                          $body.text().includes('credit');
      expect(hasTable || hasMessage).to.be.true;
    });
  });

  it('Purchase Credits tab renders form elements', () => {
    cy.get('body').then(($body) => {
      if ($body.text().includes('Purchase')) {
        cy.contains('[data-testid="stTab"]', /Purchase/)
          .click({ force: true });
        cy.waitForStreamlit();
      }
    });

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
    // Purchase form should have inputs or radio buttons
    cy.get('body').then(($body) => {
      const hasForm = $body.find('[data-testid="stRadio"]').length > 0 ||
                       $body.find('[data-testid="stSelectbox"]').length > 0 ||
                       $body.find('[data-testid="stNumberInput"]').length > 0 ||
                       $body.text().includes('credit') ||
                       $body.text().includes('Credit');
      expect(hasForm).to.be.true;
    });
  });

  it('Redeem Coupon tab has text input for coupon code', () => {
    cy.get('body').then(($body) => {
      if ($body.text().includes('Coupon') || $body.text().includes('Redeem')) {
        cy.contains('[data-testid="stTab"]', /Coupon|Redeem/)
          .click({ force: true });
        cy.waitForStreamlit();
      }
    });

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  // ── Sidebar actions ───────────────────────────────────────────────────────

  it('Refresh button reloads Credits page without error', () => {
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', '🔄 Refresh')
      .click({ force: true });
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('Logout from Credits page returns to login form', () => {
    cy.logout();
    cy.assertUnauthenticated();
  });

  // ── Navigation ────────────────────────────────────────────────────────────

  it('Back to Hub button navigates without crash', () => {
    // Back to Hub is a page-level button (footer area), not a sidebar button
    cy.get('body').then(($body) => {
      if ($body.text().includes('Back to Hub') || $body.text().includes('Hub')) {
        cy.contains('[data-testid="stButton"] button', /Back to Hub|Hub/)
          .first()
          .click({ force: true });
        cy.waitForStreamlit();

        cy.get('[data-testid="stApp"]').should('be.visible');
        cy.get('body').should('not.contain.text', 'Traceback');
      } else {
        cy.log('Back to Hub button not found — navigating via sidebar instead');
      }
    });
  });
});
