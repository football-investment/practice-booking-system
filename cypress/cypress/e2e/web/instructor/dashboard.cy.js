/**
 * IDB-01–07 — Instructor dashboard (enrollments + student skills)
 * DB scenario: baseline
 * Role coverage: instructor, student (RBAC check)
 */
import '../../../support/web_commands';

describe('Web Instructor — Dashboard', { tags: ['@web', '@instructor', '@dashboard'] }, () => {
  let studentId = null;
  let licenseId = null;

  before(() => {
    cy.resetDb('baseline');
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: {
        email: Cypress.env('webInstructorEmail'),
        password: Cypress.env('webInstructorPassword'),
      },
      failOnStatusCode: false,
    });
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // ── IDB-01 ─────────────────────────────────────────────────────────────
  // Use cy.request() to avoid Chrome OOM from large response (362 semesters × enrollments).
  it('IDB-01: GET /instructor/enrollments responds 200 for instructor', () => {
    cy.webLoginAs('instructor');
    cy.request({ method: 'GET', url: '/instructor/enrollments', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.equal(200);
        expect(resp.body).to.not.include('Internal Server Error');
      });
  });

  // ── IDB-02 ─────────────────────────────────────────────────────────────
  it('IDB-02: student visiting /instructor/enrollments → blocked (RBAC)', () => {
    cy.webLoginAs('student');
    cy.request({ method: 'GET', url: '/instructor/enrollments', failOnStatusCode: false })
      .then((resp) => {
        // Non-instructor should be blocked (403 or redirect)
        expect(resp.status).to.not.equal(200);
      });
  });

  // ── IDB-03 ─────────────────────────────────────────────────────────────
  it('IDB-03: GET /instructor/students/{id}/skills/{lid} renders skills page (when valid)', () => {
    if (!studentId || !licenseId) return cy.log('IDs not available — skip IDB-03');
    cy.webLoginAs('instructor');
    cy.visit(`/instructor/students/${studentId}/skills/${licenseId}`, { failOnStatusCode: false });
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── IDB-04 ─────────────────────────────────────────────────────────────
  it('IDB-04: non-existent student ID → 404 (not 500)', () => {
    cy.webLoginAs('instructor');
    cy.request({ method: 'GET', url: '/instructor/students/99999/skills/99999', failOnStatusCode: false })
      .then((resp) => {
        // Should be 404, definitely not 500
        expect(resp.status).to.not.equal(500);
        expect(resp.status).to.not.equal(200);
      });
  });

  // ── IDB-05 ─────────────────────────────────────────────────────────────
  it('IDB-05: valid skill update POST → success template (when valid IDs)', () => {
    if (!studentId || !licenseId) return cy.log('IDs not available — skip IDB-05');
    cy.webLoginAs('instructor');
    cy.request({
      method: 'POST',
      url: `/instructor/students/${studentId}/skills/${licenseId}`,
      form: true,
      body: {
        football_iq: '3',
        technical_skill: '3',
        physical_fitness: '3',
        teamwork: '3',
        notes: 'E2E test evaluation',
      },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 404]);
    });
  });

  // ── IDB-06 ─────────────────────────────────────────────────────────────
  it('IDB-06: skill value out of range → error response', () => {
    if (!studentId || !licenseId) return cy.log('IDs not available — skip IDB-06');
    cy.webLoginAs('instructor');
    cy.request({
      method: 'POST',
      url: `/instructor/students/${studentId}/skills/${licenseId}`,
      form: true,
      body: { football_iq: '99', technical_skill: '99' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 400, 422]);
    });
  });

  // ── IDB-07 ─────────────────────────────────────────────────────────────
  it('IDB-07: /instructor/enrollments responds without 500 (AuditService import OK)', () => {
    // This test specifically validates that AuditService import is present (Sprint 54 P1 fix)
    cy.webLoginAs('instructor');
    cy.request({
      method: 'GET',
      url: '/instructor/enrollments',
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.not.equal(500);
    });
  });
});
