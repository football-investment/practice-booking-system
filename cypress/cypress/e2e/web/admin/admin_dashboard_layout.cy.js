/**
 * ADM-DASH-01–03 — Admin Dashboard unified layout verification
 *
 * Verifies that /dashboard (admin role) renders the unified admin_base.html
 * layout: admin-header, admin nav bar with all 14 links, admin-container,
 * and the admin action cards grid.
 */
import '../../../support/web_commands';

describe('Admin Dashboard — Unified Layout', {
  tags: ['@web', '@admin', '@layout'],
}, () => {

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // ── ADM-DASH-01 ────────────────────────────────────────────────────────────
  it('ADM-DASH-01: admin visits /dashboard → unified admin header present', () => {
    cy.webLoginAs('admin');
    cy.visit('/dashboard');
    cy.url().should('include', '/dashboard');

    // Unified admin header (from admin_base.html)
    cy.get('.admin-header').should('be.visible');
    cy.get('.admin-header').should('contain.text', 'ADMIN');
  });

  // ── ADM-DASH-02 ────────────────────────────────────────────────────────────
  it('ADM-DASH-02: admin /dashboard → unified nav bar with all key links', () => {
    cy.webLoginAs('admin');
    cy.visit('/dashboard');

    // Admin nav (from admin_base.html — 14 items)
    cy.get('.admin-nav').should('be.visible');
    cy.get('.admin-nav a[href="/admin/users"]').should('exist');
    cy.get('.admin-nav a[href="/admin/sessions"]').should('exist');
    cy.get('.admin-nav a[href="/admin/bookings"]').should('exist');
    cy.get('.admin-nav a[href="/admin/enrollments"]').should('exist');
    cy.get('.admin-nav a[href="/admin/semesters"]').should('exist');
    cy.get('.admin-nav a[href="/admin/analytics"]').should('exist');
    cy.get('.admin-nav a[href="/admin/tournaments"]').should('exist');
    cy.get('.admin-nav a[href="/admin/locations"]').should('exist');
    cy.get('.admin-nav a[href="/admin/game-presets"]').should('exist');
    cy.get('.admin-nav a[href="/admin/system-events"]').should('exist');
    cy.get('.admin-nav a[href="/admin/payments"]').should('exist');
    cy.get('.admin-nav a[href="/admin/coupons"]').should('exist');
    cy.get('.admin-nav a[href="/admin/invitation-codes"]').should('exist');
  });

  // ── ADM-DASH-03 ────────────────────────────────────────────────────────────
  it('ADM-DASH-03: admin /dashboard → action cards grid and admin-container present', () => {
    cy.webLoginAs('admin');
    cy.visit('/dashboard');

    // admin-container wrapper (from admin_base.html)
    cy.get('.admin-container').should('exist');

    // Admin action cards grid
    cy.get('[data-testid="admin-dashboard-grid"]').should('be.visible');
    cy.get('[data-testid="admin-dashboard-grid"] .admin-action-card').should('have.length.at.least', 5);

    // Spot-check key action cards
    cy.get('[data-testid="admin-dashboard-grid"]').should('contain.text', 'User Management');
    cy.get('[data-testid="admin-dashboard-grid"]').should('contain.text', 'Enrollment Management');
    cy.get('[data-testid="admin-dashboard-grid"]').should('contain.text', 'Payment Management');
  });

});
