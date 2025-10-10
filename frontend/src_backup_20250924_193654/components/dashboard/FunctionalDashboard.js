import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './FunctionalDashboard.css';

/**
 * FUNCTIONAL-FIRST STUDENT DASHBOARD
 * Prioritizes working features over visual polish
 * Based on 89 documented student API endpoints
 */
const FunctionalDashboard = () => {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState({
    // Basic dashboard data
    nextSession: null,
    progress: 0,
    activeProjects: [],
    recentBookings: [],
    notifications: 0,
    achievements: [],
    
    // LFA Education Center specific data
    specialization: null,
    adaptiveRecommendations: [],
    recentFeedback: [],
    performanceAnalytics: null,
    pendingQuizzes: [],
    gamificationData: null
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load dashboard data function (extracted for reuse)
  const loadDashboardData = async () => {
    try {
      // Parallel API calls for better performance - LFA Education Center
      const [
        sessionsResponse,
        bookingsResponse,
        projectsResponse,
        gamificationResponse,
        notificationsResponse,
        specializationResponse,
        adaptiveResponse,
        feedbackResponse,
        analyticsResponse,
        quizzesResponse
      ] = await Promise.allSettled([
        // Basic APIs
        apiService.getSessions({ limit: 5, upcoming: true }),
        apiService.getMyBookings({ limit: 3 }),
        apiService.getMyProjects(),
        apiService.getGamificationProfile(),
        apiService.getNotifications({ limit: 1 }),
        
        // LFA Education Center APIs
        apiService.getCurrentSpecialization(),
        apiService.getAdaptiveLearningRecommendations(),
        apiService.getRecentFeedback({ limit: 2 }),
        apiService.getPerformanceAnalytics(),
        apiService.getPendingQuizzes({ limit: 2 })
      ]);

      // Process responses safely
      const nextSession = sessionsResponse.status === 'fulfilled' && 
        sessionsResponse.value?.sessions?.[0] || null;

      const recentBookings = bookingsResponse.status === 'fulfilled' ? 
        bookingsResponse.value?.bookings || [] : [];

      const activeProjects = projectsResponse.status === 'fulfilled' ?
        projectsResponse.value?.projects || [] : [];

      const gamification = gamificationResponse.status === 'fulfilled' ?
        gamificationResponse.value || {} : {};

      const notifications = notificationsResponse.status === 'fulfilled' ?
        notificationsResponse.value?.unread_count || 0 : 0;

      // LFA Education Center specific data processing
      const specialization = specializationResponse.status === 'fulfilled' ?
        specializationResponse.value || null : null;

      const adaptiveRecommendations = adaptiveResponse.status === 'fulfilled' ?
        adaptiveResponse.value?.recommendations || [] : [];

      const recentFeedback = feedbackResponse.status === 'fulfilled' ?
        feedbackResponse.value?.feedback || [] : [];

      const performanceAnalytics = analyticsResponse.status === 'fulfilled' ?
        analyticsResponse.value || null : null;

      const pendingQuizzes = quizzesResponse.status === 'fulfilled' ?
        quizzesResponse.value?.quizzes || [] : [];

      return {
        nextSession,
        progress: gamification.experience_points || 0,
        activeProjects,
        recentBookings,
        notifications,
        achievements: gamification.recent_achievements || [],
        
        // LFA Education Center data
        specialization,
        adaptiveRecommendations,
        recentFeedback,
        performanceAnalytics,
        pendingQuizzes,
        gamificationData: gamification
      };

    } catch (err) {
      console.error('Dashboard data loading failed:', err);
      throw err;
    }
  };

  // Load all dashboard data
  useEffect(() => {
    const initializeDashboard = async () => {
      setLoading(true);
      setError(null);

      try {
        const dashboardData = await loadDashboardData();
        setDashboardData(dashboardData);
      } catch (err) {
        setError('Unable to load dashboard data. Please refresh the page.');
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      initializeDashboard();
    }
  }, [user]);

  // Handle session booking
  const handleBookSession = async (sessionId) => {
    try {
      setLoading(true);
      await apiService.bookSession({ session_id: sessionId });
      
      // Show success message
      const sessionTitle = dashboardData.nextSession?.title || 'Session';
      alert(`✅ Successfully booked: ${sessionTitle}`);
      
      // Refresh dashboard data to reflect changes
      const updatedData = await loadDashboardData();
      if (updatedData) {
        setDashboardData(updatedData);
      }
      
    } catch (error) {
      console.error('Session booking failed:', error);
      alert(`❌ Booking failed: ${error.message || 'Please try again later'}`);
    } finally {
      setLoading(false);
    }
  };

  // Navigation helpers
  const navigateTo = (path) => {
    window.location.href = path;
  };

  // LFA Education Center specific handlers
  const handleStartAdaptiveLesson = async (recommendationId) => {
    try {
      await apiService.startAdaptiveLesson(recommendationId);
      navigateTo(`/student/adaptive-learning/${recommendationId}`);
    } catch (error) {
      alert(`❌ Failed to start lesson: ${error.message}`);
    }
  };

  const handleTakeQuiz = (quizId) => {
    navigateTo(`/student/quiz/${quizId}/take`);
  };

  if (loading) {
    return (
      <div className="functional-dashboard">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="functional-dashboard">
        <div className="error-state">
          <h3>⚠️ Dashboard Error</h3>
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>
            🔄 Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="functional-dashboard">
      {/* Quick Status Strip */}
      <div className="status-strip">
        <div className="status-item">
          <span className="label">Next Session:</span>
          <span className="value">
            {dashboardData.nextSession ? 
              new Date(dashboardData.nextSession.date_start).toLocaleDateString() :
              'None scheduled'
            }
          </span>
        </div>
        <div className="status-item">
          <span className="label">Progress:</span>
          <span className="value">{dashboardData.progress} XP</span>
        </div>
        <div className="status-item">
          <span className="label">Notifications:</span>
          <span className="value">{dashboardData.notifications}</span>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        
        {/* SESSION MANAGEMENT CARD - Priority #1 */}
        <div className="dashboard-card session-card">
          <div className="card-header">
            <h3>📅 Next Session</h3>
          </div>
          <div className="card-content">
            {dashboardData.nextSession ? (
              <div className="session-info">
                <h4>{dashboardData.nextSession.title}</h4>
                <p className="session-time">
                  {new Date(dashboardData.nextSession.date_start).toLocaleString()}
                </p>
                <p className="session-location">
                  📍 {dashboardData.nextSession.location || 'Location TBA'}
                </p>
                <div className="session-actions">
                  <button 
                    className="btn-primary"
                    onClick={() => handleBookSession(dashboardData.nextSession.id)}
                  >
                    📋 Book This Session
                  </button>
                  <button 
                    className="btn-secondary"
                    onClick={() => navigateTo('/student/sessions')}
                  >
                    📋 View All Sessions
                  </button>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <p>No upcoming sessions available</p>
                <button 
                  className="btn-secondary"
                  onClick={() => navigateTo('/student/sessions')}
                >
                  📅 Browse Sessions
                </button>
              </div>
            )}
          </div>
        </div>

        {/* PROGRESS OVERVIEW CARD - Priority #2 */}
        <div className="dashboard-card progress-card">
          <div className="card-header">
            <h3>📈 Your Progress</h3>
          </div>
          <div className="card-content">
            <div className="progress-stats">
              <div className="stat">
                <span className="stat-value">{dashboardData.progress}</span>
                <span className="stat-label">Experience Points</span>
              </div>
              <div className="stat">
                <span className="stat-value">{dashboardData.activeProjects.length}</span>
                <span className="stat-label">Active Projects</span>
              </div>
              <div className="stat">
                <span className="stat-value">{dashboardData.recentBookings.length}</span>
                <span className="stat-label">Recent Bookings</span>
              </div>
            </div>
            
            {dashboardData.achievements.length > 0 && (
              <div className="recent-achievements">
                <h4>🏆 Recent Achievements</h4>
                <ul>
                  {dashboardData.achievements.slice(0, 3).map((achievement, index) => (
                    <li key={index}>{achievement.name}</li>
                  ))}
                </ul>
              </div>
            )}

            <button 
              className="btn-secondary"
              onClick={() => navigateTo('/student/profile')}
            >
              📊 View Full Progress
            </button>
          </div>
        </div>

        {/* ACTIVE LEARNING CARD - Priority #3 */}
        <div className="dashboard-card learning-card">
          <div className="card-header">
            <h3>🎓 Active Learning</h3>
          </div>
          <div className="card-content">
            {dashboardData.activeProjects.length > 0 ? (
              <div className="projects-list">
                <h4>Current Projects:</h4>
                <ul>
                  {dashboardData.activeProjects.slice(0, 3).map(project => (
                    <li key={project.id}>
                      <strong>{project.title}</strong>
                      <span className="project-progress">
                        {project.progress || 0}% complete
                      </span>
                    </li>
                  ))}
                </ul>
                <button 
                  className="btn-secondary"
                  onClick={() => navigateTo('/student/projects')}
                >
                  📋 View All Projects
                </button>
              </div>
            ) : (
              <div className="empty-state">
                <p>No active projects</p>
                <button 
                  className="btn-secondary"
                  onClick={() => navigateTo('/student/projects')}
                >
                  🔍 Browse Projects
                </button>
              </div>
            )}

            <div className="quiz-section">
              <h4>📝 Quizzes Available</h4>
              <button 
                className="btn-primary"
                onClick={() => navigateTo('/student/quiz')}
              >
                🧠 Take Quiz
              </button>
            </div>
          </div>
        </div>

        {/* QUICK ACTIONS PANEL - Priority #4 */}
        <div className="dashboard-card actions-card">
          <div className="card-header">
            <h3>⚡ Quick Actions</h3>
          </div>
          <div className="card-content">
            <div className="actions-grid">
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/sessions')}
              >
                <span className="action-icon">📅</span>
                <span className="action-label">Book Training</span>
                <small>Schedule session</small>
              </button>
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/quiz')}
              >
                <span className="action-icon">🧠</span>
                <span className="action-label">Knowledge Test</span>
                <small>Take assessment</small>
              </button>
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/progress')}
              >
                <span className="action-icon">📊</span>
                <span className="action-label">View Analytics</span>
                <small>Detailed progress</small>
              </button>
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/projects')}
              >
                <span className="action-icon">📋</span>
                <span className="action-label">My Projects</span>
                <small>Active assignments</small>
              </button>
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/feedback')}
              >
                <span className="action-icon">💬</span>
                <span className="action-label">Feedback Hub</span>
                <small>Coach reviews</small>
              </button>
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/mentoring')}
              >
                <span className="action-icon">👥</span>
                <span className="action-label">Find Mentor</span>
                <small>Get guidance</small>
              </button>
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/portfolio')}
              >
                <span className="action-icon">🎯</span>
                <span className="action-label">Portfolio</span>
                <small>Track achievements</small>
              </button>
              <button 
                className="action-btn"
                onClick={() => navigateTo('/student/gamification')}
              >
                <span className="action-icon">🏆</span>
                <span className="action-label">Achievements</span>
                <small>Badges & rewards</small>
              </button>
            </div>
          </div>
        </div>

        {/* SPECIALIZATION STATUS CARD - LFA Education Center */}
        <div className="dashboard-card specialization-card">
          <div className="card-header">
            <h3>🎓 My Specialization</h3>
          </div>
          <div className="card-content">
            {dashboardData.specialization ? (
              <>
                <div className="specialization-info">
                  <div className="specialization-current">
                    <strong>Current: {dashboardData.specialization.track_name || 'Player Track'}</strong>
                    <span className="semester-badge">Semester {dashboardData.specialization.semester || 1}</span>
                  </div>
                  <p className="specialization-milestone">
                    Next milestone: {dashboardData.specialization.next_milestone || 'Complete 5 more modules for Advanced Training'}
                  </p>
                </div>
                <div className="specialization-badges">
                  <span className="status-badge status-active">
                    {dashboardData.specialization.status || 'Active'}
                  </span>
                  <span className="status-badge status-semester">
                    Semester {dashboardData.specialization.semester || 1}
                  </span>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>No specialization assigned</p>
                <button 
                  className="btn-secondary"
                  onClick={() => navigateTo('/student/specializations')}
                >
                  Choose Specialization
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ADAPTIVE LEARNING CARD - LFA Education Center */}
        <div className="dashboard-card adaptive-card">
          <div className="card-header">
            <h3>🤖 Adaptive Learning</h3>
          </div>
          <div className="card-content">
            {dashboardData.adaptiveRecommendations.length > 0 ? (
              <>
                <div className="adaptive-info">
                  <strong>Recommended for You</strong>
                  <p>Based on your recent performance analysis</p>
                </div>
                <div className="adaptive-recommendations">
                  {dashboardData.adaptiveRecommendations.slice(0, 2).map((rec, index) => (
                    <div key={index} className="adaptive-item">
                      <div className="adaptive-details">
                        <strong>AI Suggested: {rec.title}</strong>
                        <small>Difficulty: {rec.difficulty} • Est. {rec.estimated_time}</small>
                        <small className="adaptive-reason">{rec.reason}</small>
                      </div>
                      <button 
                        className="btn-primary adaptive-start-btn"
                        onClick={() => handleStartAdaptiveLesson(rec.id)}
                      >
                        Start
                      </button>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <p>No recommendations available</p>
                <button 
                  className="btn-secondary"
                  onClick={() => navigateTo('/student/adaptive-learning')}
                >
                  Explore Learning
                </button>
              </div>
            )}
          </div>
        </div>

        {/* FEEDBACK & ANALYTICS CARD - LFA Education Center */}
        <div className="dashboard-card feedback-card">
          <div className="card-header">
            <h3>💬 Recent Feedback</h3>
          </div>
          <div className="card-content">
            {dashboardData.recentFeedback.length > 0 ? (
              <div className="feedback-list">
                {dashboardData.recentFeedback.map((feedback, index) => (
                  <div key={index} className="feedback-item">
                    <div className="feedback-details">
                      <strong>{feedback.coach_name || 'Coach Martinez'}</strong>
                      <p>"{feedback.message || 'Great improvement this session!'}"</p>
                      <small>{feedback.session_type || 'Technical Skills Session'}</small>
                    </div>
                    <div className="feedback-rating">
                      ⭐ {feedback.rating || '4.8'}
                    </div>
                  </div>
                ))}
                
                {dashboardData.performanceAnalytics && (
                  <div className="feedback-item analytics-item">
                    <div className="feedback-details">
                      <strong>System Analysis</strong>
                      <p>Performance increased {dashboardData.performanceAnalytics.improvement || '15%'} this week</p>
                      <small>{dashboardData.performanceAnalytics.category || 'Ball Control Metrics'}</small>
                    </div>
                    <div className="feedback-rating improvement-badge">
                      📈 {dashboardData.performanceAnalytics.improvement || '+15%'}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-state">
                <p>No recent feedback</p>
                <button 
                  className="btn-secondary"
                  onClick={() => navigateTo('/student/feedback')}
                >
                  View All Feedback
                </button>
              </div>
            )}
          </div>
        </div>

        {/* RECENT ACTIVITY CARD */}
        <div className="dashboard-card activity-card">
          <div className="card-header">
            <h3>🕒 Recent Activity</h3>
          </div>
          <div className="card-content">
            {dashboardData.recentBookings.length > 0 ? (
              <ul className="activity-list">
                {dashboardData.recentBookings.map(booking => (
                  <li key={booking.id} className="activity-item">
                    <span className="activity-type">📅</span>
                    <span className="activity-desc">
                      Booked session on {new Date(booking.booking_date).toLocaleDateString()}
                    </span>
                    <span className="activity-status">
                      {booking.status}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No recent activity</p>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default FunctionalDashboard;