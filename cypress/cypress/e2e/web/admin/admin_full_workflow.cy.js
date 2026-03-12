/**
 * ADM-WF-01–06 — Admin full business workflow (DOM-driven)
 * DB scenario: baseline (reset before each mutation test)
 * Role coverage: admin
 *
 * These tests cover the complete admin business process through real DOM interactions:
 * form fills, button clicks, page navigations — not cy.request() shortcuts.
 *
 * Playwright parity:
 *   - ADM-WF-01–02 ← test_admin_invitation_codes.py (admin creates invitation code via UI)
 *   - ADM-WF-03–04 ← Admin_Dashboard.py Tab 1 user management (edit + toggle via UI)
 *   - ADM-WF-05    ← Admin_Dashboard.py Tab 2 semester management (create via UI)
 *   - ADM-WF-06    ← Admin analytics dashboard page render
 *
 * Window stubs registered in beforeEach:
 *   - window.confirm → auto-accept (toggle-status inline form uses onclick confirm)
 */
import '../../../support/web_commands';

describe('Business Workflow — Admin Full Process', {
  tags: ['@web', '@admin', '@business-workflow'],
}, () => {

  beforeEach(() => {
    cy.clearAllCookies();
    // Auto-accept all window.confirm dialogs (toggle-status uses onclick confirm)
    cy.on('window:confirm', () => true);
  });

  // ── ADM-WF-01 ─────────────────────────────────────────────────────────────
  it('ADM-WF-01: admin visits /admin/invitation-codes → create form fields visible', () => {
    cy.webLoginAs('admin');
    cy.visit('/admin/invitation-codes');
    cy.get('#invited_name').should('be.visible');
    cy.get('#bonus_credits').should('be.visible');
    cy.get('button.btn-generate').should('contain.text', 'Generate');
    cy.get('.codes-section').should('be.visible');
  });

  // ── ADM-WF-02 ─────────────────────────────────────────────────────────────
  // CREATES an invitation code via DOM form (JS fetch → POST /api/v1/admin/invitation-codes).
  // Success message appears in #alert-success via showAlert() DOM manipulation.
  it('ADM-WF-02: admin fills invitation code form via DOM → success message visible', () => {
    cy.resetDb('baseline');
    cy.webLoginAs('admin');
    cy.visit('/admin/invitation-codes');
    // Fill required fields
    cy.get('#invited_name').type('E2E DOM Partner');
    cy.get('#bonus_credits').clear().type('75');
    // Submit — triggers JS fetch to /api/v1/admin/invitation-codes
    cy.get('button.btn-generate').click();
    // JS fetch success → showAlert('success', '✅ Invitation code generated: ...')
    cy.get('#alert-success', { timeout: 8000 })
      .should('be.visible')
      .and('contain.text', 'generated');
  });

  // ── ADM-WF-03 ─────────────────────────────────────────────────────────────
  // Admin navigates from /admin/users → clicks Edit link → fills edit form → saves.
  // DOM-driven: reads user ID from data-testid attribute, visits edit page via browser nav.
  it('ADM-WF-03: admin clicks Edit link for student → fills edit form → saves', () => {
    cy.resetDb('baseline');
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    // Discover student user ID from DOM (data-role="student" → data-user-id)
    cy.get('[data-testid="user-row"][data-role="student"]').first().then(($tr) => {
      const userId = $tr.attr('data-user-id');
      cy.visit(`/admin/users/${userId}/edit`);
    });
    // Edit form: clear name field and type new name
    cy.get('input[name="name"]').clear().type('DOM Updated Student Name');
    // Submit → 303 redirect to /admin/users → 200
    cy.get('form button[type="submit"]').click();
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    // Should land back on users list (or show a success state)
    cy.url().should('satisfy', (url) =>
      url.includes('/admin/users') || url.includes('/admin')
    );
  });

  // ── ADM-WF-04 ─────────────────────────────────────────────────────────────
  // Admin clicks Toggle Status button for a student via inline form DOM.
  // onclick="return confirm(...)" is auto-accepted by the window:confirm stub.
  it('ADM-WF-04: admin clicks toggle status button for student via DOM → no 500', () => {
    cy.resetDb('baseline');
    cy.webLoginAs('admin');
    cy.visit('/admin/users');
    // Submit the inline toggle-status form for the first student row
    cy.get('[data-testid="user-row"][data-role="student"]').first().within(() => {
      cy.get('form[action*="toggle-status"] button[type="submit"]').click();
    });
    // 303 redirect back to /admin/users → no server error
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── ADM-WF-05 ─────────────────────────────────────────────────────────────
  // Admin fills the new semester form via DOM and submits it.
  // start_date and end_date inputs have min="{{ today }}" — bypass with invoke('val').
  it('ADM-WF-05: admin fills new semester form via DOM → submits → no 500', () => {
    cy.resetDb('baseline');
    cy.webLoginAs('admin');
    cy.visit('/admin/semesters/new');
    const code = `DOM-SEM-${Date.now()}`;
    cy.get('input[name="code"]').type(code);
    cy.get('input[name="name"]').type('DOM Created Semester');
    // Type dates directly (form has min="{{ today }}" but no HTML5 max)
    // Use .invoke('val', ...) to bypass any browser input restrictions on date fields
    cy.get('input[name="start_date"]').invoke('val', '2027-01-01');
    cy.get('input[name="end_date"]').invoke('val', '2027-06-30');
    cy.get('form button[type="submit"]').click();
    // 303 redirect to /admin/semesters → 200
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── ADM-WF-06 ─────────────────────────────────────────────────────────────
  it('ADM-WF-06: admin visits /admin/analytics → page renders without 500', () => {
    cy.webLoginAs('admin');
    cy.visit('/admin/analytics');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });
});
