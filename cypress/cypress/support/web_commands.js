/**
 * Custom Cypress commands for FastAPI Jinja2 web routes (localhost:8000).
 *
 * These are separate from the Streamlit commands in commands.js.
 * Import in web specs via:  import '../../../support/web_commands'
 *
 * ── CSRF strategy ───────────────────────────────────────────────────────────
 *
 * The FastAPI app uses Double Submit Cookie CSRF protection:
 *   - Cookie:  csrf_token  (httponly=false — JS must read it)
 *   - Header:  X-CSRF-Token  (must match the cookie value)
 *   - Bypass:  any request with  Authorization: Bearer <anything>  skips CSRF
 *
 * Two layers are used here:
 *
 * 1. Browser-level form interactions (cy.visit + cy.get + cy.click):
 *    cy.setupCsrf() registers cy.intercept() handlers for POST/PUT/PATCH/DELETE.
 *    Each interceptor reads the csrf_token from the outgoing Cookie header and
 *    copies it into the X-CSRF-Token request header.  Token rotation (server
 *    refreshes the cookie after every mutating request) is handled automatically
 *    because the interceptor reads the cookie value at request-send time.
 *
 * 2. Direct HTTP calls (cy.request()):
 *    cy.request() bypasses the browser network stack, so cy.intercept() does
 *    NOT apply.  We overwrite cy.request() globally to add
 *    "Authorization: Bearer test-csrf-bypass" to every POST/PUT/PATCH/DELETE
 *    that targets a web route (i.e. the URL does NOT contain /api/v1/).
 *    CSRFProtectionMiddleware skips validation for Bearer-authenticated requests.
 *    Session auth is unaffected — web routes read the access_token *cookie*,
 *    not the Authorization header.
 */

// ── CSRF: browser-level form interception ──────────────────────────────────

/**
 * Register cy.intercept() handlers that auto-inject the X-CSRF-Token header
 * into every browser-level POST / PUT / PATCH / DELETE by reading the
 * csrf_token value from the outgoing Cookie header.
 *
 * Call once per test — typically from inside cy.webLogin() so it is set up
 * before any form is submitted.  Cypress clears all intercept registrations
 * automatically after each test, so there is no leak between tests.
 */
Cypress.Commands.add('setupCsrf', () => {
  const injectCsrfHeader = (req) => {
    // Cookies are serialised into the Cookie request header by the browser.
    // Extract the csrf_token value and mirror it in X-CSRF-Token.
    const cookieStr = req.headers['cookie'] || req.headers['Cookie'] || '';
    const match = cookieStr.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (match) {
      req.headers['X-CSRF-Token'] = match[1];
    }
  };

  cy.intercept({ method: 'POST'   }, injectCsrfHeader);
  cy.intercept({ method: 'PUT'    }, injectCsrfHeader);
  cy.intercept({ method: 'PATCH'  }, injectCsrfHeader);
  cy.intercept({ method: 'DELETE' }, injectCsrfHeader);
});

// ── CSRF: cy.request() auto-bypass ─────────────────────────────────────────

/**
 * Overwrite cy.request() so that every state-changing call (POST/PUT/PATCH/
 * DELETE) that targets a *web* route automatically receives the Bearer bypass
 * header.  API routes (/api/v1/*) are already CSRF-exempt and are left alone.
 *
 * Caller-supplied headers always win — pass  headers: { Authorization: '...' }
 * in the options object to override the default bypass header.
 */
Cypress.Commands.overwrite('request', (originalFn, ...args) => {
  // Normalise the multiple call signatures of cy.request():
  //   cy.request(url)
  //   cy.request(method, url)
  //   cy.request(method, url, body)
  //   cy.request(options)
  let options = {};
  if (args.length === 1 && typeof args[0] === 'object' && args[0] !== null) {
    options = { ...args[0] };
  } else if (typeof args[0] === 'string') {
    if (args.length === 1)      options = { method: 'GET', url: args[0] };
    else if (args.length === 2) options = { method: args[0], url: args[1] };
    else                        options = { method: args[0], url: args[1], body: args[2] };
  } else {
    options = { ...args[0] };
  }

  const method = (options.method || 'GET').toUpperCase();
  const url    = String(options.url || '');

  // Inject Bearer bypass for web-route mutations only.
  // Skip: safe HTTP methods, and any URL that targets the /api/v1/ namespace.
  if (
    ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) &&
    !url.includes('/api/v1/')
  ) {
    options = {
      ...options,
      headers: {
        Authorization: 'Bearer test-csrf-bypass',
        ...options.headers,   // explicit caller headers always win
      },
    };
  }

  return originalFn(options);
});

