/**
 * Role-based Dashboard Configurations
 * Centralized configuration system for unified dashboard
 * Defines widgets, layouts, navigation, and quick actions per user role
 */

// Base configuration shared across roles
const baseConfig = {
  header: {
    showSearch: true,
    showNotifications: true,
    showProfileMenu: true,
    showThemeToggle: true
  },
  statusOverview: {
    refreshInterval: 30000, // 30 seconds
    showPerformanceMetrics: true,
    animations: true
  }
};

// Student Dashboard Configuration
const studentConfig = {
  ...baseConfig,
  role: 'student',
  layout: {
    columns: 3,
    spacing: 'comfortable',
    responsive: true
  },
  navigation: [
    {
      id: 'overview',
      label: 'Dashboard',
      icon: 'dashboard',
      path: '/student/dashboard'
    },
    {
      id: 'specialization',
      label: 'Specialization',
      icon: 'school',
      path: '/student/specialization-select'
    },
    {
      id: 'learning-profile',
      label: 'Learning Profile',
      icon: 'account_circle',
      path: '/student/learning-profile'
    },
    {
      id: 'achievements',
      label: 'Achievements',
      icon: 'emoji_events',
      path: '/student/gamification'
    },
    {
      id: 'learning',
      label: 'My Learning',
      icon: 'menu_book',
      path: '/student/learning',
      submenu: [
        { id: 'tracks', label: 'My Tracks', path: '/student/tracks' },
        { id: 'sessions', label: 'Sessions', path: '/student/sessions' },
        { id: 'quizzes', label: 'Quizzes', path: '/student/quizzes' },
        { id: 'certificates', label: 'Certificates', path: '/student/certificates' }
      ]
    },
    {
      id: 'progress',
      label: 'Progress',
      icon: 'trending_up',
      path: '/student/progress',
      submenu: [
        { id: 'analytics', label: 'My Analytics', path: '/student/analytics' },
        { id: 'achievements', label: 'Achievements', path: '/student/achievements' }
      ]
    },
    {
      id: 'connect',
      label: 'Connect',
      icon: 'forum',
      path: '/student/connect',
      submenu: [
        { id: 'feedback', label: 'Feedback', path: '/student/feedback' }
      ]
    }
  ],
  widgets: [
    {
      id: 'learning_progress',
      type: 'TrackProgressWidget',
      title: 'My Learning Journey',
      size: 'large',
      priority: 1,
      refreshable: true
    },
    {
      id: 'next_session',
      type: 'NextSessionWidget',
      title: 'Next Session',
      size: 'medium',
      priority: 2,
      refreshable: true
    },
    {
      id: 'achievements',
      type: 'AchievementsWidget',
      title: 'Recent Achievements',
      size: 'medium',
      priority: 3,
      refreshable: false
    },
    {
      id: 'recent_activity',
      type: 'ActivityFeedWidget',
      title: 'Recent Activity',
      size: 'large',
      priority: 4,
      refreshable: true
    },
    {
      id: 'quick_stats',
      type: 'QuickStatsWidget',
      title: 'Quick Stats',
      size: 'small',
      priority: 5,
      refreshable: true
    }
  ],
  quickActions: [
    {
      id: 'book_session',
      label: 'Book Session',
      icon: 'event',
      action: 'navigate',
      target: '/student/sessions',
      color: 'primary'
    },
    {
      id: 'take_quiz',
      label: 'Take Quiz',
      icon: 'quiz',
      action: 'navigate',
      target: '/student/quizzes',
      color: 'secondary'
    },
    {
      id: 'view_progress',
      label: 'View Progress',
      icon: 'assessment',
      action: 'navigate',
      target: '/student/progress',
      color: 'info'
    }
  ],
  statusOverview: {
    ...baseConfig.statusOverview,
    showTrackProgress: true,
    showUpcomingSessions: true,
    showAchievements: true
  }
};

