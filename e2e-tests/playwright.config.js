// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined, // Increased workers for better speed
  timeout: 60000, // 60 second global timeout
  globalTimeout: 600000, // 10 minute global timeout for entire test suite
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['github']
  ],
  use: {
    baseURL: process.env.TEST_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000, // 10 second action timeout
    navigationTimeout: 30000, // 30 second navigation timeout
    ignoreHTTPSErrors: true
    // Removed global launchOptions - now handled per-browser for compatibility
  },

  projects: [
    // Core Desktop Browsers - optimized for speed and reliability
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Chrome-specific optimizations for CI
        launchOptions: {
          args: process.env.CI ? [
            '--no-sandbox',
            '--disable-setuid-sandbox', 
            '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-extensions',
            '--disable-default-apps'
          ] : []
        }
      }
    },
    {
      name: 'firefox', 
      use: { 
        ...devices['Desktop Firefox'],
        // Firefox-specific optimizations
        launchOptions: process.env.CI ? {
          firefoxUserPrefs: {
            'media.navigator.streams.fake': true,
            'media.navigator.permission.disabled': true
          }
        } : {}
      }
    },
    {
      name: 'webkit',
      use: { 
        ...devices['Desktop Safari'],
        // WebKit optimizations for CI reliability
        actionTimeout: 15000, // WebKit can be slower
        // WebKit-specific launch options (no sandbox flags for WebKit)
        launchOptions: process.env.CI ? {
          // WebKit doesn't support Chrome flags like --no-sandbox
          // Use WebKit-specific options instead
        } : {}
      }
    }
    
    // Mobile testing handled by BrowserStack iOS Safari tests
    // Removed mobile emulation to improve CI speed and avoid redundancy
  ],

  webServer: process.env.CI ? undefined : [
    // Backend server for local testing
    {
      command: 'uvicorn app.main:app --host 0.0.0.0 --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI
    },
    // Frontend server for local testing  
    {
      command: 'cd frontend && npm start',
      port: 3000,
      reuseExistingServer: !process.env.CI
    }
  ]
});