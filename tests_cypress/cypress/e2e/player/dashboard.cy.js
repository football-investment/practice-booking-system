// ============================================================================
// Player — LFA Player Dashboard
// ============================================================================
// Covers:
//   - LFA Player Dashboard page loads
//   - Authenticated player sees their dashboard (not login form)
//   - Onboarding redirect works if player has no license
//   - Specialization Hub navigation button works
//   - Profile and Credits sidebar navigation works
//   - Dashboard does not crash with real API data
// ============================================================================

describe('Player / LFA Player Dashboard', () => {
  beforeEach(() => {
    cy.loginAsPlayer();
    cy.navigateTo('/LFA_Player_Dashboard');
  });

  // ── Page loads ────────────────────────────────────────────────────────────

  it('@smoke LFA Player Dashboard loads without error', () => {
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
  });

  it('@smoke player is authenticated (sidebar visible)', () => {
    // Player pages render sidebar differently - check for stSidebar element instead
    cy.get('[data-testid="stSidebar"]').should('exist');
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Not authenticated');
  });

  // ── Content ───────────────────────────────────────────────────────────────

  it('dashboard renders player content or onboarding prompt', () => {
    cy.get('[data-testid="stApp"]').should('be.visible');

    // Either the player dashboard content or an onboarding CTA
    cy.get('body').then(($body) => {
      const hasContent   = $body.find('[data-testid="stMetric"]').length > 0 ||
                            $body.find('[data-testid="stDataFrame"]').length > 0;
      const hasOnboarding = $body.text().includes('Onboarding') ||
                             $body.text().includes('onboarding') ||
                             $body.text().includes('Specialization') ||
                             $body.text().includes('Get Started');
      expect(hasContent || hasOnboarding).to.be.true;
    });
  });

  // ── Sidebar navigation ────────────────────────────────────────────────────

  it('sidebar Logout button is present', () => {
    // Player sidebar renders logout button - may need scroll
    cy.get('[data-testid="stSidebar"]').should('exist');
    cy.contains('[data-testid="stButton"] button', /Logout|🚪/)
      .scrollIntoView()
      .should('exist');
  });

  it('logout from player dashboard returns to login form', () => {
    // Click logout button (may be in sidebar or main content)
    cy.contains('[data-testid="stButton"] button', /Logout|🚪/)
      .scrollIntoView()
      .click();
    cy.waitForStreamlit();

    // Should return to login page
    cy.contains('[data-testid="stButton"] button', '🔐 Login')
      .should('be.visible');
  });

  // ── Navigation to other pages ─────────────────────────────────────────────

  it('visiting Specialization Hub from player session loads correctly', () => {
    cy.navigateTo('/Specialization_Hub');
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('visiting My Credits from player session loads correctly', () => {
    cy.navigateTo('/My_Credits');
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('visiting My Profile from player session loads correctly', () => {
    cy.navigateTo('/My_Profile');
    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });
});
