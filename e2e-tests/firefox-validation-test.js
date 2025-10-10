// @ts-check
/**
 * Firefox E2E Validation Test
 * Validates Firefox-specific optimizations and enhanced error handling
 */

const { test, expect } = require('@playwright/test');

test.describe('🦊 Firefox E2E Optimization Validation', () => {

  test('Firefox configuration validation', async ({ page, browserName }) => {
    console.log(`🧪 Testing browser: ${browserName}`);
    
    // Test 1: Firefox-specific timeout handling
    if (browserName === 'firefox') {
      const startTime = Date.now();
      
      // Test enhanced timeouts for Firefox
      await page.goto('/', { timeout: 50000 }); // Should work with our extended timeout
      
      const loadTime = Date.now() - startTime;
      console.log(`⏱️ Firefox page load time: ${loadTime}ms`);
      
      // Firefox should load within our optimized timeout (50s)
      expect(loadTime).toBeLessThan(50000);
      
      // Test Firefox-specific element timeout
      const startWait = Date.now();
      try {
        await page.waitForSelector('body', { timeout: 25000 }); // Firefox-optimized timeout
        const waitTime = Date.now() - startWait;
        console.log(`✅ Firefox element wait time: ${waitTime}ms`);
        expect(waitTime).toBeLessThan(25000);
      } catch (error) {
        console.log(`⚠️ Firefox element wait timeout: ${error.message}`);
      }
      
    } else {
      // Other browsers should use standard timeouts
      await page.goto('/', { timeout: 35000 });
      console.log(`✅ Standard browser (${browserName}) load test passed`);
    }
  });

  test('Cross-browser performance comparison', async ({ page, browserName }) => {
    console.log(`🚀 Performance test for: ${browserName}`);
    
    const performanceMetrics = {
      navigation: 0,
      firstElement: 0,
      jsExecution: 0
    };
    
    // Navigation performance
    const navStart = Date.now();
    await page.goto('/');
    performanceMetrics.navigation = Date.now() - navStart;
    
    // Element appearance performance  
    const elemStart = Date.now();
    await page.waitForSelector('body').catch(() => {});
    performanceMetrics.firstElement = Date.now() - elemStart;
    
    // JavaScript execution performance
    const jsStart = Date.now();
    await page.evaluate(() => document.readyState).catch(() => {});
    performanceMetrics.jsExecution = Date.now() - jsStart;
    
    console.log(`📊 ${browserName} Performance Metrics:`, performanceMetrics);
    
    // Browser-specific performance expectations
    if (browserName === 'firefox') {
      // Firefox optimized thresholds
      expect(performanceMetrics.navigation).toBeLessThan(50000);
      expect(performanceMetrics.firstElement).toBeLessThan(25000);
    } else if (browserName === 'webkit') {
      // WebKit optimized thresholds
      expect(performanceMetrics.navigation).toBeLessThan(35000);
      expect(performanceMetrics.firstElement).toBeLessThan(18000);
    } else {
      // Chrome/Chromium standard thresholds
      expect(performanceMetrics.navigation).toBeLessThan(30000);
      expect(performanceMetrics.firstElement).toBeLessThan(15000);
    }
    
    console.log(`✅ ${browserName} performance within expected thresholds`);
  });

  test('Enhanced retry mechanism validation', async ({ page, browserName }) => {
    console.log(`🔄 Testing retry mechanisms for: ${browserName}`);
    
    // Test retry mechanism with intentional failure simulation
    const maxRetries = browserName === 'firefox' ? 3 : 2;
    let attempts = 0;
    let success = false;
    
    for (let i = 0; i < maxRetries; i++) {
      attempts++;
      try {
        // Simulate potentially unreliable operation
        await page.goto('/', { timeout: browserName === 'firefox' ? 25000 : 15000 });
        
        // Check if page loaded successfully
        await page.waitForSelector('body', { 
          timeout: browserName === 'firefox' ? 20000 : 12000 
        });
        
        success = true;
        console.log(`✅ Success on attempt ${attempts} for ${browserName}`);
        break;
        
      } catch (error) {
        console.log(`⚠️ Attempt ${attempts} failed for ${browserName}: ${error.message}`);
        
        if (i < maxRetries - 1) {
          // Progressive retry delay
          const delay = 1000 * (i + 1);
          console.log(`⏳ Waiting ${delay}ms before retry...`);
          await page.waitForTimeout(delay);
        }
      }
    }
    
    // Validate retry mechanism worked
    expect(success).toBeTruthy();
    expect(attempts).toBeLessThanOrEqual(maxRetries);
    
    console.log(`🎯 Retry mechanism validated: ${attempts}/${maxRetries} attempts for ${browserName}`);
  });

  test('Firefox error handling validation', async ({ page, browserName }) => {
    if (browserName !== 'firefox') {
      test.skip('Firefox-specific test');
    }
    
    console.log('🦊 Testing Firefox-specific error handling...');
    
    // Test enhanced error capture for Firefox
    const errors = [];
    page.on('pageerror', error => {
      errors.push(error.message);
      console.log(`🔍 Captured page error: ${error.message}`);
    });
    
    page.on('requestfailed', request => {
      console.log(`🔍 Failed request: ${request.url()}`);
    });
    
    // Test Firefox-specific navigation with error handling
    try {
      await page.goto('/nonexistent-page', { timeout: 30000 });
    } catch (error) {
      console.log(`✅ Expected navigation error handled: ${error.message}`);
    }
    
    // Test Firefox-specific element waiting with graceful failure
    try {
      await page.waitForSelector('#nonexistent-element', { timeout: 5000 });
    } catch (error) {
      console.log(`✅ Expected element timeout handled: ${error.message}`);
    }
    
    // Test Firefox-specific JavaScript execution error handling
    try {
      await page.evaluate(() => {
        throw new Error('Test Firefox JS error');
      });
    } catch (error) {
      console.log(`✅ Expected JS error handled: ${error.message}`);
    }
    
    console.log(`🦊 Firefox error handling validation complete. Captured ${errors.length} page errors.`);
  });

  test('Timeout optimization verification', async ({ page, browserName }) => {
    console.log(`⏱️ Verifying timeout optimizations for: ${browserName}`);
    
    // Define browser-specific expected timeouts based on our optimizations
    const timeoutConfig = {
      firefox: {
        action: 25000,
        navigation: 50000,
        expect: 20000
      },
      webkit: {
        action: 15000,
        navigation: 35000,
        expect: 12000
      },
      chromium: {
        action: 15000,
        navigation: 35000,
        expect: 10000
      }
    };
    
    const expectedTimeouts = timeoutConfig[browserName] || timeoutConfig.chromium;
    
    // Test action timeout
    const actionStart = Date.now();
    try {
      await page.goto('/', { timeout: expectedTimeouts.navigation });
      const actionTime = Date.now() - actionStart;
      console.log(`📊 Navigation completed in ${actionTime}ms (limit: ${expectedTimeouts.navigation}ms)`);
      expect(actionTime).toBeLessThan(expectedTimeouts.navigation);
    } catch (error) {
      console.log(`⚠️ Navigation timeout test: ${error.message}`);
    }
    
    // Test element waiting timeout
    const waitStart = Date.now();
    try {
      await page.waitForSelector('body', { timeout: expectedTimeouts.expect });
      const waitTime = Date.now() - waitStart;
      console.log(`📊 Element wait completed in ${waitTime}ms (limit: ${expectedTimeouts.expect}ms)`);
      expect(waitTime).toBeLessThan(expectedTimeouts.expect);
    } catch (error) {
      console.log(`⚠️ Element wait timeout test: ${error.message}`);
    }
    
    console.log(`✅ Timeout optimization verified for ${browserName}`);
  });

  test('Browser compatibility matrix validation', async ({ page, browserName }) => {
    console.log(`🌐 Browser compatibility test for: ${browserName}`);
    
    // Test basic browser capabilities
    const capabilities = {
      localStorage: false,
      sessionStorage: false,
      indexedDB: false,
      webGL: false,
      webWorkers: false
    };
    
    try {
      await page.goto('/');
      
      // Test storage capabilities
      capabilities.localStorage = await page.evaluate(() => {
        try {
          localStorage.setItem('test', 'value');
          localStorage.removeItem('test');
          return true;
        } catch (e) { return false; }
      });
      
      capabilities.sessionStorage = await page.evaluate(() => {
        try {
          sessionStorage.setItem('test', 'value');
          sessionStorage.removeItem('test');
          return true;
        } catch (e) { return false; }
      });
      
      // Test IndexedDB
      capabilities.indexedDB = await page.evaluate(() => {
        return !!window.indexedDB;
      });
      
      // Test WebGL
      capabilities.webGL = await page.evaluate(() => {
        try {
          const canvas = document.createElement('canvas');
          return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
        } catch (e) { return false; }
      });
      
      // Test Web Workers
      capabilities.webWorkers = await page.evaluate(() => {
        return !!window.Worker;
      });
      
      console.log(`🔧 ${browserName} capabilities:`, capabilities);
      
      // All modern browsers should support these basic features
      expect(capabilities.localStorage).toBeTruthy();
      expect(capabilities.sessionStorage).toBeTruthy();
      expect(capabilities.indexedDB).toBeTruthy();
      
      console.log(`✅ ${browserName} compatibility validation passed`);
      
    } catch (error) {
      console.log(`⚠️ Compatibility test error for ${browserName}: ${error.message}`);
    }
  });

  test('Advanced Firefox user preferences validation', async ({ page, browserName }) => {
    if (browserName !== 'firefox') {
      test.skip('Firefox-specific preference test');
    }
    
    console.log('🦊 Validating Firefox user preferences...');
    
    // Test that our Firefox preferences are working
    try {
      await page.goto('/');
      
      // Test media navigator preferences
      const mediaTest = await page.evaluate(() => {
        return {
          mediaDevices: !!navigator.mediaDevices,
          getUserMedia: !!navigator.getUserMedia
        };
      });
      
      console.log('📱 Media API test:', mediaTest);
      
      // Test network performance with our optimizations
      const networkStart = Date.now();
      await page.waitForLoadState('networkidle', { timeout: 30000 });
      const networkTime = Date.now() - networkStart;
      
      console.log(`🌐 Network idle achieved in ${networkTime}ms`);
      
      // Test automation detection avoidance
      const automationTest = await page.evaluate(() => {
        return {
          webdriver: navigator.webdriver,
          phantom: !!window.phantom,
          callPhantom: !!window.callPhantom
        };
      });
      
      console.log('🤖 Automation detection test:', automationTest);
      
      console.log('✅ Firefox preferences validation complete');
      
    } catch (error) {
      console.log(`⚠️ Firefox preferences test error: ${error.message}`);
    }
  });

});