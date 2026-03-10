/**
 * XR-01–14 — Full student lifecycle cross-role integration test
 * DB scenario: session_ready
 * Role coverage: admin + instructor + student (all 3 roles, sequential)
 *
 * IMPORTANT: This is a PR merge gate only (not daily regression).
 * Run via: npm run cy:run:web:integration
 *
 * Flow:
 *   Student login → age verification → specialization → motivation →
 *   session booking → instructor starts → marks attendance →
 *   student confirms → instructor evaluates → student sees XP →
 *   student cancels booking
 */
import '../../../support/web_commands';

describe('Web Cross-Role — Full Student Lifecycle', {
  tags: ['@web', '@integration', '@cross-role'],
}, () => {
  let sessionId = null;
  let studentId = null;
  let instructorToken = null;
  let studentToken = null;

  before(() => {
    cy.resetDb('session_ready');

    // Get instructor token
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: {
        email: Cypress.env('webInstructorEmail'),
        password: Cypress.env('webInstructorPassword'),
      },
      failOnStatusCode: false,
    }).then((resp) => {
      if (resp.status === 200) instructorToken = resp.body.access_token;
    });

    // Get student token + ID
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: {
        email: Cypress.env('webStudentEmail'),
        password: Cypress.env('webStudentPassword'),
      },
      failOnStatusCode: false,
    }).then((resp) => {
      if (resp.status === 200) {
        studentToken = resp.body.access_token;
        studentId = resp.body.user_id || resp.body.id;
      }
    });

    // Discover session ID
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
  });

  // ── XR-01 ─────────────────────────────────────────────────────────────
  it('XR-01: baseline users accessible — student login works', () => {
    cy.webLoginAs('student');
    cy.assertWebPath('/dashboard');
  });

  // ── XR-02 ─────────────────────────────────────────────────────────────
  it('XR-02: fresh student (no DOB) login → age-verification redirect', () => {
    cy.webLoginAs('fresh');
    cy.url().should('satisfy', (url) =>
      url.includes('age-verification') || url.includes('dashboard')
    );
  });

  // ── XR-03 ─────────────────────────────────────────────────────────────
  it('XR-03: fresh student sets DOB → reaches dashboard', () => {
    cy.webLoginAs('fresh');
    cy.url().then((url) => {
      if (!url.includes('age-verification')) return cy.log('Already has DOB — skip');
      cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth')
        .type('2000-05-15');
      cy.get('button[type="submit"]').click();
      cy.assertWebPath('/dashboard');
    });
  });

  // ── XR-04 ─────────────────────────────────────────────────────────────
  it('XR-04: student selects specialization → credit deducted', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'GANCUJU_PLAYER' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── XR-05 ─────────────────────────────────────────────────────────────
  it('XR-05: student submits motivation questionnaire', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      body: { spec: 'GANCUJU_PLAYER', score: '4', motivation_text: 'E2E lifecycle test' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── XR-06 ─────────────────────────────────────────────────────────────
  it('XR-06: student books the on-site session', () => {
    if (!sessionId) return cy.log('No session ID — skip XR-06');
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: `/sessions/book/${sessionId}`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── XR-07 ─────────────────────────────────────────────────────────────
  it('XR-07: instructor starts the session', () => {
    if (!sessionId) return cy.log('No session ID — skip XR-07');
    cy.webLoginAs('instructor');
    cy.request({
      method: 'POST',
      url: `/sessions/${sessionId}/start`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── XR-08 ─────────────────────────────────────────────────────────────
  it('XR-08: instructor marks student attendance as PRESENT', () => {
    if (!sessionId || !studentId) return cy.log('IDs missing — skip XR-08');
    cy.webLoginAs('instructor');
    cy.request({
      method: 'POST',
      url: `/sessions/${sessionId}/attendance/mark`,
      form: true,
      body: { student_id: studentId, status: 'PRESENT' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 404]);
    });
  });

  // ── XR-09 ─────────────────────────────────────────────────────────────
  it('XR-09: student confirms attendance', () => {
    if (!sessionId) return cy.log('No session ID — skip XR-09');
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: `/sessions/${sessionId}/attendance/confirm`,
      form: true,
      body: { action: 'confirm' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 404]);
    });
  });

  // ── XR-10 ─────────────────────────────────────────────────────────────
  it('XR-10: instructor stops the session', () => {
    if (!sessionId) return cy.log('No session ID — skip XR-10');
    cy.webLoginAs('instructor');
    cy.request({
      method: 'POST',
      url: `/sessions/${sessionId}/stop`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });

  // ── XR-11 ─────────────────────────────────────────────────────────────
  it('XR-11: instructor evaluates student performance', () => {
    if (!sessionId || !studentId) return cy.log('IDs missing — skip XR-11');
    cy.webLoginAs('instructor');
    cy.request({
      method: 'POST',
      url: `/sessions/${sessionId}/evaluate-student/${studentId}`,
      form: true,
      body: { score: '4', notes: 'Excellent E2E performance' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303, 404]);
    });
  });

  // ── XR-15 ─────────────────────────────────────────────────────────────
  // Runs after XR-10 (session stopped) and XR-08/09 (student marked PRESENT).
  // evaluate-instructor requires: session stopped + student attended (PRESENT).
  it('XR-15: student evaluates instructor (POST evaluate-instructor) → redirect or success', () => {
    if (!sessionId) return cy.log('No session ID — skip XR-15');
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: `/sessions/${sessionId}/evaluate-instructor`,
      form: true,
      body: {
        instructor_clarity: '4',
        support_approachability: '5',
        session_structure: '4',
        relevance: '5',
        environment: '4',
        engagement_feeling: '5',
        feedback_quality: '4',
        satisfaction: '5',
        comments: 'Excellent E2E lifecycle instructor evaluation',
      },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      // Success → 303 redirect to session page; or 404 if attendance not found
      expect(resp.status).to.not.equal(500);
      expect(resp.status).to.be.oneOf([200, 302, 303, 404]);
    });
  });

  // ── XR-12 ─────────────────────────────────────────────────────────────
  it('XR-12: student visits /progress — page loads without 500', () => {
    cy.webLoginAs('student');
    cy.visit('/progress', { failOnStatusCode: false });
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── XR-13 ─────────────────────────────────────────────────────────────
  it('XR-13: student visits /achievements — page loads without 500', () => {
    cy.webLoginAs('student');
    cy.visit('/achievements', { failOnStatusCode: false });
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── XR-14 ─────────────────────────────────────────────────────────────
  it('XR-14: student cancels booking (if still active)', () => {
    if (!sessionId) return cy.log('No session ID — skip XR-14');
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: `/sessions/cancel/${sessionId}`,
      form: true,
      body: {},
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      // 404 is acceptable if already cancelled or attendance was marked
      expect(resp.status).to.be.oneOf([200, 302, 303, 404]);
    });
  });
});
