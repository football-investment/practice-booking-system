/**
 * AGE-01–07 — Age verification flow (FastAPI Jinja2, localhost:8000)
 * DB scenario: student_no_dob
 * Role coverage: student (fresh, no DOB)
 */
import '../../support/web_commands';

describe('Web Auth — Age Verification', { tags: ['@web', '@auth', '@student'] }, () => {
  before(() => {
    cy.resetDb('student_no_dob');
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // ── AGE-01 ─────────────────────────────────────────────────────────────
  it('AGE-01: fresh student (no DOB) login → redirected to /age-verification', () => {
    cy.webLoginAs('fresh');
    cy.assertWebPath('/age-verification');
  });

  // ── AGE-02 ─────────────────────────────────────────────────────────────
  it('AGE-02: /age-verification renders the DOB form', () => {
    cy.webLoginAs('fresh');
    cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth').should('exist');
    cy.get('button[type="submit"]').should('exist');
  });

  // ── AGE-03 ─────────────────────────────────────────────────────────────
  it('AGE-03: future date → error on page', () => {
    cy.webLoginAs('fresh');
    cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth')
      .type('2099-01-01');
    cy.get('button[type="submit"]').click();
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('future') || $body.text().includes('jövő') || $body.text().includes('invalid')
    );
  });

  // ── AGE-04 ─────────────────────────────────────────────────────────────
  it('AGE-04: age < 5 years → error mentioning minimum age', () => {
    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
    const dob = twoYearsAgo.toISOString().split('T')[0];

    cy.webLoginAs('fresh');
    cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth').type(dob);
    cy.get('button[type="submit"]').click();
    cy.get('body').should('contain.text', '5');
  });

  // ── AGE-05 ─────────────────────────────────────────────────────────────
  it('AGE-05: age > 120 years → error', () => {
    cy.webLoginAs('fresh');
    cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth')
      .type('1900-01-01');
    cy.get('button[type="submit"]').click();
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('valid') || $body.text().includes('érvényes') || $body.text().includes('invalid')
    );
  });

  // ── AGE-06 ─────────────────────────────────────────────────────────────
  it('AGE-06: valid DOB → redirect to /dashboard', () => {
    cy.webLoginAs('fresh');
    cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth')
      .type('2000-05-15');
    cy.get('button[type="submit"]').click();
    cy.assertWebPath('/dashboard');
  });

  // ── AGE-07 ─────────────────────────────────────────────────────────────
  it('AGE-07: admin (already has DOB) visiting /age-verification → redirected to /dashboard', () => {
    cy.webLoginAs('admin');
    cy.visit('/age-verification');
    cy.assertWebPath('/dashboard');
  });
});
