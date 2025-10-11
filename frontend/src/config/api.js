/**
 * API Configuration
 * Centralized API endpoint definitions for the LFA Academy application
 */

// Base URL - use environment variable or default to localhost
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

/**
 * API Endpoints
 * All backend API endpoints organized by feature
 */
export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    ME: '/auth/me',
  },

  // Curriculum
  CURRICULUM: {
    LESSONS: '/curriculum/lessons',
    MODULES: '/curriculum/modules',
    TRACKS: '/curriculum/tracks',
    EXERCISES: '/curriculum/exercises',
    EXERCISE_SUBMIT: (exerciseId) => `/curriculum/exercise/${exerciseId}/submit`,
    EXERCISE_GRADE: (submissionId) => `/curriculum/exercise/submission/${submissionId}/grade`,
  },

  // Quizzes
  QUIZ: {
    AVAILABLE: '/quizzes/available',
    DETAILS: (quizId) => `/quizzes/${quizId}`,
    START: '/quizzes/start',
    SUBMIT: '/quizzes/submit',
    RESULTS: (attemptId) => `/quizzes/attempt/${attemptId}/results`,
  },

  // Adaptive Learning
  ADAPTIVE: {
    PROFILE: '/adaptive-learning/profile',
    RECOMMENDATIONS: '/adaptive-learning/recommendations',
    PERFORMANCE_HISTORY: '/adaptive-learning/performance-history',
    DISMISS_RECOMMENDATION: (recId) => `/adaptive-learning/recommendations/${recId}/dismiss`,
  },

  // Competency
  COMPETENCY: {
    MY_COMPETENCIES: '/competency/my-competencies',
    CATEGORIES: '/competency/categories',
    BREAKDOWN: (categoryId) => `/competency/breakdown/${categoryId}`,
    ASSESSMENT_HISTORY: '/competency/assessment-history',
    MILESTONES: '/competency/milestones',
  },

  // Specializations
  SPECIALIZATION: {
    PROGRESS: '/specializations/progress',
    TRACKS: '/specializations/tracks',
  },

  // Projects
  PROJECTS: {
    LIST: '/projects',
    DETAILS: (projectId) => `/projects/${projectId}`,
    ENROLL: (projectId) => `/projects/${projectId}/enroll`,
    PROGRESS: (projectId) => `/projects/${projectId}/progress`,
  },

  // Sessions
  SESSIONS: {
    LIST: '/sessions',
    DETAILS: (sessionId) => `/sessions/${sessionId}`,
    BOOK: (sessionId) => `/sessions/${sessionId}/book`,
    CANCEL: (sessionId) => `/sessions/${sessionId}/cancel`,
  },

  // Attendance
  ATTENDANCE: {
    MY_ATTENDANCE: '/attendance/my-attendance',
    MARK: (sessionId) => `/attendance/sessions/${sessionId}/mark`,
  },

  // Bookings
  BOOKINGS: {
    MY_BOOKINGS: '/bookings/my-bookings',
    CANCEL: (bookingId) => `/bookings/${bookingId}/cancel`,
  },
};

/**
 * HTTP Methods
 */
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  PATCH: 'PATCH',
  DELETE: 'DELETE',
};

/**
 * HTTP Status Codes
 */
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500,
};

export default {
  API_BASE_URL,
  API_ENDPOINTS,
  HTTP_METHODS,
  HTTP_STATUS,
};
