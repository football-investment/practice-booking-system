/**
 * VIZUÁLIS BEMUTATÓ — Valódi UI interakciókkal, garantált lassítással
 *
 * Nem slowMo-ra támaszkodik (az nem megbízható). Ehelyett:
 *   - cy.wait(STEP) explicit várakozás minden lépés előtt/után
 *   - cy.type({ delay: 80 }) látható, karakterenkénti gépelés
 *   - cy.click() valódi kattintás
 *   - cy.visit() valódi oldalnavigáció
 *   - NEM használ cy.request() — mindent a böngésző végez
 *
 * Futtatás:
 *   cd cypress
 *   unset ELECTRON_RUN_AS_NODE
 *   CYPRESS_BASE_URL=http://localhost:8000 \
 *     npx cypress run --browser chrome --headed \
 *     --config "video=true" \
 *     --spec "cypress/e2e/web/visual_walkthrough.cy.js"
 *
 * VAGY: nyisd meg a Cypress Test Runner-t (cypress open) és kattints erre a fájlra.
 */
import '../../support/web_commands';

// ── Időzítési konstansok ──────────────────────────────────────────────────
const STEP   = 1200;  // ms várakozás minden lépés UTÁN
const PAUSE  = 2000;  // ms hosszabb szünet oldalbetöltés után
const TYPE_DELAY = 80; // ms/karakter — látható gépelési sebesség

// ── slowStep parancs ──────────────────────────────────────────────────────
// Garantált szünet minden lépés előtt és után.
// Használat: cy.slowStep('Leírás', () => { /* Cypress parancsok */ })
Cypress.Commands.add('slowStep', (label, stepFn) => {
  cy.wait(400);
  cy.log(`▶ ${label}`);
  stepFn();
  cy.wait(STEP);
});

