// Enhanced error diagnostics for iPad/Safari debugging

class ErrorDiagnostics {
  constructor() {
    this.errors = [];
    this.networkLogs = [];
    this.sourceMapInfo = {};
    this.setupGlobalHandlers();
    this.setupNetworkMonitoring();
    this.checkEnvironment();
    this.analyzeSourceMaps();
  }

  setupGlobalHandlers() {
    // Override the default error handler with more detailed logging
    const originalError = window.onerror;
    window.onerror = (message, source, lineno, colno, error) => {
      const errorInfo = {
        timestamp: new Date().toISOString(),
        message: message,
        source: source,
        line: lineno,
        column: colno,
        error: error,
        stack: error?.stack,
        userAgent: navigator.userAgent,
        url: window.location.href,
        referrer: document.referrer
      };

      console.error('🚨 DETAILED ERROR:', errorInfo);
      this.errors.push(errorInfo);

      // Try to send error to server for logging
      this.logErrorToServer(errorInfo);

      // Call original handler if exists
      if (originalError) {
        return originalError.call(window, message, source, lineno, colno, error);
      }
      return false;
    };

    // Enhanced unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      const errorInfo = {
        timestamp: new Date().toISOString(),
        type: 'unhandledrejection',
        reason: event.reason,
        promise: event.promise,
        userAgent: navigator.userAgent,
        url: window.location.href
      };

      console.error('🚨 UNHANDLED PROMISE REJECTION:', errorInfo);
      this.errors.push(errorInfo);
      this.logErrorToServer(errorInfo);
    });
  }

  setupNetworkMonitoring() {
    console.log('📡 Setting up network monitoring...');
    
    // Monitor fetch requests
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const startTime = performance.now();
      const url = args[0];
      const options = args[1] || {};
      
      const logEntry = {
        timestamp: new Date().toISOString(),
        url: url,
        method: options.method || 'GET',
        headers: options.headers || {},
        startTime: startTime
      };
      
      try {
        const response = await originalFetch.apply(window, args);
        const endTime = performance.now();
        
        logEntry.status = response.status;
        logEntry.statusText = response.statusText;
        logEntry.duration = endTime - startTime;
        logEntry.responseHeaders = {};
        
        // Try to extract response headers
        for (let [key, value] of response.headers.entries()) {
          logEntry.responseHeaders[key] = value;
        }
        
        console.log(`📡 NETWORK [${response.status}]:`, logEntry);
        this.networkLogs.push(logEntry);
        
        // Keep only last 30 network logs
        if (this.networkLogs.length > 30) {
          this.networkLogs.shift();
        }
        
        return response;
      } catch (error) {
        const endTime = performance.now();
        logEntry.error = error.message;
        logEntry.duration = endTime - startTime;
        
        console.error('📡 NETWORK ERROR:', logEntry);
        this.networkLogs.push(logEntry);
        throw error;
      }
    };
  }

  analyzeSourceMaps() {
    console.log('🗺️ Analyzing source maps...');
    
    // Check if source maps are available
    const scripts = Array.from(document.getElementsByTagName('script'));
    
    scripts.forEach((script, index) => {
      if (script.src) {
        const sourceMapUrl = script.src + '.map';
        
        // Test if source map exists
        fetch(sourceMapUrl, { method: 'HEAD' })
          .then(response => {
            this.sourceMapInfo[script.src] = {
              available: response.ok,
              status: response.status,
              url: sourceMapUrl
            };
            console.log(`🗺️ Source map for ${script.src}:`, this.sourceMapInfo[script.src]);
          })
          .catch(error => {
            this.sourceMapInfo[script.src] = {
              available: false,
              error: error.message,
              url: sourceMapUrl
            };
          });
      }
    });
  }

  checkEnvironment() {
    const env = {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      cookieEnabled: navigator.cookieEnabled,
      onLine: navigator.onLine,
      url: window.location.href,
      protocol: window.location.protocol,
      host: window.location.host,
      localStorage: this.testLocalStorage(),
      sessionStorage: this.testSessionStorage(),
      fetch: typeof fetch !== 'undefined',
      Promise: typeof Promise !== 'undefined',
      Symbol: typeof Symbol !== 'undefined'
    };

    console.log('🔍 ENVIRONMENT CHECK:', env);
    return env;
  }

  testLocalStorage() {
    try {
      const testKey = '__test__';
      localStorage.setItem(testKey, 'test');
      localStorage.removeItem(testKey);
      return true;
    } catch (e) {
      return false;
    }
  }

  testSessionStorage() {
    try {
      const testKey = '__test__';
      sessionStorage.setItem(testKey, 'test');
      sessionStorage.removeItem(testKey);
      return true;
    } catch (e) {
      return false;
    }
  }

  async logErrorToServer(errorInfo) {
    try {
      // Don't log to server in development to avoid noise
      if (process.env.NODE_ENV === 'development') {
        return;
      }

      await fetch('/api/v1/errors/log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorInfo),
      });
    } catch (e) {
      // Silently fail to avoid recursive errors
      console.warn('Failed to log error to server:', e);
    }
  }

  getErrorSummary() {
    return {
      totalErrors: this.errors.length,
      errors: this.errors.slice(-10), // Last 10 errors
      networkLogs: this.networkLogs.slice(-10), // Last 10 network calls
      sourceMapInfo: this.sourceMapInfo,
      environment: this.checkEnvironment(),
      debugInfo: {
        isFirefox: navigator.userAgent.toLowerCase().includes('firefox'),
        isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
        isSafari: navigator.userAgent.toLowerCase().includes('safari') && !navigator.userAgent.toLowerCase().includes('chrome'),
        currentUrl: window.location.href,
        bundleJsLoaded: !!document.querySelector('script[src*="bundle.js"]'),
        reactDevMode: process.env.NODE_ENV === 'development'
      }
    };
  }

  // Method to manually test common error scenarios
  testScenarios() {
    console.log('🧪 Testing common error scenarios...');

    // Test 1: Date parsing
    try {
      const testDate = new Date('2025-09-15');
      console.log('✅ Date parsing test:', testDate.toString());
    } catch (e) {
      console.error('❌ Date parsing test failed:', e);
    }

    // Test 2: JSON parsing
    try {
      const testJson = JSON.parse('{"test": "value"}');
      console.log('✅ JSON parsing test:', testJson);
    } catch (e) {
      console.error('❌ JSON parsing test failed:', e);
    }

    // Test 3: Local storage
    try {
      localStorage.setItem('test', 'value');
      const value = localStorage.getItem('test');
      localStorage.removeItem('test');
      console.log('✅ LocalStorage test:', value);
    } catch (e) {
      console.error('❌ LocalStorage test failed:', e);
    }

    // Test 4: Network request
    fetch('/api/v1/health')
      .then(response => response.json())
      .then(data => console.log('✅ Network test:', data))
      .catch(error => console.error('❌ Network test failed:', error));
  }
}

// Create global instance
const errorDiagnostics = new ErrorDiagnostics();

// Expose for manual testing
window.errorDiagnostics = errorDiagnostics;

export default errorDiagnostics;