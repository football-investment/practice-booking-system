// Environment Configuration
// Secure configuration management for different environments

const config = {
  development: {
    apiUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000',
    enableDebug: process.env.REACT_APP_ENABLE_DEBUG === 'true',
    showTestCredentials: process.env.NODE_ENV === 'development' && process.env.REACT_APP_SHOW_TEST_CREDS === 'true',
    environment: 'development'
  },
  
  production: {
    apiUrl: process.env.REACT_APP_API_URL || '/api',
    enableDebug: false,
    showTestCredentials: false, // Never show credentials in production
    environment: 'production'
  },
  
  test: {
    apiUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000',
    enableDebug: false,
    showTestCredentials: false,
    environment: 'test'
  }
};

// Get current environment configuration
const currentEnv = process.env.NODE_ENV || 'development';
const environmentConfig = config[currentEnv] || config.development;

// Security validation - ensure no credentials are exposed
if (environmentConfig.showTestCredentials && currentEnv === 'production') {
  console.error('SECURITY ERROR: Test credentials cannot be shown in production!');
  environmentConfig.showTestCredentials = false;
}

// Log current environment (only in development)
if (environmentConfig.enableDebug) {
  console.log(`Environment: ${currentEnv}`);
  console.log('Config:', environmentConfig);
}

export default environmentConfig;