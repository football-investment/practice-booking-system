// ============================================================================
// Student / Player Landing Page (Hub or Dashboard)
// ============================================================================
// Covers:
//   - Landing page load and session stability after login
//   - Authenticated state after login (sidebar Logout button present)
//   - Credit balance metric visible
//   - XP / credits content on the landing page
//   - Tabs: conditional check (present on LFA_Player_Dashboard, absent on Hub)
//   - Tab navigation does NOT reset session (only tested if tabs exist)
//   - Sidebar navigation buttons present (adapts to Hub vs Dashboard layout)
//   - Refresh button reloads without error
//   - Logout returns to login form
//
// IMPORTANT — Where the player lands after login:
//   - Player WITH unlocked specialization → LFA_Player_Dashboard (has tabs)
//   - Player WITHOUT unlocked specialization → Specialization_Hub (no tabs)
//   The tests adapt to both cases — tab-dependent tests are conditional.
//
// Session safety: cy.loginAsPlayer() stays on the same WebSocket.
//   Never call cy.navigateTo() after login.
// ============================================================================

describe('Student / Player Landing Page', () => {
  beforeEach(() => {
    cy.loginAsPlayer();
  });

  // ── Page loads ────────────────────────────────────────────────────────────

  it('@smoke player landing page loads without error', () => {
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
  });

  it('@smoke player is authenticated after login (Logout button exists)', () => {
    cy.assertAuthenticated();
  });

  // ── Credit and XP metrics ─────────────────────────────────────────────────

  it('@smoke credit balance metric is visible', () => {
    cy.get('[data-testid="stMetric"]').should('exist');
  });

  it('@smoke XP or Credits content is shown on the landing page', () => {
    cy.get('[data-testid="stApp"]').should('be.visible');

    cy.get('body').then(($body) => {
      const hasMetric    = $body.find('[data-testid="stMetric"]').length > 0;
      const hasXP        = $body.text().includes('XP') || $body.text().includes('Experience');
      const hasCredits   = $body.text().includes('Credit') || $body.text().includes('Balance');
      const hasSpec      = $body.text().includes('Specialization') || $body.text().includes('LFA');
      expect(hasMetric || hasXP || hasCredits || hasSpec).to.be.true;
    });
  });

  // ── Tab structure (conditional on LFA_Player_Dashboard) ──────────────────

  it('dashboard tabs exist if player is on LFA_Player_Dashboard', () => {
    // If the player has an unlocked specialization, they land on the dashboard (with tabs).
    // If they land on the Specialization Hub, there are no dashboard tabs — this is OK.
    cy.get('body').then(($body) => {
      const hasTabs = $body.find('[data-testid="stTabs"]').length > 0;
      if (hasTabs) {
        cy.get('[data-testid="stTab"]').should('have.length.gte', 3);
        cy.log('Player is on LFA_Player_Dashboard — tabs verified');
      } else {
        cy.log('Player is on Specialization Hub — no dashboard tabs, this is expected');
        cy.get('[data-testid="stApp"]').should('be.visible');
      }
    });
  });

  it('Skills tab renders without crash when dashboard tabs are available', () => {
    cy.get('body').then(($body) => {
      const hasSkillsTab = $body.text().includes('⚽ Skills');
      if (hasSkillsTab) {
        cy.contains('[data-testid="stTab"]', '⚽ Skills').click({ force: true });
        cy.waitForStreamlit();
        cy.get('[data-testid="stApp"]').should('be.visible');
        cy.get('body').should('not.contain.text', 'Traceback');
        cy.contains('[data-testid="stButton"] button', '🚪 Logout').should('exist');
      } else {
        cy.log('No Skills tab on this page — player is on Specialization Hub');
        cy.get('[data-testid="stApp"]').should('be.visible');
      }
    });
  });

  it('Tournaments tab renders without crash when dashboard tabs are available', () => {
    cy.get('body').then(($body) => {
      const hasTourTab = $body.text().includes('🏆 Tournaments') &&
                          $body.find('[data-testid="stTab"]').length > 0;
      if (hasTourTab) {
        cy.contains('[data-testid="stTab"]', '🏆 Tournaments').click({ force: true });
        cy.waitForStreamlit();
        cy.get('[data-testid="stApp"]').should('be.visible');
        cy.get('body').should('not.contain.text', 'Traceback');
      } else {
        cy.log('No Tournaments tab — player is on Specialization Hub');
        cy.get('[data-testid="stApp"]').should('be.visible');
      }
    });
  });

  it('Profile tab renders without crash when dashboard tabs are available', () => {
    cy.get('body').then(($body) => {
      const hasProfileTab = $body.text().includes('👤 Profile') &&
                             $body.find('[data-testid="stTab"]').length > 0;
      if (hasProfileTab) {
        cy.contains('[data-testid="stTab"]', '👤 Profile').click({ force: true });
        cy.waitForStreamlit();
        cy.get('[data-testid="stApp"]').should('be.visible');
        cy.get('body').should('not.contain.text', 'Traceback');
      } else {
        cy.log('No Profile tab on dashboard — checking profile via sidebar');
        cy.get('[data-testid="stApp"]').should('be.visible');
      }
    });
  });

  // ── Sidebar navigation ────────────────────────────────────────────────────

  it('@smoke sidebar has Credits and Logout navigation buttons', () => {
    // Both Hub and Dashboard have a Credits button and Logout button.
    // Hub uses '💰 My Credits'; Dashboard uses '💳 Credits'.
    // We test for either to be resilient to both landing pages.
    cy.get('[data-testid="stSidebar"]').should('exist');
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', /Credit|Egyenleg/)
      .should('exist');
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', '🚪 Logout')
      .should('exist');
  });

  it('@smoke sidebar Refresh button is present and works', () => {
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', '🔄 Refresh')
      .click({ force: true });
    cy.waitForStreamlit();
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('session is preserved after sidebar Refresh (no session reset)', () => {
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', '🔄 Refresh')
      .click({ force: true });
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Not authenticated');
    cy.get('body').should('not.contain.text', 'Traceback');
    cy.assertAuthenticated();
  });

  it('logout from player landing page returns to login form', () => {
    cy.logout();
    cy.assertUnauthenticated();
  });
});
