import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import SessionCard from '../../components/student/SessionCard';
import './StudentDashboard.css';

const StudentDashboard = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [gamificationData, setGamificationData] = useState(null);
  const [projectSummary, setProjectSummary] = useState(null);
  const [error, setError] = useState('');

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError('');
    
    try {
      console.log('Loading student dashboard data...');
      
      const [sessionsResponse, bookingsResponse, gamificationResponse, projectSummaryResponse] = await Promise.all([
        apiService.getSessions().catch(err => {
          console.warn('Sessions API failed:', err);
          if (err.message.includes('Session expired')) {
            throw err; // Re-throw auth errors to handle properly
          }
          return {};
        }),
        apiService.getMyBookings().catch(err => {
          console.warn('Bookings API failed:', err);
          if (err.message.includes('Session expired')) {
            throw err; // Re-throw auth errors to handle properly  
          }
          return {};
        }),
        apiService.getMyGamificationData().catch(err => {
          console.warn('Gamification API failed:', err);
          if (err.message.includes('Session expired')) {
            throw err; // Re-throw auth errors to handle properly  
          }
          return null;
        }),
        apiService.getMyProjectSummary().catch(err => {
          console.warn('Project Summary API failed:', err);
          if (err.message.includes('Session expired')) {
            throw err; // Re-throw auth errors to handle properly  
          }
          return null;
        })
      ]);
      
      // Debug logs removed for production
      
      const sessionsData = Array.isArray(sessionsResponse) ? sessionsResponse : 
                          (sessionsResponse?.sessions || sessionsResponse?.data || []);
      
      // Extract data arrays from API response objects (already defined above for debug)
      const bookingsData = Array.isArray(bookingsResponse) ? bookingsResponse :
                          (bookingsResponse?.bookings || bookingsResponse?.data || []);
      
      // Ensure we have arrays
      const finalSessionsData = Array.isArray(sessionsData) ? sessionsData : [];
      const finalBookingsData = Array.isArray(bookingsData) ? bookingsData : [];
      
      setSessions(finalSessionsData);
      setBookings(finalBookingsData);
      setGamificationData(gamificationResponse);
      setProjectSummary(projectSummaryResponse);
      
      // Dashboard data loaded successfully
      
    } catch (err) {
      console.error('Dashboard load failed:', err);
      setError('Failed to load dashboard data: ' + (err.message || 'Unknown error'));
      setSessions([]);
      setBookings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps






  // Enhanced data processing for active and upcoming sessions
  const now = new Date();
  
  // Active sessions (currently happening) - only from user's bookings
  const activeSessions = Array.isArray(bookings) ? bookings
    .filter(booking => {
      if (!booking.session) return false;
      
      // Parse UTC timestamps explicitly and compare with UTC now
      const sessionStart = new Date(booking.session.date_start + (booking.session.date_start.includes('Z') ? '' : 'Z'));
      const sessionEnd = new Date(booking.session.date_end + (booking.session.date_end.includes('Z') ? '' : 'Z'));
      const nowUTC = new Date(now.getTime() + (now.getTimezoneOffset() * 60000));
      
      const isActive = booking.status === 'confirmed' && sessionStart <= nowUTC && sessionEnd >= nowUTC;
      
      // Removed debug logging for production
      
      return isActive;
    })
    .map(booking => ({
      ...booking.session,
      bookingId: booking.id,
      // Ensure all required fields exist with proper defaults
      title: booking.session.title || `Session ${booking.session.id}`,
      instructor_name: booking.session.instructor_name || (typeof booking.session.instructor === 'object' ? booking.session.instructor?.name : booking.session.instructor) || "TBD",
      location: booking.session.location || "TBD", 
      sport_type: booking.session.sport_type || "General",
      level: booking.session.level || "All Levels",
      description: booking.session.description || "Training session",
      capacity: booking.session.capacity || 20,
      current_bookings: booking.session.current_bookings || 0,
      is_full: booking.session.is_full || false
    }))
    .slice(0, 3) : [];

  const upcomingSessions = Array.isArray(sessions) ? sessions
    .filter(session => {
      const sessionStart = new Date(session.date_start);
      const now = new Date();
      const isFuture = sessionStart > now;
      
      // Debug logging for session 223
      if (session.id === 223) {
        console.log('🎯 Debug Session 223 filtering:', {
          id: session.id,
          title: session.title,
          date_start: session.date_start,
          sessionStart: sessionStart.toISOString(),
          now: now.toISOString(),
          isFuture: isFuture
        });
      }
      
      return isFuture;
    })
    .map(session => ({
      ...session,
      // Ensure all required fields exist with proper defaults
      title: session.title || `Session ${session.id}`,
      instructor_name: session.instructor_name || (typeof session.instructor === 'object' ? session.instructor?.name : session.instructor) || "TBD",
      location: session.location || "TBD", 
      sport_type: session.sport_type || "General",
      level: session.level || "All Levels",
      description: session.description || "Training session",
      duration: session.duration || 90,
      capacity: session.capacity || 20,
      current_bookings: session.current_bookings || 0,
      is_full: session.is_full || false
    }))
    .slice(0, 3) : [];
    
  const availableSessions = Array.isArray(sessions) ? sessions.filter(session => {
    const sessionStart = new Date(session.date_start);
    const now = new Date();
    return !session.is_full && sessionStart > now;
  }) : [];
  const attendanceRate = Array.isArray(bookings) && bookings.length > 0 ? 
    Math.round((bookings.filter(b => b.attended).length / bookings.length) * 100) : 0;

  if (loading) {
    return <div className="dashboard-loading">Loading your dashboard...</div>;
  }

  return (
    <div className="student-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1>🎓 Student Dashboard</h1>
          <p>Welcome, {user?.nickname || user?.name || user?.email?.split('@')[0]}! 
            <span className="role-badge">Student</span>
            {gamificationData && gamificationData.status.is_returning && (
              <span className="veteran-badge" title={`${gamificationData.stats.semesters_participated} semesters, Level ${gamificationData.stats.level}`}>
                {gamificationData.status.icon} {gamificationData.status.title}
              </span>
            )}
          </p>
          {gamificationData && (
            <div className="xp-progress-bar">
              <div className="xp-info">
                <span>Level {gamificationData.stats.level} • {gamificationData.next_level.current_xp} XP</span>
                <span>{gamificationData.next_level.next_level_xp - gamificationData.next_level.current_xp} XP to Level {gamificationData.stats.level + 1}</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${gamificationData.next_level.progress_percentage}%` }}
                ></div>
              </div>
            </div>
          )}
        </div>
        <div className="header-actions">
          <button onClick={loadDashboardData} disabled={loading} className="refresh-btn">
            🔄 Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>My Bookings</h3>
          <div className="stat-number">{Array.isArray(bookings) ? bookings.length : 0}</div>
          <Link to="/student/bookings" className="stat-link">View all →</Link>
        </div>
        <div className="stat-card">
          <h3>Available Sessions</h3>
          <div className="stat-number">{availableSessions.length}</div>
          <Link to="/student/sessions" className="stat-link">Browse →</Link>
        </div>
        <div className="stat-card">
          <h3>Attendance Rate</h3>
          <div className="stat-number">{attendanceRate}%</div>
          <Link to="/student/feedback" className="stat-link">Feedback →</Link>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <h2>Quick Actions</h2>
        <div className="action-grid">
          <Link to="/student/sessions" className="action-card">
            <div className="action-icon">📅</div>
            <h3>Browse Sessions</h3>
            <p>Find and book available practice sessions</p>
          </Link>
          <Link to="/student/bookings" className="action-card">
            <div className="action-icon">📋</div>
            <h3>My Bookings</h3>
            <p>Manage your current and past bookings</p>
          </Link>
          <Link to="/student/profile" className="action-card">
            <div className="action-icon">👤</div>
            <h3>Profile</h3>
            <p>Update your personal information</p>
          </Link>
          <Link to="/student/feedback" className="action-card">
            <div className="action-icon">⭐</div>
            <h3>Feedback</h3>
            <p>Rate your completed sessions</p>
          </Link>
          <Link to="/student/quiz" className="action-card">
            <div className="action-icon">📝</div>
            <h3>Knowledge Tests</h3>
            <p>Take quizzes and earn XP by testing your knowledge</p>
          </Link>
          <Link to="/student/projects" className="action-card">
            <div className="action-icon">📁</div>
            <h3>Projects</h3>
            <p>Browse and enroll in semester projects</p>
          </Link>
          <Link to="/student/messages" className="action-card">
            <div className="action-icon">💬</div>
            <h3>Messages</h3>
            <p>Communicate with instructors and get updates</p>
          </Link>
        </div>
      </div>

      {/* Achievements Section - Show for returning students */}
      {gamificationData && gamificationData.status.is_returning && gamificationData.achievements.length > 0 && (
        <div className="achievements-section">
          <h2>
            🏆 Your Achievements
            <span className="achievement-count">{gamificationData.achievements.length} earned</span>
          </h2>
          <div className="achievements-grid">
            {gamificationData.achievements.slice(0, 6).map(achievement => (
              <div key={achievement.id} className="achievement-card" title={achievement.description}>
                <div className="achievement-icon">{achievement.icon}</div>
                <div className="achievement-info">
                  <h4>{achievement.title}</h4>
                  <p>{achievement.description}</p>
                  <span className="achievement-date">
                    Earned {new Date(achievement.earned_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="view-all-achievements">
            <Link to="/student/gamification" className="btn-secondary">
              View Full Profile & All Achievements →
            </Link>
          </div>
        </div>
      )}

      {/* Gamification Section - Show for new students */}
      {gamificationData && !gamificationData.status.is_returning && (
        <div className="achievements-section">
          <h2>
            🎓 Your Learning Journey
            <span className="achievement-count">Level {gamificationData.stats.level}</span>
          </h2>
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="welcome-message">
              <div className="welcome-icon">🌟</div>
              <h3>Welcome to Your Learning Adventure!</h3>
              <p>Start attending sessions, giving feedback, and watch your achievements unlock as you progress through your semesters.</p>
            </div>
            <div style={{ marginTop: '1.5rem' }}>
              <Link to="/student/gamification" className="btn-secondary">
                🚀 Explore Your Profile & Future Achievements
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Current Project Section */}
      {projectSummary?.current_project && (
        <div className="current-project-section">
          <h2>
            🎯 Current Project
            <span className="section-badge">
              {Math.round(projectSummary.current_project.completion_percentage)}% complete
            </span>
          </h2>
          
          <div className="current-project-card">
            <div className="project-header-info">
              <h3>{projectSummary.current_project.project_title}</h3>
              <p className="project-description">
                {projectSummary.current_project.project_description}
              </p>
            </div>
            
            <div className="project-stats">
              <div className="project-stat">
                <span className="stat-value">{projectSummary.current_project.sessions_completed}</span>
                <span className="stat-label">/ {projectSummary.current_project.required_sessions} sessions</span>
              </div>
              <div className="project-stat">
                <span className="stat-value">{projectSummary.current_project.xp_reward}</span>
                <span className="stat-label">XP reward</span>
              </div>
              <div className="project-stat">
                <span className="stat-value">
                  {projectSummary.current_project.project_deadline ? 
                    new Date(projectSummary.current_project.project_deadline).toLocaleDateString('hu-HU') : 
                    'No deadline'
                  }
                </span>
                <span className="stat-label">Deadline</span>
              </div>
            </div>
            
            <div className="project-progress">
              <div className="progress-bar-container">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${projectSummary.current_project.completion_percentage}%` }}
                  ></div>
                </div>
                <span className="progress-text">
                  {Math.round(projectSummary.current_project.completion_percentage)}%
                </span>
              </div>
            </div>
            
            <div className="project-actions">
              <Link 
                to={`/student/projects/${projectSummary.current_project.project_id}/progress`}
                className="btn-primary"
              >
                📊 View Progress
              </Link>
              <Link 
                to="/student/projects/my"
                className="btn-secondary"
              >
                🎯 My Projects
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Active Sessions - Only show if there are active sessions */}
      {activeSessions.length > 0 && (
        <div className="active-sessions-section">
          <h2>
            🔴 LIVE - Active Session
            <span className="live-badge">HAPPENING NOW</span>
          </h2>
          
          <div className="active-sessions-container">
            {activeSessions.map(session => (
              <div key={session.id} className="active-session-card">
                <div className="active-session-header">
                  <div className="session-info">
                    <h3>{session.title}</h3>
                    <p className="session-time">
                      🕐 {new Date(session.date_start).toLocaleTimeString()} - {new Date(session.date_end).toLocaleTimeString()}
                    </p>
                    <p className="session-location">📍 {session.location}</p>
                  </div>
                  <div className="live-indicator">
                    <div className="live-dot"></div>
                    <span>LIVE</span>
                  </div>
                </div>
                
                <div className="active-session-actions">
                  <button 
                    className="checkin-btn"
                    onClick={async () => {
                      try {
                        await apiService.checkIn(session.bookingId);
                        alert('Successfully checked in!');
                        loadDashboardData(); // Refresh
                      } catch (err) {
                        alert(`Check-in failed: ${err.message}`);
                      }
                    }}
                  >
                    ✅ Check In
                  </button>
                  <Link 
                    to={`/student/sessions/${session.id}`}
                    className="details-btn"
                  >
                    📋 Details
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming Sessions */}
      <div className="upcoming-section">
        <h2>
          📅 Upcoming Sessions
          <span className="section-badge">{upcomingSessions.length} sessions</span>
        </h2>
        
        {loading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading your upcoming sessions...</p>
          </div>
        ) : error ? (
          <div className="error-state">
            <p>⚠️ {error}</p>
            <button onClick={loadDashboardData} className="retry-btn">
              Try Again
            </button>
          </div>
        ) : upcomingSessions.length === 0 ? (
          <div className="empty-state">
            <p>No upcoming sessions booked</p>
            <Link to="/student/sessions" className="cta-button">Browse Available Sessions</Link>
          </div>
        ) : (
          <div className="sessions-grid-new">
            {upcomingSessions.map(session => (
              <SessionCard 
                key={session.id}
                session={session}
                onViewDetails={(session) => {
                  // Navigate to session details
                  window.location.href = `/student/sessions/${session.id}`;
                }}
                onBook={(session) => {
                  // Handle booking logic
                  console.log('Booking session:', session.id);
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default StudentDashboard;