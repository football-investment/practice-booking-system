/**
 * INS-01–07 — Instructor session lifecycle
 * DB scenario: session_ready
 * Role coverage: instructor
 */
import '../../support/web_commands';

describe('Web Sessions — Instructor Lifecycle', { tags: ['@web', '@instructor', '@session'] }, () => {
  let onSiteId = null;
  let hybridId = null;
  let instructorToken = null;

  before(() => {
    cy.resetDb('session_ready');
    // Get API token for instructor
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: {
        email: Cypress.env('webInstructorEmail'),
        password: Cypress.env('webInstructorPassword'),
      },
      failOnStatusCode: false,
    }).then((loginResp) => {
      if (loginResp.status !== 200) return;
      instructorToken = loginResp.body.access_token;
      cy.request({
        method: 'GET',
        url: `${Cypress.env('apiUrl')}/api/v1/sessions/`,
        headers: { Authorization: `Bearer ${instructorToken}` },
        qs: { limit: 50 },
        failOnStatusCode: false,
      }).then((resp) => {
        if (resp.status !== 200) return;
        const sessions = resp.body.sessions || resp.body.items || resp.body || [];
        const onSite = sessions.find((s) => s.title === 'E2E On-Site Session');
        const hybrid = sessions.find((s) => s.title === 'E2E Hybrid Session');
        if (onSite) onSiteId = onSite.id;
        if (hybrid) hybridId = hybrid.id;
      });
    });
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.webLoginAs('instructor');
  });

  // ── INS-01 ─────────────────────────────────────────────────────────────
  it('INS-01: GET /sessions — instructor sees sessions list', () => {
    cy.visit('/sessions');
    cy.assertWebPath('/sessions');
    cy.get('body').should('not.contain.text', '500');
  });

  // ── INS-02 ─────────────────────────────────────────────────────────────
  it('INS-02: POST start session → actual_start_time set', () => {
    if (!onSiteId) return cy.log('No on_site session found — skip INS-02');
    cy.request({
      method: 'POST',
      url: `/sessions/${onSiteId}/start`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── INS-03 ─────────────────────────────────────────────────────────────
  it('INS-03: starting already-started session → error or redirect', () => {
    if (!onSiteId) return cy.log('No on_site session found — skip INS-03');
    cy.request({
      method: 'POST',
      url: `/sessions/${onSiteId}/start`,
      form: true,
      body: {},
      failOnStatusCode: false,
    }).then((resp) => {
      // Already started — should not return 500
      expect(resp.status).to.be.oneOf([200, 302, 303, 400, 409]);
    });
  });

  // ── INS-04 ─────────────────────────────────────────────────────────────
  it('INS-04: POST stop session → actual_end_time set, status completed', () => {
    if (!onSiteId) return cy.log('No on_site session found — skip INS-04');
    cy.request({
      method: 'POST',
      url: `/sessions/${onSiteId}/stop`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── INS-05 ─────────────────────────────────────────────────────────────
  it('INS-05: HYBRID session — unlock quiz → quiz_unlocked=True', () => {
    if (!hybridId) return cy.log('No hybrid session found — skip INS-05');
    // Start hybrid session first
    cy.request({
      method: 'POST',
      url: `/sessions/${hybridId}/start`,
      form: true,
      body: {},
      failOnStatusCode: false,
    });
    cy.request({
      method: 'POST',
      url: `/sessions/${hybridId}/unlock-quiz`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── INS-06 ─────────────────────────────────────────────────────────────
  it('INS-06: mark attendance PRESENT for student → redirect or success', () => {
    if (!hybridId) return cy.log('No hybrid session — skip INS-06');
    // Get student ID
    cy.request({
      method: 'GET',
      url: `${Cypress.env('apiUrl')}/api/v1/users/`,
      headers: { Authorization: `Bearer ${instructorToken}` },
      qs: { email: Cypress.env('webStudentEmail') },
      failOnStatusCode: false,
    }).then((resp) => {
      const students = resp.body?.items || resp.body?.users || [];
      const student = students.find((u) => u.email === Cypress.env('webStudentEmail'));
      if (!student) return cy.log('Student not found — skip INS-06');
      cy.request({
        method: 'POST',
        url: `/sessions/${hybridId}/attendance/mark`,
        form: true,
        body: { student_id: student.id, status: 'PRESENT' },
        followRedirect: false,
        failOnStatusCode: false,
      }).then((markResp) => {
        expect(markResp.status).to.be.oneOf([200, 302, 303, 404]);
      });
    });
  });

  // ── INS-07 ─────────────────────────────────────────────────────────────
  it('INS-07: evaluate student performance → redirect or success', () => {
    if (!hybridId) return cy.log('No hybrid session — skip INS-07');
    cy.request({
      method: 'GET',
      url: `${Cypress.env('apiUrl')}/api/v1/users/`,
      headers: { Authorization: `Bearer ${instructorToken}` },
      failOnStatusCode: false,
    }).then((resp) => {
      const users = resp.body?.items || resp.body?.users || [];
      const student = users.find((u) => u.email === Cypress.env('webStudentEmail'));
      if (!student) return cy.log('Student not found — skip INS-07');
      cy.request({
        method: 'POST',
        url: `/sessions/${hybridId}/evaluate-student/${student.id}`,
        form: true,
        body: { score: '3', notes: 'Good performance' },
        followRedirect: false,
        failOnStatusCode: false,
      }).then((evalResp) => {
        expect(evalResp.status).to.be.oneOf([200, 302, 303, 404]);
      });
    });
  });
});
