// iOS Safari Testing with BrowserStack WebDriver
const { remote } = require('webdriverio');

const BROWSERSTACK_CONFIG = {
  user: process.env.BROWSERSTACK_USERNAME,
  key: process.env.BROWSERSTACK_ACCESS_KEY,
  server: 'hub.browserstack.com'
};

const DEVICE_CONFIG = {
  'iPhone 14': {
    'bstack:options': {
      deviceName: 'iPhone 14',
      osVersion: '16',
      browserName: 'Safari',
      realMobile: true,
      local: true,
      networkLogs: true,
      debug: true,
      consoleLogs: 'info',
      buildName: 'Cross-Platform-Testing',
      sessionName: 'iOS Safari - iPhone 14'
    }
  },
  'iPhone 13': {
    'bstack:options': {
      deviceName: 'iPhone 13',
      osVersion: '15',
      browserName: 'Safari',
      realMobile: true,
      local: true,
      networkLogs: true,
      debug: true,
      consoleLogs: 'info',
      buildName: 'Cross-Platform-Testing',
      sessionName: 'iOS Safari - iPhone 13'
    }
  },
  'iPad Pro 12.9 2022': {
    'bstack:options': {
      deviceName: 'iPad Pro 12.9 2022', 
      osVersion: '16',
      browserName: 'Safari',
      realMobile: true,
      local: true,
      networkLogs: true,
      debug: true,
      consoleLogs: 'info',
      buildName: 'Cross-Platform-Testing',
      sessionName: 'iOS Safari - iPad Pro'
    }
  }
};

async function runIOSSafariTests() {
  const deviceName = process.env.DEVICE || 'iPhone 14';
  const config = DEVICE_CONFIG[deviceName];
  
  if (!config) {
    throw new Error(`Device ${deviceName} not supported`);
  }

  console.log(`🚀 Starting iOS Safari tests on ${deviceName}...`);
  
  const driver = await remote({
    hostname: BROWSERSTACK_CONFIG.server,
    user: BROWSERSTACK_CONFIG.user,
    key: BROWSERSTACK_CONFIG.key,
    capabilities: {
      ...config,
      'bstack:options': {
        ...config['bstack:options'],
        local: true, // Enable BrowserStack Local for localhost testing
        localIdentifier: process.env.BROWSERSTACK_LOCAL_IDENTIFIER || `github-actions-${process.env.GITHUB_RUN_ID || 'local'}`
      }
    }
  });

  try {
    await testStudentOnboarding(driver, deviceName);
    await testSessionBooking(driver, deviceName);
    await testMobileInteractions(driver, deviceName);
    await testNetworkHandling(driver, deviceName);
    
    console.log('✅ All iOS Safari tests passed!');
    
  } catch (error) {
    console.error('❌ iOS Safari test failed:', error);
    throw error;
  } finally {
    await driver.deleteSession();
  }
}

async function testStudentOnboarding(driver, device) {
  console.log(`📝 Testing student onboarding on ${device}...`);
  
  // Navigate to app
  await driver.url('http://localhost:3000/login');
  
  // Wait for page load
  await driver.waitForDisplayed('[data-testid="email"]', { timeout: 15000 });
  
  // Login
  await driver.setValue('[data-testid="email"]', 'alex.newcomer@student.com');
  await driver.setValue('[data-testid="password"]', 'student123');
  await driver.click('[data-testid="login-button"]');
  
  // Should redirect to onboarding
  await driver.waitForDisplayed('h1', { timeout: 10000 });
  const heading = await driver.$('h1').getText();
  
  if (!heading.includes('Welcome')) {
    throw new Error('Onboarding page not loaded correctly');
  }
  
  // Fill onboarding form (iOS-specific interactions)
  await driver.setValue('[name="nickname"]', 'Alex');
  await driver.setValue('[name="phone"]', '+36301234567');
  
  // Test iOS date picker
  await driver.click('[name="dateOfBirth"]');
  await driver.setValue('[name="dateOfBirth"]', '1995-05-15');
  
  // Test iOS checkbox interactions
  await driver.click('[data-testid="interest-football"]');
  
  // Fill remaining fields
  await driver.setValue('[name="emergencyContact"]', 'Jane Newcomer');
  await driver.setValue('[name="emergencyPhone"]', '+36309876543');
  
  // Submit form
  await driver.click('[data-testid="complete-onboarding"]');
  
  // Wait for dashboard
  await driver.waitForDisplayed('[data-testid="welcome-message"]', { timeout: 15000 });
  
  console.log(`✅ Student onboarding test passed on ${device}`);
}

async function testSessionBooking(driver, device) {
  console.log(`🏃 Testing session booking on ${device}...`);
  
  // Navigate to sessions
  await driver.url('http://localhost:3000/student/sessions');
  
  // Wait for sessions to load
  await driver.waitForDisplayed('[data-testid="session-list"]', { timeout: 10000 });
  
  // Check if sessions are displayed
  const sessions = await driver.$$('[data-testid="session-card"]');
  if (sessions.length === 0) {
    throw new Error('No sessions loaded');
  }
  
  // Test booking interaction
  const bookButton = await driver.$('[data-testid="book-button"]');
  if (await bookButton.isExisting()) {
    await bookButton.click();
    
    // Wait for booking confirmation
    await driver.waitForDisplayed('[data-testid="booking-success"]', { timeout: 10000 });
  }
  
  console.log(`✅ Session booking test passed on ${device}`);
}

async function testMobileInteractions(driver, device) {
  console.log(`📱 Testing mobile interactions on ${device}...`);
  
  // Test touch interactions
  const sessionCard = await driver.$('[data-testid="session-card"]');
  if (await sessionCard.isExisting()) {
    // Test tap (vs click)
    await sessionCard.touchAction('tap');
  }
  
  // Test scroll behavior
  await driver.execute('window.scrollTo(0, document.body.scrollHeight)');
  await driver.pause(1000);
  await driver.execute('window.scrollTo(0, 0)');
  
  // Test orientation change (if supported)
  try {
    await driver.setOrientation('LANDSCAPE');
    await driver.pause(2000);
    await driver.setOrientation('PORTRAIT');
  } catch (error) {
    console.log('Orientation change not supported, skipping...');
  }
  
  console.log(`✅ Mobile interactions test passed on ${device}`);
}

async function testNetworkHandling(driver, device) {
  console.log(`🌐 Testing network handling on ${device}...`);
  
  // Test app behavior with network conditions
  // This would integrate with BrowserStack's network simulation
  
  // Test offline handling
  await driver.setNetworkConnection({
    type: 'airplane' // Simulate airplane mode
  });
  
  // Try to navigate
  await driver.url('http://localhost:3000/student/projects');
  await driver.pause(3000);
  
  // Restore connection  
  await driver.setNetworkConnection({
    type: 'all' // Restore all connections
  });
  
  console.log(`✅ Network handling test passed on ${device}`);
}

// Run the tests
runIOSSafariTests().catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});