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
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        
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
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // AUTH ENDPOINTS
  async login(credentials) {
    return this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
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
    return this.request('/api/v1/gamification/me');
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
}

export const apiService = new ApiService();
export default apiService;