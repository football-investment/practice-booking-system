/**
 * STU-JOURNEY-01–06 — Student core journey: onboarding state → dashboard → skills → skill history
 * DB scenario: student_skill_history
 * Role coverage: student (primary)
 *
 * This suite validates the system against the core user journey:
 *   onboarding_completed → /dashboard → /skills (29 bars) → /skills/history (EMA chart)
 *
 * Tests covered:
 *   STU-JOURNEY-01  /dashboard loads with student nav and no 500
 *   STU-JOURNEY-02  /dashboard spec entry point accessible (LFA_FOOTBALL_PLAYER)
 *   STU-JOURNEY-03  /skills page renders — has_lfa_license=True, no 500
 *   STU-JOURNEY-04  /skills/data JSON endpoint returns 29 skills with level > 0
 *   STU-JOURNEY-05  /skills/history page renders with Chart.js canvas
 *   STU-JOURNEY-06  /skills/history/data?skill=passing returns EMA timeline (≥1 entry, skill_value_after > 0)
 */
import '../../../support/web_commands';

describe('Student Core Journey', {
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
  it('STU-JOURNEY-01: /dashboard → student layout, no 500', () => {
    cy.visit('/dashboard');
    cy.url().should('include', '/dashboard');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    // Student header / nav must be present
    cy.get('.s-header, .student-header, .site-header, nav').should('exist');
    // Content area renders (spec cards or dashboard section)
    cy.get('.admin-container, .s-content, main, .dashboard-content, .container').should('exist');
  });

  // ── STU-JOURNEY-02 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-02: /dashboard/LFA_FOOTBALL_PLAYER → accessible after onboarding', () => {
    cy.request({
      method: 'GET',
      url: '/dashboard/LFA_FOOTBALL_PLAYER',
      failOnStatusCode: false,
    }).then((resp) => {
      // Must not be 500 — either 200 (spec dashboard) or redirect (303) to it
      expect(resp.status).to.not.equal(500);
      expect(resp.body).to.not.include('Internal Server Error');
      // Not a 403 either — student has onboarding_completed=True
      expect(resp.status).to.not.equal(403);
    });
  });

  // ── STU-JOURNEY-03 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-03: /skills page loads — has_lfa_license=True, no 500', () => {
    cy.visit('/skills');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    // Page title or heading
    cy.get('h1, h2, .page-title, .s-header').should('exist');
    // Skills section must exist (even before JS lazy-load)
    cy.get('body').should('include.text', 'skill');
  });

  // ── STU-JOURNEY-04 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-04: GET /skills/data → JSON with 29 skills, average_level > 0', () => {
    cy.request({ method: 'GET', url: '/skills/data', failOnStatusCode: false })
      .then((resp) => {
        expect(resp.status).to.equal(200);
        const data = resp.body;
        expect(data).to.have.property('skills');
        const skillKeys = Object.keys(data.skills);
        // All 29 skills must be present
        expect(skillKeys.length).to.be.at.least(29);
        // Average level should be above 0 (seeded at 70.0)
        expect(data.average_level).to.be.greaterThan(0);
      });
  });

  // ── STU-JOURNEY-05 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-05: /skills/history page renders with Chart.js canvas', () => {
    cy.visit('/skills/history');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    // The Chart.js canvas element must exist
    cy.get('canvas').should('exist');
    // Skill selector dropdown (all 29 skills)
    cy.get('select, .skill-selector').should('exist');
  });

  // ── STU-JOURNEY-06 ─────────────────────────────────────────────────────────
  it('STU-JOURNEY-06: GET /skills/history/data?skill=passing → EMA timeline ≥1 entry, skill_value_after > 0', () => {
    cy.request({
      method: 'GET',
      url: '/skills/history/data?skill=passing',
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.equal(200);
      const data = resp.body;
      expect(data).to.have.property('skill', 'passing');
      expect(data).to.have.property('timeline');
      expect(data.timeline).to.have.length.at.least(1);
      // At least one entry must have skill_value_after > 0
      const hasPositiveValue = data.timeline.some((e) => e.skill_value_after > 0);
      expect(hasPositiveValue).to.be.true;
      // Verify EMA delta direction: 2nd tournament (placement 1) should push value higher
      if (data.timeline.length >= 2) {
        const first  = data.timeline[0].skill_value_after;
        const second = data.timeline[1].skill_value_after;
        expect(second).to.be.greaterThan(first);
      }
    });
  });

});
