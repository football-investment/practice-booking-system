import React, { useMemo } from 'react';
import './ContentArea.css';

/**
 * Content Area Component
 * Dynamic widget renderer for dashboard content
 */
const ContentArea = ({
  activeSection = 'overview',
  data = {},
  config = {},
  userRole = 'student',
  onDataRefresh
}) => {

  // Widget renderers based on section and role
  const renderSectionContent = useMemo(() => {
    switch (activeSection) {
      case 'overview':
        return renderOverviewSection();
      case 'learning':
        return renderLearningSection();
      case 'progress':
        return renderProgressSection();
      case 'connect':
        return renderConnectSection();
      case 'teaching':
        return renderTeachingSection();
      case 'analytics':
        return renderAnalyticsSection();
      case 'tools':
        return renderToolsSection();
      case 'users':
        return renderUsersSection();
      case 'content':
        return renderContentSection();
      case 'system':
        return renderSystemSection();
      default:
        return renderDefaultSection();
    }
  }, [activeSection, data, userRole]);

  // Overview Section - Default dashboard view
  function renderOverviewSection() {
    return (
      <div className="content-section overview-section">
        <div className="section-header">
          <h2>Dashboard Overview</h2>
          <button 
            className="refresh-button"
            onClick={onDataRefresh}
            title="Refresh data"
          >
            <span className="material-icons">refresh</span>
          </button>
        </div>

        <div className="widgets-container">
          {/* Primary Widget */}
          {userRole === 'student' && (
            <div className="widget primary-widget">
              <div className="widget-header">
                <h3>My Learning Journey</h3>
                <span className="widget-icon">🎓</span>
              </div>
              <div className="widget-content">
                <div className="progress-overview">
                  <div className="progress-item">
                    <span className="progress-label">Overall Progress</span>
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${data.learningJourney?.overallProgress || 0}%` }}
                      />
                    </div>
                    <span className="progress-value">{data.learningJourney?.overallProgress || 0}%</span>
                  </div>
                  
                  <div className="learning-stats">
                    <div className="stat-item">
                      <span className="stat-value">{data.learningJourney?.activeTracks || 0}</span>
                      <span className="stat-label">Active Tracks</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-value">{data.learningJourney?.completedModules || 0}</span>
                      <span className="stat-label">Completed Modules</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {userRole === 'instructor' && (
            <div className="widget primary-widget">
              <div className="widget-header">
                <h3>Today's Teaching</h3>
                <span className="widget-icon">👨‍🏫</span>
              </div>
              <div className="widget-content">
                <div className="teaching-overview">
                  <div className="session-count">
                    <span className="count-value">{data.overview?.sessionsToday || 0}</span>
                    <span className="count-label">Sessions Today</span>
                  </div>
                  <div className="students-overview">
                    <div className="student-stat">
                      <span className="stat-value">{data.overview?.activeStudents || 0}</span>
                      <span className="stat-label">Active Students</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {userRole === 'admin' && (
            <div className="widget primary-widget">
              <div className="widget-header">
                <h3>System Status</h3>
                <span className="widget-icon">🖥️</span>
              </div>
              <div className="widget-content">
                <div className="system-overview">
                  <div className="system-health">
                    <div className="health-indicator">
                      <div className={`health-dot ${data.performance?.systemHealth >= 95 ? 'good' : 'warning'}`} />
                      <span>System Health: {data.performance?.systemHealth || 100}%</span>
                    </div>
                  </div>
                  <div className="system-stats">
                    <div className="stat-item">
                      <span className="stat-value">{data.overview?.totalUsers || 0}</span>
                      <span className="stat-label">Total Users</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-value">{data.overview?.activeSessions || 0}</span>
                      <span className="stat-label">Active Sessions</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Secondary Widgets */}
          <div className="widget secondary-widget">
            <div className="widget-header">
              <h3>Recent Activity</h3>
              <span className="material-icons widget-icon">history</span>
            </div>
            <div className="widget-content">
              <div className="activity-list">
                {data.recentActivity && data.recentActivity.length > 0 ? (
                  data.recentActivity.slice(0, 5).map((activity, index) => (
                    <div key={index} className="activity-item">
                      <div className="activity-time">
                        {new Date(activity.timestamp).toLocaleTimeString()}
                      </div>
                      <div className="activity-description">
                        {activity.description}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="no-activity">
                    <span className="material-icons">event_note</span>
                    <p>No recent activity</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="widget secondary-widget">
            <div className="widget-header">
              <h3>Upcoming</h3>
              <span className="material-icons widget-icon">event</span>
            </div>
            <div className="widget-content">
              <div className="upcoming-list">
                {data.upcomingItems && data.upcomingItems.length > 0 ? (
                  data.upcomingItems.slice(0, 3).map((item, index) => (
                    <div key={index} className="upcoming-item">
                      <div className="upcoming-time">
                        {new Date(item.date).toLocaleDateString()}
                      </div>
                      <div className="upcoming-title">
                        {item.title}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="no-upcoming">
                    <span className="material-icons">event_available</span>
                    <p>No upcoming events</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Learning Section - Student focused content
  function renderLearningSection() {
    return (
      <div className="content-section learning-section">
        <div className="section-header">
          <h2>My Learning</h2>
        </div>
        <div className="learning-content">
          <p>Learning content will be implemented here.</p>
          <p>This will include tracks, sessions, quizzes, and certificates.</p>
        </div>
      </div>
    );
  }

  // Progress Section - Analytics and progress tracking
  function renderProgressSection() {
    return (
      <div className="content-section progress-section">
        <div className="section-header">
          <h2>Progress & Analytics</h2>
        </div>
        <div className="progress-content">
          <p>Progress analytics will be implemented here.</p>
          <p>This will include detailed charts and performance metrics.</p>
        </div>
      </div>
    );
  }

  // Connect Section - Communication features
  function renderConnectSection() {
    return (
      <div className="content-section connect-section">
        <div className="section-header">
          <h2>Connect & Communicate</h2>
        </div>
        <div className="connect-content">
          <p>Communication features will be implemented here.</p>
          <p>This will include messages, feedback, and notifications.</p>
        </div>
      </div>
    );
  }

  // Teaching Section - Instructor focused content
  function renderTeachingSection() {
    return (
      <div className="content-section teaching-section">
        <div className="section-header">
          <h2>Teaching Tools</h2>
        </div>
        <div className="teaching-content">
          <p>Teaching tools will be implemented here.</p>
          <p>This will include session management, student tracking, and content creation.</p>
        </div>
      </div>
    );
  }

  // Analytics Section - Data and reporting
  function renderAnalyticsSection() {
    return (
      <div className="content-section analytics-section">
        <div className="section-header">
          <h2>Analytics & Reports</h2>
        </div>
        <div className="analytics-content">
          <p>Detailed analytics will be implemented here.</p>
          <p>This will include performance metrics, trends, and custom reports.</p>
        </div>
      </div>
    );
  }

  // Tools Section - Instructor utilities
  function renderToolsSection() {
    return (
      <div className="content-section tools-section">
        <div className="section-header">
          <h2>Instructor Tools</h2>
        </div>
        <div className="tools-content">
          <p>Instructor tools will be implemented here.</p>
          <p>This will include attendance tracking, grading, and communication tools.</p>
        </div>
      </div>
    );
  }

  // Users Section - Admin user management
  function renderUsersSection() {
    return (
      <div className="content-section users-section">
        <div className="section-header">
          <h2>User Management</h2>
        </div>
        <div className="users-content">
          <p>User management tools will be implemented here.</p>
          <p>This will include user creation, role management, and access control.</p>
        </div>
      </div>
    );
  }

  // Content Section - Admin content management
  function renderContentSection() {
    return (
      <div className="content-section content-section-admin">
        <div className="section-header">
          <h2>Content Management</h2>
        </div>
        <div className="content-management">
          <p>Content management tools will be implemented here.</p>
          <p>This will include track management, session creation, and resource organization.</p>
        </div>
      </div>
    );
  }

  // System Section - Admin system management
  function renderSystemSection() {
    return (
      <div className="content-section system-section">
        <div className="section-header">
          <h2>System Management</h2>
        </div>
        <div className="system-content">
          <p>System management tools will be implemented here.</p>
          <p>This will include configuration, monitoring, and maintenance tools.</p>
        </div>
      </div>
    );
  }

  // Default Section - Fallback content
  function renderDefaultSection() {
    return (
      <div className="content-section default-section">
        <div className="section-header">
          <h2>Content Area</h2>
        </div>
        <div className="default-content">
          <div className="placeholder-content">
            <span className="material-icons placeholder-icon">dashboard</span>
            <h3>Welcome to your Dashboard</h3>
            <p>Select a section from the sidebar to get started.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`content-area content-area--${userRole}`}>
      {renderSectionContent}
    </div>
  );
};

export default ContentArea;