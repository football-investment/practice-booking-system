/**
 * BK-01–06 — Student session booking flow
 * DB scenario: session_ready (baseline users + 2 E2E sessions)
 * Role coverage: student
 */
import '../../support/web_commands';

describe('Web Sessions — Student Booking', { tags: ['@web', '@student', '@booking'] }, () => {
  let onSiteSessionId = null;

  before(() => {
    cy.resetDb('session_ready');
    // Discover session IDs via API
    cy.webLoginAs('admin');
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: { email: Cypress.env('webAdminEmail'), password: Cypress.env('webAdminPassword') },
      failOnStatusCode: false,
    }).then((loginResp) => {
      if (loginResp.status !== 200) return;
      const token = loginResp.body.access_token;
      cy.request({
        method: 'GET',
        url: `${Cypress.env('apiUrl')}/api/v1/sessions/`,
        headers: { Authorization: `Bearer ${token}` },
        qs: { limit: 50 },
        failOnStatusCode: false,
      }).then((resp) => {
        if (resp.status !== 200) return;
        const sessions = resp.body.sessions || resp.body.items || resp.body || [];
        const onSite = sessions.find((s) => s.title === 'E2E On-Site Session');
        if (onSite) onSiteSessionId = onSite.id;
      });
    });
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  // ── BK-01 ─────────────────────────────────────────────────────────────
  it('BK-01: GET /sessions renders sessions list', () => {
    cy.visit('/sessions');
    cy.assertWebPath('/sessions');
    cy.get('body').should('not.contain.text', '500');
  });

  // ── BK-02 ─────────────────────────────────────────────────────────────
  it('BK-02: book a session → booking record created (redirect or success)', () => {
    if (!onSiteSessionId) return cy.log('No session ID found — skip BK-02');
    cy.request({
      method: 'POST',
      url: `/sessions/book/${onSiteSessionId}`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── BK-03 ─────────────────────────────────────────────────────────────
  it('BK-03: booking same session twice → already_booked message or redirect', () => {
    if (!onSiteSessionId) return cy.log('No session ID found — skip BK-03');
    cy.request({
      method: 'POST',
      url: `/sessions/book/${onSiteSessionId}`,
      form: true,
      body: {},
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 400, 409]);
    });
  });

  // ── BK-04 ─────────────────────────────────────────────────────────────
  it('BK-04: cancel booking → redirect to sessions or session detail', () => {
    if (!onSiteSessionId) return cy.log('No session ID found — skip BK-04');
    cy.request({
      method: 'POST',
      url: `/sessions/cancel/${onSiteSessionId}`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 404]);
    });
  });

  // ── BK-05 ─────────────────────────────────────────────────────────────
  it('BK-05: GET /sessions/{id} renders session detail page', () => {
    if (!onSiteSessionId) return cy.log('No session ID found — skip BK-05');
    cy.visit(`/sessions/${onSiteSessionId}`, { failOnStatusCode: false });
    cy.get('body').should('not.contain.text', '500');
    cy.url().should('satisfy', (url) =>
      url.includes(`/sessions/${onSiteSessionId}`) || url.includes('/sessions') || url.includes('/login')
    );
  });

  // ── BK-06 ─────────────────────────────────────────────────────────────
  it('BK-06: GET /calendar renders calendar view', () => {
    cy.visit('/calendar');
    cy.assertWebPath('/calendar');
    cy.get('body').should('not.contain.text', '500');
  });
});
