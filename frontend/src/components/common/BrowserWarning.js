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
    return 'ismeretlen böngésző';
  };

  const getWarningMessage = () => {
    if (browserInfo.isFirefox) {
      return 'A Firefox böngésző használata során script hibák léphetnek fel iOS eszközökön. A legjobb felhasználói élmény érdekében javasoljuk a Chrome böngésző használatát.';
    }
    if (browserInfo.isSafari) {
      return 'A Safari böngésző támogatott, de a Chrome böngésző használatával még jobb teljesítményt érhet el.';
    }
    return 'Az optimális működés érdekében javasoljuk a Chrome böngésző használatát iOS eszközökön.';
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
          <h4>Böngésző figyelmeztetés</h4>
          <button 
            className="browser-warning-close"
            onClick={handleIgnore}
            aria-label="Bezárás"
          >
            ×
          </button>
        </div>
        
        <div className="browser-warning-body">
          <p>
            <strong>Jelenlegi böngésző:</strong> {getBrowserName()}
          </p>
          <p>{getWarningMessage()}</p>
          
          {browserInfo.isFirefox && (
            <div className="firefox-issues">
              <h5>🔍 Ismert Firefox problémák iOS-en:</h5>
              <ul>
                <li>Script betöltési hibák</li>
                <li>Checkbox kezelési problémák</li>
                <li>Hálózati kérések időtúllépése</li>
                <li>Onboarding folyamat megszakadása</li>
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
            📱 Megnyitás Chrome-ban
          </button>
          
          <button 
            className="btn-secondary"
            onClick={handleIgnore}
          >
            Folytatás jelenlegi böngészővel
          </button>
          
          <button 
            className="btn-tertiary"
            onClick={handleDismiss}
          >
            Ne jelenjen meg 24 órán át
          </button>
        </div>
        
        <div className="browser-warning-footer">
          <small>
            💡 <strong>Ajánlás:</strong> Chrome letöltése az App Store-ból az optimális élményért
          </small>
        </div>
      </div>
    </div>
  );
};

export default BrowserWarning;