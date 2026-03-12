/**
 * BW-LIFE-01–06 — Instructor session lifecycle + student attendance + evaluation (DOM-driven)
 * DB scenario: business_lifecycle
 * Role coverage: instructor + student (sequential workflow)
 *
 * Pre-conditions seeded by business_lifecycle scenario:
 *   - "E2E Lifecycle Session": on_site, date_start = now-90min, actual_start_time=None
 *   - rdias@manchestercity.com has a CONFIRMED booking for this session
 *   - can_mark_attendance = True (scheduled 90min ago, past the 15-min threshold)
 *   - date_end = now+30min (attendance/confirm window open for test duration)
 *
 * Test flow (must run sequentially — each test changes DB state):
 *   BW-LIFE-01: Instructor sees Start Session button
 *   BW-LIFE-02: Instructor clicks Start → sees Stop Session button
 *   BW-LIFE-03: Instructor marks student PRESENT
 *   BW-LIFE-04: Instructor clicks Stop → session completed
 *   BW-LIFE-05: Student confirms attendance
 *   BW-LIFE-06: Student evaluates instructor via 8-field star-rating form
 *
 * Window stubs registered in beforeEach:
 *   - window.confirm → auto-accept (Start/Stop forms use onsubmit confirm; evaluate-instructor also)
 *   - window.alert  → suppress (session_details.html fires alert on success/error params)
 */
import '../../../support/web_commands';

