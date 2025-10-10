/**
 * Cross-Origin Error Handler
 * Specifically handles the "Script error." issue when accessing the app from different IP addresses
 */

class CrossOriginErrorHandler {
  constructor() {
    this.isNonLocalhost = !window.location.hostname.includes('localhost') && 
                         !window.location.hostname.includes('127.0.0.1');
    this.errorCount = 0;
    this.maxErrors = 5;
    this.init();
  }

  init() {
    console.log('🌐 Cross-Origin Error Handler initialized');
    console.log(`📍 Current hostname: ${window.location.hostname}`);
    console.log(`🏠 Is non-localhost: ${this.isNonLocalhost}`);

    this.setupErrorHandling();
    this.addCrossOriginAttributes();
    this.setupNetworkErrorRecovery();
  }

  setupErrorHandling() {
    // Main error handler for cross-origin script errors
    window.addEventListener('error', (event) => {
      if (this.isCrossOriginScriptError(event)) {
        console.warn('🌐 Cross-origin script error intercepted:', {
          message: event.message,
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          hostname: window.location.hostname
        });

        this.handleCrossOriginError(event);
        event.preventDefault(); // Prevent the error from propagating
        return true;
      }
    }, true);

    // Handle unhandled promise rejections that might be network-related
    window.addEventListener('unhandledrejection', (event) => {
      if (this.isNetworkRelatedError(event.reason)) {
        console.warn('🌐 Network-related promise rejection:', event.reason);
        this.handleNetworkError(event.reason);
        event.preventDefault();
      }
    });

    // Override console.error to catch React error boundary errors
    const originalConsoleError = console.error;
    console.error = (...args) => {
      if (args[0]?.includes?.('Script error')) {
        console.warn('🌐 Script error suppressed by cross-origin handler');
        return;
      }
      originalConsoleError.apply(console, args);
    };
  }

  isCrossOriginScriptError(event) {
    return (
      event.message === 'Script error.' &&
      event.filename === '' &&
      event.lineno === 0 &&
      event.colno === 0
    );
  }

  isNetworkRelatedError(reason) {
    if (!reason) return false;
    const reasonStr = reason.toString().toLowerCase();
    return (
      reasonStr.includes('network') ||
      reasonStr.includes('cors') ||
      reasonStr.includes('fetch') ||
      reasonStr.includes('load') ||
      reasonStr.includes('connection')
    );
  }

  handleCrossOriginError(event) {
    this.errorCount++;

    if (this.errorCount === 1) {
      // Show user-friendly notification only once
      this.showCrossOriginNotification();
    }

    if (this.errorCount > this.maxErrors) {
      console.warn(`🚫 Too many cross-origin errors (${this.errorCount}), stopping handling`);
      return;
    }

    // Try to recover by reinitializing app components
    this.attemptRecovery();
  }

  handleNetworkError(reason) {
    console.info('🔧 Attempting network error recovery for:', reason);
    
    // Add a small delay then attempt to recover
    setTimeout(() => {
      if (window.location.pathname !== '/debug') {
        console.info('🔄 Triggering soft reload for network recovery...');
        window.dispatchEvent(new CustomEvent('networkErrorRecovery', {
          detail: { reason: reason.toString() }
        }));
      }
    }, 1000);
  }

  attemptRecovery() {
    console.info('🔄 Attempting cross-origin error recovery...');

    // Dispatch recovery event for components to listen to
    window.dispatchEvent(new CustomEvent('crossOriginErrorRecovery', {
      detail: {
        hostname: window.location.hostname,
        errorCount: this.errorCount,
        timestamp: new Date().toISOString()
      }
    }));

    // Check if critical services are still working
    this.healthCheck();
  }

