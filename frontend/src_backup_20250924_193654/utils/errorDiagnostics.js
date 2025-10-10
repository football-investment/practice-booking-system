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
      // Handle cross-origin "Script error." gracefully
      if (message === 'Script error.' && !source && !lineno && !colno) {
        console.warn('🌐 Cross-origin script error detected - this is usually safe to ignore');
        console.info('💡 This often happens when accessing the app from a different IP address');
        console.info('📍 Current URL:', window.location.href);
        
        // Try to recover gracefully
        this.handleCrossOriginError();
        return true; // Prevent default error handling
      }

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
        referrer: document.referrer,
        isCrossOrigin: message === 'Script error.' && !source
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
      
      // Prevent the default unhandled rejection behavior
      event.preventDefault();
    });

    // Add specific error handler for cross-origin issues
    window.addEventListener('error', (event) => {
      if (event.message === 'Script error.' && event.filename === '') {
        console.warn('🌐 Cross-origin script error via event listener');
        this.handleCrossOriginError();
        event.preventDefault();
      }
    }, true);
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

  handleCrossOriginError() {
    console.info('🔧 Attempting cross-origin error recovery...');
    
    // Check if we're accessing from a non-localhost IP
    const isNonLocalhost = !window.location.hostname.includes('localhost') && 
                          !window.location.hostname.includes('127.0.0.1');
    
    if (isNonLocalhost) {
      console.info('🌍 Detected access from external IP:', window.location.hostname);
      console.info('💡 This can cause CORS and script loading issues');
      
      // Add a user-friendly notification
      this.showCrossOriginNotification();
    }
    
    // Try to reinitialize critical services
    setTimeout(() => {
      console.info('🔄 Reinitializing app services...');
      
      // Dispatch a custom event to trigger app reinitialization
      window.dispatchEvent(new CustomEvent('crossOriginRecovery', {
        detail: { hostname: window.location.hostname }
      }));
    }, 1000);
  }

  showCrossOriginNotification() {
    // Only show once per session
    if (sessionStorage.getItem('crossOriginWarningShown')) {
      return;
    }
    
    const notification = document.createElement('div');
    notification.innerHTML = `
      <div style="
        position: fixed;
        top: 20px;
        right: 20px;
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 15px;
        max-width: 350px;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      ">
        <div style="font-weight: 600; color: #856404; margin-bottom: 8px;">
          🌐 Network Access Detected
        </div>
        <div style="color: #856404; line-height: 1.4;">
          You're accessing from IP ${window.location.hostname}. Some features may work differently than on localhost.
        </div>
        <button onclick="this.parentElement.parentElement.remove()" style="
          margin-top: 10px;
          background: #ffc107;
          border: none;
          padding: 5px 10px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        ">OK</button>
      </div>
    `;
    
    document.body.appendChild(notification);
    sessionStorage.setItem('crossOriginWarningShown', 'true');
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 10000);
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
        reactDevMode: process.env.NODE_ENV === 'development',
        isNonLocalhost: !window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1'),
        crossOriginErrorsCount: this.errors.filter(e => e.isCrossOrigin).length
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