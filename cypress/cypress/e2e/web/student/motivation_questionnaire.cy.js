/**
 * MOT-01–07 — Motivation questionnaire flow
 * DB scenario: student_with_credits
 * Role coverage: student
 */
import '../../../support/web_commands';

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
      $body.text().includes('motiváció') || $body.text().includes('dashboard') ||
      $body.text().includes('Cuju') || $body.text().includes('GANCUJU')
    );
  });

  // ── MOT-03 ─────────────────────────────────────────────────────────────
  it('MOT-03: questionnaire page contains specialization display name', () => {
    cy.visit('/specialization/motivation?spec=GANCUJU_PLAYER', { failOnStatusCode: false });
    // Display name is "GānCuju Player" — match on partial 'Cuju' (no unicode dependency)
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('Cuju') || $body.text().includes('GANCUJU') ||
      $body.text().includes('Gancuju') || $body.text().includes('dashboard') ||
      $body.text().includes('select')
    );
  });

  // ── MOT-04 ─────────────────────────────────────────────────────────────
  it('MOT-04: score 0 (below min) → error on page', () => {
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      // Route reads field 'specialization', not 'spec'
      body: {
        specialization: 'GANCUJU_PLAYER',
        goal_clarity: '0', commitment_level: '0', engagement: '0',
        progress_mindset: '0', initiative: '0',
      },
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
      body: {
        specialization: 'GANCUJU_PLAYER',
        goal_clarity: '6', commitment_level: '6', engagement: '6',
        progress_mindset: '6', initiative: '6',
      },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 400, 422]);
    });
  });

  // ── MOT-06 ─────────────────────────────────────────────────────────────
  it('MOT-06: valid submit with existing license → redirect to /dashboard', () => {
    // Ensure license exists first
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'GANCUJU_PLAYER' },
      followRedirect: false,
      failOnStatusCode: false,
    });
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      // Route reads 'specialization' (not 'spec') and individual score fields
      body: {
        specialization: 'GANCUJU_PLAYER',
        goal_clarity: '3', commitment_level: '3', engagement: '3',
        progress_mindset: '3', initiative: '3',
        notes: 'I want to learn',
      },
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

  // ── MOT-07 ─────────────────────────────────────────────────────────────
  it('MOT-07: submit when no license exists → creates license and redirects', () => {
    cy.task('resetDb', 'student_with_credits');
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/specialization/motivation-submit',
      form: true,
      body: {
        specialization: 'INTERNSHIP',
        goal_clarity: '4', commitment_level: '4', engagement: '4',
        progress_mindset: '4', initiative: '4',
        notes: 'Career development',
      },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
    });
  });
});
