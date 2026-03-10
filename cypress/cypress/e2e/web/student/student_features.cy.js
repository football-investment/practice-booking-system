/**
 * FEAT-01–06 — Student feature pages: credits, about-specializations,
 *              dashboard-fresh, dashboard/{spec_type}, attendance change-request
 * DB scenario: student_with_credits
 * Role coverage: student (primary), negative edge cases
 */
import '../../../support/web_commands';

describe('Web Student — Feature Pages', { tags: ['@web', '@student', '@features'] }, () => {
  before(() => {
    cy.resetDb('student_with_credits');
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  // ── FEAT-01 ────────────────────────────────────────────────────────────
  it('FEAT-01: GET /about-specializations → 200, page renders without 500', () => {
    cy.request({ method: 'GET', url: '/about-specializations', failOnStatusCode: false }).then((resp) => {
      expect(resp.status).to.equal(200);
      expect(resp.body).to.not.include('Internal Server Error');
      // Page should contain specialization content
      expect(resp.body).to.include('specializ');
    });
  });

  // ── FEAT-02 ────────────────────────────────────────────────────────────
  it('FEAT-02: GET /credits → 200, credit balance page renders', () => {
    cy.request({ method: 'GET', url: '/credits', failOnStatusCode: false }).then((resp) => {
      expect(resp.status).to.equal(200);
      expect(resp.body).to.not.include('Internal Server Error');
      // Page should mention credits
      expect(resp.body).to.include('credit');
    });
  });

  // ── FEAT-03 ────────────────────────────────────────────────────────────
  it('FEAT-03: GET /dashboard-fresh → 200, cache-bypass route works', () => {
    cy.request({ method: 'GET', url: '/dashboard-fresh', failOnStatusCode: false }).then((resp) => {
      expect(resp.status).to.equal(200);
      expect(resp.body).to.not.include('Internal Server Error');
    });
  });

  // ── FEAT-04 ────────────────────────────────────────────────────────────
  it('FEAT-04: GET /dashboard/{spec_type} without license → not 500', () => {
    // Student has no license in student_with_credits scenario.
    // Route raises 403 (access denied) — must not be 500.
    cy.request({
      method: 'GET',
      url: '/dashboard/GANCUJU_PLAYER',
      failOnStatusCode: false,
    }).then((resp) => {
      // Must not crash the server — 403 or redirect are both acceptable
      expect(resp.status).to.not.equal(500);
      expect(resp.body).to.not.include('Internal Server Error');
    });
  });

  // ── FEAT-05 ────────────────────────────────────────────────────────────
  it('FEAT-05: POST /sessions/{id}/attendance/change-request with no pending request → error redirect', () => {
    // No change request exists → route redirects with error=no_change_request
    cy.request({
      method: 'POST',
      url: '/sessions/99999/attendance/change-request',
      form: true,
      body: { action: 'approve' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      // Should redirect (303) or return a non-500 error
      expect(resp.status).to.not.equal(500);
      expect(resp.status).to.be.oneOf([302, 303, 404]);
    });
  });

  // ── FEAT-06 ────────────────────────────────────────────────────────────
  it('FEAT-06: POST evaluate-instructor without session ended → error redirect (not 500)', () => {
    // No completed session exists for this student → route should redirect with error
    cy.request({
      method: 'POST',
      url: '/sessions/99999/evaluate-instructor',
      form: true,
      body: {
        instructor_clarity: '4',
        support_approachability: '4',
        session_structure: '4',
        relevance: '4',
        environment: '4',
        engagement_feeling: '4',
        feedback_quality: '4',
        satisfaction: '4',
        comments: 'E2E test evaluation',
      },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      // Missing session → redirect with error (not 500)
      expect(resp.status).to.not.equal(500);
      expect(resp.status).to.be.oneOf([302, 303, 404]);
    });
  });
});
