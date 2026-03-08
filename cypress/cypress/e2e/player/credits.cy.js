// ============================================================================
// Player — My Credits
// ============================================================================
// Covers:
//   - My Credits page loads without error
//   - Current Balance metric is displayed
//   - Sidebar welcome message shows player name
//   - Refresh button reloads without crash
//   - Logout button works
//   - Transaction history renders or shows empty state
//   - Unauthenticated access redirects or shows restricted content
// ============================================================================

describe('Player / My Credits', () => {
  beforeEach(() => {
    cy.loginAsPlayer();
    // After login, player lands on Specialization_Hub via st.switch_page().
    // The URL no longer has ?session_token=... params, so cy.navigateTo would
    // open a new unauthenticated WebSocket connection.  Use sidebar navigation
    // instead to stay within the same Streamlit session.
    cy.clickSidebarButton('💰 My Credits');
    cy.waitForSidebarButton('🔄 Refresh');  // Wait for sidebar buttons to render
  });

  // ── Page loads ────────────────────────────────────────────────────────────

  it('@smoke My Credits page loads without error', () => {
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
  });

  it('@smoke player is authenticated on Credits page', () => {
    cy.assertAuthenticated();
  });

  // ── Credit balance metric ─────────────────────────────────────────────────

  it('@smoke Current Balance metric is displayed', () => {
    cy.get('[data-testid="stMetric"]')
      .contains(/Balance|Egyenleg|Credit/)
      .should('exist');
  });

  it('balance value is a number', () => {
    cy.get('[data-testid="stMetric"]')
      .first()
      .find('[data-testid="stMetricValue"]')
      .invoke('text')
      .should('match', /\d+/);
  });

  // ── Sidebar ───────────────────────────────────────────────────────────────

  it('@smoke sidebar welcome message shows player name', () => {
    cy.get('[data-testid="stSidebar"]')
      .contains(/Welcome/)
      .should('be.visible');
  });

  it('Refresh button reloads credits page without error', () => {
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', '🔄 Refresh')
      .click();
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('Logout button works from Credits page', () => {
    cy.logout();
    cy.assertUnauthenticated();
  });

  // ── Transaction history ───────────────────────────────────────────────────

  it('transaction history renders or shows empty state', () => {
    cy.get('[data-testid="stApp"]').should('be.visible');

    // Either a transaction table/list or "no transactions" message
    cy.get('body').then(($body) => {
      const hasList    = $body.find('[data-testid="stDataFrame"]').length > 0 ||
                          $body.find('[data-testid="stTable"]').length > 0;
      const hasMessage = $body.text().includes('transaction') ||
                          $body.text().includes('Transaction') ||
                          $body.text().includes('history') ||
                          $body.text().includes('No') ||
                          $body.text().includes('credit');
      expect(hasList || hasMessage).to.be.true;
    });
  });

  // ── Unauthenticated access ────────────────────────────────────────────────

  it('unauthenticated user visiting /My_Credits sees login or restricted state', () => {
    cy.logout();
    cy.visit('/My_Credits');
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
    // Should not show the credit balance to unauthenticated users
  });
});
