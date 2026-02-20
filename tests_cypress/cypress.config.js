const { defineConfig } = require('cypress');

module.exports = defineConfig({
  // ── Cypress Cloud Integration ──────────────────────────────────────────
  // Cypress Cloud Project ID (practice-booking-system-e2e)
  // See: docs/CYPRESS_CLOUD_SETUP.md for full setup instructions
  projectId: 'k5j9m2',

  e2e: {
    // ── Target application ──────────────────────────────────────────────────
    // Streamlit default port. Override with CYPRESS_BASE_URL env var.
    baseUrl: process.env.CYPRESS_BASE_URL || 'http://localhost:8501',

    // ── Test discovery ──────────────────────────────────────────────────────
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx}',
    supportFile: 'cypress/support/e2e.js',
    fixturesFolder: 'cypress/fixtures',

    // ── Timeouts ────────────────────────────────────────────────────────────
    // Streamlit redraws the full React tree on every state change.
    // These generous timeouts prevent flaky failures during rerenders.
    defaultCommandTimeout:  15000,  // cy.get(), cy.contains()
    requestTimeout:         20000,  // cy.request(), cy.intercept()
    responseTimeout:        20000,
    pageLoadTimeout:        60000,  // full Streamlit boot can take ~5–10 s
    execTimeout:            60000,

    // ── Viewport ────────────────────────────────────────────────────────────
    viewportWidth:  1440,
    viewportHeight: 900,

    // ── Artifacts ───────────────────────────────────────────────────────────
    screenshotsFolder: 'cypress/screenshots',
    videosFolder:      'cypress/videos',
    video:             false,          // enable in CI: CYPRESS_video=true
    screenshotOnRunFailure: true,

    // ── Retries ─────────────────────────────────────────────────────────────
    retries: {
      runMode:  2,   // CI: retry failing tests twice
      openMode: 0,   // Interactive: no retries (see failures immediately)
    },

    // ── Environment variables ────────────────────────────────────────────────
    // Override any of these with CYPRESS_<KEY>=value or cypress.env.json.
    env: {
      // API base URL (FastAPI backend)
      apiUrl:           process.env.CYPRESS_API_URL     || 'http://localhost:8000',

      // Test user credentials (admin)
      adminEmail:       process.env.CYPRESS_ADMIN_EMAIL    || 'admin@lfa.com',
      adminPassword:    process.env.CYPRESS_ADMIN_PASSWORD || 'admin123',

      // Test user credentials (instructor)
      instructorEmail:  process.env.CYPRESS_INSTRUCTOR_EMAIL    || 'grandmaster@lfa.com',
      instructorPassword: process.env.CYPRESS_INSTRUCTOR_PASSWORD || 'TestInstructor2026',

      // Test user credentials (player / student)
      playerEmail:      process.env.CYPRESS_PLAYER_EMAIL    || 'rdias@manchestercity.com',
      playerPassword:   process.env.CYPRESS_PLAYER_PASSWORD || 'TestPlayer2026',

      // Flag to skip tests that require a live backend
      skipApiTests:     process.env.CYPRESS_SKIP_API_TESTS === 'true',
    },

    // ── Plugin setup ─────────────────────────────────────────────────────────
    setupNodeEvents(on, config) {
      // @cypress/grep — tag-based test filtering
      // Usage: cy:run:smoke → runs tests tagged @smoke
      try {
        require('@cypress/grep/src/plugin')(config);
      } catch {
        // Gracefully skip if @cypress/grep not installed yet
      }
      return config;
    },
  },
});
