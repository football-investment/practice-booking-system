/**
 * Axios Instance with Interceptors
 * Centralized HTTP client for all API calls with authentication and error handling
 */

import axios from 'axios';
import { API_BASE_URL } from '../config/api';

/**
 * Create axios instance with base configuration
 */
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request Interceptor
 * Automatically adds authentication token to all requests
 */
axiosInstance.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = localStorage.getItem('access_token');

    // If token exists, add it to Authorization header
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log request in development
    if (process.env.NODE_ENV === 'development') {
      console.log('🚀 API Request:', {
        method: config.method?.toUpperCase(),
        url: config.url,
        data: config.data,
      });
    }

    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 * Handles responses and errors globally
 */
axiosInstance.interceptors.response.use(
  (response) => {
    // Log response in development
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ API Response:', {
        status: response.status,
        url: response.config.url,
        data: response.data,
      });
    }

    return response;
  },
  (error) => {
    // Handle different error scenarios
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;

      console.error('❌ API Error:', {
        status,
        url: error.config?.url,
        data,
      });

      // Handle specific status codes
      switch (status) {
        case 401:
          // Unauthorized - clear token and redirect to login
          console.warn('🔒 Unauthorized - Redirecting to login');
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');

          // Only redirect if not already on login page
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          break;

        case 403:
          // Forbidden - user doesn't have permission
          console.warn('🚫 Forbidden - Insufficient permissions');
          break;

        case 404:
          // Not Found
          console.warn('🔍 Not Found:', error.config?.url);
          break;

        case 500:
          // Server Error
          console.error('💥 Server Error:', data);
          break;

        default:
          console.error('❌ Error:', status, data);
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('📡 Network Error - No response received');
    } else {
      // Error in request setup
      console.error('⚙️ Request Setup Error:', error.message);
    }

    return Promise.reject(error);
  }
);

/**
 * Helper function to check if user is authenticated
 */
export const isAuthenticated = () => {
  const token = localStorage.getItem('access_token');
  return !!token;
};

/**
 * Helper function to get current user from localStorage
 */
export const getCurrentUser = () => {
  try {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  } catch (error) {
    console.error('Error parsing user from localStorage:', error);
    return null;
  }
};

/**
 * Helper function to set auth data in localStorage
 */
export const setAuthData = (token, user) => {
  localStorage.setItem('access_token', token);
  localStorage.setItem('user', JSON.stringify(user));
};

/**
 * Helper function to clear auth data from localStorage
 */
export const clearAuthData = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
};

export default axiosInstance;
