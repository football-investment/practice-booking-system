/**
 * TOUR-I-01–03 — Instructor tournament management view (DOM-driven)
 * DB scenario: tournament_e2e_enrolled
 * Role coverage: instructor (master_instructor_id = grandmaster@lfa.com)
 *
 * Playwright parity (test_tournament_playwright.py):
 *   - TOUR-I-01 ← step 9 (instructor views assigned tournament list)
 *   - TOUR-I-02 ← step 9 (tournament meta: name, code, status, enrolled count)
 *   - TOUR-I-03 ← step 10 (instructor sees enrolled participant in table)
 *
 * DB setup: tournament_e2e_enrolled pre-enrolls rdias@manchestercity.com so
 * the instructor immediately sees 1 participant in TOURN-E2E-2026.
 *
 * Panel scoping: uses cy.contains(selector, text) to find the specific E2E
 * tournament panel by its code — avoids picking old panels from previous runs.
 */
import '../../../support/web_commands';

describe('Tournament Management — Instructor', {
  tags: ['@web', '@instructor', '@tournament'],
}, () => {

  before(() => {
    cy.resetDb('tournament_e2e_enrolled');
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.on('window:alert', () => {});
    cy.webLoginAs('instructor');
  });

  // ── TOUR-I-01 ────────────────────────────────────────────────────────────
  // Instructor visits /instructor/tournaments → page renders without 500,
  // the TOURN-E2E-2026 panel is visible.
  it('TOUR-I-01: GET /instructor/tournaments → E2E tournament panel visible', () => {
    cy.visit('/instructor/tournaments');
    cy.get('body').should('not.contain.text', 'Internal Server Error');

    // Page heading
    cy.contains('My Tournaments').should('be.visible');

    // The E2E tournament panel exists (identified by its code)
    cy.contains('[data-testid="instructor-tournament-panel"]', 'TOURN-E2E-2026')
      .should('be.visible');
  });

  // ── TOUR-I-02 ────────────────────────────────────────────────────────────
  // Tournament meta visible within the TOURN-E2E-2026 panel:
  // name, status badge, enrollment count = 1 (pre-enrolled in scenario).
  // Scoped with .within() to avoid picking up content from other panels.
  it('TOUR-I-02: Tournament meta (name, code, status, capacity) visible in E2E panel', () => {
    cy.visit('/instructor/tournaments');
    cy.get('body').should('not.contain.text', 'Internal Server Error');

    // Target SPECIFICALLY the TOURN-E2E-2026 panel
    cy.contains('[data-testid="instructor-tournament-panel"]', 'TOURN-E2E-2026')
      .within(() => {
        // Tournament name
        cy.contains('E2E Tournament').should('exist');

        // Status badge
        cy.contains('Enrollment Open').should('exist');

        // Enrollment count = 1
        cy.get('[data-testid="enrollment-count"]')
          .invoke('text')
          .then((txt) => {
            expect(parseInt(txt.trim(), 10)).to.equal(1);
          });
      });
  });

  // ── TOUR-I-03 ────────────────────────────────────────────────────────────
  // Instructor sees the pre-enrolled student in the participants table
  // of the TOURN-E2E-2026 panel.
  it('TOUR-I-03: Pre-enrolled student appears in TOURN-E2E-2026 participants table', () => {
    cy.visit('/instructor/tournaments');
    cy.get('body').should('not.contain.text', 'Internal Server Error');

    cy.contains('[data-testid="instructor-tournament-panel"]', 'TOURN-E2E-2026')
      .within(() => {
        // Participants table rendered, not empty state
        cy.get('[data-testid="participants-table"]').should('be.visible');
        cy.get('[data-testid="no-participants"]').should('not.exist');

        // At least one participant row
        cy.get('[data-testid="participant-row"]').should('have.length.at.least', 1);

        // Student email in the table
        cy.get('[data-testid="participants-table"]')
          .should('contain.text', 'rdias@manchestercity.com');
      });
  });
});
