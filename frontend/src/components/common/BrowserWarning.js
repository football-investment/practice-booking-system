import React, { useState, useEffect } from 'react';
import './BrowserWarning.css';

const BrowserWarning = () => {
  const [showWarning, setShowWarning] = useState(false);
  const [browserInfo, setBrowserInfo] = useState({});

  useEffect(() => {
    const detectBrowser = () => {
      const ua = navigator.userAgent.toLowerCase();
      const isIOS = /ipad|iphone|ipod/.test(ua) && !window.MSStream;
      const isChrome = ua.includes('chrome') && !ua.includes('edg');
      const isFirefox = ua.includes('firefox');
      const isSafari = ua.includes('safari') && !ua.includes('chrome');

      const info = {
        isIOS,
        isChrome,
        isFirefox,
        isSafari,
        userAgent: navigator.userAgent
      };

      setBrowserInfo(info);

      // Show warning for non-Chrome browsers on iOS
      if (isIOS && !isChrome) {
        setShowWarning(true);
        console.warn('🔥 Non-Chrome browser detected on iOS device');
      }
    };

    detectBrowser();
  }, []);

  const handleDismiss = () => {
    setShowWarning(false);
    // Remember user's choice for 24 hours
    localStorage.setItem('browser-warning-dismissed', Date.now().toString());
  };

  const handleIgnore = () => {
    setShowWarning(false);
  };

  // Check if warning was recently dismissed
  useEffect(() => {
    const dismissed = localStorage.getItem('browser-warning-dismissed');
    if (dismissed) {
      const dismissedTime = parseInt(dismissed);
      const now = Date.now();
      const hoursSinceDismissal = (now - dismissedTime) / (1000 * 60 * 60);

      if (hoursSinceDismissal < 24) {
        setShowWarning(false);
      }
    }
  }, []);

  if (!showWarning) return null;

  const getBrowserIcon = () => {
    if (browserInfo.isFirefox) return '🔥';
    if (browserInfo.isSafari) return '🧭';
    return '🌐';
  };

  const getBrowserName = () => {
    if (browserInfo.isFirefox) return 'Firefox';
    if (browserInfo.isSafari) return 'Safari';
    return 'Unknown Browser';
  };

  const getWarningMessage = () => {
    if (browserInfo.isFirefox) {
      return 'Using Firefox browser may cause script errors on iOS devices. For the best user experience, we recommend using Chrome browser.';
    }
    if (browserInfo.isSafari) {
      return 'Safari browser is supported, but you can achieve even better performance using Chrome browser.';
    }
    return 'For optimal performance, we recommend using Chrome browser on iOS devices.';
  };

  const getSeverityLevel = () => {
    if (browserInfo.isFirefox) return 'critical';
    if (browserInfo.isSafari) return 'warning';
    return 'info';
  };

  return (
    <div className={`browser-warning ${getSeverityLevel()}`}>
      <div className="browser-warning-content">
        <div className="browser-warning-header">
          <span className="browser-icon">{getBrowserIcon()}</span>
          <h4>Browser Warning</h4>
          <button
            className="browser-warning-close"
            onClick={handleIgnore}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="browser-warning-body">
          <p>
            <strong>Current Browser:</strong> {getBrowserName()}
          </p>
          <p>{getWarningMessage()}</p>

          {browserInfo.isFirefox && (
            <div className="firefox-issues">
              <h5>🔍 Known Firefox Issues on iOS:</h5>
              <ul>
                <li>Script loading errors</li>
                <li>Checkbox handling problems</li>
                <li>Network request timeouts</li>
                <li>Onboarding process interruptions</li>
              </ul>
            </div>
          )}
        </div>

        <div className="browser-warning-actions">
          <button
            className="btn-primary"
            onClick={() => {
              // Try to open in Chrome (if available)
              const currentUrl = window.location.href;
              const chromeUrl = currentUrl.replace('http://', 'googlechrome://');
              window.open(chromeUrl, '_self');
            }}
          >
            📱 Open in Chrome
          </button>

          <button
            className="btn-secondary"
            onClick={handleIgnore}
          >
            Continue with Current Browser
          </button>

          <button
            className="btn-tertiary"
            onClick={handleDismiss}
          >
            Don't Show for 24 Hours
          </button>
        </div>

        <div className="browser-warning-footer">
          <small>
            💡 <strong>Recommendation:</strong> Download Chrome from the App Store for optimal experience
          </small>
        </div>
      </div>
    </div>
  );
};

export default BrowserWarning;
