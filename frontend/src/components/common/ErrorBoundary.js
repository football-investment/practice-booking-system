import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null 
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('🚨 React Error Boundary caught an error:', {
      error: error,
      errorInfo: errorInfo,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    });

    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Error logged above - no additional diagnostics needed

    // Attempt to send to backend for logging
    this.logErrorToBackend(error, errorInfo);
  }

  async logErrorToBackend(error, errorInfo) {
    try {
      const apiUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://localhost:8000' 
        : 'http://192.168.1.129:8000';

      await fetch(`${apiUrl}/api/v1/debug/log-error`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'react_error_boundary',
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href
        }),
      });
    } catch (logError) {
      console.warn('Failed to log React error to backend:', logError);
    }
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      return (
        <div style={{
          padding: '20px',
          margin: '20px',
          backgroundColor: '#ffebee',
          border: '1px solid #f44336',
          borderRadius: '4px',
          fontFamily: 'monospace'
        }}>
          <h2>🚨 Something went wrong</h2>
          <details style={{ whiteSpace: 'pre-wrap' }}>
            <summary>Error Details (click to expand)</summary>
            <h3>Error:</h3>
            <pre>{this.state.error && this.state.error.toString()}</pre>
            
            <h3>Error Stack:</h3>
            <pre>{this.state.error && this.state.error.stack}</pre>
            
            <h3>Component Stack:</h3>
            <pre>{this.state.errorInfo && this.state.errorInfo.componentStack}</pre>
            
            <h3>Debug Information:</h3>
            <pre>{JSON.stringify({
              timestamp: new Date().toISOString(),
              userAgent: navigator.userAgent,
              url: window.location.href,
              platform: navigator.platform,
              language: navigator.language
            }, null, 2)}</pre>
          </details>
          
          <div style={{ marginTop: '20px' }}>
            <button 
              onClick={() => window.location.reload()}
              style={{
                padding: '10px 15px',
                backgroundColor: '#2196f3',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                marginRight: '10px',
                cursor: 'pointer'
              }}
            >
              Reload Page
            </button>
            
            <button 
              onClick={() => {
                this.setState({ hasError: false, error: null, errorInfo: null });
              }}
              style={{
                padding: '10px 15px',
                backgroundColor: '#ff9800',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Try Again
            </button>
            
            <a 
              href="/debug"
              style={{
                display: 'inline-block',
                padding: '10px 15px',
                backgroundColor: '#4caf50',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '4px',
                marginLeft: '10px'
              }}
            >
              Go to Debug Page
            </a>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;