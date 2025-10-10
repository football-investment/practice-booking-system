import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import InstructorSessionCard from '../../components/instructor/InstructorSessionCard';
import './InstructorDashboard.css';

const InstructorDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [projects, setProjects] = useState([]);
  const [upcomingSessions, setUpcomingSessions] = useState([]);
  const [todaySessions, setTodaySessions] = useState([]);
  const [stats, setStats] = useState({
    totalSessions: 0,
    totalProjects: 0,
    totalStudents: 0,
    avgRating: 0
  });
  const [error, setError] = useState('');

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError('');
    
    try {
      console.log('Loading instructor dashboard data...');
      
      // Load instructor sessions
      const sessionsResponse = await apiService.getInstructorSessions().catch(err => {
        console.warn('Sessions API failed:', err);
        return { sessions: [] };
      });
      
      // Load instructor projects
      const projectsResponse = await apiService.getInstructorProjects().catch(err => {
        console.warn('Projects API failed:', err);
        return { projects: [] };
      });
      
      const sessionsData = Array.isArray(sessionsResponse) ? sessionsResponse : 
                          (sessionsResponse?.sessions || []);
      const projectsData = Array.isArray(projectsResponse) ? projectsResponse :
                          (projectsResponse?.projects || []);
      
      setSessions(sessionsData);
      setProjects(projectsData);
      
      // Process sessions for today and upcoming
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      
      const todaySessionsFiltered = sessionsData.filter(session => {
        const sessionDate = new Date(session.date_start);
        const sessionDateOnly = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());
        return sessionDateOnly.getTime() === today.getTime();
      });
      
      const upcomingSessionsFiltered = sessionsData
        .filter(session => new Date(session.date_start) > now)
        .sort((a, b) => new Date(a.date_start) - new Date(b.date_start))
        .slice(0, 5);
      
      setTodaySessions(todaySessionsFiltered);
      setUpcomingSessions(upcomingSessionsFiltered);
      
      // Calculate stats
      const totalStudents = sessionsData.reduce((sum, session) => sum + (session.current_bookings || 0), 0);
      const ratedSessions = sessionsData.filter(s => s.instructor_rating && s.instructor_rating > 0);
      const avgRating = ratedSessions.length > 0 ? 
        ratedSessions.reduce((sum, s) => sum + s.instructor_rating, 0) / ratedSessions.length : 0;
      
      setStats({
        totalSessions: sessionsData.length,
        totalProjects: projectsData.length,
        totalStudents: totalStudents,
        avgRating: avgRating
      });
      
      console.log('Instructor dashboard loaded:', { 
        sessions: sessionsData.length, 
        projects: projectsData.length,
        todaySessions: todaySessionsFiltered.length,
        upcomingSessions: upcomingSessionsFiltered.length
      });
      
    } catch (err) {
      console.error('Dashboard load failed:', err);
      setError('Failed to load dashboard data: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);




  if (loading) {
    return <div className="dashboard-loading">Loading your instructor dashboard...</div>;
  }

  return (
    <div className="instructor-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1>👨‍🏫 Instructor Dashboard</h1>
          <p>Welcome, {user?.nickname || user?.name || user?.email?.split('@')[0]}! 
            <span className="role-badge instructor">Instructor</span>
          </p>
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
          <h3>My Sessions</h3>
          <div className="stat-number">{stats.totalSessions}</div>
          <Link to="/instructor/sessions" className="stat-link">Manage →</Link>
        </div>
        <div className="stat-card">
          <h3>My Projects</h3>
          <div className="stat-number">{stats.totalProjects}</div>
          <Link to="/instructor/projects" className="stat-link">Manage →</Link>
        </div>
        <div className="stat-card">
          <h3>Total Students</h3>
          <div className="stat-number">{stats.totalStudents}</div>
          <Link to="/instructor/students" className="stat-link">View →</Link>
        </div>
        <div className="stat-card">
          <h3>Avg Rating</h3>
          <div className="stat-number">{stats.avgRating > 0 ? stats.avgRating.toFixed(1) : '-'}</div>
          <Link to="/instructor/feedback" className="stat-link">Reviews →</Link>
        </div>
      </div>

      {/* Today's Sessions */}
      {todaySessions.length > 0 && (
        <div className="today-sessions-section">
          <h2>
            📅 Today's Sessions
            <span className="section-badge">{todaySessions.length} sessions</span>
          </h2>
          <div className="sessions-grid-new">
            {todaySessions.map(session => (
              <InstructorSessionCard
                key={session.id}
                session={session}
                onViewDetails={(session) => {
                  navigate(`/instructor/sessions/${session.id}`);
                }}
                onEdit={(session) => {
                  navigate(`/instructor/sessions/${session.id}/edit`);
                }}
                onDelete={(sessionId) => {
                  // Handle delete logic
                  console.log('Delete session:', sessionId);
                }}
                onAttendance={(session) => {
                  navigate(`/instructor/attendance/${session.id}`);
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="quick-actions">
        <h2>Quick Actions</h2>
        <div className="action-grid">
          <Link to="/instructor/sessions" className="action-card">
            <div className="action-icon">📅</div>
            <h3>Manage Sessions</h3>
            <p>View and manage your scheduled sessions</p>
          </Link>
          <Link to="/instructor/projects" className="action-card">
            <div className="action-icon">📁</div>
            <h3>Manage Projects</h3>
            <p>Oversee student project progress</p>
          </Link>
          <Link to="/instructor/students" className="action-card">
            <div className="action-icon">👥</div>
            <h3>Student Overview</h3>
            <p>View enrolled students and their progress</p>
          </Link>
          <Link to="/instructor/messages" className="action-card">
            <div className="action-icon">💬</div>
            <h3>Messages</h3>
            <p>View and send messages to students</p>
          </Link>
          <Link to="/instructor/feedback" className="action-card">
            <div className="action-icon">⭐</div>
            <h3>Student Feedback</h3>
            <p>Review feedback from your sessions</p>
          </Link>
          <Link to="/instructor/attendance" className="action-card">
            <div className="action-icon">📊</div>
            <h3>Attendance Tracking</h3>
            <p>Track student attendance patterns</p>
          </Link>
          <Link to="/instructor/profile" className="action-card">
            <div className="action-icon">👤</div>
            <h3>Profile</h3>
            <p>Update your instructor profile</p>
          </Link>
        </div>
      </div>

      {/* Upcoming Sessions */}
      {upcomingSessions.length > 0 && (
        <div className="upcoming-section">
          <h2>
            🔜 Upcoming Sessions
            <span className="section-badge">Next {upcomingSessions.length}</span>
          </h2>
          
          <div className="sessions-grid-new">
            {upcomingSessions.map(session => (
              <InstructorSessionCard
                key={session.id}
                session={session}
                onViewDetails={(session) => {
                  navigate(`/instructor/sessions/${session.id}`);
                }}
                onEdit={(session) => {
                  navigate(`/instructor/sessions/${session.id}/edit`);
                }}
                onDelete={(sessionId) => {
                  // Handle delete logic
                  console.log('Delete session:', sessionId);
                }}
                onAttendance={(session) => {
                  navigate(`/instructor/attendance/${session.id}`);
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default InstructorDashboard;