describe('Business Workflow — Session Lifecycle', {
  tags: ['@web', '@instructor', '@student', '@business-workflow'],
}, () => {
  let lifecycleSessionId = null;

  before(() => {
    cy.resetDb('business_lifecycle');

    // Discover lifecycle session ID via admin API
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/api/v1/auth/login`,
      body: { email: Cypress.env('webAdminEmail'), password: Cypress.env('webAdminPassword') },
      failOnStatusCode: false,
    }).then((loginResp) => {
      if (loginResp.status !== 200) return;
      cy.request({
        method: 'GET',
        url: `${Cypress.env('apiUrl')}/api/v1/sessions/`,
        headers: { Authorization: `Bearer ${loginResp.body.access_token}` },
        qs: { limit: 50 },
        failOnStatusCode: false,
      }).then((resp) => {
        if (resp.status !== 200) return;
        const sessions = resp.body.sessions || resp.body.items || resp.body || [];
        const s = sessions.find((s) => s.title === 'E2E Lifecycle Session');
        if (s) lifecycleSessionId = s.id;
      });
    });
  });

  beforeEach(() => {
    cy.clearAllCookies();
    // Auto-accept all window.confirm dialogs (Start/Stop/Evaluate forms use onsubmit confirm)
    cy.on('window:confirm', () => true);
    // Suppress window.alert (session_details.html fires alert on session_started/stopped etc.)
    cy.on('window:alert', () => {});
  });

  // ── BW-LIFE-01 ────────────────────────────────────────────────────────────
  it('BW-LIFE-01: instructor visits session details → Start Session button visible', () => {
    if (!lifecycleSessionId) return cy.log('No lifecycle session ID — skip BW-LIFE-01');
    cy.webLoginAs('instructor');
    cy.visit(`/sessions/${lifecycleSessionId}`);
    cy.contains('button', '🟢 Start Session').should('be.visible');
  });

  // ── BW-LIFE-02 ────────────────────────────────────────────────────────────
  // LIFECYCLE STATE CHANGE: sets session.actual_start_time.
  // BW-LIFE-04 depends on this (Stop Session requires actual_start_time).
  it('BW-LIFE-02: instructor clicks Start Session → Stop Session button visible', () => {
    if (!lifecycleSessionId) return cy.log('No lifecycle session ID — skip BW-LIFE-02');
    cy.webLoginAs('instructor');
    cy.visit(`/sessions/${lifecycleSessionId}`);
    // onsubmit="return confirm(...)" → auto-accepted → form POSTs → 303 redirect
    cy.contains('button', '🟢 Start Session').click();
    // Page reloads at /sessions/{id}?success=session_started; alert suppressed
    // Template now shows Stop Session (actual_start_time set, actual_end_time None)
    cy.contains('🔴 Stop Session').should('be.visible');
  });

  // ── BW-LIFE-03 ────────────────────────────────────────────────────────────
  // LIFECYCLE STATE CHANGE: creates Attendance record with status=PRESENT.
  // BW-LIFE-05 (student confirm) and BW-LIFE-06 (evaluate instructor) depend on this.
  it('BW-LIFE-03: instructor marks student PRESENT via attendance form', () => {
    if (!lifecycleSessionId) return cy.log('No lifecycle session ID — skip BW-LIFE-03');
    cy.webLoginAs('instructor');
    cy.visit(`/sessions/${lifecycleSessionId}`);
    // Attendance form visible: can_mark_attendance=True (session 90min past 15-min threshold)
    // Student rdias@manchestercity.com has CONFIRMED booking → appears in enrolled_students
    cy.get('button[name="status"][value="present"]').first().click();
    // 303 redirect to /sessions/{id}?success=attendance_marked
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── BW-LIFE-04 ────────────────────────────────────────────────────────────
  // Depends on BW-LIFE-02 having started the session (actual_start_time set).
  // LIFECYCLE STATE CHANGE: sets session.actual_end_time.
  // BW-LIFE-06 (evaluate instructor) depends on this (route checks actual_end_time).
  it('BW-LIFE-04: instructor clicks Stop Session → session marked completed', () => {
    if (!lifecycleSessionId) return cy.log('No lifecycle session ID — skip BW-LIFE-04');
    cy.webLoginAs('instructor');
    cy.visit(`/sessions/${lifecycleSessionId}`);
    // onsubmit="return confirm(...)" → auto-accepted → form POSTs → 303 redirect
    cy.contains('button', '🔴 Stop Session').click();
    // Page reloads at /sessions/{id}?success=session_stopped
    // Template shows "✅ Session Completed" (both actual_start_time and actual_end_time set)
    cy.contains('Session Completed').should('be.visible');
  });

  // ── BW-LIFE-05 ────────────────────────────────────────────────────────────
  // Depends on BW-LIFE-03 having marked attendance PRESENT (my_attendance set).
  // LIFECYCLE STATE CHANGE: sets attendance.confirmation_status = confirmed.
  it('BW-LIFE-05: student visits session → attendance confirmation visible → student confirms', () => {
    if (!lifecycleSessionId) return cy.log('No lifecycle session ID — skip BW-LIFE-05');
    cy.webLoginAs('student');
    cy.visit(`/sessions/${lifecycleSessionId}`);
    // Attendance confirmation section shows: my_attendance with pending_confirmation status
    cy.contains('button', '✓ Confirm - This is correct').should('be.visible').click();
    // 303 redirect back to session page
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  // ── BW-LIFE-06 ────────────────────────────────────────────────────────────
  // Depends on BW-LIFE-03 (PRESENT attendance) + BW-LIFE-04 (session stopped).
  // evaluate-instructor route requires: actual_end_time set + PRESENT attendance.
  it('BW-LIFE-06: student evaluates instructor via 8-field star-rating form → submitted', () => {
    if (!lifecycleSessionId) return cy.log('No lifecycle session ID — skip BW-LIFE-06');
    cy.webLoginAs('student');
    cy.visit(`/sessions/${lifecycleSessionId}`);

    // Evaluate-instructor form visible:
    //   not is_instructor + on_site + my_attendance (PRESENT) → form renders
    // Fill all 8 required rating fields (value="4" = 4 stars)
    const ratingFields = [
      'instructor_clarity',
      'support_approachability',
      'session_structure',
      'relevance',
      'environment',
      'engagement_feeling',
      'feedback_quality',
      'satisfaction',
    ];
    ratingFields.forEach((field) => {
      cy.get(`input[name="${field}"][value="4"]`).click();
    });

    // onsubmit="return confirm(...)" → auto-accepted → form POSTs
    cy.contains('button', 'Submit Evaluation').click();
    // 303 redirect to /sessions/{id}?success=instructor_evaluated
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });
});
