import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';

function DashboardPage() {
  const { user, logout } = useAuth();
  const [health, setHealth] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiStatus, setApiStatus] = useState('disconnected');

  useEffect(() => {
    loadDashboardData();
    // Check API status every 30 seconds
    const interval = setInterval(checkApiStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkApiStatus = async () => {
    try {
      await apiService.healthCheck();
      setApiStatus('connected');
    } catch (error) {
      setApiStatus('disconnected');
    }
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Check API status first
      await checkApiStatus();
      
      // Load health info
      const healthData = await apiService.detailedHealthCheck();
      setHealth(healthData);

      // Load sessions
      const sessionsData = await apiService.getSessions();
      setSessions(Array.isArray(sessionsData) ? sessionsData : []);

      // Load user's bookings
      const bookingsData = await apiService.getMyBookings();
      setBookings(Array.isArray(bookingsData) ? bookingsData : []);

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">🔄 Loading dashboard...</div>;
  }

  return (
    <div className="dashboard">
      {/* API Status Indicator */}
      <div className={`api-status ${apiStatus === 'connected' ? 'api-connected' : 'api-disconnected'}`}>
        {apiStatus === 'connected' ? '🟢 API Connected' : '🔴 API Disconnected'}
      </div>

      {/* User Info */}
      <div className="card">
        <h2>👋 Welcome, {user?.name}!</h2>
        <p><strong>Role:</strong> {user?.role}</p>
        <p><strong>Email:</strong> {user?.email}</p>
        <button onClick={logout} className="btn btn-danger">
          🚪 Logout
        </button>
        
        {user?.role === 'admin' && (
          <div style={{marginTop: '1rem'}}>
            <button onClick={() => window.location.href = '/admin'} className="btn">
              🛠️ Admin Panel
            </button>
          </div>
        )}
      </div>

      {/* System Health */}
      {health && (
        <div className="card">
          <h2>🏥 System Health</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-number">{health.database?.users_count || 0}</span>
              <span className="stat-label">👥 Total Users</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">{health.database?.sessions_count || 0}</span>
              <span className="stat-label">🏫 Total Sessions</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">{sessions.length}</span>
              <span className="stat-label">📅 Available Sessions</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">{bookings.length}</span>
              <span className="stat-label">📝 My Bookings</span>
            </div>
          </div>
        </div>
      )}

      {/* Available Sessions */}
      <div className="card">
        <h2>🏫 Available Sessions</h2>
        {sessions.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>📚 Session</th>
                <th>📅 Date</th>
                <th>🌐 Mode</th>
                <th>👥 Capacity</th>
                <th>🎯 Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.slice(0, 5).map((session) => (
                <tr key={session.id}>
                  <td>{session.title || `Session ${session.id}`}</td>
                  <td>{session.date_start ? new Date(session.date_start).toLocaleDateString() : 'N/A'}</td>
                  <td>
                    <span className="status-badge status-active">
                      {session.mode || 'offline'}
                    </span>
                  </td>
                  <td>{session.capacity || 'N/A'}</td>
                  <td>
                    <button className="btn" style={{fontSize: '0.8rem', padding: '0.5rem'}}>
                      📝 Book
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No sessions available</p>
        )}
      </div>

      {/* My Bookings */}
      <div className="card">
        <h2>📝 My Bookings</h2>
        {bookings.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>📚 Session</th>
                <th>📊 Status</th>
                <th>📅 Booked Date</th>
                <th>🎯 Action</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((booking, index) => (
                <tr key={booking.id || index}>
                  <td>Session {booking.session_id || index + 1}</td>
                  <td>
                    <span className={`status-badge ${booking.status === 'confirmed' ? 'status-active' : 'status-inactive'}`}>
                      {booking.status || 'pending'}
                    </span>
                  </td>
                  <td>{booking.created_at ? new Date(booking.created_at).toLocaleDateString() : 'N/A'}</td>
                  <td>
                    <button className="btn btn-danger" style={{fontSize: '0.8rem', padding: '0.5rem'}}>
                      ❌ Cancel
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No bookings found</p>
        )}
      </div>

      {/* Backend Testing Info */}
      <div className="card">
        <h2>🧪 Backend Testing Status</h2>
        <p><strong>Purpose:</strong> This frontend tests backend API functionality</p>
        <p><strong>API Base URL:</strong> http://localhost:8000</p>
        <p><strong>Current Status:</strong> 
          <span className={`status-badge ${apiStatus === 'connected' ? 'status-active' : 'status-inactive'}`}>
            {apiStatus === 'connected' ? 'Connected & Working' : 'Disconnected'}
          </span>
        </p>
        <button onClick={loadDashboardData} className="btn">
          🔄 Refresh Data
        </button>
      </div>
    </div>
  );
}

export default DashboardPage;