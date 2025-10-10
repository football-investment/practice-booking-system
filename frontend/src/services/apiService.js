import { getApiUrl } from '../config/network';

const API_BASE_URL = getApiUrl();

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const token = localStorage.getItem('token');
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        // Only add Authorization header if token exists AND this is not a login request
        ...(token && !endpoint.includes('/auth/login') && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    };

    try {
      // Add timeout to prevent hanging requests
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      config.signal = controller.signal;
      
      const response = await fetch(url, config);
      clearTimeout(timeoutId);
      
      // Log all request details for debugging
      console.log(`🌐 API Request: ${config.method || 'GET'} ${url}`, {
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        ok: response.ok
      });
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        console.error('❌ API Error Response:', error);
        
        let errorMessage = error.detail || `HTTP ${response.status}`;
        
        // User-friendly error messages
        switch (response.status) {
          case 400:
            if (error.detail === "Inactive user") {
              errorMessage = "Your account has been deactivated. Contact an administrator.";
            }
            break;
          case 401:
            if (error.detail === "Could not validate credentials" || error.detail?.includes("token") || error.detail?.includes("credentials")) {
              errorMessage = "Session expired. Please log in again.";
              // Clear invalid token
              localStorage.removeItem('token');
              localStorage.removeItem('user');
              // Don't redirect immediately during quiz submission - let user see the error first
              setTimeout(() => {
                window.location.href = '/login';
              }, 2000);
            } else {
              errorMessage = "Invalid email or password.";
            }
            break;
          case 403:
            errorMessage = "Access denied.";
            break;
          case 500:
            errorMessage = "Server error. Please try again later.";
            break;
          default:
            errorMessage = error.detail || `HTTP ${response.status}`;
            break;
        }
        
        throw new Error(errorMessage);
      }
      
      return await response.json();
    } catch (error) {
      // Enhanced error handling for cross-origin and network issues
      console.error('API Request failed:', {
        url,
        error: error.message,
        name: error.name,
        cause: error.cause,
        baseURL: this.baseURL
      });
      
      // Handle different types of network errors
      if (error.name === 'AbortError') {
        const timeoutError = new Error('Request timeout - server may be unreachable');
        timeoutError.type = 'TIMEOUT';
        throw timeoutError;
      }
      
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        const networkError = new Error('Network error - check if backend server is running');
        networkError.type = 'NETWORK';
        networkError.originalError = error;
        
        // Add guidance for cross-origin access
        const hostname = window.location.hostname;
        if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
          networkError.message += `\n\nTip: You're accessing from ${hostname}. Make sure the backend is also accessible on this network.`;
        }
        
        throw networkError;
      }
      
      if (error.message.includes('CORS') || error.message.includes('cors')) {
        const corsError = new Error('Cross-origin request blocked');
        corsError.type = 'CORS';
        corsError.originalError = error;
        throw corsError;
      }
      
      // Default error handling
      throw error;
    }
  }

  // GENERIC HTTP METHODS
  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async patch(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  // AUTH ENDPOINTS
  async login(credentials) {
    console.log('🔍 ApiService login called with:', {
      email: credentials.email,
      hasPassword: !!credentials.password,
      baseURL: this.baseURL
    });
    
    // CRITICAL: Don't send Authorization header for login requests
    // Clear any existing token before login attempt
    const oldToken = localStorage.getItem('token');
    if (oldToken) {
      console.log('🗑️ Removing old token for fresh login');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
    
    const response = await this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
      headers: {
        // Explicitly don't include Authorization header
        'Content-Type': 'application/json'
      }
    });
    
    console.log('✅ ApiService login successful:', {
      hasToken: !!response.access_token,
      tokenType: response.token_type
    });
    
    return response;
  }

  async logout() {
    return this.request('/api/v1/auth/logout', { method: 'POST' });
  }

  async changePassword(passwordData) {
    return this.request('/api/v1/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(passwordData),
    });
  }

  // USER ENDPOINTS
  async getCurrentUser() {
    return this.request('/api/v1/users/me');
  }

  async updateProfile(profileData) {
    return this.request('/api/v1/users/me', {
      method: 'PATCH',
      body: JSON.stringify(profileData),
    });
  }

  // changePassword moved to later section to avoid duplicates

  async uploadProfilePicture(imageFile) {
    const formData = new FormData();
    formData.append('file', imageFile);
    
    return this.request('/api/v1/users/me/avatar', {
      method: 'POST',
      headers: {
        // Don't set Content-Type header for FormData, browser sets it automatically
      },
      body: formData,
    });
  }

  async getUsers() {
    return this.request('/api/v1/users/');
  }

  async createUser(userData) {
    return this.request('/api/v1/users/', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async updateUser(userId, userData) {
    return this.request(`/api/v1/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(userData),
    });
  }

  async deleteUser(userId) {
    return this.request(`/api/v1/users/${userId}`, {
      method: 'DELETE',
    });
  }

  // SESSION ENDPOINTS
  async getSessions() {
    try {
      const response = await this.request('/api/v1/sessions/');
      // API response received
      return response;
    } catch (error) {
      console.error('getSessions API error:', error);
      throw error;
    }
  }

  async getSession(sessionId) {
    return this.request(`/api/v1/sessions/${sessionId}`);
  }

  async getMySessions() {
    try {
      return await this.request('/api/v1/sessions/');
    } catch (error) {
      console.warn('getMySessions API failed, using fallback:', error);
      // FALLBACK - return empty array for sessions
      return [];
    }
  }

  // Session CRUD methods moved to SESSION CRUD OPERATIONS section to avoid duplicates

  // BOOKING ENDPOINTS
  async createBooking(bookingData) {
    return this.request('/api/v1/bookings/', {
      method: 'POST',
      body: JSON.stringify(bookingData),
    });
  }

  async getMyBookings() {
    try {
        const response = await this.request('/api/v1/bookings/me');
        // Enhanced booking data received
        
        // Ensure we get the enhanced booking data with attendance info
        return {
            ...response,
            bookings: response.bookings?.map(booking => ({
                ...booking,
                // Enhanced properties from backend hybrid_property fields
                attended: booking.attended || false,
                can_give_feedback: booking.can_give_feedback || false,
                feedback_submitted: booking.feedback_submitted || false,
                // Additional computed properties for frontend
                is_past_session: booking.session ? new Date(booking.session.date_end) < new Date() : false,
                can_cancel: booking.status === 'confirmed' && booking.session ? 
                    new Date(booking.session.date_start) > new Date() : false
            })) || []
        };
    } catch (error) {
        console.error('Failed to get my bookings:', error);
        throw error;
    }
  }

  async getAllBookings() {
    return this.request('/api/v1/bookings/');
  }

  async cancelBooking(bookingId) {
    return this.request(`/api/v1/bookings/${bookingId}`, {
      method: 'DELETE',
    });
  }

  // GROUP ENDPOINTS
  async getGroups() {
    return this.request('/api/v1/groups/');
  }

  async getGroup(groupId) {
    return this.request(`/api/v1/groups/${groupId}`);
  }

  async createGroup(groupData) {
    return this.request('/api/v1/groups/', {
      method: 'POST',
      body: JSON.stringify(groupData),
    });
  }

  async updateGroup(groupId, groupData) {
    return this.request(`/api/v1/groups/${groupId}`, {
      method: 'PATCH',
      body: JSON.stringify(groupData),
    });
  }

  async deleteGroup(groupId) {
    return this.request(`/api/v1/groups/${groupId}`, {
      method: 'DELETE',
    });
  }

  // SEMESTER ENDPOINTS
  async getSemesters() {
    return this.request('/api/v1/semesters/');
  }

  async createSemester(semesterData) {
    return this.request('/api/v1/semesters/', {
      method: 'POST',
      body: JSON.stringify(semesterData),
    });
  }

  async updateSemester(semesterId, semesterData) {
    return this.request(`/api/v1/semesters/${semesterId}`, {
      method: 'PATCH',
      body: JSON.stringify(semesterData),
    });
  }

  async deleteSemester(semesterId) {
    return this.request(`/api/v1/semesters/${semesterId}`, {
      method: 'DELETE',
    });
  }

  // FEEDBACK ENDPOINTS
  async submitFeedback(feedbackData) {
    return this.request('/api/v1/feedback/', {
      method: 'POST',
      body: JSON.stringify(feedbackData),
    });
  }

  async getMyFeedback() {
    return this.request('/api/v1/feedback/me');
  }

  async getAllFeedback() {
    return this.request('/api/v1/feedback/');
  }

  async updateFeedback(feedbackId, feedbackData) {
    return this.request(`/api/v1/feedback/${feedbackId}`, {
      method: 'PATCH',
      body: JSON.stringify(feedbackData),
    });
  }

  async deleteFeedback(feedbackId) {
    return this.request(`/api/v1/feedback/${feedbackId}`, {
      method: 'DELETE',
    });
  }

  // ATTENDANCE ENDPOINTS
  async getAttendance() {
    return this.request('/api/v1/attendance/');
  }

  async checkIn(bookingId, notes = null) {
    return this.request(`/api/v1/attendance/${bookingId}/checkin`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  // markAttendance moved to later section to avoid duplicates

  // GAMIFICATION ENDPOINTS
  async getMyGamificationData() {
    try {
      return await this.request('/api/v1/gamification/me');
    } catch (error) {
      console.warn('Gamification API failed, using fallback:', error);
      // FALLBACK - return data matching UI structure
      return {
        stats: {
          total_xp: 0,
          level: 1,
          semesters_participated: 0,
          total_attended: 0,
          attendance_rate: 0,
          feedback_given: 0
        },
        achievements: [],
        status: {
          title: "📚 New Student",
          icon: "📚",
          is_returning: false
        },
        next_level: {
          current_xp: 0,
          next_level_xp: 1000,
          progress_percentage: 80
        }
      };
    }
  }

  // QUIZ ENDPOINTS
  async getAvailableQuizzes() {
    return this.request('/api/v1/quizzes/available');
  }

  async getQuizzesByCategory(category) {
    return this.request(`/api/v1/quizzes/category/${category}`);
  }

  async getQuizForTaking(quizId) {
    return this.request(`/api/v1/quizzes/${quizId}`);
  }

  async startQuizAttempt(quizId) {
    return this.request('/api/v1/quizzes/start', {
      method: 'POST',
      body: JSON.stringify({ quiz_id: quizId }),
    });
  }

  async submitQuizAttempt(attemptId, answers) {
    return this.request('/api/v1/quizzes/submit', {
      method: 'POST',
      body: JSON.stringify({ 
        attempt_id: attemptId, 
        answers: answers 
      }),
    });
  }

  async getMyQuizAttempts() {
    return this.request('/api/v1/quizzes/attempts/my');
  }

  async getMyQuizStatistics() {
    return this.request('/api/v1/quizzes/statistics/my');
  }

  async getQuizDashboardOverview() {
    return this.request('/api/v1/quizzes/dashboard/overview');
  }

  // Admin/Instructor quiz endpoints
  async createQuiz(quizData) {
    return this.request('/api/v1/quizzes/', {
      method: 'POST',
      body: JSON.stringify(quizData),
    });
  }

  async getAllQuizzesAdmin() {
    return this.request('/api/v1/quizzes/admin/all');
  }

  async getQuizAdmin(quizId) {
    return this.request(`/api/v1/quizzes/admin/${quizId}`);
  }

  async getQuizStatistics(quizId) {
    return this.request(`/api/v1/quizzes/statistics/${quizId}`);
  }

  async getQuizLeaderboard(quizId) {
    return this.request(`/api/v1/quizzes/leaderboard/${quizId}`);
  }

  // PROJECT ENDPOINTS
  async getProjects(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/projects/${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  async getMyProjects(params = {}) {
    try {
      // Use the correct endpoint: /projects/my/summary for dashboard
      return await this.request('/api/v1/projects/my/summary');
    } catch (error) {
      console.warn('getMyProjects API failed, using fallback:', error);
      // FALLBACK - return empty structure for projects
      return { projects: [], total: 0 };
    }
  }

  async getProject(projectId) {
    return this.request(`/api/v1/projects/${projectId}`);
  }

  async enrollInProject(projectId) {
    return this.request(`/api/v1/projects/${projectId}/enroll`, {
      method: 'POST',
    });
  }

  async withdrawFromProject(projectId) {
    return this.request(`/api/v1/projects/${projectId}/enroll`, {
      method: 'DELETE',
    });
  }

  async getMyCurrentProject() {
    return this.request('/api/v1/projects/my/current');
  }

  async getMyProjectSummary() {
    return this.request('/api/v1/projects/my/summary');
  }

  async getProjectProgress(projectId) {
    return this.request(`/api/v1/projects/${projectId}/progress`);
  }

  // Milestone management endpoints
  async submitMilestone(projectId, milestoneId) {
    return this.request(`/api/v1/projects/${projectId}/milestones/${milestoneId}/submit`, {
      method: 'POST'
    });
  }

  async approveMilestone(projectId, milestoneId, feedback = null) {
    return this.request(`/api/v1/projects/${projectId}/milestones/${milestoneId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ feedback })
    });
  }

  async rejectMilestone(projectId, milestoneId, feedback) {
    return this.request(`/api/v1/projects/${projectId}/milestones/${milestoneId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ feedback })
    });
  }

  // Admin/Instructor project endpoints (createProject moved to PROJECT CRUD OPERATIONS section)

  // INSTRUCTOR ENDPOINTS
  async getInstructorSessions() {
    return this.request('/api/v1/sessions/instructor/my');
  }

  async getInstructorProjects() {
    return this.request('/api/v1/projects/instructor/my');
  }

  // PROJECT CRUD OPERATIONS
  async createProject(projectData) {
    return this.request('/api/v1/projects/', {
      method: 'POST',
      body: JSON.stringify(projectData),
    });
  }

  async updateProject(projectId, projectData) {
    return this.request(`/api/v1/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(projectData),
    });
  }

  async deleteProject(projectId) {
    return this.request(`/api/v1/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  async getProjectDetails(projectId) {
    return this.request(`/api/v1/projects/${projectId}`);
  }

  async getInstructorStudents() {
    return this.request('/api/v1/users/instructor/students');
  }

  async getInstructorStudentDetails(studentId) {
    return this.request(`/api/v1/users/instructor/students/${studentId}`);
  }

  async getInstructorStudentProgress(studentId) {
    return this.request(`/api/v1/users/instructor/students/${studentId}/progress`);
  }

  async getInstructorFeedback() {
    return this.request('/api/v1/feedback/instructor/my');
  }

  async getInstructorAttendance() {
    return this.request('/api/v1/attendance/instructor/overview');
  }

  async getProjectStudents(projectId) {
    return this.request(`/api/v1/projects/${projectId}/students`);
  }

  async enrollStudentInProject(projectId, studentId) {
    return this.request(`/api/v1/projects/${projectId}/instructor/enroll/${studentId}`, {
      method: 'POST',
    });
  }

  async removeStudentFromProject(projectId, studentId) {
    return this.request(`/api/v1/projects/${projectId}/instructor/enroll/${studentId}`, {
      method: 'DELETE',
    });
  }

  // SESSION CRUD OPERATIONS
  async createSession(sessionData) {
    return this.request('/api/v1/sessions/', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    });
  }

  async updateSession(sessionId, sessionData) {
    return this.request(`/api/v1/sessions/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify(sessionData),
    });
  }

  async deleteSession(sessionId) {
    return this.request(`/api/v1/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  async getSessionDetails(sessionId) {
    return this.request(`/api/v1/sessions/${sessionId}`);
  }

  async getSessionBookings(sessionId) {
    return this.request(`/api/v1/sessions/${sessionId}/bookings`);
  }

  async addSessionNote(sessionId, note) {
    return this.request(`/api/v1/sessions/${sessionId}/notes`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
  }

  async getSessionNotes(sessionId) {
    return this.request(`/api/v1/sessions/${sessionId}/notes`);
  }

  async getSessionAttendance(sessionId) {
    return this.request(`/api/v1/sessions/${sessionId}/attendance`);
  }

  async markAttendance(sessionId, userId, attended) {
    return this.request(`/api/v1/sessions/${sessionId}/attendance`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        attended: attended
      }),
    });
  }

  // NOTIFICATIONS ENDPOINTS
  async getMyNotifications(page = 1, size = 50, unreadOnly = false) {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
      unread_only: unreadOnly.toString()
    });
    return this.request(`/api/v1/notifications/me?${params}`);
  }

  async markNotificationsAsRead(notificationIds) {
    return this.request('/api/v1/notifications/mark-read', {
      method: 'PUT',
      body: JSON.stringify({
        notification_ids: notificationIds
      })
    });
  }

  async markAllNotificationsAsRead() {
    return this.request('/api/v1/notifications/mark-all-read', {
      method: 'PUT'
    });
  }

  async createNotification(notificationData) {
    return this.request('/api/v1/notifications/', {
      method: 'POST',
      body: JSON.stringify(notificationData)
    });
  }

  async deleteNotification(notificationId) {
    return this.request(`/api/v1/notifications/${notificationId}`, {
      method: 'DELETE'
    });
  }

  // HEALTH CHECK
  async getHealth() {
    return this.request('/health');
  }

  // MESSAGES ENDPOINTS
  async getInboxMessages(page = 1, size = 50, unreadOnly = false) {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
      unread_only: unreadOnly.toString()
    });
    return this.request(`/api/v1/messages/inbox?${params}`);
  }

  async getSentMessages(page = 1, size = 50) {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString()
    });
    return this.request(`/api/v1/messages/sent?${params}`);
  }

  async getMessage(messageId) {
    return this.request(`/api/v1/messages/${messageId}`);
  }

  async sendMessage(messageData) {
    return this.request('/api/v1/messages/', {
      method: 'POST',
      body: JSON.stringify(messageData),
    });
  }

  async sendMessageByNickname(messageData) {
    return this.request('/api/v1/messages/by-nickname', {
      method: 'POST',
      body: JSON.stringify(messageData),
    });
  }

  async markMessageAsRead(messageId) {
    return this.request(`/api/v1/messages/${messageId}`, {
      method: 'PUT',
      body: JSON.stringify({ is_read: true }),
    });
  }

  async getAvailableUsers() {
    return this.request('/api/v1/messages/users/available');
  }

  async deleteMessage(messageId) {
    return this.request(`/api/v1/messages/${messageId}`, {
      method: 'DELETE',
    });
  }

  async editMessage(messageId, newContent) {
    return this.request(`/api/v1/messages/${messageId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: newContent
      })
    });
  }

  async deleteConversation(userId) {
    return this.request(`/api/v1/messages/conversation/${userId}`, {
      method: 'DELETE',
    });
  }

  // 💰 PAYMENT VERIFICATION ENDPOINTS
  async getStudentsPaymentStatus() {
    return this.request('/api/v1/payment-verification/students');
  }

  async verifyStudentPayment(studentId) {
    return this.request(`/api/v1/payment-verification/students/${studentId}/verify`, {
      method: 'POST',
    });
  }

  async unverifyStudentPayment(studentId) {
    return this.request(`/api/v1/payment-verification/students/${studentId}/unverify`, {
      method: 'POST',
    });
  }

  async getStudentPaymentStatus(studentId) {
    return this.request(`/api/v1/payment-verification/students/${studentId}/status`);
  }

  // 🎓🔀 PARALLEL SPECIALIZATION ENDPOINTS
  async getMySpecializations() {
    return this.request('/api/v1/parallel-specializations/my-specializations');
  }

  async getAvailableSpecializations() {
    return this.request('/api/v1/parallel-specializations/available');
  }

  async getSpecializationDashboard() {
    return this.request('/api/v1/parallel-specializations/dashboard');
  }

  async startNewSpecialization(specialization) {
    return this.request('/api/v1/parallel-specializations/start', {
      method: 'POST',
      body: JSON.stringify({ specialization }),
    });
  }

  async validateSpecializationAddition(specialization) {
    return this.request(`/api/v1/parallel-specializations/validate/${specialization}`);
  }

  async getSpecializationCombinations() {
    return this.request('/api/v1/parallel-specializations/combinations');
  }

  async getSemesterSpecializationInfo(semester) {
    return this.request(`/api/v1/parallel-specializations/semester-info/${semester}`);
  }

  async getProgressionRules() {
    return this.request('/api/v1/parallel-specializations/progression-rules');
  }

  // 🏮 GANCUJU LICENSE SYSTEM ENDPOINTS
  async getLicenseMetadata(specialization = null) {
    const url = specialization 
      ? `/api/v1/licenses/metadata?specialization=${specialization}`
      : '/api/v1/licenses/metadata';
    return this.request(url);
  }

  async getLicenseLevelMetadata(specialization, level) {
    return this.request(`/api/v1/licenses/metadata/${specialization}/${level}`);
  }

  async getSpecializationProgression(specialization) {
    return this.request(`/api/v1/licenses/progression/${specialization}`);
  }

  async getMyLicenses() {
    return this.request('/api/v1/licenses/my-licenses');
  }

  async getLicenseDashboard() {
    return this.request('/api/v1/licenses/dashboard');
  }

  async requestLicenseAdvancement(specialization, targetLevel, reason = '') {
    return this.request('/api/v1/licenses/advance', {
      method: 'POST',
      body: JSON.stringify({
        specialization,
        target_level: targetLevel,
        reason
      }),
    });
  }

  async checkAdvancementRequirements(specialization, level) {
    return this.request(`/api/v1/licenses/requirements/${specialization}/${level}`);
  }

  async getLicenseMarketingContent(specialization, level = null) {
    const url = level 
      ? `/api/v1/licenses/marketing/${specialization}?level=${level}`
      : `/api/v1/licenses/marketing/${specialization}`;
    return this.request(url);
  }

  // Gamification Profile API
  async getGamificationProfile() {
    try {
      return await this.request('/api/v1/gamification/profile');
    } catch (error) {
      console.warn('Gamification profile unavailable:', error.message);
      // Return fallback data structure
      return {
        points: 0,
        level: 1,
        achievements: [],
        stats: {
          sessions_attended: 0,
          projects_completed: 0,
          quizzes_passed: 0
        }
      };
    }
  }

  // Unified Dashboard API Methods
  async getDashboardOverview(params = {}) {
    const { role } = params;
    
    try {
      // Build unified dashboard data by combining existing endpoints
      const dashboardData = {
        overview: {},
        widgets: [],
        quick_actions: [],
        notifications: [],
        performance_metrics: {},
        user: null
      };

      // Get user info
      try {
        const userInfo = await this.getCurrentUser();
        dashboardData.user = userInfo;
      } catch (err) {
        console.warn('User info unavailable:', err.message);
      }

      // Role-specific data loading
      if (role === 'student') {
        try {
          // Get student-specific overview data
          const [sessions, projects, quiz, gamification] = await Promise.allSettled([
            this.getSessions(),
            this.getProjects(), 
            this.getQuizDashboardOverview(),
            this.getMyGamificationData()
          ]);

          dashboardData.overview = {
            upcoming_sessions: sessions.status === 'fulfilled' && Array.isArray(sessions.value) ? sessions.value.slice(0, 3) : [],
            enrolled_projects: projects.status === 'fulfilled' && Array.isArray(projects.value) ? projects.value.slice(0, 3) : [],
            quiz_progress: quiz.status === 'fulfilled' ? quiz.value : {},
            gamification: gamification.status === 'fulfilled' ? gamification.value : {
              points: 0, level: 1, achievements: [], stats: { sessions_attended: 0, projects_completed: 0, quizzes_passed: 0 }
            }
          };

          dashboardData.quick_actions = [
            { id: 'view_sessions', title: 'View Sessions', icon: 'calendar', url: '/student/sessions' },
            { id: 'my_projects', title: 'My Projects', icon: 'folder', url: '/student/projects/my' },
            { id: 'take_quiz', title: 'Take Quiz', icon: 'quiz', url: '/student/quiz' },
            { id: 'view_profile', title: 'Profile', icon: 'user', url: '/student/profile' }
          ];
        } catch (err) {
          console.warn('Student dashboard data error:', err.message);
        }
      } else if (role === 'instructor') {
        try {
          // Get instructor-specific data
          const [sessions, projects] = await Promise.allSettled([
            this.getInstructorSessions(),
            this.getInstructorProjects()
          ]);

          dashboardData.overview = {
            my_sessions: sessions.status === 'fulfilled' && Array.isArray(sessions.value) ? sessions.value.slice(0, 3) : [],
            my_projects: projects.status === 'fulfilled' && Array.isArray(projects.value) ? projects.value.slice(0, 3) : []
          };

          dashboardData.quick_actions = [
            { id: 'manage_sessions', title: 'Manage Sessions', icon: 'calendar', url: '/instructor/sessions' },
            { id: 'manage_projects', title: 'Manage Projects', icon: 'folder', url: '/instructor/projects' },
            { id: 'view_students', title: 'Students', icon: 'users', url: '/instructor/students' },
            { id: 'analytics', title: 'Analytics', icon: 'chart', url: '/instructor/analytics' }
          ];
        } catch (err) {
          console.warn('Instructor dashboard data error:', err.message);
        }
      } else if (role === 'admin') {
        dashboardData.quick_actions = [
          { id: 'user_management', title: 'Manage Users', icon: 'users', url: '/admin/users' },
          { id: 'session_management', title: 'Manage Sessions', icon: 'calendar', url: '/admin/sessions' },
          { id: 'project_management', title: 'Manage Projects', icon: 'folder', url: '/admin/projects' },
          { id: 'reports', title: 'Reports', icon: 'chart', url: '/admin/reports' }
        ];
      }

      return dashboardData;
    } catch (error) {
      console.error('Dashboard overview error:', error);
      throw new Error(`Dashboard data unavailable: ${error.message}`);
    }
  }

  async getLearningJourneyOverview() {
    try {
      // Combine multiple endpoints for learning journey
      const [projects, quiz, gamification] = await Promise.allSettled([
        this.getProjects(),
        this.getQuizDashboardOverview(),
        this.getMyGamificationData()
      ]);

      return {
        projects: projects.status === 'fulfilled' && Array.isArray(projects.value) ? projects.value : [],
        quiz_progress: quiz.status === 'fulfilled' ? quiz.value : {},
        achievements: gamification.status === 'fulfilled' && Array.isArray(gamification.value?.achievements) ? gamification.value.achievements : []
      };
    } catch (error) {
      console.error('Learning journey error:', error);
      throw new Error(`Learning journey unavailable: ${error.message}`);
    }
  }

  // LFA Education Center specific API methods

  async getPerformanceAnalytics() {
    try {
      return await this.request('/api/v1/analytics/performance');
    } catch (error) {
      console.warn('Performance analytics not available:', error);
      return null;
    }
  }

  async getPendingQuizzes(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/quizzes/pending${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Pending quizzes not available:', error);
      return { quizzes: [] };
    }
  }

  async getActiveProjects(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/projects/active${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Active projects not available:', error);
      return { projects: [] };
    }
  }

  async startAdaptiveLesson(recommendationId) {
    return await this.request(`/api/v1/adaptive-learning/start/${recommendationId}`, {
      method: 'POST'
    });
  }

  async getNotifications(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/notifications${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Notifications not available:', error);
      return { unread_count: 0 };
    }
  }

  // ========== LFA EDUCATION CENTER - COMPLETE API INTEGRATION ==========
  
  // Next Session API
  async getNextSession(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/sessions/next${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Next session not available:', error);
      return null;
    }
  }

  // Progress Overview API
  async getProgressOverview(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/progress/overview${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Progress overview not available:', error);
      return { skills: [], overall_progress: 0 };
    }
  }

  // Gamification API
  async getGamificationMe(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/gamification/me${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Gamification data not available:', error);
      return { points: 0, level: 1, achievements: [] };
    }
  }

  // Achievements API - REAL BACKEND DATA
  async getAchievements() {
    try {
      return await this.request('/api/v1/students/dashboard/achievements');
    } catch (error) {
      console.warn('Achievements data not available:', error);
      return {
        achievements: [],
        summary: {
          skill_improved: 0,
          training_consistency: 0,
          focus_array: 0,
          total_unlocked: 0
        },
        gamification_stats: { total_xp: 0, level: 1, achievements: [] }
      };
    }
  }

  // Specializations API
  async getCurrentSpecialization(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/specializations/current${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Current specialization not available:', error);
      return null;
    }
  }

  async getSpecializationOptions(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/specializations/options${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  // Adaptive Learning API
  async getAdaptiveLearningRecommendations(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/adaptive-learning/recommendations${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Adaptive learning recommendations not available:', error);
      return { recommendations: [] };
    }
  }

  async startAdaptiveLearningModule(recommendationId, data = {}) {
    return this.request(`/api/v1/adaptive-learning/start/${recommendationId}`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // Feedback API
  async getRecentFeedback(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/feedback/recent${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Recent feedback not available:', error);
      return { feedback: [] };
    }
  }

  async getFeedbackHub(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/feedback/hub${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  // Analytics API
  async getPerformanceSummary(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `/api/v1/analytics/performance-summary${queryString ? `?${queryString}` : ''}`;
      return await this.request(url);
    } catch (error) {
      console.warn('Performance summary not available:', error);
      return { overall_score: 0, recent_performance: [] };
    }
  }

  async getDetailedAnalytics(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/analytics/detailed${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  // Quizzes API
  async getQuizzesAll(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/quizzes/${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  // Mentoring API
  async getMentors(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/mentoring/mentors${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  async requestMentor(mentorId, data = {}) {
    return this.request(`/api/v1/mentoring/request/${mentorId}`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // Portfolio API
  async getPortfolio(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/v1/portfolio/${queryString ? `?${queryString}` : ''}`;
    return this.request(url);
  }

  async updatePortfolio(data = {}) {
    return this.request('/api/v1/portfolio/', {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  // Dashboard Data Aggregation API - REAL BACKEND INTEGRATION
  async getLFADashboardData(params = {}) {
    console.log('🚨 PRODUCTION MODE: Loading REAL dashboard data from backend endpoints');
    
    try {
      // Parallel API calls to new specialized endpoints
      const [
        semesterProgressResponse,
        achievementsResponse,
        dailyChallengeResponse,
        sessionsResponse,
        projectsResponse
      ] = await Promise.allSettled([
        this.request('/api/v1/students/dashboard/semester-progress'),
        this.request('/api/v1/students/dashboard/achievements'),
        this.request('/api/v1/students/dashboard/daily-challenge'),
        this.getMySessions(),
        this.getMyProjects()
      ]);

      // Extract data from responses
      const semesterProgress = semesterProgressResponse.status === 'fulfilled' 
        ? semesterProgressResponse.value 
        : { progress: { current_phase: 'No Active Semester', completion_percentage: 0, timeline: [] } };

      const achievements = achievementsResponse.status === 'fulfilled' 
        ? achievementsResponse.value 
        : { achievements: [], summary: { total_unlocked: 0 } };

      const dailyChallenge = dailyChallengeResponse.status === 'fulfilled'
        ? dailyChallengeResponse.value
        : { daily_challenge: null };

      const sessions = sessionsResponse.status === 'fulfilled' 
        ? sessionsResponse.value 
        : { sessions: [], total: 0 };

      const projects = projectsResponse.status === 'fulfilled' 
        ? projectsResponse.value 
        : { projects: [], total: 0 };

      // Find next upcoming session
      const upcomingSessions = sessions.sessions?.filter(session => {
        const sessionDate = new Date(session.date_start);
        return sessionDate > new Date();
      }).sort((a, b) => new Date(a.date_start) - new Date(b.date_start));

      const nextSession = upcomingSessions?.[0] || null;

      // Return 100% REAL BACKEND DATA
      return {
        // Semester Progress
        semesterProgress: semesterProgress.progress,
        
        // Achievement Progress
        achievements: achievements.achievements,
        achievementSummary: achievements.summary,
        
        // Daily Challenge
        dailyChallenge: dailyChallenge.daily_challenge,

        // Next Session
        nextSession: nextSession ? {
          id: nextSession.id,
          title: nextSession.title,
          date_start: nextSession.date_start,
          date_end: nextSession.date_end,
          instructor: nextSession.instructor_name || 'TBA',
          location: nextSession.location || 'TBA',
          capacity: nextSession.capacity,
          current_bookings: nextSession.current_bookings || 0
        } : null,

        // Projects
        activeProjects: {
          projects: projects.projects || [],
          total: projects.total || 0
        }
      };

    } catch (error) {
      console.error('❌ CRITICAL: Real dashboard data loading failed:', error);
      
      // Return minimal REAL data structure - NO MOCK DATA
      return {
        semesterProgress: { current_phase: 'No Active Semester', completion_percentage: 0, timeline: [] },
        achievements: [],
        achievementSummary: { total_unlocked: 0 },
        dailyChallenge: null,
        nextSession: null,
        activeProjects: { projects: [], total: 0 }
      };
    }
  }
}

export const apiService = new ApiService();
export default apiService;