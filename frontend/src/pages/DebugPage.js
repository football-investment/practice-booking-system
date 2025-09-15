import React, { useState, useEffect } from 'react';

const DebugPage = () => {
  const [diagnostics, setDiagnostics] = useState(null);
  const [testResults, setTestResults] = useState([]);
  const [compatibilityReport, setCompatibilityReport] = useState(null);

  useEffect(() => {
    // Get initial diagnostics
    if (window.errorDiagnostics) {
      setDiagnostics(window.errorDiagnostics.getErrorSummary());
    }
    
    // Get iOS/Firefox compatibility report
    if (window.iosBrowserCompatibility) {
      setCompatibilityReport(window.iosBrowserCompatibility.getCompatibilityReport());
    }
  }, []);

  const runTests = () => {
    console.log('🧪 Running diagnostic tests...');
    const results = [];

    // Test 1: Basic JavaScript
    try {
      const obj = { test: 'value' };
      results.push({ test: 'Basic JavaScript', status: 'PASS', result: obj.test });
    } catch (e) {
      results.push({ test: 'Basic JavaScript', status: 'FAIL', error: e.message });
    }

    // Test 2: Date handling
    try {
      const date = new Date('2025-09-15');
      results.push({ test: 'Date parsing', status: 'PASS', result: date.toISOString() });
    } catch (e) {
      results.push({ test: 'Date parsing', status: 'FAIL', error: e.message });
    }

    // Test 3: API call with detailed error handling using absolute URL
    const apiUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
      ? 'http://localhost:8000' 
      : `http://192.168.1.129:8000`;
    
    const healthUrl = `${apiUrl}/api/v1/debug/health`;
    console.log('Testing API endpoint:', healthUrl);
    
    fetch(healthUrl)
      .then(response => {
        console.log('API Response status:', response.status);
        console.log('API Response headers:', [...response.headers.entries()]);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.text().then(text => {
          console.log('Raw API Response:', text);
          console.log('API Response length:', text.length);
          console.log('API Response first 100 chars:', text.substring(0, 100));
          
          try {
            const parsed = JSON.parse(text);
            console.log('Parsed JSON successfully:', parsed);
            return parsed;
          } catch (jsonError) {
            console.error('JSON Parse Error details:', {
              error: jsonError.message,
              rawText: text,
              textLength: text.length,
              firstChar: text.charAt(0),
              lastChar: text.charAt(text.length - 1)
            });
            throw new Error(`JSON Parse Error: ${jsonError.message}. Raw response: ${text}`);
          }
        });
      })
      .then(data => {
        results.push({ test: 'API Health Check', status: 'PASS', result: data });
        setTestResults([...results]);
      })
      .catch(error => {
        console.error('API Health Check failed:', error);
        results.push({ test: 'API Health Check', status: 'FAIL', error: error.message });
        setTestResults([...results]);
      });

    setTestResults(results);
  };

  const forceCrash = () => {
    // Intentionally trigger different types of errors for testing
    console.log('💥 Force triggering test errors...');
    
    // Undefined variable access (similar to bundle.js:62321:67)
    setTimeout(() => {
      try {
        // eslint-disable-next-line no-undef, no-unused-expressions
        nonExistentVariable.someProperty; // This will throw
      } catch (e) {
        console.log('Caught undefined variable error:', e);
      }
    }, 100);

    // Promise rejection
    setTimeout(() => {
      Promise.reject(new Error('Test promise rejection'));
    }, 200);

    // Date parsing error
    setTimeout(() => {
      try {
        new Date('invalid-date').getTime();
      } catch (e) {
        console.log('Caught date error:', e);
      }
    }, 300);
    
    // Force a cross-origin script error simulation
    setTimeout(() => {
      try {
        // Try to trigger "Script error" by accessing external script context
        const script = document.createElement('script');
        script.src = 'http://example.com/nonexistent.js';
        script.onerror = () => console.log('💥 Cross-origin script error triggered');
        document.head.appendChild(script);
      } catch (e) {
        console.log('Cross-origin error test:', e);
      }
    }, 400);
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>🔍 Debug Page</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <button onClick={runTests} style={{ margin: '5px', padding: '10px' }}>
          Run Diagnostic Tests
        </button>
        <button onClick={forceCrash} style={{ margin: '5px', padding: '10px', backgroundColor: '#ff6b6b', color: 'white' }}>
          Test Error Handling
        </button>
        <button onClick={() => window.location.reload()} style={{ margin: '5px', padding: '10px' }}>
          Reload Page
        </button>
        <button 
          onClick={() => {
            if (window.iosBrowserCompatibility) {
              window.iosBrowserCompatibility.testScriptLoadingIssues();
              window.iosBrowserCompatibility.simulateBundleJsError();
              setCompatibilityReport(window.iosBrowserCompatibility.getCompatibilityReport());
            }
          }} 
          style={{ margin: '5px', padding: '10px', backgroundColor: '#ff9800', color: 'white' }}
        >
          Test iOS/Firefox Issues
        </button>
      </div>

      <h2>Environment Info:</h2>
      <pre style={{ background: '#f0f0f0', padding: '10px', fontSize: '12px' }}>
        User Agent: {navigator.userAgent}
        {'\n'}URL: {window.location.href}
        {'\n'}Protocol: {window.location.protocol}
        {'\n'}Host: {window.location.host}
        {'\n'}Language: {navigator.language}
        {'\n'}Platform: {navigator.platform}
        {'\n'}Online: {navigator.onLine ? 'Yes' : 'No'}
        {'\n'}Cookies: {navigator.cookieEnabled ? 'Enabled' : 'Disabled'}
      </pre>

      <h2>Test Results:</h2>
      {testResults.length > 0 ? (
        <div>
          {testResults.map((result, index) => (
            <div key={index} style={{ 
              margin: '5px 0', 
              padding: '5px', 
              backgroundColor: result.status === 'PASS' ? '#d4edda' : '#f8d7da',
              border: `1px solid ${result.status === 'PASS' ? '#c3e6cb' : '#f5c6cb'}`
            }}>
              <strong>{result.test}:</strong> {result.status}
              {result.result && <div>Result: {JSON.stringify(result.result)}</div>}
              {result.error && <div>Error: {result.error}</div>}
            </div>
          ))}
        </div>
      ) : (
        <p>No tests run yet</p>
      )}

      <h2>Error Diagnostics:</h2>
      {diagnostics ? (
        <div>
          <div style={{ marginBottom: '20px' }}>
            <h3>Browser & Environment Info:</h3>
            <pre style={{ background: '#e8f4f8', padding: '10px', fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(diagnostics.debugInfo, null, 2)}
            </pre>
            <pre style={{ background: '#f0f8e8', padding: '10px', fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(diagnostics.environment, null, 2)}
            </pre>
          </div>
          
          <div style={{ marginBottom: '20px' }}>
            <h3>Source Map Information:</h3>
            <pre style={{ background: '#fff3e0', padding: '10px', fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(diagnostics.sourceMapInfo, null, 2)}
            </pre>
          </div>
          
          <div style={{ marginBottom: '20px' }}>
            <h3>Network Logs (Last 10):</h3>
            <pre style={{ background: '#f3e5f5', padding: '10px', fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(diagnostics.networkLogs, null, 2)}
            </pre>
          </div>
          
          <div style={{ marginBottom: '20px' }}>
            <h3>Errors (Last 10):</h3>
            <pre style={{ background: '#ffebee', padding: '10px', fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(diagnostics.errors, null, 2)}
            </pre>
          </div>
        </div>
      ) : (
        <p>Diagnostics not loaded</p>
      )}

      <h2>iOS/Firefox Compatibility Report:</h2>
      {compatibilityReport ? (
        <div>
          <div style={{ marginBottom: '20px' }}>
            <h3>Browser Detection:</h3>
            <pre style={{ background: '#e3f2fd', padding: '10px', fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(compatibilityReport.browserInfo, null, 2)}
            </pre>
          </div>
          
          <div style={{ marginBottom: '20px' }}>
            <h3>Network Information:</h3>
            <pre style={{ background: '#e8f5e8', padding: '10px', fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(compatibilityReport.networkInfo, null, 2)}
            </pre>
          </div>
          
          <div style={{ marginBottom: '20px' }}>
            <h3>Compatibility Issues:</h3>
            <pre style={{ 
              background: compatibilityReport.issues.length > 0 ? '#ffebee' : '#e8f5e8', 
              padding: '10px', 
              fontSize: '12px', 
              overflow: 'auto' 
            }}>
              {compatibilityReport.issues.length > 0 
                ? JSON.stringify(compatibilityReport.issues, null, 2)
                : 'No compatibility issues detected'
              }
            </pre>
          </div>
        </div>
      ) : (
        <p>Compatibility report not loaded</p>
      )}

      <h2>Console Commands:</h2>
      <p>Open browser console and try:</p>
      <ul>
        <li><code>window.errorDiagnostics.testScenarios()</code></li>
        <li><code>window.errorDiagnostics.getErrorSummary()</code></li>
        <li><code>window.iosBrowserCompatibility.getCompatibilityReport()</code></li>
        <li><code>window.iosBrowserCompatibility.testScriptLoadingIssues()</code></li>
        <li><code>window.iosBrowserCompatibility.simulateBundleJsError()</code></li>
      </ul>
    </div>
  );
};

export default DebugPage;