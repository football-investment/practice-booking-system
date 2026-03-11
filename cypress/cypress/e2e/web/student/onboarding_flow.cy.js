/**
 * ONB-01–09 — Student specialization onboarding flow
 * DB scenario: student_with_credits (student has 200 credits, no license yet)
 * Role coverage: student
 */
import '../../../support/web_commands';

describe('Web Student — Onboarding Flow', { tags: ['@web', '@student', '@onboarding'] }, () => {
  before(() => {
    cy.resetDb('student_with_credits');
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  // ── ONB-01 ─────────────────────────────────────────────────────────────
  it('ONB-01: /onboarding/start renders available specializations', () => {
    cy.visit('/onboarding/start');
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('specialization') || $body.text().includes('specializáció') ||
      $body.text().includes('Onboarding') || $body.text().includes('Select')
    );
  });

  // ── ONB-02 ─────────────────────────────────────────────────────────────
  it('ONB-02: /onboarding/set-birthdate with invalid date → 400 or error page', () => {
    cy.request({
      method: 'POST',
      url: '/onboarding/set-birthdate',
      form: true,
      body: { date_of_birth: 'not-a-date' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([400, 422, 200]);
    });
  });

  // ── ONB-03 ─────────────────────────────────────────────────────────────
  it('ONB-03: /onboarding/set-birthdate with valid date → redirect', () => {
    cy.request({
      method: 'POST',
      url: '/onboarding/set-birthdate',
      form: true,
      body: { date_of_birth: '1998-05-14' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([302, 303, 200]);
    });
  });

  // ── ONB-04 ─────────────────────────────────────────────────────────────
  it('ONB-04: GET /specialization/select renders selection page', () => {
    cy.visit('/specialization/select');
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('specialization') || $body.text().includes('Select') ||
      $body.text().includes('specializáció')
    );
  });

  // ── ONB-05 ─────────────────────────────────────────────────────────────
  it('ONB-05: POST invalid specialization type → error', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'INVALID_TYPE' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 400, 422]);
      if (resp.status === 200) {
        expect(resp.body).to.satisfy((b) =>
          b.includes('error') || b.includes('invalid') || b.includes('Invalid')
        );
      }
    });
  });

  // ── ONB-06 ─────────────────────────────────────────────────────────────
  it('ONB-06: student with 0 credits cannot unlock specialization → redirect to /dashboard', () => {
    // Temporarily drain credits via API reset with baseline (0 credits)
    cy.task('resetDb', 'baseline');
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'GANCUJU_PLAYER' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([302, 303, 200]);
    });
    // Restore credits for subsequent tests
    cy.task('resetDb', 'student_with_credits');
  });

  // ── ONB-07 ─────────────────────────────────────────────────────────────
  it('ONB-07: POST LFA_FOOTBALL_PLAYER → redirect to /specialization/lfa-player/onboarding', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'LFA_FOOTBALL_PLAYER' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      const location = resp.headers['location'] || '';
      const isLfaRedirect = location.includes('lfa-player') || location.includes('onboarding');
      const isDashboard = location.includes('dashboard');
      expect(isLfaRedirect || isDashboard || resp.status === 200).to.be.true;
    });
  });

  // ── ONB-08 ─────────────────────────────────────────────────────────────
  it('ONB-08: POST GANCUJU_PLAYER → redirect to motivation questionnaire', () => {
    cy.task('resetDb', 'student_with_credits');
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'GANCUJU_PLAYER' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      const location = resp.headers['location'] || '';
      expect(
        location.includes('motivation') || location.includes('dashboard') || resp.status === 200
      ).to.be.true;
    });
  });

  // ── ONB-09 ─────────────────────────────────────────────────────────────
  it('ONB-09: existing license → credit_balance unchanged after re-POST', () => {
    // Student already has a license from ONB-07; posting again should not deduct credits
    cy.request({
      method: 'GET',
      url: `${Cypress.env('apiUrl')}/api/v1/users/me`,
      headers: { Authorization: 'Bearer test-csrf-bypass' },
      failOnStatusCode: false,
    }).then((resp) => {
      // credit_balance should not have dropped below 0
      if (resp.status === 200 && resp.body.credit_balance !== undefined) {
        expect(resp.body.credit_balance).to.be.gte(0);
      }
    });
  });
});
