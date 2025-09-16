// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  
  // Enhanced retry strategy for Firefox stability
  retries: process.env.CI ? 3 : 1, // Increased retries for CI
  workers: process.env.CI ? 2 : undefined,
  
  // Extended timeouts for Firefox optimization
  timeout: 75000, // 75 second test timeout for Firefox
  globalTimeout: 900000, // 15 minute global timeout for retry mechanisms
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['github']
  ],
  use: {
    baseURL: process.env.TEST_URL || 'http://localhost:3000',
    
    // Enhanced debugging and error capture
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Optimized timeouts for cross-browser stability
    actionTimeout: 15000, // Increased for Firefox compatibility
    navigationTimeout: 35000, // Extended for all browsers
    
    // Enhanced error handling
    ignoreHTTPSErrors: true,
    acceptDownloads: false,
    
    // Improved test reliability settings
    viewport: { width: 1280, height: 720 },
    locale: 'en-US',
    timezoneId: 'UTC'
    
    // Browser-specific launchOptions handled individually for compatibility
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
        // Advanced Firefox-specific optimizations for booking flow stability
        actionTimeout: 25000, // Extended for Firefox rendering delays
        navigationTimeout: 50000, // Extended for Firefox navigation issues
        expect: {
          timeout: 20000, // Extended expect timeout for Firefox DOM updates
          toHaveURL: { timeout: 25000 }, // Specific URL navigation timeout
          toBeVisible: { timeout: 18000 } // Element visibility timeout
        },
        launchOptions: {
          firefoxUserPrefs: {
            // Media and automation optimizations
            'media.navigator.streams.fake': true,
            'media.navigator.permission.disabled': true,
            'dom.webdriver.enabled': false,
            'useAutomationExtension': false,
            
            // Security and network optimizations
            'security.tls.insecure_fallback_hosts': 'localhost',
            'network.cookie.sameSite.laxByDefault': false,
            
            // Performance optimizations for E2E testing
            'dom.ipc.processCount': 1,
            'browser.tabs.remote.autostart': false,
            'layers.acceleration.disabled': true,
            
            // Disable Firefox features that interfere with automation
            'browser.safebrowsing.enabled': false,
            'browser.safebrowsing.malware.enabled': false,
            'datareporting.healthreport.uploadEnabled': false,
            'datareporting.policy.dataSubmissionEnabled': false,
            
            // Network optimizations
            'network.http.max-connections': 40,
            'network.http.max-connections-per-server': 8,
            'network.prefetch-next': false,
            
            // Disable unnecessary background activities
            'browser.newtabpage.activity-stream.feeds.telemetry': false,
            'browser.newtabpage.activity-stream.telemetry': false,
            'browser.ping-centre.telemetry': false
          },
          
          // Additional Firefox args for CI/automation stability
          args: process.env.CI ? [
            '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
          ] : []
        },
        
        // Enhanced video/screenshot settings for Firefox debugging
        video: process.env.CI ? 'retain-on-failure' : 'off',
        screenshot: 'only-on-failure',
        
        // Context options for better Firefox reliability
        viewport: { width: 1280, height: 720 },
        ignoreHTTPSErrors: true,
        acceptDownloads: false,
        
        // Enhanced debugging for Firefox issues
        trace: process.env.DEBUG ? 'on' : 'retain-on-failure'
      }
    },
    {
      name: 'webkit',
      use: { 
        ...devices['Desktop Safari'],
        // WebKit optimizations for CI reliability
        actionTimeout: 25000, // Extended for WebKit mobile testing
        navigationTimeout: 40000, // Extended for WebKit navigation
        
        // Enable touch support for mobile testing
        hasTouch: true,
        isMobile: false, // Keep desktop context but enable touch
        
        // Extended timeouts for WebKit element detection
        expect: {
          timeout: 20000, // Extended expect timeout for WebKit DOM updates
          toBeVisible: { timeout: 15000 } // Element visibility timeout
        },
        
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