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

    // Admin nav (from admin_base.html — dropdown nav after menu restructure)
    // Flat: Analytics, Game Config (/game-presets), System (/system-events)
    // Dropdown groups: People→users/instructors/sport-directors, Venues→locations/pitches,
    //   Programs→semesters/enrollments, Events→tournaments, Sessions, Finance→payments/coupons
    cy.get('.admin-nav').should('be.visible');
    cy.get('.admin-nav a[href="/admin/users"]').should('exist');
    cy.get('.admin-nav a[href="/admin/semesters"]').should('exist');
    cy.get('.admin-nav a[href="/admin/sessions"]').should('exist');
    cy.get('.admin-nav a[href="/admin/tournaments"]').should('exist');
    cy.get('.admin-nav a[href="/admin/payments"]').should('exist');
    cy.get('.admin-nav a[href="/admin/locations"]').should('exist');
    cy.get('.admin-nav a[href="/admin/game-presets"]').should('exist');
    cy.get('.admin-nav a[href="/admin/analytics"]').should('exist');
    cy.get('.admin-nav a[href="/admin/system-events"]').should('exist');
  });

  // ── ADM-DASH-03 ────────────────────────────────────────────────────────────
  it('ADM-DASH-03: admin /dashboard → KPI cards and admin-container present', () => {
    cy.webLoginAs('admin');
    cy.visit('/dashboard');

    // admin-container wrapper (from admin_base.html)
    cy.get('.admin-container').should('exist');

    // 4-layer operational dashboard: KPI row with metric cards (replaces old action-card grid)
    cy.get('.kpi-row').should('exist');
    cy.get('.kpi-card').should('have.length.at.least', 3);

    // KPI cards link to key admin sections
    cy.get('.kpi-card[href="/admin/users"]').should('exist');
  });

});
