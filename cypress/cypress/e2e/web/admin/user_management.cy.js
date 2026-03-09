/**
 * ADM-01–06 — Admin page access and RBAC
 * DB scenario: baseline
 * Role coverage: admin, student (RBAC check)
 */
import '../../support/web_commands';

const ADMIN_PAGES = [
  { id: 'ADM-01', path: '/admin/users',       name: 'users' },
  { id: 'ADM-03', path: '/admin/semesters',   name: 'semesters' },
  { id: 'ADM-04', path: '/admin/enrollments', name: 'enrollments' },
  { id: 'ADM-05', path: '/admin/payments',    name: 'payments' },
  { id: 'ADM-06', path: '/admin/analytics',   name: 'analytics' },
];

describe('Web Admin — User Management & Pages', { tags: ['@web', '@admin'] }, () => {
  before(() => {
    cy.resetDb('baseline');
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  ADMIN_PAGES.forEach(({ id, path, name }) => {
    it(`${id}: GET ${path} renders ${name} page for admin`, () => {
      cy.webLoginAs('admin');
      cy.visit(path, { failOnStatusCode: false });
      cy.assertWebPath(path);
      cy.get('body').should('not.contain.text', '500');
    });
  });

  // ── ADM-02 ─────────────────────────────────────────────────────────────
  it('ADM-02: student visiting /admin/users → redirect (RBAC — not admin)', () => {
    cy.webLoginAs('student');
    cy.visit('/admin/users', { failOnStatusCode: false });
    cy.url().should('satisfy', (url) =>
      url.includes('login') || url.includes('dashboard') || !url.includes('/admin/users')
    );
  });

  // ── ADM-07: instructor also blocked from admin ─────────────────────────
  it('ADM-07: instructor visiting /admin/users → redirect (RBAC)', () => {
    cy.webLoginAs('instructor');
    cy.visit('/admin/users', { failOnStatusCode: false });
    cy.url().should('satisfy', (url) =>
      url.includes('login') || url.includes('dashboard') || !url.includes('/admin/users')
    );
  });

  // ── ADM-08: admin dashboard page ──────────────────────────────────────
  it('ADM-08: GET /dashboard renders admin dashboard for admin user', () => {
    cy.webLoginAs('admin');
    cy.visit('/dashboard');
    cy.assertWebPath('/dashboard');
    cy.get('body').should('not.contain.text', '500');
  });
});
