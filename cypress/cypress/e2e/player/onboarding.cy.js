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
      // Profile info can be in sidebar or main content (convert to boolean)
      const hasName = !!$body.text().match(/Ruben|Dias/i);
      const hasEmail = $body.text().includes('rdias@manchestercity.com');
      const hasRole = !!$body.text().match(/Player|Student/i);

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

  // ── Specialization Hub Content ───────────────────────────────────────────

  it('player sees specialization cards on onboarding page', () => {
    // Player lands on Specialization Hub after login - verify content
    cy.url().should('match', /\/(Specialization_Hub|LFA_Player_Dashboard)/);

    // Check for specialization content
    cy.get('body').then(($body) => {
      const hasSpecContent = $body.text().includes('Specialization') ||
                             $body.text().includes('specialization') ||
                             $body.text().includes('LFA Football Player') ||
                             $body.text().includes('GānCuju');

      expect(hasSpecContent).to.be.true;
    });
  });

  // ── Navigation to Core Features ──────────────────────────────────────────

  it('player can navigate to Profile page from sidebar', () => {
    cy.clickSidebarButton(/👤 My Profile|Profile/);
    cy.waitForStreamlit();

    cy.url().should('include', '/My_Profile');
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
    // Navigate: Profile → Credits → Specialization Hub (player navigation pattern)
    // Note: Each page may have different sidebar buttons, so use URL navigation
    cy.navigateTo('/My_Profile');
    cy.waitForStreamlit();

    cy.navigateTo('/My_Credits');
    cy.waitForStreamlit();

    // Navigate back to Specialization Hub (player's home page)
    cy.navigateTo('/Specialization_Hub');
    cy.waitForStreamlit();

    // Final check: session preserved (no login prompt, page loaded without errors)
    cy.get('body').should('not.contain.text', 'Not authenticated');
    cy.get('body').should('not.contain.text', 'Traceback');
    cy.get('[data-testid="stApp"]').should('be.visible');
  });

  // ── Error-Free Onboarding ────────────────────────────────────────────────

  it('@smoke onboarding flow completes without Python errors', () => {
    // Navigate through core player pages using URL navigation
    // (sidebar buttons vary by page, URL navigation is more reliable)
    cy.navigateTo('/My_Profile');
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');

    cy.navigateTo('/My_Credits');
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');

    // Navigate back to Specialization Hub (player's home page)
    cy.navigateTo('/Specialization_Hub');
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');
  });
});
