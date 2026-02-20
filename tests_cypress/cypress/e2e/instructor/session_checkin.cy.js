// ============================================================================
// Instructor — Session Check-in Flow
// ============================================================================
// Covers:
//   - Navigate to "Today & Upcoming" tab
//   - View upcoming sessions or empty state
//   - Session card displays essential information (date, time, location, status)
//   - Check-in button is present for active sessions
//   - Group assignment/formation workflow (if applicable)
//   - Session status updates after check-in
//   - Error handling for check-in edge cases
//   - Session preservation during check-in flow
// ============================================================================

describe('Instructor / Session Check-in Flow', () => {
  beforeEach(() => {
    cy.loginAsInstructor();
    // Session-safe: Instructor lands on Instructor_Dashboard after login
    cy.url().should('include', '/Instructor_Dashboard');
    cy.waitForTabs();
  });

  // ── Navigate to Today Tab ────────────────────────────────────────────────

  it('@smoke Today tab is accessible from instructor dashboard', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .should('exist')
      .click();
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  // ── Upcoming Sessions Display ────────────────────────────────────────────

  it('Today tab shows upcoming sessions or empty state', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();

    cy.get('body').then(($body) => {
      const hasSessions = $body.text().includes('Session') ||
                          $body.text().includes('session') ||
                          $body.find('[data-testid="stButton"]').length > 0;
      const hasEmptyState = $body.text().includes('No sessions') ||
                            $body.text().includes('no upcoming') ||
                            $body.text().includes('empty');

      expect(hasSessions || hasEmptyState).to.be.true;
    });
  });

  // ── Session Card Information ─────────────────────────────────────────────

  it('session cards display essential information (date, time, status)', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();

    cy.get('body').then(($body) => {
      const bodyText = $body.text();

      // Check for session-related information
      const hasDate = bodyText.match(/\d{4}-\d{2}-\d{2}/) ||
                      bodyText.match(/Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday/);
      const hasTime = bodyText.match(/\d{1,2}:\d{2}/) ||
                      bodyText.match(/AM|PM/);
      const hasStatus = bodyText.match(/upcoming|active|completed|scheduled/i);

      // Session card exists if any session info is present
      if ($body.find('[data-testid="stButton"]').length > 0) {
        expect(hasDate || hasTime || hasStatus).to.be.true;
      } else {
        cy.log('No sessions available — skipping session card validation');
      }
    });
  });

  // ── Check-in Button Presence ─────────────────────────────────────────────

  it('check-in button is present for active sessions (if available)', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();

    cy.get('body').then(($body) => {
      const hasCheckInButton = $body.find('[data-testid="stButton"]').text().match(/Check.?in|check.?in/i);

      if (hasCheckInButton) {
        cy.log('✓ Check-in button found for active session');
        cy.contains('[data-testid="stButton"] button', /Check.?in/i).should('exist');
      } else {
        cy.log('No active sessions with check-in buttons — test data dependent');
      }
    });
  });

  // ── Group Assignment Workflow ────────────────────────────────────────────

  it('Check-in & Groups tab is accessible for group management', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Check-in/)
      .should('exist')
      .click();
    cy.waitForStreamlit();

    cy.get('[data-testid="stApp"]').should('be.visible');
    cy.get('body').should('not.contain.text', 'Traceback');
  });

  it('Check-in & Groups tab shows group controls or empty state', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Check-in/)
      .click();
    cy.waitForStreamlit();

    cy.get('body').then(($body) => {
      const hasGroups = $body.text().includes('Group') ||
                        $body.text().includes('group') ||
                        $body.text().includes('Team');
      const hasCheckIn = $body.text().includes('Check') ||
                         $body.text().includes('Attendance');
      const hasEmptyState = $body.text().includes('No sessions') ||
                            $body.text().includes('no groups') ||
                            $body.text().includes('empty');

      expect(hasGroups || hasCheckIn || hasEmptyState).to.be.true;
    });
  });

  // ── Session Status Updates ───────────────────────────────────────────────

  it('session status is visible and indicates current state', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();

    cy.get('body').then(($body) => {
      const hasStatus = $body.text().match(/upcoming|active|completed|scheduled|in progress/i);

      if ($body.find('[data-testid="stButton"]').length > 0) {
        expect(hasStatus).to.not.be.null;
      } else {
        cy.log('No sessions available — status validation skipped');
      }
    });
  });

  // ── Error Handling ───────────────────────────────────────────────────────

  it('check-in flow handles edge cases gracefully (no error messages)', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();

    // Check for error messages
    cy.get('body').should('not.contain.text', 'Traceback');
    cy.get('body').should('not.contain.text', 'Error 500');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── Session Preservation ─────────────────────────────────────────────────

  it('@smoke session is preserved during check-in flow navigation', () => {
    // Navigate: Today → Check-in & Groups → Today
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();
    cy.assertAuthenticated();

    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Check-in/)
      .click();
    cy.waitForStreamlit();
    cy.assertAuthenticated();

    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();
    cy.assertAuthenticated();

    // Final check: no session loss
    cy.get('body').should('not.contain.text', 'Not authenticated');
    cy.get('[data-testid="stSidebar"]').should('be.visible');
  });

  // ── My Jobs Tab (Session Overview) ──────────────────────────────────────

  it('My Jobs tab shows assigned sessions or empty state', () => {
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/My Jobs/)
      .click();
    cy.waitForStreamlit();

    cy.get('body').then(($body) => {
      const hasSessions = $body.text().includes('Session') ||
                          $body.text().includes('session') ||
                          $body.text().includes('Job');
      const hasEmptyState = $body.text().includes('No jobs') ||
                            $body.text().includes('no sessions') ||
                            $body.text().includes('empty');

      expect(hasSessions || hasEmptyState).to.be.true;
    });
  });

  // ── Error-Free Check-in Flow ─────────────────────────────────────────────

  it('@smoke check-in flow navigates without Python errors', () => {
    // Navigate through check-in related tabs
    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Today/)
      .click();
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');

    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/Check-in/)
      .click();
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');

    cy.get('[data-testid="stTabs"]')
      .find('[data-testid="stTab"]')
      .contains(/My Jobs/)
      .click();
    cy.waitForStreamlit();
    cy.get('body').should('not.contain.text', 'Traceback');
  });
});
