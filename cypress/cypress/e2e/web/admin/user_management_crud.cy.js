/**
 * ADM-CRUD-01–10 — Admin CRUD operations (users, semesters)
 * DB scenario: baseline
 * Role coverage: admin (all CRUD), student (RBAC blocked)
 *
 * Uses cy.request() to avoid OOM on large admin pages.
 *
 * ── Why beforeEach resets DB ──────────────────────────────────────────────────
 * ADM-CRUD-03 edits a user (name + email), which would corrupt the admin
 * user's session if admin is accidentally picked.  Moving resetDb to
 * beforeEach (instead of before) also guards against Cypress retries: Cypress
 * re-runs beforeEach before each retry attempt, so even if a test mutates the
 * DB the next attempt starts from a clean baseline.
 *
 * ── Student-user targeting ────────────────────────────────────────────────────
 * The /admin/users page lists users ORDER BY id.  On a fresh CI database the
 * admin user always has the lowest id (id=1).  Tests that POST to
 * /admin/users/{id}/edit or /admin/users/{id}/toggle-status must NOT target
 * the admin user, because:
 *   • Editing admin's email breaks the JWT lookup (server looks up the JWT
 *     email in DB; if the email changed the lookup returns 404 → 401).
 *   • Toggling the admin's own status returns 400 (self-toggle guard).
 *
 * Solution: search the page HTML for the `badge-student` CSS class to find a
 * student row, then extract the user id from the adjacent edit/toggle link.
 */
import '../../../support/web_commands';