// Instructor Dashboard Configuration
const instructorConfig = {
  ...baseConfig,
  role: 'instructor',
  layout: {
    columns: 3,
    spacing: 'comfortable',
    responsive: true
  },
  navigation: [
    {
      id: 'overview',
      label: 'Dashboard',
      icon: 'dashboard',
      path: '/instructor/dashboard'
    },
    {
      id: 'teaching',
      label: 'Teaching',
      icon: 'school',
      path: '/instructor/teaching',
      submenu: [
        { id: 'sessions', label: 'My Sessions', path: '/instructor/sessions' },
        { id: 'projects', label: 'Projects', path: '/instructor/projects' },
        { id: 'students', label: 'Students', path: '/instructor/students' }
      ]
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: 'analytics',
      path: '/instructor/analytics',
      submenu: [
        { id: 'performance', label: 'Performance', path: '/instructor/analytics' },
        { id: 'reports', label: 'Reports', path: '/instructor/reports' }
      ]
    },
    {
      id: 'tools',
      label: 'Tools',
      icon: 'build',
      path: '/instructor/tools',
      submenu: [
        { id: 'attendance', label: 'Attendance', path: '/instructor/attendance' },
        { id: 'feedback', label: 'Feedback', path: '/instructor/feedback' }
      ]
    }
  ],
  widgets: [
    {
      id: 'todays_sessions',
      type: 'TodaysSessionsWidget',
      title: 'Today\'s Sessions',
      size: 'large',
      priority: 1,
      refreshable: true
    },
    {
      id: 'student_progress',
      type: 'StudentProgressWidget',
      title: 'Student Progress Overview',
      size: 'large',
      priority: 2,
      refreshable: true
    },
    {
      id: 'pending_tasks',
      type: 'PendingTasksWidget',
      title: 'Pending Tasks',
      size: 'medium',
      priority: 3,
      refreshable: true
    },
    {
      id: 'class_performance',
      type: 'ClassPerformanceWidget',
      title: 'Class Performance',
      size: 'medium',
      priority: 4,
      refreshable: true
    },
    {
      id: 'recent_feedback',
      type: 'RecentFeedbackWidget',
      title: 'Recent Feedback',
      size: 'small',
      priority: 5,
      refreshable: true
    }
  ],
  quickActions: [
    {
      id: 'create_session',
      label: 'Create Session',
      icon: 'add_circle',
      action: 'modal',
      target: 'create_session_modal',
      color: 'primary'
    },
    {
      id: 'grade_quiz',
      label: 'Grade Quiz',
      icon: 'grading',
      action: 'navigate',
      target: '/instructor/grading',
      color: 'secondary'
    },
    {
      id: 'send_message',
      label: 'Send Message',
      icon: 'send',
      action: 'modal',
      target: 'compose_message_modal',
      color: 'info'
    },
    {
      id: 'view_analytics',
      label: 'Analytics',
      icon: 'bar_chart',
      action: 'navigate',
      target: '/instructor/analytics',
      color: 'success'
    }
  ],
  statusOverview: {
    ...baseConfig.statusOverview,
    showTodaysSessions: true,
    showStudentCount: true,
    showPendingTasks: true,
    showRating: true
  }
};

