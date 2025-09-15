import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalSessions: 0,
    totalBookings: 0,
    totalFeedback: 0
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboardData();
  }, []);


  const loadDashboardData = async () => {
    setLoading(true);
    setError('');
    
    try {
      console.log('Loading admin dashboard data...');
      
      const [usersResponse, sessionsResponse, bookingsResponse, feedbackResponse] = await Promise.all([
        apiService.getUsers().catch(() => ({})),
        apiService.getSessions().catch(() => ({})),
        apiService.getAllBookings().catch(() => ({})),
        apiService.getAllFeedback().catch(() => ({}))
      ]);

      console.log('Users API response:', usersResponse);
      console.log('Sessions API response:', sessionsResponse);
      console.log('Bookings API response:', bookingsResponse);
      console.log('Feedback API response:', feedbackResponse);

      // Extract data arrays from API response objects
      const usersData = usersResponse?.users || usersResponse || [];
      const sessionsData = sessionsResponse?.sessions || sessionsResponse || [];
      const bookingsData = bookingsResponse?.bookings || bookingsResponse || [];
      const feedbackData = feedbackResponse?.feedback || feedbackResponse || [];

      setStats({
        totalUsers: usersData.length,
        totalSessions: sessionsData.length,
        totalBookings: bookingsData.length,
        totalFeedback: feedbackData.length
      });

      // Create recent activity from bookings
      const recentBookings = bookingsData
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5);
      
      setRecentActivity(recentBookings);
      
      console.log('Admin dashboard loaded:', {
        users: usersData.length,
        sessions: sessionsData.length,
        bookings: bookingsData.length,
        feedback: feedbackData.length
      });
      
    } catch (err) {
      console.error('Admin dashboard load failed:', err);
      setError('Failed to load dashboard data: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return <div className="admin-loading">Loading admin dashboard...</div>;
  }

  return (
    <div className="admin-dashboard">
      {/* Header */}
      <div className="admin-header">
        <div>
          <h1>👨‍💼 Admin Dashboard</h1>
          <p>Welcome, {user?.name || user?.email?.split('@')[0]}! <span className="role-badge admin">Administrator</span></p>
        </div>
        <div className="header-actions">
          <button onClick={loadDashboardData} disabled={loading} className="refresh-btn">
            🔄 Refresh
          </button>
        </div>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* System Stats */}
      <div className="admin-stats-grid">
        <div className="admin-stat-card users">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <h3>Total Users</h3>
            <div className="stat-number">{stats.totalUsers}</div>
            <Link to="/admin/users" className="stat-action">Manage Users →</Link>
          </div>
        </div>
        
        <div className="admin-stat-card sessions">
          <div className="stat-icon">📅</div>
          <div className="stat-content">
            <h3>Total Sessions</h3>
            <div className="stat-number">{stats.totalSessions}</div>
            <Link to="/admin/sessions" className="stat-action">Manage Sessions →</Link>
          </div>
        </div>
        
        <div className="admin-stat-card bookings">
          <div className="stat-icon">📋</div>
          <div className="stat-content">
            <h3>Total Bookings</h3>
            <div className="stat-number">{stats.totalBookings}</div>
            <Link to="/admin/bookings" className="stat-action">Manage Bookings →</Link>
          </div>
        </div>
        
        <div className="admin-stat-card feedback">
          <div className="stat-icon">⭐</div>
          <div className="stat-content">
            <h3>Feedback Items</h3>
            <div className="stat-number">{stats.totalFeedback}</div>
            <Link to="/admin/feedback" className="stat-action">View Feedback →</Link>
          </div>
        </div>
      </div>

      {/* Management Grid */}
      <div className="admin-management-grid">
        <h2>System Management</h2>
        <div className="management-cards">
          <Link to="/admin/users" className="management-card users">
            <div className="card-icon">👥</div>
            <h3>User Management</h3>
            <p>Create, edit, and manage user accounts</p>
            <div className="card-stats">{stats.totalUsers} users</div>
          </Link>

          <Link to="/admin/sessions" className="management-card sessions">
            <div className="card-icon">📅</div>
            <h3>Session Management</h3>
            <p>Schedule and manage practice sessions</p>
            <div className="card-stats">{stats.totalSessions} sessions</div>
          </Link>

          <Link to="/admin/bookings" className="management-card bookings">
            <div className="card-icon">📋</div>
            <h3>Booking Management</h3>
            <p>View and manage all student bookings</p>
            <div className="card-stats">{stats.totalBookings} bookings</div>
          </Link>

          <Link to="/admin/groups" className="management-card groups">
            <div className="card-icon">👥</div>
            <h3>Group Management</h3>
            <p>Create and manage student groups</p>
            <div className="card-stats">Manage groups</div>
          </Link>

          <Link to="/admin/semesters" className="management-card semesters">
            <div className="card-icon">📚</div>
            <h3>Semester Management</h3>
            <p>Manage academic semesters</p>
            <div className="card-stats">Academic terms</div>
          </Link>

          <Link to="/admin/attendance" className="management-card attendance">
            <div className="card-icon">✅</div>
            <h3>Attendance Tracking</h3>
            <p>Track and export attendance data</p>
            <div className="card-stats">View reports</div>
          </Link>

          <Link to="/admin/feedback" className="management-card feedback">
            <div className="card-icon">⭐</div>
            <h3>Feedback Overview</h3>
            <p>View all student feedback and ratings</p>
            <div className="card-stats">{stats.totalFeedback} reviews</div>
          </Link>

          <div className="management-card system">
            <div className="card-icon">⚙️</div>
            <h3>System Settings</h3>
            <p>Configure global system settings</p>
            <div className="card-stats">Coming soon</div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="recent-activity-section">
        <h2>Recent Activity</h2>
        {recentActivity.length === 0 ? (
          <div className="empty-state">
            <p>No recent activity</p>
          </div>
        ) : (
          <div className="activity-list">
            {recentActivity.map(activity => (
              <div key={activity.id} className="activity-item">
                <div className="activity-icon">📋</div>
                <div className="activity-content">
                  <p className="activity-text">
                    <strong>{activity.user?.email || 'User'}</strong> booked 
                    <strong> {activity.session?.title || `Session ${activity.session?.id}`}</strong>
                  </p>
                  <p className="activity-time">
                    {new Date(activity.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="activity-status">
                  <span className={`status-badge ${activity.status}`}>
                    {activity.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="admin-quick-actions">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <Link to="/admin/sessions" className="quick-action create-session">
            <span className="action-icon">➕</span>
            Create New Session
          </Link>
          <Link to="/admin/users" className="quick-action create-user">
            <span className="action-icon">👤</span>
            Add New User
          </Link>
          <Link to="/admin/groups" className="quick-action create-group">
            <span className="action-icon">👥</span>
            Create Group
          </Link>
          <Link to="/admin/attendance" className="quick-action export-data">
            <span className="action-icon">📊</span>
            Export Reports
          </Link>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;