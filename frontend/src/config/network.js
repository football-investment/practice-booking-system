// Network configuration for local development
// Update LOCAL_NETWORK_IP with your Mac's IP address when testing from other devices

export const NETWORK_CONFIG = {
  // Your Mac's local network IP - get this with: ifconfig | grep "inet "
  LOCAL_NETWORK_IP: '192.168.1.129',
  
  // Backend port
  BACKEND_PORT: 8000,
  
  // Frontend port (if different from 3000)
  FRONTEND_PORT: 3000
};

// Get the appropriate API URL based on how the frontend is accessed
export const getApiUrl = () => {
  let baseUrl;

  if (process.env.NODE_ENV === 'production') {
    baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  } else {
    const hostname = window.location.hostname;

    // If accessing via localhost, use localhost for backend too
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      baseUrl = `http://localhost:${NETWORK_CONFIG.BACKEND_PORT}`;
    } else {
      // If accessing via local network IP, use the Mac's IP for backend
      baseUrl = `http://${NETWORK_CONFIG.LOCAL_NETWORK_IP}:${NETWORK_CONFIG.BACKEND_PORT}`;
    }
  }

  // Add /api/v1 prefix if not already present
  if (!baseUrl.endsWith('/api/v1')) {
    return `${baseUrl}/api/v1`;
  }
  return baseUrl;
};

// Instructions for iPad testing:
try {
  console.log('🔧 Network Configuration:');
  console.log(`📱 For iPad testing, access frontend at: http://${NETWORK_CONFIG.LOCAL_NETWORK_IP}:${NETWORK_CONFIG.FRONTEND_PORT}`);
  console.log(`🖥️  Backend automatically configured for: ${getApiUrl()}`);
  console.log(`🌐 Current hostname: ${window.location.hostname}`);
  console.log(`📝 Update LOCAL_NETWORK_IP in frontend/src/config/network.js if your IP changes`);
} catch (error) {
  console.error('Network configuration error:', error);
}