// Admin Dashboard Configuration
const adminConfig = {
  ...baseConfig,
  role: 'admin',
  layout: {
    columns: 4,
    spacing: 'compact',
    responsive: true
  },
  navigation: [
    {
      id: 'overview',
      label: 'Dashboard',
      icon: 'dashboard',
      path: '/admin/dashboard'
    },
    {
      id: 'users',
      label: 'User Management',
      icon: 'people',
      path: '/admin/users',
      submenu: [
        { id: 'all_users', label: 'All Users', path: '/admin/users' },
        { id: 'instructors', label: 'Instructors', path: '/admin/users/instructors' },
        { id: 'students', label: 'Students', path: '/admin/users/students' }
      ]
    },
    {
      id: 'content',
      label: 'Content Management',
      icon: 'library_books',
      path: '/admin/content',
      submenu: [
        { id: 'tracks', label: 'Tracks', path: '/admin/tracks' },
        { id: 'sessions', label: 'Sessions', path: '/admin/sessions' },
        { id: 'projects', label: 'Projects', path: '/admin/projects' }
      ]
    },
    {
      id: 'system',
      label: 'System',
      icon: 'settings',
      path: '/admin/system',
      submenu: [
        { id: 'configuration', label: 'Configuration', path: '/admin/config' },
        { id: 'monitoring', label: 'Monitoring', path: '/admin/monitoring' },
        { id: 'reports', label: 'Reports', path: '/admin/reports' }
      ]
    }
  ],
  widgets: [
    {
      id: 'system_overview',
      type: 'SystemOverviewWidget',
      title: 'System Overview',
      size: 'large',
      priority: 1,
      refreshable: true
    },
    {
      id: 'user_statistics',
      type: 'UserStatisticsWidget',
      title: 'User Statistics',
      size: 'medium',
      priority: 2,
      refreshable: true
    },
    {
      id: 'recent_activity',
      type: 'SystemActivityWidget',
      title: 'Recent System Activity',
      size: 'large',
      priority: 3,
      refreshable: true
    },
    {
      id: 'performance_metrics',
      type: 'PerformanceMetricsWidget',
      title: 'Performance Metrics',
      size: 'medium',
      priority: 4,
      refreshable: true
    },
    {
      id: 'alerts',
      type: 'SystemAlertsWidget',
      title: 'System Alerts',
      size: 'small',
      priority: 5,
      refreshable: true
    }
  ],
  quickActions: [
    {
      id: 'create_user',
      label: 'Create User',
      icon: 'person_add',
      action: 'modal',
      target: 'create_user_modal',
      color: 'primary'
    },
    {
      id: 'system_config',
      label: 'System Config',
      icon: 'settings',
      action: 'navigate',
      target: '/admin/config',
      color: 'secondary'
    },
    {
      id: 'generate_report',
      label: 'Generate Report',
      icon: 'assessment',
      action: 'modal',
      target: 'report_generator_modal',
      color: 'info'
    },
    {
      id: 'system_monitor',
      label: 'System Monitor',
      icon: 'monitor',
      action: 'navigate',
      target: '/admin/monitoring',
      color: 'warning'
    }
  ],
  statusOverview: {
    ...baseConfig.statusOverview,
    showSystemHealth: true,
    showUserCount: true,
    showSystemAlerts: true,
    showPerformanceMetrics: true
  }
};

/**
 * Get dashboard configuration based on user role
 * @param {string} role - User role (student, instructor, admin)
 * @returns {Object} Dashboard configuration object
 */
export const getDashboardConfig = (role) => {
  switch (role?.toLowerCase()) {
    case 'student':
      return studentConfig;
    case 'instructor':
      return instructorConfig;
    case 'admin':
      return adminConfig;
    default:
      console.warn(`Unknown role: ${role}, falling back to student config`);
      return studentConfig;
  }
};

/**
 * Get navigation configuration for a specific role
 * @param {string} role - User role
 * @returns {Array} Navigation configuration array
 */
export const getNavigationConfig = (role) => {
  const config = getDashboardConfig(role);
  return config?.navigation || [];
};

/**
 * Get widget configuration for a specific role
 * @param {string} role - User role
 * @returns {Array} Widget configuration array
 */
export const getWidgetConfig = (role) => {
  const config = getDashboardConfig(role);
  return config?.widgets || [];
};

/**
 * Get quick actions for a specific role
 * @param {string} role - User role
 * @returns {Array} Quick actions array
 */
export const getQuickActions = (role) => {
  const config = getDashboardConfig(role);
  return config?.quickActions || [];
};

export default {
  getDashboardConfig,
  getNavigationConfig,
  getWidgetConfig,
  getQuickActions
};