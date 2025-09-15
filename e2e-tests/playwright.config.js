// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['github']
  ],
  use: {
    baseURL: process.env.TEST_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },

  projects: [
    // Desktop Browsers (Chromium, Firefox, WebKit)
    {
      name: 'Chromium Desktop',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'Firefox Desktop', 
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'WebKit Desktop',
      use: { ...devices['Desktop Safari'] }
    },

    // Mobile Devices (Emulation)
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] }
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] }
    },
    {
      name: 'iPad Safari',
      use: { ...devices['iPad Pro'] }
    }
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