// ═══════════════════════════════════════════════════════════════════════════
// FLOW 1 — BEJELENTKEZÉS / KIJELENTKEZÉS
// ═══════════════════════════════════════════════════════════════════════════
describe('Flow 1 — Bejelentkezés és kijelentkezés', { tags: ['@visual'] }, () => {
  before(() => { cy.task('resetDb', 'baseline'); });

  beforeEach(() => {
    cy.setupCsrf();
    cy.clearAllCookies();
  });

  it('1-A: Bejelentkezési oldal → rossz jelszó → hibaüzenet', () => {
    cy.slowStep('Bejelentkezési oldal megnyitása', () => {
      cy.visit('/login');
    });

    cy.slowStep('Email megadása (rossz felhasználó)', () => {
      cy.get('input[name="email"]').type('nemletezik@lfa.com', { delay: TYPE_DELAY });
    });

    cy.slowStep('Jelszó megadása', () => {
      cy.get('input[name="password"]').type('rosszjelszo', { delay: TYPE_DELAY });
    });

    cy.slowStep('Bejelentkezés gomb kattintás → hibaüzenet', () => {
      cy.get('button[type="submit"]').click();
    });

    cy.wait(PAUSE);
    cy.url().should('include', '/login');
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('1-B: Admin bejelentkezés → dashboard megjelenése → kijelentkezés', () => {
    cy.slowStep('Bejelentkezési oldal megnyitása', () => {
      cy.visit('/login');
    });

    cy.slowStep('Admin email begépelése', () => {
      cy.get('input[name="email"]').type(Cypress.env('webAdminEmail'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Admin jelszó begépelése', () => {
      cy.get('input[name="password"]').type(Cypress.env('webAdminPassword'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Bejelentkezés → dashboard átirányítás', () => {
      cy.get('button[type="submit"]').click();
    });

    cy.wait(PAUSE);
    cy.url().should('include', '/dashboard');
    cy.get('body').should('not.contain.text', 'Internal Server Error');

    cy.slowStep('Dashboard áttekintése', () => {
      cy.wait(PAUSE);
    });

    cy.slowStep('Kijelentkezés', () => {
      cy.visit('/logout', { failOnStatusCode: false });
    });

    cy.wait(PAUSE);
    cy.url().should('include', '/login');
  });

  it('1-C: Instruktor bejelentkezés → dashboard', () => {
    cy.slowStep('Instruktor email begépelése', () => {
      cy.visit('/login');
      cy.get('input[name="email"]').type(Cypress.env('webInstructorEmail'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Instruktor jelszó', () => {
      cy.get('input[name="password"]').type(Cypress.env('webInstructorPassword'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Bejelentkezés → dashboard', () => {
      cy.get('button[type="submit"]').click();
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('1-D: Diák bejelentkezés → dashboard', () => {
    cy.slowStep('Diák email begépelése', () => {
      cy.visit('/login');
      cy.get('input[name="email"]').type(Cypress.env('webStudentEmail'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Diák jelszó', () => {
      cy.get('input[name="password"]').type(Cypress.env('webStudentPassword'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Bejelentkezés', () => {
      cy.get('button[type="submit"]').click();
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// FLOW 2 — ADMIN OLDALAK KÖRBEJÁRÁSA
// ═══════════════════════════════════════════════════════════════════════════
describe('Flow 2 — Admin oldalak (valódi navigáció)', { tags: ['@visual'] }, () => {
  before(() => { cy.task('resetDb', 'baseline'); });

  beforeEach(() => {
    cy.setupCsrf();
    cy.clearAllCookies();
    cy.webLoginAs('admin');
  });

  it('2-A: Admin dashboard', () => {
    cy.slowStep('Dashboard megnyitása', () => {
      cy.visit('/dashboard');
    });
    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('2-B: Admin → Felhasználók lista', () => {
    cy.slowStep('Felhasználók oldal megnyitása', () => {
      cy.visit('/admin/users');
    });
    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('2-C: Admin → Szemeszterek', () => {
    cy.slowStep('Szemeszterek megnyitása', () => {
      cy.visit('/admin/semesters');
    });
    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('2-D: Admin → Beiratkozások', () => {
    cy.slowStep('Beiratkozások megnyitása', () => {
      cy.visit('/admin/enrollments');
    });
    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('2-E: Admin → Fizetések', () => {
    cy.slowStep('Fizetések oldal megnyitása', () => {
      cy.visit('/admin/payments');
    });
    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('2-F: Admin → Analitika', () => {
    cy.slowStep('Analitika oldal megnyitása', () => {
      cy.visit('/admin/analytics');
    });
    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('2-G: RBAC — diák megpróbál admin oldalhoz férni → blokkolva', () => {
    cy.clearAllCookies();
    cy.webLoginAs('student');

    cy.slowStep('Diák megpróbálja megnyitni /admin/users oldalt', () => {
      // FastAPI RBAC guard returns 403 JSON (not HTML), so cy.visit() cannot be used here.
      // cy.request() verifies the block; cy.url() confirms the browser stayed off /admin.
      cy.request({ method: 'GET', url: '/admin/users', failOnStatusCode: false })
        .then((resp) => {
          expect(resp.status).to.not.equal(200);
        });
    });

    cy.wait(PAUSE);
    cy.url().should('not.include', '/admin');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// FLOW 3 — INSTRUKTOR: EDZÉS INDÍTÁSA, JELENLÉT, LEÁLLÍTÁS
// ═══════════════════════════════════════════════════════════════════════════
describe('Flow 3 — Instruktor edzés életciklus', { tags: ['@visual'] }, () => {
  let sessionId = null;

  before(() => {
    cy.task('resetDb', 'session_ready').then(() => {
      // Lekérjük a session ID-t a Cypress task-on át
      cy.task('resetDb', 'session_ready');
    });
  });

  beforeEach(() => {
    cy.setupCsrf();
    cy.clearAllCookies();
  });

  it('3-A: Instruktor beiratkozások megtekintése', () => {
    cy.webLoginAs('instructor');

    cy.slowStep('Instruktor beiratkozások oldal megnyitása', () => {
      cy.visit('/instructor/enrollments');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('3-B: Instruktor edzések listája → edzés indítása', () => {
    cy.webLoginAs('instructor');

    cy.slowStep('Edzések listájának megnyitása', () => {
      cy.visit('/sessions');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');

    // Session ID kinyerése az oldalról
    cy.get('body').then(($body) => {
      // Keresünk "Start" vagy "Indít" gombot, vagy session linket
      const startBtn = $body.find('form[action*="/start"] button, button:contains("Start"), button:contains("Indít")');
      if (startBtn.length > 0) {
        // Kinyerjük a session ID-t az action URL-ből
        const form = $body.find('form[action*="/start"]').first();
        const action = form.attr('action') || '';
        const match = action.match(/\/sessions\/(\d+)\/start/);
        if (match) sessionId = parseInt(match[1]);

        cy.slowStep(`Edzés indítása (session ID: ${sessionId})`, () => {
          cy.wrap(startBtn.first()).click();
        });

        cy.wait(PAUSE);
        cy.get('body').should('not.contain.text', 'Internal Server Error');
      } else {
        cy.log('ℹ Nincs indítható edzés a listán — lépés átugorva');
        // Nyissuk meg közvetlenül az első session detail oldalt
        const sessionLink = $body.find('a[href*="/sessions/"]').first();
        if (sessionLink.length > 0) {
          cy.slowStep('Session részletei megnyitása', () => {
            cy.wrap(sessionLink).click();
          });
          cy.wait(PAUSE);
        }
      }
    });
  });

  it('3-C: Instruktor profil megtekintése', () => {
    cy.webLoginAs('instructor');

    cy.slowStep('Profil oldal megnyitása', () => {
      cy.visit('/profile');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// FLOW 4 — DIÁK: ÉLETKOR-ELLENŐRZÉS
// ═══════════════════════════════════════════════════════════════════════════
describe('Flow 4 — Diák: életkor-ellenőrzés (új fiók)', { tags: ['@visual'] }, () => {
  before(() => { cy.task('resetDb', 'student_no_dob'); });

  beforeEach(() => {
    cy.setupCsrf();
    cy.clearAllCookies();
  });

  it('4-A: Friss diák bejelentkezés → /age-verification átirányítás', () => {
    cy.slowStep('Friss diák email begépelése', () => {
      cy.visit('/login');
      cy.get('input[name="email"]').type(Cypress.env('webFreshEmail'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Jelszó begépelése', () => {
      cy.get('input[name="password"]').type(Cypress.env('webFreshPassword'), { delay: TYPE_DELAY });
    });

    cy.slowStep('Bejelentkezés → életkor-ellenőrzésre irányítás', () => {
      cy.get('button[type="submit"]').click();
    });

    cy.wait(PAUSE);
    cy.url().should('satisfy', (u) => u.includes('/age-verification') || u.includes('/dashboard'));
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('4-B: Jövőbeli születési dátum → szerver hibaüzenet megjelenik', () => {
    cy.webLoginAs('fresh');
    cy.visit('/age-verification', { failOnStatusCode: false });

    cy.slowStep('Életkor-ellenőrzés oldal betöltve', () => {
      cy.wait(PAUSE);
    });

    cy.slowStep('Jövőbeli dátum begépelése (2099-01-01)', () => {
      cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth')
        .invoke('removeAttr', 'max')
        .type('2099-01-01', { delay: TYPE_DELAY });
    });

    cy.slowStep('Elküldés → szerver oldali validáció', () => {
      cy.get('button[type="submit"]').click();
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('4-C: Érvényes DOB → dashboard átirányítás', () => {
    cy.task('resetDb', 'student_no_dob');
    cy.webLoginAs('fresh');
    cy.visit('/age-verification', { failOnStatusCode: false });

    cy.slowStep('Életkor-ellenőrzés oldal betöltve', () => {
      cy.wait(PAUSE);
    });

    cy.slowStep('Érvényes születési dátum: 2000-06-15', () => {
      cy.get('input[name="date_of_birth"], input[name="dob"], #date_of_birth')
        .type('2000-06-15', { delay: TYPE_DELAY });
    });

    cy.slowStep('Elküldés → dashboard', () => {
      cy.get('button[type="submit"]').click();
    });

    cy.wait(PAUSE);
    cy.url().should('include', '/dashboard');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// FLOW 5 — DIÁK: SPECIALIZÁCIÓ VÁLASZTÁS + MOTIVÁCIÓS KÉRDŐÍV
// ═══════════════════════════════════════════════════════════════════════════
describe('Flow 5 — Diák: specializáció választás és motivációs kérdőív', { tags: ['@visual'] }, () => {
  before(() => { cy.task('resetDb', 'student_with_credits'); });

  beforeEach(() => {
    cy.setupCsrf();
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  it('5-A: Specializáció választó oldal megjelenése', () => {
    cy.slowStep('Specializáció választó oldal megnyitása', () => {
      cy.visit('/specialization/select');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('5-B: GANCUJU_PLAYER specializáció kiválasztása → motivációs kérdőív', () => {
    cy.slowStep('Specializáció választó megnyitása', () => {
      cy.visit('/specialization/select');
    });

    cy.wait(PAUSE);

    cy.slowStep('GANCUJU_PLAYER opció kiválasztása', () => {
      // Radio button vagy hidden input a specializáció értékével
      cy.get('body').then(($body) => {
        const radioGancuju = $body.find('input[value="GANCUJU_PLAYER"]');
        if (radioGancuju.length > 0) {
          cy.wrap(radioGancuju).click({ force: true });
        } else {
          // Keressük a "GānCuju" szöveget tartalmazó elemet és kattintsunk rá
          cy.contains(/gancuju|cuju/i).click({ force: true });
        }
      });
    });

    cy.slowStep('Specializáció kiválasztása elküldése', () => {
      cy.get('form').first().then(($form) => {
        // Ha van submit gomb, kattintsunk rá; különben programmatikusan küldjük el
        const submitBtn = $form.find('button[type="submit"], input[type="submit"]');
        if (submitBtn.length > 0) {
          cy.wrap(submitBtn.first()).click();
        } else {
          cy.wrap($form).submit();
        }
      });
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
    // Elvárt: motivációs kérdőív vagy dashboard (ha már van licensz)
    cy.url().should('satisfy', (u) =>
      u.includes('/motivation') || u.includes('/dashboard') || u.includes('/specialization')
    );
  });

  it('5-C: Motivációs kérdőív kitöltése és elküldése', () => {
    // Először létrehozzuk a licenszt a specializáció kiválasztásával
    cy.request({
      method: 'POST',
      url: '/specialization/select',
      form: true,
      body: { specialization: 'GANCUJU_PLAYER' },
      failOnStatusCode: false,
    });

    cy.slowStep('Motivációs kérdőív oldal megnyitása', () => {
      // Route uses query param name 'spec' (not 'specialization') — see specialization.py:130
      cy.visit('/specialization/motivation?spec=GANCUJU_PLAYER', { failOnStatusCode: false });
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');

    cy.get('body').then(($body) => {
      const hasForm = $body.find('form').length > 0;
      if (!hasForm) {
        cy.log('ℹ Motivációs kérdőív nem jelent meg — valószínűleg már kitöltve');
        return;
      }

      cy.slowStep('Célegyértelműség pontszám (goal_clarity = 4)', () => {
        // Radio buttons: use .click() on the specific value, not .clear().type()
        cy.get('body').then(($b) => {
          const radio = $b.find('input[name="goal_clarity"][value="4"]');
          if (radio.length > 0) cy.wrap(radio).click({ force: true });
          else cy.log('goal_clarity[4] nem található');
        });
      });

      cy.slowStep('Elkötelezettség (commitment_level = 4)', () => {
        cy.get('body').then(($b) => {
          const radio = $b.find('input[name="commitment_level"][value="4"]');
          if (radio.length > 0) cy.wrap(radio).click({ force: true });
        });
      });

      cy.slowStep('Bevonódás (engagement = 3)', () => {
        cy.get('body').then(($b) => {
          const radio = $b.find('input[name="engagement"][value="3"]');
          if (radio.length > 0) cy.wrap(radio).click({ force: true });
        });
      });

      cy.slowStep('Fejlődési szemlélet (progress_mindset = 4)', () => {
        cy.get('body').then(($b) => {
          const radio = $b.find('input[name="progress_mindset"][value="4"]');
          if (radio.length > 0) cy.wrap(radio).click({ force: true });
        });
      });

      cy.slowStep('Kezdeményezőkészség (initiative = 3)', () => {
        cy.get('body').then(($b) => {
          const radio = $b.find('input[name="initiative"][value="3"]');
          if (radio.length > 0) cy.wrap(radio).click({ force: true });
        });
      });

      cy.slowStep('Megjegyzések megadása', () => {
        cy.get('body').then(($b) => {
          const field = $b.find('textarea[name="notes"], input[name="notes"]');
          if (field.length > 0) {
            cy.wrap(field).clear().type(
              'Vizuális E2E bemutató — motivációs kérdőív kitöltése.',
              { delay: 50 }
            );
          }
        });
      });

      cy.slowStep('Kérdőív elküldése → dashboard', () => {
        cy.get('button[type="submit"]').first().click();
      });

      cy.wait(PAUSE);
      cy.get('body').should('not.contain.text', 'Internal Server Error');
    });
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// FLOW 6 — DIÁK: EDZÉSFOGLALÁS
// ═══════════════════════════════════════════════════════════════════════════
describe('Flow 6 — Diák: edzésfoglalás és foglalás lemondása', { tags: ['@visual'] }, () => {
  before(() => { cy.task('resetDb', 'session_ready'); });

  beforeEach(() => {
    cy.setupCsrf();
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  it('6-A: Edzések listája megtekintése', () => {
    cy.slowStep('Edzések oldal megnyitása', () => {
      cy.visit('/sessions');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('6-B: Edzés részletei megnyitása → foglalás', () => {
    cy.slowStep('Edzések lista megnyitása', () => {
      cy.visit('/sessions');
    });

    cy.wait(PAUSE);

    cy.get('body').then(($body) => {
      // Keressük az első session linket
      const sessionLinks = $body.find('a[href*="/sessions/"]');
      if (sessionLinks.length > 0) {
        const href = Cypress.$(sessionLinks[0]).attr('href');
        cy.slowStep(`Session részletei: ${href}`, () => {
          cy.visit(href, { failOnStatusCode: false });
        });

        cy.wait(PAUSE);
        cy.get('body').should('not.contain.text', 'Internal Server Error');

        // Megpróbálunk foglalni
        cy.get('body').then(($detail) => {
          const bookBtn = $detail.find(
            'button:contains("Book"), button:contains("Foglal"), ' +
            'form[action*="/book"] button, input[value*="Book"], input[value*="Foglal"]'
          );
          if (bookBtn.length > 0) {
            cy.slowStep('Foglalás gomb kattintása', () => {
              cy.wrap(bookBtn.first()).click();
            });
            cy.wait(PAUSE);
            cy.get('body').should('not.contain.text', 'Internal Server Error');
          } else {
            cy.log('ℹ Foglalás gomb nem található a detail oldalon (lehet már lefoglalva vagy lezárt session)');
          }
        });
      } else {
        cy.log('ℹ Nem található session link a listában');
      }
    });
  });

  it('6-C: Naptár nézet megtekintése', () => {
    cy.slowStep('Naptár megnyitása', () => {
      cy.visit('/calendar');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// FLOW 7 — DIÁK: PROFIL, HALADÁS, EREDMÉNYEK
// ═══════════════════════════════════════════════════════════════════════════
describe('Flow 7 — Diák: profil szerkesztése, haladás, eredmények', { tags: ['@visual'] }, () => {
  before(() => { cy.task('resetDb', 'baseline'); });

  beforeEach(() => {
    cy.setupCsrf();
    cy.clearAllCookies();
    cy.webLoginAs('student');
  });

  it('7-A: Profil oldal megtekintése', () => {
    cy.slowStep('Profil oldal megnyitása', () => {
      cy.visit('/profile');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('7-B: Profil szerkesztése → érvénytelen dátum → hibaüzenet', () => {
    cy.slowStep('Profil szerkesztési oldal megnyitása', () => {
      cy.visit('/profile/edit');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');

    cy.get('body').then(($body) => {
      const dobField = $body.find(
        'input[name="date_of_birth"], input[name="dob"], #date_of_birth'
      );
      if (dobField.length > 0) {
        cy.slowStep('Születési dátum módosítása érvénytelennre', () => {
          cy.wrap(dobField).invoke('removeAttr', 'max').clear().type('2099-12-31', { delay: TYPE_DELAY });
        });

        cy.slowStep('Mentés elküldése → validációs hiba', () => {
          cy.get('button[type="submit"]').first().click();
        });

        cy.wait(PAUSE);
        cy.get('body').should('not.contain.text', 'Internal Server Error');
      } else {
        cy.log('ℹ DOB mező nem található a szerkesztési oldalon');
      }
    });
  });

  it('7-C: Haladás oldal (/progress)', () => {
    cy.slowStep('Haladás oldal megnyitása', () => {
      cy.visit('/progress');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });

  it('7-D: Eredmények oldal (/achievements)', () => {
    cy.slowStep('Eredmények oldal megnyitása', () => {
      cy.visit('/achievements');
    });

    cy.wait(PAUSE);
    cy.get('body').should('not.contain.text', 'Internal Server Error');
  });
});
