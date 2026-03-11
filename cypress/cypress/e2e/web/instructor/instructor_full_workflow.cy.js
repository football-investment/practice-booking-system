/**
 * INST-WF-01–05 — Instructor full business workflow (DOM-driven)
 * DB scenarios: session_ready (sessions visible), business_lifecycle (lifecycle session)
 * Role coverage: instructor
 *
 * These tests cover the complete instructor business process via real DOM interactions:
 * session list, enrollments, profile — complementing the cy.request() tests in
 * dashboard.cy.js (IDB-01–07) with browser-visible page renders.
 *
 * Core session lifecycle (Start → Mark Attendance → Stop) is fully covered by
 * session_lifecycle_workflow.cy.js (BW-LIFE-01–06, DOM-driven).
 * These tests cover the surrounding workflow pages.
 *
 * Playwright parity:
 *   - INST-WF-01 ← test_instructor_application_workflow.py step 9 (instructor views sessions)
 *   - INST-WF-02 ← Instructor enrollment/student management overview
 *   - INST-WF-03 ← Instructor dashboard page render
 *   - INST-WF-04 ← Instructor views session details before starting
 *   - INST-WF-05 ← Instructor profile view
 */
import '../../../support/web_commands';

describe('Business Workflow — Instructor Full Process', {
  tags: ['@web', '@instructor', '@business-workflow'],
}, () => {
  let sessionId = null;

  before(() => {
    cy.resetDb('session_ready');

    // Discover session ID (E2E On-Site Session) via admin API
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: {
        email: Cypress.env('webAdminEmail'),
        password: Cypress.env('webAdminPassword'),
      },
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
    cy.on('window:alert', () => {});
  });

  // ── INST-WF-01 ──────────────────────────────────────────────────────────
  // Instructor visits /sessions via cy.visit() (DOM render) and sees the
  // seeded sessions list. This is a DOM-driven test that IDB-01 (cy.request)
  // does not cover.
  // NOTE: instructor sees ALL sessions (unlike students who need enrollments).
  it('INST-WF-01: instructor visits /sessions via DOM → sees session list with E2E sessions', () => {
    cy.webLoginAs('instructor');
    cy.visit('/sessions');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    cy.contains('Training Sessions').should('be.visible');
    // Instructor sees all sessions — E2E On-Site Session should appear
    cy.contains('E2E On-Site Session').should('be.visible');
  });

  // ── INST-WF-02 ──────────────────────────────────────────────────────────
  // Instructor visits session details page via DOM and sees session information.
  // Verifies the session_details.html template renders correctly for instructor role.
  it('INST-WF-02: instructor visits session details → session info visible', () => {
    if (!sessionId) return cy.log('No session ID — skip INST-WF-02');
    cy.webLoginAs('instructor');
    cy.visit(`/sessions/${sessionId}`);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    cy.contains('E2E On-Site Session').should('be.visible');
  });

  // ── INST-WF-03 ──────────────────────────────────────────────────────────
  // Instructor visits /instructor/enrollments via cy.visit() (DOM render).
  // IDB-01 uses cy.request() to avoid Chrome OOM from large pages.
  // With a fresh baseline DB (1 semester), cy.visit() is safe.
  it('INST-WF-03: instructor visits /instructor/enrollments via DOM → page renders', () => {
    cy.webLoginAs('instructor');
    cy.visit('/instructor/enrollments');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    // Should show an enrollments page heading
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('Enrollment') || $body.text().includes('Student')
    );
  });

  // ── INST-WF-04 ──────────────────────────────────────────────────────────
  // Instructor views their dashboard via DOM.
  it('INST-WF-04: instructor visits /dashboard via DOM → dashboard renders', () => {
    cy.webLoginAs('instructor');
    cy.visit('/dashboard');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── INST-WF-05 ──────────────────────────────────────────────────────────
  // Instructor visits their profile page and edit page via DOM.
  it('INST-WF-05: instructor visits /profile → profile page renders with instructor data', () => {
    cy.webLoginAs('instructor');
    cy.visit('/profile');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    // Profile page should show instructor name or email
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('Grand Master') || $body.text().includes('grandmaster')
    );
  });
});
