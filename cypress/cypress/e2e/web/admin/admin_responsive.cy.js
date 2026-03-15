/**
 * Admin UI Responsive Layout Tests — ADM-RESP-01 to ADM-RESP-12
 *
 * Breakpoints:
 *   Desktop : ≥1024px  — all columns visible, nav horizontal
 *   Tablet  : 640–1023px — [data-priority="low"] hidden, nav wraps
 *   Mobile  : ≤639px   — [data-priority="low"]+[data-priority="medium"] hidden,
 *                          hamburger nav, filter bar stacked
 */
import '../../../support/web_commands';

// ── Viewport presets ──────────────────────────────────────────────────────────
const DESKTOP = { width: 1280, height: 800 };
const TABLET  = { width: 768,  height: 1024 };
const MOBILE  = { width: 390,  height: 844 };

describe('Admin Responsive Layout', {
  tags: ['@web', '@admin', '@responsive'],
}, () => {

  before(() => {
    cy.resetDb('baseline');
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // ── ADM-RESP-01: Desktop — table-scroll-wrap exists on /admin/users ───────
  it('ADM-RESP-01 desktop: users table wrapped in .table-scroll-wrap', () => {
    cy.viewport(DESKTOP.width, DESKTOP.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    cy.get('.table-scroll-wrap').should('exist');
  });

  // ── ADM-RESP-02: Desktop — all columns visible (no data-priority hidden) ──
  it('ADM-RESP-02 desktop: all user table columns visible', () => {
    cy.viewport(DESKTOP.width, DESKTOP.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    // ID column (data-priority="low") must be visible at desktop
    cy.get('th[data-priority="low"]').first().should('be.visible');
    // Specialization column (data-priority="medium") must be visible at desktop
    cy.get('th[data-priority="medium"]').first().should('be.visible');
  });

  // ── ADM-RESP-03: Desktop — hamburger button not visible ───────────────────
  it('ADM-RESP-03 desktop: hamburger nav button not shown', () => {
    cy.viewport(DESKTOP.width, DESKTOP.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    cy.get('.nav-hamburger').should('not.be.visible');
  });

  // ── ADM-RESP-04: Desktop — nav links visible inline ───────────────────────
  it('ADM-RESP-04 desktop: nav links visible without toggling', () => {
    cy.viewport(DESKTOP.width, DESKTOP.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    cy.get('.admin-nav .nav-item').first().should('be.visible');
  });

  // ── ADM-RESP-05: Tablet — low-priority columns hidden ────────────────────
  it('ADM-RESP-05 tablet: low-priority columns hidden', () => {
    cy.viewport(TABLET.width, TABLET.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    // [data-priority="low"] should be hidden at 768px (≤1023px breakpoint)
    cy.get('th[data-priority="low"]').first().should('not.be.visible');
  });

  // ── ADM-RESP-06: Tablet — medium-priority columns NOT hidden by CSS ──────
  it('ADM-RESP-06 tablet: medium-priority columns not hidden by CSS', () => {
    cy.viewport(TABLET.width, TABLET.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    // [data-priority="medium"] must not have display:none at tablet (≤639px rule should NOT apply)
    // Use computed CSS check — avoids Cypress overflow-visibility quirk with table cells
    cy.get('th[data-priority="medium"]').first()
      .should('have.css', 'display')
      .and('not.equal', 'none');
  });

  // ── ADM-RESP-07: Mobile — both low and medium columns hidden ─────────────
  it('ADM-RESP-07 mobile: low AND medium columns hidden', () => {
    cy.viewport(MOBILE.width, MOBILE.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    cy.get('th[data-priority="low"]').first().should('not.be.visible');
    cy.get('th[data-priority="medium"]').first().should('not.be.visible');
  });

  // ── ADM-RESP-08: Mobile — hamburger button visible ────────────────────────
  it('ADM-RESP-08 mobile: hamburger button is visible', () => {
    cy.viewport(MOBILE.width, MOBILE.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    cy.get('.nav-hamburger').should('be.visible');
  });

  // ── ADM-RESP-09: Mobile — nav collapsed by default, opens on click ────────
  it('ADM-RESP-09 mobile: nav collapses then opens on hamburger click', () => {
    cy.viewport(MOBILE.width, MOBILE.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    // Nav links should be invisible before click (collapsed)
    cy.get('.admin-nav .nav-item').first().should('not.be.visible');
    // Click hamburger → nav opens
    cy.get('.nav-hamburger').click();
    cy.get('.admin-nav .nav-item').first().should('be.visible');
  });

  // ── ADM-RESP-10: Mobile — filter bar stacks vertically ───────────────────
  it('ADM-RESP-10 mobile: filter bar stacks vertically', () => {
    cy.viewport(MOBILE.width, MOBILE.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    cy.get('.filter-bar').should('have.css', 'flex-direction', 'column');
  });

  // ── ADM-RESP-11: Mobile — table-scroll-wrap has correct overflow CSS ──────
  // Note: .table-scroll-wrap in bookings/payments is inside {% if data %} blocks.
  // Test the CSS property on the users page (always has data) to verify the class works.
  it('ADM-RESP-11 mobile: table-scroll-wrap has overflow-x auto CSS', () => {
    cy.viewport(MOBILE.width, MOBILE.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    cy.get('.table-scroll-wrap').first()
      .should('have.css', 'overflow-x', 'auto');
  });

  // ── ADM-RESP-12: Mobile — payments table wrapped in table-scroll-wrap ─────
  it('ADM-RESP-12 mobile: payments table has table-scroll-wrap', () => {
    cy.viewport(MOBILE.width, MOBILE.height);
    cy.webLoginAs('admin');
    cy.visit('/admin/payments');
    cy.get('.table-scroll-wrap').should('exist');
  });
});