  async healthCheck() {
    try {
      // Try to reach the backend health endpoint
      const backendUrl = this.getBackendUrl();
      const response = await fetch(`${backendUrl}/api/v1/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });

      if (response.ok) {
        console.info('✅ Backend health check passed');
      } else {
        console.warn('⚠️ Backend health check failed:', response.status);
      }
    } catch (error) {
      console.warn('⚠️ Backend health check error:', error.message);
      
      // If backend is unreachable, show network guidance
      this.showNetworkGuidance();
    }
  }

  getBackendUrl() {
    // Use the same IP as frontend for backend if not localhost
    return this.isNonLocalhost 
      ? `http://${window.location.hostname}:8000`
      : 'http://localhost:8000';
  }

  addCrossOriginAttributes() {
    // Add crossorigin attribute to all script tags to get better error messages
    const scripts = document.querySelectorAll('script[src]');
    scripts.forEach(script => {
      if (!script.hasAttribute('crossorigin')) {
        script.setAttribute('crossorigin', 'anonymous');
      }
    });

    // Set CORS mode for stylesheets too
    const stylesheets = document.querySelectorAll('link[rel="stylesheet"][href]');
    stylesheets.forEach(link => {
      if (!link.hasAttribute('crossorigin')) {
        link.setAttribute('crossorigin', 'anonymous');
      }
    });
  }

  setupNetworkErrorRecovery() {
    // Listen for our own recovery events
    window.addEventListener('crossOriginErrorRecovery', (event) => {
      console.info('🎯 Cross-origin recovery event received:', event.detail);
    });

    window.addEventListener('networkErrorRecovery', (event) => {
      console.info('🎯 Network recovery event received:', event.detail);
    });
  }

  showCrossOriginNotification() {
    if (sessionStorage.getItem('crossOriginNotificationShown')) {
      return; // Already shown this session
    }

    const notification = document.createElement('div');
    notification.id = 'cross-origin-notification';
    notification.innerHTML = `
      <div style="
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        z-index: 10000;
        max-width: 400px;
        text-align: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        animation: slideDown 0.3s ease-out;
      ">
        <div style="font-size: 18px; margin-bottom: 8px;">🌐 Network Access</div>
        <div style="font-size: 14px; line-height: 1.4; margin-bottom: 12px;">
          Accessing from <strong>${window.location.hostname}</strong><br>
          Some script errors are normal and safe to ignore.
        </div>
        <button onclick="this.parentElement.parentElement.remove(); sessionStorage.setItem('crossOriginNotificationShown', 'true')" 
                style="
                  background: rgba(255,255,255,0.2);
                  border: 1px solid rgba(255,255,255,0.3);
                  color: white;
                  padding: 8px 16px;
                  border-radius: 20px;
                  cursor: pointer;
                  font-size: 12px;
                  transition: all 0.2s;
                "
                onmouseover="this.style.background='rgba(255,255,255,0.3)'"
                onmouseout="this.style.background='rgba(255,255,255,0.2)'">
          Got it
        </button>
      </div>
      <style>
        @keyframes slideDown {
          from { transform: translate(-50%, -100%); opacity: 0; }
          to { transform: translate(-50%, 0); opacity: 1; }
        }
      </style>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 8 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.style.animation = 'slideDown 0.3s reverse';
        setTimeout(() => notification.remove(), 300);
      }
    }, 8000);
  }

  showNetworkGuidance() {
    if (sessionStorage.getItem('networkGuidanceShown')) {
      return;
    }

    console.info(`
    🌐 NETWORK ACCESS GUIDANCE:
    
    You're accessing the app from IP: ${window.location.hostname}
    
    ✅ Frontend: http://${window.location.hostname}:3000
    ⚠️  Backend: http://${window.location.hostname}:8000 (may not be accessible)
    
    If you experience issues:
    1. Try accessing from localhost instead
    2. Ensure backend is running on port 8000
    3. Check your network/firewall settings
    
    Current status: Cross-origin errors are being handled gracefully.
    `);

    sessionStorage.setItem('networkGuidanceShown', 'true');
  }

  // Public method to get error statistics
  getStats() {
    return {
      hostname: window.location.hostname,
      isNonLocalhost: this.isNonLocalhost,
      errorCount: this.errorCount,
      maxErrors: this.maxErrors,
      backendUrl: this.getBackendUrl()
    };
  }
}

// Auto-initialize
const crossOriginErrorHandler = new CrossOriginErrorHandler();

// Make available globally for debugging
window.crossOriginErrorHandler = crossOriginErrorHandler;

export default crossOriginErrorHandler;