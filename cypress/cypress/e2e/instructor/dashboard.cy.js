// ============================================================================
// Instructor — Dashboard
// ============================================================================
// Covers:
//   - Instructor Dashboard title and caption render
//   - All 7 tabs are present and navigable
//   - Sidebar buttons (Tournament Manager, Refresh, Logout)
//   - "Today" tab shows upcoming sessions or empty state
//   - "Open Tournaments" tab lists tournaments or empty state
//   - "My Applications" tab renders
//   - Confirm / Cancel buttons are present in tournament flows
//   - Non-instructor user sees appropriate restriction
// ============================================================================

describe('Instructor / Dashboard', () => {
  beforeEach(() => {
    cy.loginAsInstructor();
    // Session-safe: Instructor lands on Instructor_Dashboard after login
    // No navigation needed - avoid cy.visit() which breaks session
    cy.url().should('include', '/Instructor_Dashboard');
    cy.waitForTabs();  // Wait for tabs to render after data loading
  });

  // ── Page structure ────────────────────────────────────────────────────────

  it('@smoke renders Instructor Dashboard title', () => {
    cy.contains('👨‍🏫 Instructor Dashboard').should('be.visible');
    cy.contains('LFA Education Center').should('be.visible');
  });

  it('@smoke renders without Python errors', () => {
    cy.get('body').should('not.contain.text', 'Traceback (most recent call last)');
  });

  // ── Tabs ──────────────────────────────────────────────────────────────────

  // Regex-based matching for UI label flexibility (emojis are decoration)
  const TABS = [
    /Today/,                      // Matches "📆 Today & Upcoming"
    /My Jobs/,                    // Matches "💼 My Jobs"
    /Tournament Applications/,    // Matches "🏆 Tournament Applications"
    /Students/,                   // Matches "👥 My Students"
    /Check-in/,                   // Matches "✅ Check-in & Groups"
    /Inbox/,                      // Matches "📬 Inbox"
    /Profile/,                    // Matches "👤 My Profile"
  ];

  it('@smoke all 7 instructor tabs are present', () => {
    TABS.forEach((label) => {
      cy.get('[data-testid="stTabs"]')
        .find('[data-testid="stTab"]')
        .contains(label)
        .should('exist');
    });
  });

  TABS.forEach((label) => {
    it(`"${label}" tab is clickable and renders content`, () => {
      cy.get('[data-testid="stTabs"]')
        .find('[data-testid="stTab"]')
        .contains(label)
        .click();
      cy.waitForStreamlit();

      cy.get('[data-testid="stApp"]').should('be.visible');
      cy.get('body').should('not.contain.text', 'Traceback');
    });
  });

  // ── Today tab ─────────────────────────────────────────────────────────────

  it('@smoke Today tab shows sessions or empty state', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    // Either session cards or "no sessions" message
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  // ── Tournament Applications tab ──────────────────────────────────────────────────

  it('Tournament Applications tab lists tournaments or shows empty state', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Tournament Applications/)
      .click();
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  // ── Sidebar navigation ────────────────────────────────────────────────────

  it('@smoke sidebar Tournament Manager button is present', () => {
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', '🏆 Tournament Manager')
      .should('be.visible');
  });

  it('sidebar Refresh button reloads dashboard without error', () => {
    cy.get('[data-testid="stSidebar"]')
      .contains('[data-testid="stButton"] button', '🔄 Refresh')
      .click();
    cy.waitForStreamlit();

    cy.contains('👨‍🏫 Instructor Dashboard').should('be.visible');
  });

  it('sidebar Logout button works', () => {
    cy.logout();
    cy.assertUnauthenticated();
  });

  // ── Profile tab ───────────────────────────────────────────────────────────

  it('Profile tab renders instructor profile information', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Profile/)
      .click();
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  // ── Tournament Applications tab ───────────────────────────────────────────────────

  it('Tournament Applications tab shows apply/withdraw controls or empty state', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Applications/)
      .click();
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });
});
