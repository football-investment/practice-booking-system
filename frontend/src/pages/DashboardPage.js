import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import './DashboardPage.css';

const DashboardPage = () => {
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [error, setError] = useState('');
  const [user, setUser] = useState(null);

  useEffect(() => {
    loadDashboardData();
    loadUserData();
  }, []);

  const loadUserData = () => {
    const userData = localStorage.getItem('user');
    if (userData) {
      const parsedUser = JSON.parse(userData);
      console.log('🔍 LOADED USER DATA:', parsedUser); // Debug log
      console.log('📋 USER ROLE:', parsedUser.role); // Debug log
      console.log('👤 USER NAME:', parsedUser.name); // Debug log
      console.log('📧 USER EMAIL:', parsedUser.email); // Debug log
      setUser(parsedUser);
    }
  };

  const loadDashboardData = async () => {
    setLoading(true);
    setError(''); // Clear previous errors
    
    try {
      console.log('Loading dashboard data...');
      
      const [sessionsResponse, bookingsResponse] = await Promise.all([
        apiService.getSessions().catch(err => {
          console.warn('Sessions API failed:', err);
          return null; // Return null to distinguish from success
        }),
        apiService.getMyBookings().catch(err => {
          console.warn('Bookings API failed:', err);
          return null; // Return null to distinguish from success
        })
      ]);
      
      console.log('Dashboard Sessions API response:', sessionsResponse);
      console.log('Dashboard Bookings API response:', bookingsResponse);
      
      // Extract data arrays from API response objects
      const sessionsData = sessionsResponse?.sessions || sessionsResponse?.data || sessionsResponse || [];
      const bookingsData = bookingsResponse?.bookings || bookingsResponse?.data || bookingsResponse || [];
      
      setSessions(sessionsData);
      setBookings(bookingsData);
      
      console.log('Dashboard data loaded:', { 
        sessions: sessionsData.length, 
        bookings: bookingsData.length,
        sessionsTotal: sessionsResponse?.total || 0,
        bookingsTotal: bookingsResponse?.total || 0
      });
      
      // Show helpful message if no data
      if (sessionsData.length === 0 && bookingsData.length === 0) {
        console.info('📋 Empty database - no sessions or bookings found');
      }
      
    } catch (err) {
      console.error('Dashboard load failed:', err);
      setError('Failed to load dashboard data. Please refresh or contact support.');
      // Ensure arrays are set even on error
      setSessions([]);
      setBookings([]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    alert('Logged out successfully');
    window.location.href = '/login';
  };

  const handleRefresh = () => {
    loadDashboardData();
  };

  // Helper functions for dynamic user role display
  const getDashboardTitle = () => {
    if (!user?.role) return 'Dashboard';
    
    const role = user.role.toLowerCase();
    switch (role) {
      case 'admin':
        return 'Admin Dashboard';
      case 'instructor':
      case 'teacher':
        return 'Instructor Dashboard';
      case 'student':
      default:
        return 'Student Dashboard';
    }
  };

  const getDisplayName = () => {
    // Priority: full_name > name > email prefix
    if (user?.full_name && user.full_name !== 'User' && user.full_name !== 'Student User') {
      return user.full_name;
    }
    if (user?.name && user.name !== 'Student User') {
      return user.name;
    }
    if (user?.email) {
      return user.email.split('@')[0];
    }
    return 'User';
  };

  const getUserRoleIcon = () => {
    if (!user?.role) return '👤';
    
    const role = user.role.toLowerCase();
    switch (role) {
      case 'admin':
        return '👨‍💼';
      case 'instructor':
      case 'teacher':
        return '👨‍🏫';
      case 'student':
      default:
        return '🎓';
    }
  };

  const getRoleDisplayText = () => {
    if (!user?.role) return 'user';
    return user.role.charAt(0).toUpperCase() + user.role.slice(1).toLowerCase();
  };

  const availableSessions = sessions.filter(session => !session.is_full);
  const totalUsers = 142; // Mock data
  
  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div>
          <h1>{getDashboardTitle()}</h1>
          {user && (
            <p>
              {getUserRoleIcon()} Welcome, {getDisplayName()}!
              <span style={{color: '#666', fontSize: '12px', marginLeft: '8px'}}>
                ({getRoleDisplayText()})
              </span>
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="refresh-button" onClick={handleRefresh} disabled={loading}>
            {loading ? '⟳' : '🔄'} Refresh
          </button>
          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>
      
      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Users</h3>
          <div className="stat-number">{totalUsers}</div>
        </div>
        <div className="stat-card">
          <h3>Total Sessions</h3>
          <div className="stat-number">{sessions.length}</div>
        </div>
        <div className="stat-card">
          <h3>Available Sessions</h3>
          <div className="stat-number">{availableSessions.length}</div>
        </div>
        <div className="stat-card">
          <h3>My Bookings</h3>
          <div className="stat-number">{bookings.length}</div>
        </div>
      </div>
      
      <div className="content-section">
        <h2>Available Sessions</h2>
        {loading ? (
          <div className="loading-state">Loading sessions...</div>
        ) : sessions.length === 0 ? (
          <div className="empty-state">No sessions available</div>
        ) : (
          <div className="sessions-list">
            {sessions.slice(0, 10).map((session, index) => (
              <div key={session.id || index} className="session-item">
                <div className="session-info">
                  <h3>{session.title || session.name || `Session ${session.id || index + 1}`}</h3>
                  <p>
                    {session.date_start ? new Date(session.date_start).toLocaleDateString() : '2025. 03. 03.'} - 
                    {session.mode?.toUpperCase() || 'OFFLINE'} - 
                    {session.capacity || 13} capacity
                    {session.location && ` - ${session.location}`}
                  </p>
                </div>
                <button 
                  className="book-button" 
                  disabled={session.is_full}
                  style={session.is_full ? {opacity: 0.5, cursor: 'not-allowed'} : {}}
                >
                  {session.is_full ? 'Full' : 'Book'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;