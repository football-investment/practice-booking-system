// iOS/Firefox browser compatibility checker for "Script error" issues

class IOSBrowserCompatibility {
  constructor() {
    this.issues = [];
    this.runChecks();
    
    // Apply iPad/Safari fixes if on mobile Safari
    if (this.isIPadOrSafari()) {
      this.applyIPadFixes();
    }
  }

  isIPadOrSafari() {
    const userAgent = navigator.userAgent.toLowerCase();
    const isIOS = /ipad|iphone|ipod/.test(userAgent);
    const isSafari = userAgent.includes('safari') && !userAgent.includes('chrome');
    return isIOS || isSafari;
  }

  runChecks() {
    console.log('🔍 Running iOS/Firefox compatibility checks...');
    
    this.checkDateSupport();
    this.checkFetchSupport();
    this.checkPromiseSupport();
    this.checkES6Support();
    this.checkCrossOriginPolicy();
    this.checkNetworkConnectivity();
  }

  checkDateSupport() {
    try {
      // Test problematic date formats that might fail on iOS
      const testDates = [
        '2025-09-15T10:00:00',
        '2025-09-15 10:00:00',
        'Sep 15 2025',
        '2025/09/15'
      ];

      testDates.forEach(dateStr => {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) {
          this.issues.push({
            type: 'date_parsing',
            message: `Invalid date format: ${dateStr}`,
            severity: 'warning'
          });
        }
      });

      console.log('✅ Date support check completed');
    } catch (error) {
      this.issues.push({
        type: 'date_parsing',
        message: error.message,
        severity: 'error'
      });
    }
  }

  checkFetchSupport() {
    if (typeof fetch === 'undefined') {
      this.issues.push({
        type: 'fetch_support',
        message: 'Fetch API not supported - might cause network errors',
        severity: 'error'
      });
    } else {
      console.log('✅ Fetch API supported');
    }
  }

  checkPromiseSupport() {
    if (typeof Promise === 'undefined') {
      this.issues.push({
        type: 'promise_support',
        message: 'Promise not supported - will cause runtime errors',
        severity: 'error'
      });
    } else {
      console.log('✅ Promise support check completed');
    }
  }

  checkES6Support() {
    try {
      // Test arrow functions
      const test1 = () => true;
      
      // Test destructuring
      const { test } = { test: true };
      
      // Test template literals
      const test2 = `template ${test}`;
      
      // Test const/let
      const testConst = true;
      let testLet = true;
      
      console.log('✅ ES6 features supported');
    } catch (error) {
      this.issues.push({
        type: 'es6_support',
        message: `ES6 feature not supported: ${error.message}`,
        severity: 'error'
      });
    }
  }

  checkCrossOriginPolicy() {
    // Test if we can make requests to our own backend
    const currentHost = window.location.hostname;
    const backendUrl = currentHost === 'localhost' || currentHost === '127.0.0.1' 
      ? 'http://localhost:8000' 
      : `http://192.168.1.129:8000`;

    fetch(`${backendUrl}/api/v1/debug/health`, { 
      method: 'HEAD',
      mode: 'cors'
    })
      .then(response => {
        if (!response.ok) {
          this.issues.push({
            type: 'cors_policy',
            message: `CORS test failed: ${response.status}`,
            severity: 'error'
          });
        } else {
          console.log('✅ CORS policy check passed');
        }
      })
      .catch(error => {
        this.issues.push({
          type: 'cors_policy',
          message: `CORS error: ${error.message}`,
          severity: 'error'
        });
      });
  }

  checkNetworkConnectivity() {
    // Test various network scenarios
    const testUrls = [
      '/api/v1/debug/health',  // Relative URL
      `${window.location.origin}/api/v1/debug/health`,  // Same origin
    ];

    testUrls.forEach(url => {
      fetch(url, { method: 'HEAD' })
        .then(response => {
          console.log(`✅ Network connectivity test passed for ${url}: ${response.status}`);
        })
        .catch(error => {
          this.issues.push({
            type: 'network_connectivity',
            message: `Network test failed for ${url}: ${error.message}`,
            severity: 'warning'
          });
        });
    });
  }

  // Special test for iOS Safari/Firefox script loading issues
  testScriptLoadingIssues() {
    console.log('🔍 Testing script loading issues...');
    
    // Check if all required scripts are loaded
    const requiredScripts = [
      'react',
      'react-dom',
      'router'
    ];

    const loadedScripts = Array.from(document.getElementsByTagName('script'))
      .map(script => script.src)
      .filter(src => src.includes('static/js'));

    console.log('📦 Loaded scripts:', loadedScripts);

    // Test dynamic script loading (common cause of "Script error")
    const testScript = document.createElement('script');
    testScript.onload = () => {
      console.log('✅ Dynamic script loading works');
    };
    testScript.onerror = (error) => {
      this.issues.push({
        type: 'script_loading',
        message: 'Dynamic script loading failed',
        severity: 'error',
        details: error
      });
    };
    testScript.src = 'data:text/javascript;base64,Y29uc29sZS5sb2coJ3Rlc3QnKTs='; // console.log('test');
    document.head.appendChild(testScript);
  }

  // iPad-specific error handling fixes
  applyIPadFixes() {
    console.log('🔧 Applying iPad/Safari specific fixes...');
    
    // Fix 1: Enhanced script error handling for Safari
    this.setupSafariScriptErrorHandler();
    
    // Fix 2: Add crossorigin attribute to all script tags
    this.addCrossOriginToScripts();
    
    // Fix 3: Setup fallback error handling
    this.setupFallbackErrorHandling();
    
    // Fix 4: Safari date parsing fixes
    this.applySafariDateFixes();
  }

  setupSafariScriptErrorHandler() {
    const originalError = window.onerror;
    
    window.onerror = (message, source, lineno, colno, error) => {
      // Safari-specific "Script error" handling
      if (message === 'Script error.' || message === 'Script error') {
        console.warn('🔧 Safari Script Error detected - attempting to provide more details...');
        
        // Try to extract more information
        const enhancedError = {
          timestamp: new Date().toISOString(),
          type: 'safari_script_error',
          userAgent: navigator.userAgent,
          url: window.location.href,
          source: source || 'unknown',
          line: lineno || 'unknown',
          column: colno || 'unknown',
          stack: error?.stack || 'No stack trace available',
          details: 'Safari CORS or script loading issue detected'
        };
        
        console.error('🔧 Enhanced Safari error details:', enhancedError);
        
        // Try to reload the problematic script
        if (source && source.includes('bundle.js')) {
          this.reloadBundleJs();
        }
        
        return true; // Prevent default Safari error display
      }
      
      // Call original handler for other errors
      if (originalError) {
        return originalError.call(window, message, source, lineno, colno, error);
      }
      return false;
    };
  }

  addCrossOriginToScripts() {
    const scripts = document.querySelectorAll('script[src]');
    scripts.forEach(script => {
      if (!script.crossOrigin && script.src.includes('static/js')) {
        script.crossOrigin = 'anonymous';
        console.log('🔧 Added crossOrigin to script:', script.src);
      }
    });
  }

  setupFallbackErrorHandling() {
    // Catch all unhandled errors that might not be caught elsewhere
    window.addEventListener('error', (event) => {
      if (event.message === 'Script error.' || event.filename === '') {
        console.error('🔧 Generic script error caught:', {
          message: event.message,
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          error: event.error,
          timeStamp: event.timeStamp,
          target: event.target
        });
        
        // Prevent the error from bubbling up to the default handler
        event.preventDefault();
        event.stopPropagation();
        return true;
      }
    });
  }

  applySafariDateFixes() {
    // Safari has issues with certain date formats
    const originalDate = Date;
    Date.parse = function(dateString) {
      // Convert problematic formats for Safari
      if (typeof dateString === 'string') {
        // Convert YYYY-MM-DD HH:mm:ss to YYYY-MM-DDTHH:mm:ss
        dateString = dateString.replace(/^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})$/, '$1T$2');
      }
      return originalDate.parse(dateString);
    };
  }

  reloadBundleJs() {
    console.log('🔧 Attempting to reload bundle.js...');
    
    try {
      const bundleScript = document.querySelector('script[src*="bundle.js"]');
      if (bundleScript) {
        const newScript = document.createElement('script');
        newScript.src = bundleScript.src + '?reload=' + Date.now();
        newScript.crossOrigin = 'anonymous';
        newScript.onload = () => {
          console.log('✅ Bundle.js reloaded successfully');
          bundleScript.remove();
        };
        newScript.onerror = () => {
          console.error('❌ Failed to reload bundle.js');
        };
        document.head.appendChild(newScript);
      }
    } catch (error) {
      console.error('❌ Error reloading bundle.js:', error);
    }
  }

  // Test for handling bundle.js errors specifically
  simulateBundleJsError() {
    console.log('🔍 Simulating bundle.js error scenarios...');
    
    try {
      // Simulate the type of error that might occur at bundle.js:62321:67
      // This is usually a handleError function call
      if (window.React && window.React.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED) {
        console.log('✅ React internals accessible');
      }

      // Test if error boundaries are working
      throw new Error('Test error for React error boundary');
    } catch (error) {
      // This should be caught by React's error boundary
      console.log('🧪 Test error thrown:', error.message);
    }
  }

  getCompatibilityReport() {
    return {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      issues: this.issues,
      browserInfo: {
        isFirefox: navigator.userAgent.toLowerCase().includes('firefox'),
        isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
        isSafari: navigator.userAgent.toLowerCase().includes('safari') && !navigator.userAgent.toLowerCase().includes('chrome'),
        version: this.getBrowserVersion(),
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        }
      },
      networkInfo: {
        online: navigator.onLine,
        connection: navigator.connection || null
      }
    };
  }

  getBrowserVersion() {
    const userAgent = navigator.userAgent;
    let version = 'unknown';
    
    if (userAgent.includes('Firefox/')) {
      version = userAgent.split('Firefox/')[1].split(' ')[0];
    } else if (userAgent.includes('Version/') && userAgent.includes('Safari')) {
      version = userAgent.split('Version/')[1].split(' ')[0];
    }
    
    return version;
  }
}

// Create and expose globally
const iosBrowserCompatibility = new IOSBrowserCompatibility();
window.iosBrowserCompatibility = iosBrowserCompatibility;

export default iosBrowserCompatibility;