/**
 * STU-JOURNEY-01–07 — Student core journey: skill progression end-to-end validation
 * DB scenario: student_skill_history
 *
 * Purpose: Prove that the student skill progression system works end-to-end.
 * Not a coverage test — a causal correctness test.
 *
 * Seeded state (student_skill_history scenario):
 *   - Student rdias@manchestercity.com: LFA license, 29 skills @ 70.0 baseline, onboarding done
 *   - TOURN-E2E-HIST-1 (COMPLETED, ~2 months ago): student 2nd of 2 → delta expected NEGATIVE
 *   - TOURN-E2E-HIST-2 (COMPLETED, ~1 month ago):  student 1st of 2 → delta expected POSITIVE
 *   - Expected EMA: 70.0 (baseline) → 64.0 (after T1, 2nd of 2) → 71.2 (after T2, 1st of 2)
 *
 * Tests:
 *   STU-JOURNEY-01  /dashboard renders student layout, no 500
 *   STU-JOURNEY-02  /dashboard/LFA_FOOTBALL_PLAYER accessible after onboarding (not 403/500)
 *   STU-JOURNEY-03  /skills loads — has_lfa_license=True, no 500
 *   STU-JOURNEY-04  GET /skills/data → 29 skills present, average_level > 0
 *   STU-JOURNEY-05  /skills/history — EMA chart renders (canvas has dimensions, NOT empty state)
 *   STU-JOURNEY-06  Causal DOM proof — table rows: name → placement badge → delta class
 *   STU-JOURNEY-07  Causal API proof — per-tournament delta sign matches placement rank
 */
import '../../../support/web_commands';

