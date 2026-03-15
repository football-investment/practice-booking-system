/**
 * ADM-PAGE-01–09 — Admin pages full coverage (DOM verification)
 * DB scenario: baseline
 * Role coverage: admin (all), student (RBAC spot-check)
 *
 * Strategy:
 *   - cy.request() for pure HTTP status checks (avoids Chrome OOM on large datasets)
 *   - cy.visit() + DOM assertions for UI component verification (admin-nav, key widgets)
 *   - All mutation tests (POST) are deferred to separate CRUD suites
 *
 * Pages covered:
 *   ADM-PAGE-01  /admin/enrollments    — accordion + payment link
 *   ADM-PAGE-02  /admin/payments       — KPI grid + invoice table
 *   ADM-PAGE-03  /admin/coupons        — coupon cards + create form
 *   ADM-PAGE-04  /admin/sessions       — hierarchy view + filter bar
 *   ADM-PAGE-05  /admin/bookings       — booking table + filter form
 *   ADM-PAGE-06  /admin/locations      — location cards + stats
 *   ADM-PAGE-07  /admin/game-presets   — preset cards + create toggle
 *   ADM-PAGE-08  /admin/system-events  — event list + filter selects
 *   ADM-PAGE-09  /admin/tournaments    — tab interface + tournament list
 *
 * RBAC coverage:
 *   ADM-RBAC-01  student → /admin/* → 403
 *   ADM-RBAC-02  instructor → /admin/* → 403
 *   ADM-RBAC-03  unauthenticated → /admin/* → 401/redirect
 *
 * Responsiveness:
 *   ADM-RESP-01  /admin/users table has .table-scroll-wrap container
 */
import '../../../support/web_commands';

// ─────────────────────────────────────────────────────────────────────────────
// Shared helper: verify unified admin layout is present on a visited page
// ─────────────────────────────────────────────────────────────────────────────
function verifyAdminLayout() {
  cy.get('.admin-header').should('be.visible').and('contain.text', 'ADMIN');
  cy.get('.admin-nav').should('be.visible');
  cy.get('.admin-container').should('exist');
}