describe('Web Admin — CRUD Operations', { tags: ['@web', '@admin', '@crud'] }, () => {

  // Reset DB before EVERY test (including retries).
  // This ensures admin@lfa.com is always valid and student users are pristine.
  beforeEach(() => {
    cy.resetDb('baseline');
    cy.clearAllCookies();
    // cy.setupCsrf() is intentionally omitted here — cy.webLogin() calls it
    // internally before every login, so a second registration is redundant.
  });

  // ── ADM-CRUD-01 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-01: GET /admin/users/{id}/edit responds 200 for admin (first user)', () => {
    cy.webLoginAs('admin');
    // Get user list first to find a user ID
    cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.equal(200);
        // Extract first edit link href to get a user ID
        const match = resp.body.match(/href="\/admin\/users\/(\d+)\/edit"/);
        if (!match) return cy.log('No edit links found in page');
        const userId = match[1];
        return cy.request({
          method: 'GET',
          url: `/admin/users/${userId}/edit`,
          failOnStatusCode: false,
        }).then((editResp) => {
          expect(editResp.status).to.equal(200);
          expect(editResp.body).to.not.include('Internal Server Error');
          expect(editResp.body).to.include('Edit User');
        });
      });
  });

  // ── ADM-CRUD-02 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-02: non-admin cannot access edit user page (RBAC)', () => {
    cy.webLoginAs('student');
    cy.request({ method: 'GET', url: '/admin/users/1/edit', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.not.equal(200);
      });
  });

  // ── ADM-CRUD-03 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-03: edit student user with valid data → redirects to /admin/users', () => {
    cy.webLoginAs('admin');
    cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.equal(200);
        // Find a STUDENT user (badge-student) — never edit the admin user
        // (editing admin email breaks the JWT lookup → 401 on redirect).
        const match = resp.body.match(/badge-student[\s\S]{0,800}href="\/admin\/users\/(\d+)\/edit"/);
        if (!match) return cy.log('No student edit link found — skip ADM-CRUD-03');
        const userId = match[1];
        return cy.request({
          method: 'POST',
          url: `/admin/users/${userId}/edit`,
          form: true,
          // Keep the student email unchanged so the upsert in the next
          // beforeEach can find the user by email and restore their data.
          body: { name: 'Updated E2E Name', email: 'rdias@manchestercity.com', role: 'student' },
          failOnStatusCode: false,
        }).then((editResp) => {
          // 303 redirect to /admin/users (Cypress follows → 200)
          expect(editResp.status).to.equal(200);
          expect(editResp.body).to.not.include('Internal Server Error');
        });
      });
  });

  // ── ADM-CRUD-04 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-04: edit user with invalid role → 400 error', () => {
    cy.webLoginAs('admin');
    cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false })
      .then((resp) => {
        // Find a STUDENT user — avoid admin so its session stays valid
        const match = resp.body.match(/badge-student[\s\S]{0,800}href="\/admin\/users\/(\d+)\/edit"/);
        if (!match) return cy.log('No student edit link found — skip ADM-CRUD-04');
        const userId = match[1];
        return cy.request({
          method: 'POST',
          url: `/admin/users/${userId}/edit`,
          form: true,
          body: { name: 'Test', email: 'rdias@manchestercity.com', role: 'SUPER_ADMIN_INVALID' },
          failOnStatusCode: false,
        }).then((editResp) => {
          expect(editResp.status).to.be.oneOf([400, 422]);
        });
      });
  });

  // ── ADM-CRUD-05 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-05: toggle user status (student) → redirects to /admin/users', () => {
    cy.webLoginAs('admin');
    cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false })
      .then((resp) => {
        // Find a STUDENT toggle button — avoid admin (self-toggle → 400)
        const match = resp.body.match(/badge-student[\s\S]{0,800}action="\/admin\/users\/(\d+)\/toggle-status"/);
        if (!match) return cy.log('No student toggle button found — skip ADM-CRUD-05');
        const userId = match[1];
        return cy.request({
          method: 'POST',
          url: `/admin/users/${userId}/toggle-status`,
          failOnStatusCode: false,
        }).then((toggleResp) => {
          expect(toggleResp.status).to.equal(200);
          expect(toggleResp.body).to.not.include('Internal Server Error');
        });
      });
  });

  // ── ADM-CRUD-06 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-06: non-admin cannot toggle user status (RBAC)', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/admin/users/1/toggle-status',
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.not.equal(200);
    });
  });

  // ── ADM-CRUD-07 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-07: GET /admin/semesters/new responds 200 (no 500) for admin', () => {
    cy.webLoginAs('admin');
    cy.request({ method: 'GET', url: '/admin/semesters/new', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.equal(200);
        expect(resp.body).to.not.include('Internal Server Error');
        expect(resp.body).to.include('Create');
      });
  });

  // ── ADM-CRUD-08 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-08: create semester with valid data → redirects to /admin/semesters', () => {
    cy.webLoginAs('admin');
    const uniqueCode = `E2E-SEM-${Date.now()}`;
    cy.request({
      method: 'POST',
      url: '/admin/semesters/new',
      form: true,
      body: {
        code: uniqueCode,
        name: 'E2E Test Semester',
        start_date: '2027-01-01',
        end_date: '2027-06-30',
        enrollment_cost: '500',
        specialization_type: '',
        master_instructor_id: '',
      },
      failOnStatusCode: false,
    }).then((resp) => {
      // 303 → /admin/semesters (followed to 200)
      expect(resp.status).to.equal(200);
      expect(resp.body).to.not.include('Internal Server Error');
    });
  });

  // ── ADM-CRUD-09 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-09: create semester with end before start → error (not 500)', () => {
    cy.webLoginAs('admin');
    cy.request({
      method: 'POST',
      url: '/admin/semesters/new',
      form: true,
      body: {
        code: 'INVALID-DATE-SEM',
        name: 'Bad Dates',
        start_date: '2027-06-30',
        end_date: '2027-01-01',   // before start
        enrollment_cost: '500',
        specialization_type: '',
        master_instructor_id: '',
      },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.equal(200);
      expect(resp.body).to.not.include('Internal Server Error');
      // Should show an error about dates
      expect(resp.body.toLowerCase()).to.match(/error|end date|after/);
    });
  });

  // ── ADM-CRUD-10 ─────────────────────────────────────────────────────────
  it('ADM-CRUD-10: non-admin cannot create semester (RBAC)', () => {
    cy.webLoginAs('student');
    cy.request({ method: 'GET', url: '/admin/semesters/new', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.not.equal(200);
      });
  });
});