describe('Student Core Journey — Skill Progression E2E', {
  tags: ['@web', '@student', '@journey'],
}, () => {

  before(() => {
    cy.resetDb('student_skill_history');
  });

  beforeEach(() => {
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  // ── STU-JOURNEY-01 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-01: /dashboard renders student layout, no 500', () => {
    cy.visit('/dashboard');
    cy.url().should('include', '/dashboard');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    cy.get('nav, .s-header, .student-header, .site-header').should('exist');
  });

  // ── STU-JOURNEY-02 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-02: /dashboard/LFA_FOOTBALL_PLAYER accessible after onboarding', () => {
    cy.request({
      method: 'GET',
      url: '/dashboard/LFA_FOOTBALL_PLAYER',
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.not.equal(500);
      expect(resp.status).to.not.equal(403);
      expect(resp.body).to.not.include('Internal Server Error');
    });
  });

  // ── STU-JOURNEY-03 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-03: /skills page loads — has_lfa_license=True, no 500', () => {
    cy.visit('/skills');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    cy.get('h1, h2, .page-title, .s-header').should('exist');
  });

  // ── STU-JOURNEY-04 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-04: GET /skills/data → 29 skills present, average_level > 0', () => {
    cy.request({ method: 'GET', url: '/skills/data', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.equal(200);
        const data = resp.body;
        expect(data).to.have.property('skills');
        expect(Object.keys(data.skills).length).to.be.at.least(29);
        expect(data.average_level).to.be.greaterThan(0);
      });
  });

  // ── STU-JOURNEY-05 ─────────────────────────────────────────────────────────
  // Visual validation: the chart actually renders with data — not a blank/empty canvas.
  // Chart.js only sets canvas width/height after drawing; a blank chart stays at 0×0
  // or shows the empty-state div. Both are checked explicitly.
  it('STU-JOURNEY-05: /skills/history — Chart.js EMA chart renders with data (not empty canvas)', () => {
    cy.visit('/skills/history?skill=passing');

    // Wait for the async fetch to complete — #sh-content appears after data loads
    cy.get('#sh-content', { timeout: 15000 }).should('be.visible');

    // Empty state must NOT be shown (we have seeded tournament data)
    cy.get('#sh-empty').should('not.be.visible');

    // Chart wrapper must be visible (the code sets it display:block when tl.length > 0)
    cy.get('#sh-chart-wrap').should('be.visible');

    // Canvas must have non-zero rendered dimensions — Chart.js sets these on draw
    cy.get('canvas#skill-chart').then(($canvas) => {
      expect($canvas[0].width).to.be.greaterThan(0);
      expect($canvas[0].height).to.be.greaterThan(0);
    });

    // Stat cards must show real (non-placeholder) values
    cy.get('#sh-count').should('not.contain.text', '—').and('contain.text', '2');
    cy.get('#sh-baseline').should('not.contain.text', '—');

    // Net delta is positive (2nd→1st arc ends above baseline)
    cy.get('#sh-delta').should('have.class', 'sh-delta-pos');

    // Audit table is visible and has exactly 2 rows (one per tournament)
    cy.get('#sh-table-card').should('be.visible');
    cy.get('#sh-table-body tr').should('have.length', 2);
  });

  // ── STU-JOURNEY-06 ─────────────────────────────────────────────────────────
  // Causal DOM proof: the audit table rows explicitly link tournament name →
  // placement badge → delta class. Each cell is a traceable event in the EMA chain.
  it('STU-JOURNEY-06: Causal DOM proof — tournament name → placement → delta class per row', () => {
    cy.visit('/skills/history?skill=passing');
    cy.get('#sh-content', { timeout: 15000 }).should('be.visible');
    cy.get('#sh-table-body tr').should('have.length', 2);

    // Row 1: placed 2nd out of 2 → skill signal was LOW → delta NEGATIVE
    cy.get('#sh-table-body tr').eq(0).within(() => {
      // Tournament name is traceable in the table cell
      cy.contains('E2E History Tournament 1').should('exist');
      // Placement badge: 🥈 2nd (sh-p2 class)
      cy.get('.sh-placement-badge.sh-p2').should('exist');
      // Delta class on the last cell: negative (placed last — skill dropped)
      cy.get('td').last().should('have.class', 'sh-delta-neg');
    });

    // Row 2: placed 1st out of 2 → skill signal was HIGH → delta POSITIVE
    cy.get('#sh-table-body tr').eq(1).within(() => {
      cy.contains('E2E History Tournament 2').should('exist');
      // Placement badge: 🥇 1st (sh-p1 class)
      cy.get('.sh-placement-badge.sh-p1').should('exist');
      // Delta class: positive (placed 1st — skill recovered and grew)
      cy.get('td').last().should('have.class', 'sh-delta-pos');
    });
  });

  // ── STU-JOURNEY-07 ─────────────────────────────────────────────────────────
  // Causal API proof: the JSON response explicitly maps tournament name → placement
  // → delta_from_previous sign. This proves the EMA formula produces the correct
  // directional output for each event in the skill history chain.
  it('STU-JOURNEY-07: Causal API proof — JSON delta sign matches placement rank per tournament', () => {
    cy.request({ method: 'GET', url: '/skills/history/data?skill=passing', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.equal(200);
        const { timeline, baseline, current_level, total_delta } = resp.body;

        expect(timeline).to.have.length(2);

        // Tournament 1: placed 2nd of 2 (last place) → delta_from_previous MUST be negative
        const t1 = timeline[0];
        expect(t1.tournament_name).to.equal('E2E History Tournament 1');
        expect(t1.placement).to.equal(2);
        expect(t1.total_players).to.equal(2);
        expect(t1.delta_from_previous).to.be.lessThan(0,
          `T1: placed ${t1.placement}/${t1.total_players} → expected negative delta, got ${t1.delta_from_previous}`
        );

        // Tournament 2: placed 1st of 2 (winner) → delta_from_previous MUST be positive
        const t2 = timeline[1];
        expect(t2.tournament_name).to.equal('E2E History Tournament 2');
        expect(t2.placement).to.equal(1);
        expect(t2.total_players).to.equal(2);
        expect(t2.delta_from_previous).to.be.greaterThan(0,
          `T2: placed ${t2.placement}/${t2.total_players} → expected positive delta, got ${t2.delta_from_previous}`
        );

        // EMA compounds correctly: T2 value > T1 value (recovery after loss)
        expect(t2.skill_value_after).to.be.greaterThan(t1.skill_value_after,
          `EMA must rise after placing 1st: T2=${t2.skill_value_after} should exceed T1=${t1.skill_value_after}`
        );

        // Net result: current_level > baseline (positive arc wins overall)
        expect(total_delta).to.be.greaterThan(0,
          `Net delta after 2nd→1st arc should be positive (baseline=${baseline}, current=${current_level})`
        );
      });
  });

});