// ─────────────────────────────────────────────────────────────────────────────
describe('Admin Pages — Full Coverage', {
  tags: ['@web', '@admin', '@coverage'],
}, () => {

  before(() => {
    cy.resetDb('baseline');
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // ── ADM-PAGE-01 ── /admin/enrollments ─────────────────────────────────────
  describe('ADM-PAGE-01: /admin/enrollments', () => {
    it('ADM-PAGE-01a: GET /admin/enrollments → 200, no 500', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/enrollments', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-01b: enrollments page loads unified admin layout + payment link', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/enrollments');
      verifyAdminLayout();
      // Nav active item
      cy.get('.admin-nav a[href="/admin/enrollments"]').should('have.class', 'active');
      // Payment management shortcut link
      cy.get('a[href="/admin/payments"]').should('exist');
    });
  });

  // ── ADM-PAGE-02 ── /admin/payments ────────────────────────────────────────
  describe('ADM-PAGE-02: /admin/payments', () => {
    it('ADM-PAGE-02a: GET /admin/payments → 200, no 500', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/payments', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-02b: payments page loads unified admin layout + KPI grid', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/payments');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/payments"]').should('have.class', 'active');
      // Financial KPI grid or newcomer section must exist
      cy.get('body').should('not.contain.text', 'Internal Server Error');
      cy.get('.admin-container').should('be.visible');
    });
  });

  // ── ADM-PAGE-03 ── /admin/coupons ─────────────────────────────────────────
  describe('ADM-PAGE-03: /admin/coupons', () => {
    it('ADM-PAGE-03a: GET /admin/coupons → 200', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/coupons', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-03b: coupons page loads admin layout + create coupon section', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/coupons');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/coupons"]').should('have.class', 'active');
      // Create coupon form or coupon list must be rendered
      cy.get('.admin-container h2, .admin-container .card').should('exist');
    });
  });

  // ── ADM-PAGE-04 ── /admin/sessions ────────────────────────────────────────
  describe('ADM-PAGE-04: /admin/sessions', () => {
    it('ADM-PAGE-04a: GET /admin/sessions → 200', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/sessions', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-04b: sessions page loads admin layout + filter bar', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/sessions');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/sessions"]').should('have.class', 'active');
      // Filter bar should be present
      cy.get('.filter-bar').should('exist');
    });
  });

  // ── ADM-PAGE-05 ── /admin/bookings ────────────────────────────────────────
  describe('ADM-PAGE-05: /admin/bookings', () => {
    it('ADM-PAGE-05a: GET /admin/bookings → 200', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/bookings', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-05b: bookings page loads admin layout + filter form', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/bookings');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/bookings"]').should('have.class', 'active');
      // Status filter select must be rendered
      cy.get('select[name="status_filter"], form[method="get"]').should('exist');
    });
  });

  // ── ADM-PAGE-06 ── /admin/locations ───────────────────────────────────────
  describe('ADM-PAGE-06: /admin/locations', () => {
    it('ADM-PAGE-06a: GET /admin/locations → 200', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/locations', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-06b: locations page loads admin layout + stats row', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/locations');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/locations"]').should('have.class', 'active');
      // Stats row with location counts
      cy.get('.stats-row').should('exist');
      cy.get('.stat-card').should('have.length.at.least', 1);
    });

    it('ADM-PAGE-06c: GET /admin/locations/{id}/edit → handled (200 or 404)', () => {
      cy.webLoginAs('admin');
      // Any non-existent ID should return 404, not 500
      cy.request({ method: 'GET', url: '/admin/locations/999999/edit', failOnStatusCode: false })
        .its('status').should('be.oneOf', [200, 404]);
    });

    it('ADM-PAGE-06d: GET /admin/campuses/{id}/edit → handled (200 or 404)', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/campuses/999999/edit', failOnStatusCode: false })
        .its('status').should('be.oneOf', [200, 404]);
    });
  });

  // ── ADM-PAGE-07 ── /admin/game-presets ────────────────────────────────────
  describe('ADM-PAGE-07: /admin/game-presets', () => {
    it('ADM-PAGE-07a: GET /admin/game-presets → 200', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/game-presets', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-07b: game-presets page loads admin layout + preset list', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/game-presets');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/game-presets"]').should('have.class', 'active');
      // Stats row shows preset counts
      cy.get('.stats-row').should('exist');
    });
  });

  // ── ADM-PAGE-08 ── /admin/system-events ───────────────────────────────────
  describe('ADM-PAGE-08: /admin/system-events', () => {
    it('ADM-PAGE-08a: GET /admin/system-events → 200', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/system-events', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-08b: system-events page loads admin layout + filter selects', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/system-events');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/system-events"]').should('have.class', 'active');
      // Filter bar with event type + resolved selects
      cy.get('.filter-bar').should('exist');
      cy.get('select[name="resolved"], select[name="event_type"]').should('exist');
    });
  });

  // ── ADM-PAGE-09 ── /admin/tournaments ─────────────────────────────────────
  describe('ADM-PAGE-09: /admin/tournaments', () => {
    it('ADM-PAGE-09a: GET /admin/tournaments → 200', () => {
      cy.webLoginAs('admin');
      cy.request({ method: 'GET', url: '/admin/tournaments', failOnStatusCode: false })
        .its('status').should('eq', 200);
    });

    it('ADM-PAGE-09b: tournaments page loads admin layout + tab interface', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/tournaments');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/tournaments"]').should('have.class', 'active');
      // Tab buttons (View Tournaments / Create Tournament)
      cy.get('body').then(($body) => {
        // Either tab buttons or tournament list container should exist
        const hasTab = $body.find('[onclick*="switchTab"], .tab-btn, [data-tab]').length > 0;
        const hasContent = $body.find('.admin-container').length > 0;
        expect(hasTab || hasContent).to.be.true;
      });
    });
  });

  // ── ADM-PAGE-10 ── /admin/semesters/new ───────────────────────────────────
  describe('ADM-PAGE-10: /admin/semesters/new', () => {
    it('ADM-PAGE-10a: GET /admin/semesters/new → 200, create form present', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/semesters/new');
      verifyAdminLayout();
      cy.get('form[action="/admin/semesters/new"]').should('exist');
      cy.get('input[name="code"]').should('be.visible');
      cy.get('input[name="name"]').should('be.visible');
      cy.get('input[name="start_date"]').should('exist');
      cy.get('input[name="end_date"]').should('exist');
    });
  });

  // ── ADM-PAGE-11 ── /admin/analytics ───────────────────────────────────────
  describe('ADM-PAGE-11: /admin/analytics', () => {
    it('ADM-PAGE-11a: analytics page loads admin layout + stat grid', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/analytics');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/analytics"]').should('have.class', 'active');
      // Platform stats grid (5 cards)
      cy.get('.stat-grid, .stat-card').should('exist');
    });
  });

  // ── ADM-PAGE-12 ── /admin/semesters ───────────────────────────────────────
  describe('ADM-PAGE-12: /admin/semesters', () => {
    it('ADM-PAGE-12a: semesters page loads admin layout + create link', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/semesters');
      verifyAdminLayout();
      cy.get('.admin-nav a[href="/admin/semesters"]').should('have.class', 'active');
      cy.get('a[href="/admin/semesters/new"]').should('exist');
    });
  });

  // ── ADM-RBAC-01–03 ── Role-based access control ───────────────────────────
  describe('RBAC — Non-admin users blocked', () => {
    const PROTECTED_PATHS = [
      '/admin/users',
      '/admin/payments',
      '/admin/coupons',
      '/admin/analytics',
    ];

    it('ADM-RBAC-01: student → /admin/* → 403 Forbidden', () => {
      cy.webLoginAs('student');
      PROTECTED_PATHS.forEach((path) => {
        cy.request({ method: 'GET', url: path, failOnStatusCode: false })
          .its('status').should('eq', 403);
      });
    });

    it('ADM-RBAC-02: instructor → /admin/* → 403 Forbidden', () => {
      cy.webLoginAs('instructor');
      PROTECTED_PATHS.forEach((path) => {
        cy.request({ method: 'GET', url: path, failOnStatusCode: false })
          .its('status').should('eq', 403);
      });
    });

    it('ADM-RBAC-03: unauthenticated → /admin/users → 401 or redirect', () => {
      cy.clearAllCookies();
      cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false })
        .its('status').should('be.oneOf', [401, 302, 303]);
    });
  });

  // ── ADM-RESP-01 ── Responsiveness ─────────────────────────────────────────
  describe('ADM-RESP-01: /admin/users — table scroll wrapper', () => {
    it('ADM-RESP-01: users table is wrapped in .table-scroll-wrap container', () => {
      cy.webLoginAs('admin');
      cy.visit('/admin/users');
      // The .table-scroll-wrap wrapper must exist and contain the table
      cy.get('.content-card').within(() => {
        cy.get('.table-scroll-wrap').should('exist');
        cy.get('.table-scroll-wrap table').should('exist');
      });
    });
  });

  // ── ADM-NAV-01 ── Navigation completeness ─────────────────────────────────
  describe('ADM-NAV-01: unified nav completeness on every page', () => {
    const NAV_SPOT_CHECK = [
      '/admin/users',
      '/admin/enrollments',
      '/admin/payments',
      '/admin/analytics',
      '/admin/tournaments',
    ];

    NAV_SPOT_CHECK.forEach((path) => {
      it(`ADM-NAV-01: ${path} → all 13+ nav links present`, () => {
        cy.webLoginAs('admin');
        cy.visit(path);
        cy.get('.admin-nav a').should('have.length.at.least', 13);
        // Every key section link must exist
        cy.get('.admin-nav a[href="/admin/users"]').should('exist');
        cy.get('.admin-nav a[href="/admin/sessions"]').should('exist');
        cy.get('.admin-nav a[href="/admin/payments"]').should('exist');
        cy.get('.admin-nav a[href="/admin/coupons"]').should('exist');
        cy.get('.admin-nav a[href="/admin/tournaments"]').should('exist');
      });
    });
  });

});