// ── Login / logout ──────────────────────────────────────────────────────────

/**
 * Login via the FastAPI /login form (browser-level, full UI simulation).
 *
 * Flow:
 *   1. Register setupCsrf() so the form POST gets X-CSRF-Token injected.
 *   2. Clear stale cookies (ensures a clean session per test).
 *   3. Visit /login — the GET response sets the csrf_token cookie.
 *   4. Fill email + password and submit.
 *
 * On success the server issues a 303 redirect to /dashboard (or
 * /age-verification for fresh students without a DOB).  Cypress follows the
 * navigation automatically, so cy.url() reflects the final destination.
 *
 * On failure (wrong password, inactive account) the server returns 200 with
 * login.html + error message — the browser stays on /login and the error
 * element is visible in the DOM for assertFormError() / cy.get() assertions.
 */
Cypress.Commands.add('webLogin', (email, password) => {
  cy.setupCsrf();           // register CSRF interceptors before any POST
  cy.clearAllCookies();     // start each login from a clean cookie state
  cy.visit('/login');       // GET → server sets csrf_token cookie
  cy.get('input[name="email"]').type(email);
  cy.get('input[name="password"]').type(password);
  cy.get('button[type="submit"]').click();
  // Cypress automatically follows the server 303 redirect (success) or stays
  // on /login (failure).  The caller asserts the expected URL / DOM state.
});

/**
 * Login using a named role from cypress env (set in cypress.config.js).
 * Roles: 'admin' | 'instructor' | 'student' | 'fresh'
 */
Cypress.Commands.add('webLoginAs', (role) => {
  const map = {
    admin:      { email: Cypress.env('webAdminEmail'),      password: Cypress.env('webAdminPassword') },
    instructor: { email: Cypress.env('webInstructorEmail'), password: Cypress.env('webInstructorPassword') },
    student:    { email: Cypress.env('webStudentEmail'),     password: Cypress.env('webStudentPassword') },
    fresh:      { email: Cypress.env('webFreshEmail'),       password: Cypress.env('webFreshPassword') },
  };
  const creds = map[role];
  if (!creds) throw new Error(`Unknown web role: "${role}". Use admin|instructor|student|fresh.`);
  cy.webLogin(creds.email, creds.password);
});

// ── Navigation assertions ───────────────────────────────────────────────────

/** Assert that the current URL contains the given path fragment. */
Cypress.Commands.add('assertWebPath', (fragment) => {
  cy.url().should('include', fragment);
});

/** Assert that the page contains a visible element with the given text. */
Cypress.Commands.add('assertPageContains', (text) => {
  cy.contains(text).should('be.visible');
});

/** Assert that a form error message is visible on the page. */
Cypress.Commands.add('assertFormError', (text) => {
  cy.get('[class*="error"], [class*="alert"], [class*="danger"], .flash, #error')
    .should('be.visible')
    .and('contain', text);
});

// ── DB reset ────────────────────────────────────────────────────────────────

/**
 * Reset the database to the given scenario before a suite.
 * Call in before() or beforeEach() at the top of each spec.
 * Scenarios: 'baseline' | 'student_no_dob' | 'student_with_credits' | 'session_ready'
 */
Cypress.Commands.add('resetDb', (scenario = 'baseline') => {
  cy.task('resetDb', scenario);
});

// ── API helpers ─────────────────────────────────────────────────────────────

/**
 * Look up a session by title fragment via the admin API.
 * Uses explicit Bearer auth (API endpoint, already CSRF-exempt).
 * Used in session flow specs to get dynamic session IDs.
 */
Cypress.Commands.add('getSessionIdByTitle', (titleFragment) => {
  cy.request({
    method: 'GET',
    url: `${Cypress.env('apiUrl')}/api/v1/sessions/`,
    qs: { limit: 50 },
    headers: { Authorization: 'Bearer test-csrf-bypass' },
    failOnStatusCode: false,
  }).then((resp) => {
    if (resp.status !== 200) return cy.wrap(null);
    const session = resp.body.sessions?.find((s) => s.title?.includes(titleFragment));
    return cy.wrap(session?.id ?? null);
  });
});
