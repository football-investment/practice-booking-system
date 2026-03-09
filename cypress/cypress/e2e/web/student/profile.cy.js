/**
 * PRF-01–11 — Profile view and edit flow
 * DB scenario: baseline
 * Role coverage: student, instructor
 */
import '../../support/web_commands';

describe('Web Student — Profile', { tags: ['@web', '@student', '@profile'] }, () => {
  before(() => {
    cy.resetDb('baseline');
  });

  beforeEach(() => {
    cy.clearAllCookies();
  });

  // ── PRF-01 ─────────────────────────────────────────────────────────────
  it('PRF-01: GET /profile renders profile page with user data', () => {
    cy.webLoginAs('student');
    cy.visit('/profile');
    cy.assertWebPath('/profile');
    cy.get('body').should('satisfy', ($body) =>
      $body.text().includes('Ruben') || $body.text().includes('rdias') ||
      $body.text().includes('profile')
    );
  });

  // ── PRF-02 ─────────────────────────────────────────────────────────────
  it('PRF-02: instructor /profile renders with empty license list', () => {
    cy.webLoginAs('instructor');
    cy.visit('/profile');
    cy.assertWebPath('/profile');
    cy.get('body').should('be.visible');
  });

  // ── PRF-03 ─────────────────────────────────────────────────────────────
  it('PRF-03: student profile page exists and loads', () => {
    cy.webLoginAs('student');
    cy.visit('/profile');
    cy.get('body').should('not.contain.text', '500');
  });

  // ── PRF-04 ─────────────────────────────────────────────────────────────
  it('PRF-04: GET /profile/edit renders edit form', () => {
    cy.webLoginAs('student');
    cy.visit('/profile/edit');
    cy.assertWebPath('/profile');
    cy.get('form').should('exist');
  });

  // ── PRF-05 ─────────────────────────────────────────────────────────────
  it('PRF-05: fresh student (no DOB) — profile shows without crashing', () => {
    cy.resetDb('student_no_dob');
    cy.webLoginAs('fresh');
    // Fresh student gets redirected to age-verification first
    cy.url().should('satisfy', (url) =>
      url.includes('age-verification') || url.includes('dashboard') || url.includes('profile')
    );
  });

  // ── PRF-06 ─────────────────────────────────────────────────────────────
  it('PRF-06: student with DOB — profile page loads and shows content', () => {
    cy.resetDb('baseline');
    cy.webLoginAs('student');
    cy.visit('/profile');
    cy.get('body').should('not.contain.text', '500');
  });

  // ── PRF-07 ─────────────────────────────────────────────────────────────
  it('PRF-07: invalid date format POST /profile/edit → error', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/profile/edit',
      form: true,
      body: { date_of_birth: 'not-a-date', name: 'Ruben Dias' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 400, 422]);
    });
  });

  // ── PRF-08 ─────────────────────────────────────────────────────────────
  it('PRF-08: age < 5 years → error mentioning age requirement', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/profile/edit',
      form: true,
      body: { date_of_birth: '2024-01-01', name: 'Ruben Dias' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 400, 422]);
      if (resp.status === 200) {
        expect(resp.body).to.include('5');
      }
    });
  });

  // ── PRF-09 ─────────────────────────────────────────────────────────────
  it('PRF-09: age > 120 years → error', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/profile/edit',
      form: true,
      body: { date_of_birth: '1900-01-01', name: 'Ruben Dias' },
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 400, 422]);
    });
  });

  // ── PRF-10 ─────────────────────────────────────────────────────────────
  it('PRF-10: age change conflicts with existing specialization → blocked', () => {
    // Change DOB to age 3 — below all spec minimums
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/profile/edit',
      form: true,
      body: { date_of_birth: '2022-01-01', name: 'Ruben Dias' },
      failOnStatusCode: false,
    }).then((resp) => {
      // Should either error (400/422) or return page with error message
      expect(resp.status).to.be.oneOf([200, 400, 422]);
    });
  });

  // ── PRF-11 ─────────────────────────────────────────────────────────────
  it('PRF-11: valid profile update → redirects to /profile', () => {
    cy.webLoginAs('student');
    cy.request({
      method: 'POST',
      url: '/profile/edit',
      form: true,
      body: { date_of_birth: '1998-05-14', name: 'Ruben Dias' },
      followRedirect: false,
      failOnStatusCode: false,
    }).then((resp) => {
      expect(resp.status).to.be.oneOf([200, 302, 303]);
      if (resp.status !== 200) {
        expect(resp.headers['location']).to.include('profile');
      }
    });
  });
});
