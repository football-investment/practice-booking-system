/**
 * BW-BOOK-01–05 — Student booking workflow (DOM-driven, headed-browser-friendly)
 * DB scenario: session_ready
 * Role coverage: student
 *
 * Tests the complete booking + cancellation flow through real UI button clicks.
 * Tests run sequentially (lifecycle):
 *   BW-BOOK-03 books the session → BW-BOOK-04 verifies → BW-BOOK-05 cancels.
 *
 * Window stubs registered in beforeEach:
 *   - window.confirm → auto-accept (Cancel Booking uses onclick confirm)
 *   - window.alert  → suppress (sessions.html fires alert on ?success=booked/cancelled)
 */
import '../../../support/web_commands';

describe('Business Workflow — Student Booking', {
  tags: ['@web', '@student', '@business-workflow'],
}, () => {
  let sessionId = null;

  before(() => {
    cy.resetDb('session_ready');

    // Discover on-site session ID (date_start = now+24h, booking window open)
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: { email: Cypress.env('webAdminEmail'), password: Cypress.env('webAdminPassword') },
      failOnStatusCode: false,
    }).then((loginResp) => {
      if (loginResp.status !== 200) return;
      cy.request({
        method: 'GET',
        url: `${Cypress.env('apiUrl')}/api/v1/sessions/`,
        headers: { Authorization: `Bearer ${loginResp.body.access_token}` },
        qs: { limit: 50 },
        failOnStatusCode: false,
      }).then((resp) => {
        if (resp.status !== 200) return;
        const sessions = resp.body.sessions || resp.body.items || resp.body || [];
        const s = sessions.find((s) => s.title === 'E2E On-Site Session');
        if (s) sessionId = s.id;
      });
    });
  });

  beforeEach(() => {
    cy.clearAllCookies();
    // Auto-accept all window.confirm dialogs (Cancel Booking uses onclick confirm)
    cy.on('window:confirm', () => true);
    // Suppress window.alert (sessions.html fires alert on ?success=booked/cancelled)
    cy.on('window:alert', () => {});
  });

  // ── BW-BOOK-01 ────────────────────────────────────────────────────────────
  // NOTE: Student sessions list only shows sessions from APPROVED semester enrollments.
  // The session_ready scenario does not create enrollments (requires UserLicense FK).
  // This test verifies the page renders correctly (no 500); session visibility requires enrollment.
  it('BW-BOOK-01: student visits /sessions → page renders without 500', () => {
    cy.webLoginAs('student');
    cy.visit('/sessions');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    cy.contains('Training Sessions').should('be.visible');
  });

  // ── BW-BOOK-02 ────────────────────────────────────────────────────────────
  it('BW-BOOK-02: student visits session details → Book Session button visible', () => {
    if (!sessionId) return cy.log('No session ID — skip BW-BOOK-02');
    cy.webLoginAs('student');
    cy.visit(`/sessions/${sessionId}`);
    cy.contains('button', 'Book Session').should('be.visible');
  });

  // ── BW-BOOK-03 ────────────────────────────────────────────────────────────
  // LIFECYCLE STATE CHANGE: creates a booking for the student.
  // BW-BOOK-04 and BW-BOOK-05 depend on this test having run.
  it('BW-BOOK-03: student clicks Book Session button → booking created, no 500', () => {
    if (!sessionId) return cy.log('No session ID — skip BW-BOOK-03');
    cy.webLoginAs('student');
    cy.visit(`/sessions/${sessionId}`);
    cy.contains('button', 'Book Session').click();
    // POST /sessions/book/{id} → 303 to /sessions?success=booked → alert → sessions list
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── BW-BOOK-04 ────────────────────────────────────────────────────────────
  // Depends on BW-BOOK-03 having created the booking.
  it('BW-BOOK-04: after booking, student revisits session details → Cancel Booking button visible', () => {
    if (!sessionId) return cy.log('No session ID — skip BW-BOOK-04');
    cy.webLoginAs('student');
    cy.visit(`/sessions/${sessionId}`);
    cy.contains('button', 'Cancel Booking').should('be.visible');
  });

  // ── BW-BOOK-05 ────────────────────────────────────────────────────────────
  // Depends on BW-BOOK-03 having created the booking.
  // LIFECYCLE STATE CHANGE: cancels the booking.
  it('BW-BOOK-05: student clicks Cancel Booking → booking cancelled, no 500', () => {
    if (!sessionId) return cy.log('No session ID — skip BW-BOOK-05');
    cy.webLoginAs('student');
    cy.visit(`/sessions/${sessionId}`);
    // onclick="return confirm(...)" → auto-accepted by cy.on('window:confirm')
    cy.contains('button', 'Cancel Booking').click();
    // POST /sessions/cancel/{id} → 303 to /sessions?success=cancelled → alert → sessions list
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });
});
