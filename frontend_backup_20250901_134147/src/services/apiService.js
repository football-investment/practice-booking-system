import axios from 'axios';
import config from '../config/environment';

const API_BASE_URL = config.apiUrl;

class ApiService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Add token to requests if available
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Add response interceptor for better error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        // Handle 401 Unauthorized
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          // Only redirect if we're not already on the login page
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
        
        // Enhanced error messages
        const message = error.response?.data?.message || 
                       error.response?.data?.detail || 
                       error.response?.data?.error?.message ||
                       error.message || 
                       'Unknown error occurred';
        
        // Log error for debugging
        console.error('API Error:', {
          url: error.config?.url,
          method: error.config?.method,
          status: error.response?.status,
          message: message,
          data: error.response?.data
        });
        
        // Attach enhanced error info
        error.enhancedMessage = message;
        
        throw error;
      }
    );
  }

  // Auth endpoints
  async login(email, password) {
    const response = await this.api.post('/api/v1/auth/login', {
      email,
      password
    });
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.api.get('/api/v1/auth/me');
    return response.data;
  }

  // Health check
  async healthCheck() {
    const response = await this.api.get('/health');
    return response.data;
  }

  async detailedHealthCheck() {
    const response = await this.api.get('/health/detailed');
    return response.data;
  }

  // User management
  async getUsers() {
    const response = await this.api.get('/api/v1/users/');
    return response.data.users || [];
  }

  async createUser(userData) {
    const response = await this.api.post('/api/v1/users/', userData);
    return response.data;
  }

  // Semester management
  async getSemesters() {
    const response = await this.api.get('/api/v1/semesters/');
    return response.data.semesters || [];
  }

  // Session management  
  async getSessions() {
    const response = await this.api.get('/api/v1/sessions/');
    return response.data.sessions || [];
  }

  // Booking management
  async getMyBookings() {
    const response = await this.api.get('/api/v1/bookings/me');
    return response.data.bookings || [];
  }

  // Semester Management Extensions
  async getActiveSemester() {
    try {
      const response = await this.api.get('/api/v1/semesters/active');
      return response.data;
    } catch (error) {
      // If no active semester, return null instead of throwing
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  async createSemester(data) {
    const response = await this.api.post('/api/v1/semesters/', data);
    return response.data;
  }

  async updateSemester(id, data) {
    const response = await this.api.patch(`/api/v1/semesters/${id}`, data);
    return response.data;
  }

  async deleteSemester(id) {
    const response = await this.api.delete(`/api/v1/semesters/${id}`);
    return response.data;
  }

  // Session Management Extensions
  async createSession(data) {
    const response = await this.api.post('/api/v1/sessions/', data);
    return response.data;
  }

  async updateSession(id, data) {
    const response = await this.api.patch(`/api/v1/sessions/${id}`, data);
    return response.data;
  }

  async deleteSession(id) {
    const response = await this.api.delete(`/api/v1/sessions/${id}`);
    return response.data;
  }

  // User Management Extensions
  async updateUser(id, data) {
    const response = await this.api.patch(`/api/v1/users/${id}`, data);
    return response.data;
  }

  async deleteUser(id) {
    const response = await this.api.delete(`/api/v1/users/${id}`);
    return response.data;
  }

  async resetUserPassword(id) {
    const response = await this.api.post(`/api/v1/users/${id}/reset-password`);
    return response.data;
  }

  // Booking Management Extensions
  async createBooking(data) {
    const response = await this.api.post('/api/v1/bookings/', data);
    return response.data;
  }

  async cancelBooking(id) {
    const response = await this.api.delete(`/api/v1/bookings/${id}`);
    return response.data;
  }

  // Student Statistics Extensions
  async getMyStatistics(semesterId = null) {
    const url = semesterId 
      ? `/api/v1/bookings/my-stats?semester_id=${semesterId}`
      : '/api/v1/bookings/my-stats';
    const response = await this.api.get(url);
    return response.data;
  }

  // Group Management Extensions
  async getGroups(semesterId = null) {
    let url = '/api/v1/groups/';
    if (semesterId) {
      url += `?semester_id=${semesterId}`;
    }
    const response = await this.api.get(url);
    return response.data.groups || [];
  }

  async createGroup(data) {
    const response = await this.api.post('/api/v1/groups/', data);
    return response.data;
  }

  async updateGroup(id, data) {
    const response = await this.api.patch(`/api/v1/groups/${id}`, data);
    return response.data;
  }

  async deleteGroup(id) {
    const response = await this.api.delete(`/api/v1/groups/${id}`);
    return response.data;
  }

  async getGroupById(id) {
    const response = await this.api.get(`/api/v1/groups/${id}`);
    return response.data;
  }

  async addUserToGroup(groupId, userId) {
    const response = await this.api.post(`/api/v1/groups/${groupId}/users`, {
      user_id: userId
    });
    return response.data;
  }

  async removeUserFromGroup(groupId, userId) {
    const response = await this.api.delete(`/api/v1/groups/${groupId}/users/${userId}`);
    return response.data;
  }

  // Reports & Analytics Extensions
  async getReports() {
    const response = await this.api.get('/api/v1/reports/');
    return response.data;
  }

  async getSemesterReport(semesterId) {
    const response = await this.api.get(`/api/v1/reports/semester/${semesterId}`);
    return response.data;
  }

  async getUserReport(userId) {
    const response = await this.api.get(`/api/v1/reports/user/${userId}`);
    return response.data;
  }

  async getSessionReport(sessionId) {
    const response = await this.api.get(`/api/v1/reports/session/${sessionId}`);
    return response.data;
  }

  async getSystemStats() {
    const response = await this.api.get('/api/v1/reports/system-stats');
    return response.data;
  }

  async exportReport(reportType, format = 'csv') {
    const response = await this.api.get(`/api/v1/reports/export/${reportType}`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  }

  // Analytics & Dashboard Endpoints
  async getAnalyticsMetrics(filters = {}) {
    const params = new URLSearchParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params.append(key, filters[key]);
      }
    });
    
    const queryString = params.toString();
    const url = queryString ? `/api/v1/analytics/metrics?${queryString}` : '/api/v1/analytics/metrics';
    const response = await this.api.get(url);
    return response.data;
  }

  async getAttendanceAnalytics(filters = {}) {
    const params = new URLSearchParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params.append(key, filters[key]);
      }
    });
    
    const queryString = params.toString();
    const url = queryString ? `/api/v1/analytics/attendance?${queryString}` : '/api/v1/analytics/attendance';
    const response = await this.api.get(url);
    return response.data;
  }

  async getBookingAnalytics(filters = {}) {
    const params = new URLSearchParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params.append(key, filters[key]);
      }
    });
    
    const queryString = params.toString();
    const url = queryString ? `/api/v1/analytics/bookings?${queryString}` : '/api/v1/analytics/bookings';
    const response = await this.api.get(url);
    return response.data;
  }

  async getUtilizationAnalytics(filters = {}) {
    const params = new URLSearchParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params.append(key, filters[key]);
      }
    });
    
    const queryString = params.toString();
    const url = queryString ? `/api/v1/analytics/utilization?${queryString}` : '/api/v1/analytics/utilization';
    const response = await this.api.get(url);
    return response.data;
  }

  async getUserAnalytics(filters = {}) {
    const params = new URLSearchParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params.append(key, filters[key]);
      }
    });
    
    const queryString = params.toString();
    const url = queryString ? `/api/v1/analytics/users?${queryString}` : '/api/v1/analytics/users';
    const response = await this.api.get(url);
    return response.data;
  }

  // Profile Management
  async updateMe(data) {
    const response = await this.api.patch('/api/v1/users/me', data);
    return response.data;
  }

  // Feedback System
  async createFeedback(data) {
    const response = await this.api.post('/api/v1/feedback/', data);
    return response.data;
  }

  async getMyFeedback() {
    const response = await this.api.get('/api/v1/feedback/me');
    return response.data;
  }

  async updateFeedback(id, data) {
    const response = await this.api.patch(`/api/v1/feedback/${id}`, data);
    return response.data;
  }

  async deleteFeedback(id) {
    const response = await this.api.delete(`/api/v1/feedback/${id}`);
    return response.data;
  }

  // Attendance System
  async checkinToSession(bookingId) {
    const response = await this.api.post(`/api/v1/attendance/${bookingId}/checkin`);
    return response.data;
  }

  async checkoutFromSession(bookingId) {
    const response = await this.api.post(`/api/v1/attendance/${bookingId}/checkout`);
    return response.data;
  }

  // Enhanced Reporting Methods  
  async generateCustomReport(reportType, filters = {}) {
    const response = await this.api.post('/api/v1/reports/custom', {
      report_type: reportType,
      filters: filters
    });
    return response.data;
  }

  async getReportHistory() {
    const response = await this.api.get('/api/v1/reports/history');
    return response.data;
  }

  // Enhanced Session Management
  async getSessionsByGroup(groupId) {
    const response = await this.api.get(`/api/v1/sessions/?group_id=${groupId}`);
    return response.data;
  }

  async getSessionsBySemester(semesterId) {
    const response = await this.api.get(`/api/v1/sessions/?semester_id=${semesterId}`);
    return response.data;
  }

  async getSessionsByInstructor(instructorId) {
    const response = await this.api.get(`/api/v1/sessions/?instructor_id=${instructorId}`);
    return response.data;
  }

  async getSessionById(id) {
    const response = await this.api.get(`/api/v1/sessions/${id}`);
    return response.data;
  }

  async getSessionsWithFilters(filters = {}) {
    const params = new URLSearchParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params.append(key, filters[key]);
      }
    });
    
    const queryString = params.toString();
    const url = queryString ? `/api/v1/sessions/?${queryString}` : '/api/v1/sessions/';
    const response = await this.api.get(url);
    return response.data.sessions || [];
  }

  // Enhanced User Management  
  async getUsersByRole(role) {
    const response = await this.api.get(`/api/v1/users/?role=${role}`);
    return response.data.users || [];
  }

  async searchUsers(query, filters = {}) {
    const params = new URLSearchParams();
    params.append('q', query);
    
    // Add optional filters
    if (filters.role) params.append('role', filters.role);
    if (filters.is_active !== undefined) params.append('is_active', filters.is_active);
    if (filters.limit) params.append('limit', filters.limit);
    
    const response = await this.api.get(`/api/v1/users/search?${params.toString()}`);
    // Backend now returns a simple array of users, not a wrapper object
    return response.data || [];
  }
}

export const apiService = new ApiService();