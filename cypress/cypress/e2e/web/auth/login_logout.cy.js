/**
 * AUTH-01–09 — Login / logout flow (FastAPI Jinja2, localhost:8000)
 * DB scenario: baseline
 * Role coverage: admin, instructor, student (all 3 roles)
 */
import '../../../support/web_commands';

describe('Web Auth — Login / Logout', { tags: ['@web', '@auth', '@smoke'] }, () => {
  before(() => {
    cy.resetDb('baseline');
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // ── AUTH-01 ─────────────────────────────────────────────────────────────
  it('AUTH-01: unauthenticated GET / redirects to /login', () => {
    cy.visit('/');
    cy.assertWebPath('/login');
  });

  // ── AUTH-02 ─────────────────────────────────────────────────────────────
  it('AUTH-02: admin login succeeds → /dashboard', () => {
    cy.webLoginAs('admin');
    cy.assertWebPath('/dashboard');
  });

  // ── AUTH-03 ─────────────────────────────────────────────────────────────
  it('AUTH-03: instructor login succeeds → /dashboard', () => {
    cy.webLoginAs('instructor');
    cy.assertWebPath('/dashboard');
  });

  // ── AUTH-04 ─────────────────────────────────────────────────────────────
  it('AUTH-04: student login (DOB set) succeeds → /dashboard', () => {
    cy.webLoginAs('student');
    cy.assertWebPath('/dashboard');
  });

  // ── AUTH-05 ─────────────────────────────────────────────────────────────
  it('AUTH-05: wrong password → stays on /login, shows error', () => {
    cy.webLogin(Cypress.env('webAdminEmail'), 'wrongpassword');
    cy.assertWebPath('/login');
    cy.get('body').should('contain.text', 'Invalid');
  });

  // ── AUTH-06 ─────────────────────────────────────────────────────────────
  it('AUTH-06: non-existent email → stays on /login, shows error', () => {
    cy.webLogin('noone@nowhere.com', 'irrelevant');
    cy.assertWebPath('/login');
    cy.get('body').should('contain.text', 'Invalid');
  });

  // ── AUTH-07 ─────────────────────────────────────────────────────────────
  it('AUTH-07: inactive account → stays on /login, shows error', () => {
    // inactive.e2e@lfa.com is seeded with is_active=False in baseline scenario
    cy.webLogin('inactive.e2e@lfa.com', 'InactiveE2E2026');
    cy.assertWebPath('/login');
    cy.get('body').should('contain.text', 'inactive');
  });

  // ── AUTH-08 ─────────────────────────────────────────────────────────────
  it('AUTH-08: logout → redirects to /login', () => {
    cy.webLoginAs('student');
    cy.assertWebPath('/dashboard');
    cy.visit('/logout');
    cy.assertWebPath('/login');
  });

  // ── AUTH-09 ─────────────────────────────────────────────────────────────
  it('AUTH-09: after logout, /dashboard is inaccessible (auth required)', () => {
    cy.webLoginAs('student');
    cy.visit('/logout');
    // After logout the server returns 401 JSON for protected pages.
    // cy.visit() requires text/html — use cy.request() to check the status.
    cy.request({ method: 'GET', url: '/dashboard', failOnStatusCode: false }).then((resp) => {
      expect(resp.status).to.be.oneOf([401, 302, 303]);
    });
  });
});
