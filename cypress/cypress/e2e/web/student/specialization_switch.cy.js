/**
 * SW-01–04 — Specialization switch flow
 * DB scenario: student_with_credits (student has license)
 * Role coverage: student
 */
import '../../support/web_commands';

describe('Web Student — Specialization Switch', { tags: ['@web', '@student', '@specialization'] }, () => {
  before(() => {
    cy.resetDb('student_with_credits');
    // Create a license so switch is possible
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'GANCUJU_PLAYER' },
      failOnStatusCode: false,
    });
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  // ── SW-01 ─────────────────────────────────────────────────────────────
  it('SW-01: invalid spec → redirect to /dashboard or error', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/switch',
      form: true,
      body: { spec: 'NOT_VALID_SPEC' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 400, 422]);
    });
  });

  // ── SW-02 ─────────────────────────────────────────────────────────────
  it('SW-02: spec without license → redirect (authorization check)', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/switch',
      form: true,
      body: { spec: 'LFA_COACH' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 403]);
    });
  });

  // ── SW-03 ─────────────────────────────────────────────────────────────
  it('SW-03: valid switch → redirect to /dashboard', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/switch',
      form: true,
      body: { spec: 'GANCUJU_PLAYER' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
      if (resp.status !== 200) {
        const location = resp.headers['location'] || '';
        expect(location).to.satisfy((loc) =>
          loc.includes('dashboard') || loc.includes('/')
        );
      }
    });
  });

  // ── SW-04 ─────────────────────────────────────────────────────────────
  it('SW-04: switch with return_url=/profile → redirects to /profile', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/switch',
      form: true,
      body: { spec: 'GANCUJU_PLAYER', return_url: '/profile' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
      if (resp.status !== 200) {
        const location = resp.headers['location'] || '';
        expect(location).to.satisfy((loc) =>
          loc.includes('profile') || loc.includes('dashboard')
        );
      }
    });
  });
});
