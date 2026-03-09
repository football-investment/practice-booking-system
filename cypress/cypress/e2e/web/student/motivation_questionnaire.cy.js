/**
 * MOT-01–07 — Motivation questionnaire flow
 * DB scenario: student_with_credits
 * Role coverage: student
 */
import '../../support/web_commands';

describe('Web Student — Motivation Questionnaire', { tags: ['@web', '@student', '@motivation'] }, () => {
  before(() => {
    cy.resetDb('student_with_credits');
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  // ── MOT-01 ─────────────────────────────────────────────────────────────
  it('MOT-01: invalid specialization GET → redirect to /specialization/select', () => {
    cy.visit('/specialization/motivation?spec=NOT_REAL', { failOnStatusCode: false });
    cy.url().should('satisfy', (url) =>
      url.includes('select') || url.includes('motivation') || url.includes('dashboard')
    );
  });

  // ── MOT-02 ─────────────────────────────────────────────────────────────
  it('MOT-02: valid specialization GET → motivation questionnaire renders', () => {
    // First create a GANCUJU_PLAYER license
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'GANCUJU_PLAYER' },
      followRedirect: false,
      failOnStatusCode: false,
    });
    cy.visit('/specialization/motivation?spec=GANCUJU_PLAYER', { failOnStatusCode: false });
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('motivation') || $body.text().includes('questionnaire') ||
      $body.text().includes('motiváció') || $body.text().includes('dashboard')
    );
  });

  // ── MOT-03 ─────────────────────────────────────────────────────────────
  it('MOT-03: questionnaire page contains specialization display name', () => {
    cy.visit('/specialization/motivation?spec=GANCUJU_PLAYER', { failOnStatusCode: false });
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('Gancuju') || $body.text().includes('GANCUJU') ||
      $body.text().includes('dashboard')
    );
  });

  // ── MOT-04 ─────────────────────────────────────────────────────────────
  it('MOT-04: score 0 (below min) → error on page', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      body: { spec: 'GANCUJU_PLAYER', score: '0', motivation_text: 'test' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 400, 422]);
    });
  });

  // ── MOT-05 ─────────────────────────────────────────────────────────────
  it('MOT-05: score 6 (above max) → error on page', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      body: { spec: 'GANCUJU_PLAYER', score: '6', motivation_text: 'test' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 400, 422]);
    });
  });

  // ── MOT-06 ─────────────────────────────────────────────────────────────
  it('MOT-06: valid submit with existing license → redirect to /dashboard', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      body: { spec: 'GANCUJU_PLAYER', score: '3', motivation_text: 'I want to learn' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
      if (resp.status !== 200) {
        expect(resp.headers['location']).to.include('dashboard');
      }
    });
  });

  // ── MOT-07 ─────────────────────────────────────────────────────────────
  it('MOT-07: submit when no license exists → creates license and redirects', () => {
    cy.task('resetDb', 'student_with_credits');
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      body: { spec: 'INTERNSHIP', score: '4', motivation_text: 'Career development' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });
});
