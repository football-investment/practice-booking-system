// ============================================================================
// Player — Onboarding Flow
// ============================================================================
// Covers:
//   - Initial login as new player
//   - Welcome/onboarding message or wizard (if exists)
//   - Profile information display
//   - First credit balance check (initial allocation)
//   - Dashboard tabs accessibility
//   - Navigation to core features (Specialization Hub, Credits)
//   - Session preservation after onboarding
// ============================================================================

describe('Player / Onboarding Flow', () => {
  beforeEach(() => {
    cy.loginAsPlayer();
    // Session-safe: Player lands on Specialization_Hub or LFA_Player_Dashboard after login
    cy.url().should('match', /\/(Specialization_Hub|LFA_Player_Dashboard)/);
    cy.waitForStreamlit();  // Don't wait for tabs - player pages may not have them
  });

  // ── Initial Login & Landing Page ─────────────────────────────────────────

  it('@smoke player lands on dashboard or specialization hub after login', () => {
    // Either Specialization_Hub (default) or LFA_Player_Dashboard
    cy.url().should('match', /\/(Specialization_Hub|LFA_Player_Dashboard)/);
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('@smoke player sees welcome message or personalized content', () => {
    // Check for player name, welcome message, or onboarding content
    cy.get('[data-testid="stSidebar"]').should('be.visible');

    cy.get('body').then(($body) => {
      const hasWelcome = $body.text().includes('Welcome') ||
                         $body.text().includes('welcome');
      const hasPlayerName = $body.text().match(/Ruben|Dias|rdias/i);
      const hasOnboarding = $body.text().includes('Get Started') ||
                            $body.text().includes('onboard');

      expect(hasWelcome || hasPlayerName || hasOnboarding).to.be.true;
    });
  });

  // ── Profile Information ──────────────────────────────────────────────────

  it('player profile shows basic information (name, email, role)', () => {
    // Navigate to sidebar or profile section
    cy.get('[data-testid="stSidebar"]').should('be.visible');

    cy.get('body').then(($body) => {
      // Profile info can be in sidebar or main content
      const hasName = $body.text().match(/Ruben|Dias/i);
      const hasEmail = $body.text().includes('rdias@manchestercity.com');
      const hasRole = $body.text().match(/Player|Student/i);

      expect(hasName || hasEmail || hasRole).to.be.true;
    });
  });

  // ── Initial Credit Balance ───────────────────────────────────────────────

  it('@smoke player has initial credit balance visible', () => {
    // Navigate to Credits page via sidebar
    cy.clickSidebarButton(/💰 My Credits|💳 Credits/);
    cy.waitForStreamlit();

    // Credit balance should be visible
    cy.get('[data-testid="stMetric"]')
      .contains(/Balance|Egyenleg|Credit/)
      .should('exist');

    // Balance should be a number (initial allocation, could be 0 or positive)
    cy.get('[data-testid="stMetric"]')
      .first()
      .find('[data-testid="stMetricValue"]')
      .invoke('text')
      .should('match', /\d+/);
  });

  it('initial credit balance is non-negative (0 or positive)', () => {
    cy.clickSidebarButton(/💰 My Credits|💳 Credits/);
    cy.waitForStreamlit();

    cy.get('[data-testid="stMetric"]')
      .first()
      .find('[data-testid="stMetricValue"]')
      .invoke('text')
      .then((balanceText) => {
        const balance = parseInt(balanceText.replace(/[^\d]/g, ''), 10);
        expect(balance).to.be.gte(0);
      });
  });

  // ── Dashboard Tabs Accessibility ─────────────────────────────────────────

  it('player dashboard tabs are accessible after onboarding', () => {
    // Navigate to LFA_Player_Dashboard if not already there
    cy.url().then((url) => {
      if (!url.includes('LFA_Player_Dashboard')) {
        cy.clickSidebarButton(/Dashboard|Home/);
        cy.waitForStreamlit();
      }
    });

    // Check for dashboard tabs
    cy.get('body').then(($body) => {
      const hasTabs = $body.find('[data-testid="stTabs"]').length > 0;
      const hasTabContent = $body.find('[data-testid="stTab"]').length > 0;

      expect(hasTabs || hasTabContent).to.be.true;
    });
  });

  // ── Navigation to Core Features ──────────────────────────────────────────

  it('player can navigate to Specialization Hub from sidebar', () => {
    cy.clickSidebarButton(/Specialization Hub|Hub/);
    cy.waitForStreamlit();

    cy.url().should('include', '/Specialization_Hub');
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('player can navigate to Credits page from sidebar', () => {
    cy.clickSidebarButton(/💰 My Credits|💳 Credits/);
    cy.waitForStreamlit();

    cy.url().should('include', '/My_Credits');
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  // ── Session Preservation ─────────────────────────────────────────────────

  it('session is preserved after navigating through onboarding flow', () => {
    // Navigate: Dashboard → Specialization Hub → Credits → Dashboard
    cy.clickSidebarButton(/Specialization Hub|Hub/);
    cy.waitForStreamlit();
    cy.assertAuthenticated();

    cy.clickSidebarButton(/💰 My Credits|💳 Credits/);
    cy.waitForStreamlit();
    cy.assertAuthenticated();

    cy.clickSidebarButton(/Dashboard|Home/);
    cy.waitForStreamlit();
    cy.assertAuthenticated();

    // Final check: no session loss
    cy.get('body').should('not.contain.text', 'Not authenticated');
    cy.get('[data-testid="stSidebar"]').should('be.visible');
  });

  // ── Error-Free Onboarding ────────────────────────────────────────────────

  it('@smoke onboarding flow completes without Python errors', () => {
    // Navigate through core onboarding pages
    cy.clickSidebarButton(/Specialization Hub|Hub/);
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');

    cy.clickSidebarButton(/💰 My Credits|💳 Credits/);
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');

    cy.clickSidebarButton(/Dashboard|Home/);
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');
  });
});
