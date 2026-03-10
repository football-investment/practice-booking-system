/**
 * QUIZ-01–11 — Quiz learning flow (HTTP smoke + UI rendering + score grading)
 *
 * DB scenario  : baseline
 *   - quiz id=1 "Smoke Test Quiz" always present (0 questions) — used by QUIZ-01..05
 *   - "E2E UI Quiz" seeded with 2 real questions — used by QUIZ-06..11
 *
 *   E2E UI Quiz structure (deterministic, used for grading assertions):
 *     Q1: "What colour is the sky on a clear day?"
 *         option[0] = Blue  (is_correct=True,  order_index=1)
 *         option[1] = Green (is_correct=False, order_index=2)
 *     Q2: "How many sides does a triangle have?"
 *         option[0] = 3 (is_correct=True,  order_index=1)
 *         option[1] = 4 (is_correct=False, order_index=2)
 *     passing_score = 0.5  →  50 points threshold
 *     score formula: (earned_points / total_points) * 100   (0–100 float)
 *
 * Role coverage: student (primary path), unauthenticated (RBAC)
 */
import '../../../support/web_commands';

describe('Web Student — Quiz Learning Flow', { tags: ['@web', '@student', '@quiz'] }, () => {

  beforeEach(() => {
    cy.resetDb('baseline');
    cy.clearAllCookies();
  });

  // ── QUIZ-01 ──────────────────────────────────────────────────────────────
  it('QUIZ-01: GET /quizzes/1/take → 200, renders quiz page (no 500)', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'GET',
      url: '/quizzes/1/take',
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.equal(200);
      expect(resp.body).to.not.include('Internal Server Error');
    });
  });

  // ── QUIZ-02 ──────────────────────────────────────────────────────────────
  it('QUIZ-02: visit quiz page → submit → renders result page (no 500)', () => {
    cy.webLoginAs('student');

    cy.visit('/quizzes/1/take');
    cy.get('[name="attempt_id"]').should('exist').invoke('val').then((attemptId) => {
      expect(attemptId).to.match(/^\d+$/);

      cy.request({
        method: 'POST',
        url: '/quizzes/1/submit',
        form: true,
        body: {
          attempt_id: attemptId,
          time_spent: '5',
          session_id: '',
        },
        failOnStatusCode: false,
      }).then((resp) => {
        expect(resp.status).to.equal(200);
        expect(resp.body).to.not.include('Internal Server Error');
      });
    });
  });

  // ── QUIZ-03 ──────────────────────────────────────────────────────────────
  it('QUIZ-03: GET /quizzes/9999/take → 404 (not 500)', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'GET',
      url: '/quizzes/9999/take',
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.equal(404);
    });
  });

  // ── QUIZ-04 ──────────────────────────────────────────────────────────────
  it('QUIZ-04: double submit of same attempt → second submit returns 400', () => {
    cy.webLoginAs('student');

    cy.visit('/quizzes/1/take');
    cy.get('[name="attempt_id"]').invoke('val').then((attemptId) => {
      const body = { attempt_id: attemptId, time_spent: '5', session_id: '' };

      // First submit → success
      cy.request({ method: 'POST', url: '/quizzes/1/submit', form: true, body, failOnStatusCode: false })
        .then((firstResp) => {
          expect(firstResp.status).to.equal(200);

          // Second submit (same attempt_id) → 400
          cy.request({ method: 'POST', url: '/quizzes/1/submit', form: true, body, failOnStatusCode: false })
            .then((secondResp) => {
              expect(secondResp.status).to.equal(400);
            });
        });
    });
  });

  // ── QUIZ-05 ──────────────────────────────────────────────────────────────
  it('QUIZ-05: unauthenticated GET /quizzes/1/take → redirect to login (not 200)', () => {
    cy.request({
      method: 'GET',
      url: '/quizzes/1/take',
      failOnStatusCode: false,
      followRedirect: false,
    }).then((resp) => {
      // Should redirect (302/303) or return 401/403 — NOT 200
      expect(resp.status).to.not.equal(200);
    });
  });

  // ── QUIZ-06 ──────────────────────────────────────────────────────────────
  it('QUIZ-06: take page renders quiz title, 2 questions and radio answer inputs', () => {
    cy.webLoginAs('student');
    cy.task('getE2eQuizId').then((quizId) => {
      expect(quizId).to.be.a('number');

      cy.visit(`/quizzes/${quizId}/take`);

      // Quiz title is visible in the header
      cy.get('.quiz-header h1').should('contain.text', 'E2E UI Quiz');

      // Timer element is rendered
      cy.get('#timer').should('be.visible');

      // Exactly 2 questions are rendered
      cy.get('.question').should('have.length', 2);

      // Each question has at least 2 radio inputs (answer options)
      cy.get('.question').each(($q) => {
        cy.wrap($q).find('input[type="radio"]').should('have.length.at.least', 2);
      });

      // Submit button is visible and initially enabled
      cy.get('#submitBtn').should('be.visible').and('not.be.disabled');
    });
  });

  // ── QUIZ-07 ──────────────────────────────────────────────────────────────
  it('QUIZ-07: select answers and submit → result page renders score stats', () => {
    cy.webLoginAs('student');
    cy.task('getE2eQuizId').then((quizId) => {
      cy.visit(`/quizzes/${quizId}/take`);

      // Select the first radio option in each question
      cy.get('.question').each(($q) => {
        cy.wrap($q).find('input[type="radio"]').first().check();
      });

      // Click submit (form POSTs to /quizzes/{id}/submit, server renders result inline)
      cy.get('#submitBtn').click();

      // Result page DOM is now rendered
      cy.get('.result-title').should('be.visible');

      // Stats block is present
      cy.get('.stats').should('be.visible');
      cy.get('.stat-label').should('contain.text', 'Score');
      cy.get('.stat-label').should('contain.text', 'Correct Answers');

      // Quiz title shown in the footer
      cy.get('.time-info').should('contain.text', 'E2E UI Quiz');
    });
  });

  // ── QUIZ-08 ──────────────────────────────────────────────────────────────
  it('QUIZ-08: zero correct answers → result page shows "Try Again" link', () => {
    cy.webLoginAs('student');
    cy.task('getE2eQuizId').then((quizId) => {
      // Visit take page to obtain a fresh attempt_id
      cy.visit(`/quizzes/${quizId}/take`);
      cy.get('[name="attempt_id"]').invoke('val').then((attemptId) => {
        // Submit with no question answers selected → 0 correct → fail (0% < 50% passing)
        cy.request({
          method: 'POST',
          url: `/quizzes/${quizId}/submit`,
          form: true,
          body: { attempt_id: attemptId, time_spent: '1', session_id: '' },
          failOnStatusCode: false,
        }).then((resp) => {
          expect(resp.status).to.equal(200);
          // "Try Again" button is present in the result HTML
          expect(resp.body).to.include('Try Again');
        });
      });
    });
  });

  // ── QUIZ-09 ──────────────────────────────────────────────────────────────
  it('QUIZ-09: 1 of 2 correct → score 50.0%, "Correct Answers: 1 / 2", passes boundary', () => {
    cy.webLoginAs('student');
    cy.task('getE2eQuizId').then((quizId) => {
      cy.visit(`/quizzes/${quizId}/take`);

      // Q1: select WRONG answer (Green = 2nd radio, order_index=2, is_correct=False)
      cy.get('.question').eq(0).find('input[type="radio"]').eq(1).check();
      // Q2: select CORRECT answer (3 = 1st radio, order_index=1, is_correct=True)
      cy.get('.question').eq(1).find('input[type="radio"]').eq(0).check();

      cy.get('#submitBtn').click();

      // Score: 1 point earned / 2 total × 100 = 50.0%
      cy.contains('.stat-label', 'Score')
        .parent().find('.stat-value')
        .should('have.text', '50.0%');

      // Correct answers counter
      cy.contains('.stat-label', 'Correct Answers')
        .parent().find('.stat-value')
        .should('have.text', '1 / 2');

      // 50.0 >= 50 threshold → passed ("Understood!")
      cy.get('.result-title').should('have.class', 'passed');
    });
  });

  // ── QUIZ-10 ──────────────────────────────────────────────────────────────
  it('QUIZ-10: 2 of 2 correct → score 100.0%, "Correct Answers: 2 / 2", passed', () => {
    cy.webLoginAs('student');
    cy.task('getE2eQuizId').then((quizId) => {
      cy.visit(`/quizzes/${quizId}/take`);

      // Q1: select CORRECT answer (Blue = 1st radio, order_index=1, is_correct=True)
      cy.get('.question').eq(0).find('input[type="radio"]').eq(0).check();
      // Q2: select CORRECT answer (3 = 1st radio, order_index=1, is_correct=True)
      cy.get('.question').eq(1).find('input[type="radio"]').eq(0).check();

      cy.get('#submitBtn').click();

      // Score: 2 points earned / 2 total × 100 = 100.0%
      cy.contains('.stat-label', 'Score')
        .parent().find('.stat-value')
        .should('have.text', '100.0%');

      // Correct answers counter
      cy.contains('.stat-label', 'Correct Answers')
        .parent().find('.stat-value')
        .should('have.text', '2 / 2');

      // 100.0 >= 50 threshold → passed
      cy.get('.result-title').should('have.class', 'passed');
    });
  });

  // ── QUIZ-11 ──────────────────────────────────────────────────────────────
  it('QUIZ-11: 0 of 2 correct → score 0.0%, "Needs Review", "Try Again" visible', () => {
    cy.webLoginAs('student');
    cy.task('getE2eQuizId').then((quizId) => {
      cy.visit(`/quizzes/${quizId}/take`);

      // Q1: select WRONG answer (Green = 2nd radio, order_index=2, is_correct=False)
      cy.get('.question').eq(0).find('input[type="radio"]').eq(1).check();
      // Q2: select WRONG answer (4 = 2nd radio, order_index=2, is_correct=False)
      cy.get('.question').eq(1).find('input[type="radio"]').eq(1).check();

      cy.get('#submitBtn').click();

      // Score: 0 points earned / 2 total × 100 = 0.0%
      cy.contains('.stat-label', 'Score')
        .parent().find('.stat-value')
        .should('have.text', '0.0%');

      // Correct answers counter
      cy.contains('.stat-label', 'Correct Answers')
        .parent().find('.stat-value')
        .should('have.text', '0 / 2');

      // 0.0 < 50 threshold → failed → "Needs Review"
      cy.get('.result-title')
        .should('have.class', 'failed')
        .and('contain.text', 'Needs Review');

      // "Try Again" link is present and visible
      cy.get('a.btn-secondary')
        .should('be.visible')
        .and('contain.text', 'Try Again');
    });
  });
});
