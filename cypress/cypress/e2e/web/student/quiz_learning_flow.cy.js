/**
 * QUIZ-01–05 — Quiz learning flow (GET take + POST submit)
 * DB scenario: baseline (quiz id=1 "Smoke Test Quiz" always present, 0 questions)
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

    // Visit the take page to create a QuizAttempt and get the attempt_id
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
});
