/**
 * ADM-01–08 — Admin page access and RBAC
 * DB scenario: baseline
 * Role coverage: admin, student, instructor (RBAC checks)
 *
 * Note: cy.request() is used instead of cy.visit() for admin pages because the
 * live DB can contain large amounts of data (1 000+ semesters, users, etc.)
 * that make the rendered HTML pages too large for the browser to process reliably
 * in a headless test environment.  cy.request() shares cookies with the browser
 * session and still validates the HTTP response status and body content.
 */
import '../../../support/web_commands';

const ADMIN_PAGES = [
  { id: 'ADM-01', path: '/admin/users',             name: 'users' },
  { id: 'ADM-03', path: '/admin/semesters',         name: 'semesters' },
  { id: 'ADM-04', path: '/admin/enrollments',       name: 'enrollments' },
  { id: 'ADM-05', path: '/admin/payments',          name: 'payments' },
  { id: 'ADM-06', path: '/admin/analytics',         name: 'analytics' },
  { id: 'ADM-09', path: '/admin/coupons',           name: 'coupons' },
  { id: 'ADM-10', path: '/admin/invitation-codes',  name: 'invitation-codes' },
];

describe('Web Admin — User Management & Pages', { tags: ['@web', '@admin'] }, () => {
  before(() => {
    cy.resetDb('baseline');
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // Admin pages: use cy.request() to avoid Chrome OOM crash on large HTML pages.
  // cy.request() shares the browser cookie jar — the access_token cookie set by
  // cy.webLoginAs() is automatically included in the request.
  ADMIN_PAGES.forEach(({ id, path, name }) => {
    it(`${id}: GET ${path} responds 200 (no 500) for admin`, () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: path, failOnStatusCode: false }).then((resp) => {
        expect(resp.status).to.equal(200);
        expect(resp.body).to.not.include('Internal Server Error');
      });
    });
  });

  // ── ADM-02 ─────────────────────────────────────────────────────────────
  it('ADM-02: student visiting /admin/users → blocked (RBAC — not admin)', () => {
    cy.webLoginAs('student');
    cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false }).then((resp) => {
      // Admin requires ADMIN role — non-admin users should get 403
      expect(resp.status).to.not.equal(200);
    });
  });

  // ── ADM-07: instructor also blocked from admin ─────────────────────────
  it('ADM-07: instructor visiting /admin/users → blocked (RBAC)', () => {
    cy.webLoginAs('instructor');
    cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false }).then((resp) => {
      expect(resp.status).to.not.equal(200);
    });
  });

  // ── ADM-08: admin dashboard page ──────────────────────────────────────
  it('ADM-08: GET /dashboard responds 200 for admin user', () => {
    cy.webLoginAs('admin');
    cy.request({ method: 'GET', url: '/dashboard', failOnStatusCode: false }).then((resp) => {
      expect(resp.status).to.equal(200);
      expect(resp.body).to.not.include('Internal Server Error');
    });
  });
});
