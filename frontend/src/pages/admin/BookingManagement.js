import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const BookingManagement = () => {
  const { logout } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sessionFilter, setSessionFilter] = useState('all');
  const [cancellingBooking, setCancellingBooking] = useState(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      console.log('Loading booking management data...');
      
      const [bookingsResponse, sessionsResponse, usersResponse] = await Promise.all([
        apiService.getAllBookings().catch(() => ({})),
        apiService.getSessions().catch(() => ({})),
        apiService.getUsers().catch(() => ({}))
      ]);
      
      console.log('Bookings API response:', bookingsResponse);
      console.log('Sessions API response:', sessionsResponse);
      console.log('Users API response:', usersResponse);
      
      // Extract data arrays from API response objects
      const bookingsData = bookingsResponse?.bookings || bookingsResponse || [];
      const sessionsData = sessionsResponse?.sessions || sessionsResponse || [];
      const usersData = usersResponse?.users || usersResponse || [];
      
      setBookings(bookingsData);
      setSessions(sessionsData);
      setUsers(usersData);
      
      console.log('Booking management data loaded:', {
        bookings: bookingsData.length,
        sessions: sessionsData.length,
        users: usersData.length
      });
      
    } catch (err) {
      console.error('Failed to load booking data:', err);
      setError('Failed to load booking data: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) {
      return;
    }
    
    setCancellingBooking(bookingId);
    try {
      await apiService.cancelBooking(bookingId);
      setSuccess('Booking cancelled successfully');
      loadAllData();
    } catch (err) {
      console.error('Cancel booking failed:', err);
      setError(`Failed to cancel booking: ${err.message}`);
    } finally {
      setCancellingBooking(null);
    }
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user?.full_name || user?.email || `User ${userId}`;
  };

  const getSessionName = (sessionId) => {
    const session = sessions.find(s => s.id === sessionId);
    return session?.title || `Session ${sessionId}`;
  };

  const filteredBookings = bookings.filter(booking => {
    const user = users.find(u => u.id === booking.user_id);
    const session = sessions.find(s => s.id === booking.session_id);
    
    const matchesSearch = 
      user?.email?.toLowerCase().includes(search.toLowerCase()) ||
      user?.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      session?.title?.toLowerCase().includes(search.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || booking.status === statusFilter;
    const matchesSession = sessionFilter === 'all' || booking.session_id === parseInt(sessionFilter);
    
    return matchesSearch && matchesStatus && matchesSession;
  });

  const bookingStats = {
    total: bookings.length,
    confirmed: bookings.filter(b => b.status === 'confirmed').length,
    cancelled: bookings.filter(b => b.status === 'cancelled').length,
    attended: bookings.filter(b => b.attended === true).length,
    missed: bookings.filter(b => b.attended === false).length
  };

  return (
    <div className="booking-management">
      {/* Navigation */}
      <div className="admin-page-header">
        <div>
          <Link to="/admin/dashboard" className="back-link">← Admin Dashboard</Link>
          <h1>Booking Management</h1>
        </div>
        <div className="header-actions">
          <button onClick={loadAllData} disabled={loading} className="refresh-btn">
            🔄 Refresh
          </button>
          <button onClick={() => logout()} className="logout-btn">Logout</button>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Booking Stats */}
      <div className="booking-stats">
        <div className="stat-item">
          <span className="stat-value">{bookingStats.total}</span>
          <span className="stat-label">Total Bookings</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{bookingStats.confirmed}</span>
          <span className="stat-label">Confirmed</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{bookingStats.cancelled}</span>
          <span className="stat-label">Cancelled</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{bookingStats.attended}</span>
          <span className="stat-label">Attended</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{bookingStats.missed}</span>
          <span className="stat-label">Missed</span>
        </div>
      </div>

      {/* Filters */}
      <div className="booking-filters">
        <div className="search-section">
          <input
            type="text"
            placeholder="Search by user name, email, or session..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="filter-section">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="status-filter"
          >
            <option value="all">All Status</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
            <option value="pending">Pending</option>
          </select>
          
          <select
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="session-filter"
          >
            <option value="all">All Sessions</option>
            {sessions.map(session => (
              <option key={session.id} value={session.id}>
                {session.title || `Session ${session.id}`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Bookings Table */}
      <div className="bookings-table-container">
        {loading ? (
          <div className="table-loading">Loading bookings...</div>
        ) : filteredBookings.length === 0 ? (
          <div className="table-empty">
            <h3>No bookings found</h3>
            <p>Try adjusting your search or filters</p>
          </div>
        ) : (
          <table className="bookings-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Session</th>
                <th>Booking Date</th>
                <th>Session Date</th>
                <th>Status</th>
                <th>Attendance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredBookings.map(booking => {
                const user = users.find(u => u.id === booking.user_id);
                const session = sessions.find(s => s.id === booking.session_id);
                
                return (
                  <tr key={booking.id}>
                    <td className="user-info">
                      <div className="user-avatar">
                        {user?.role === 'admin' ? '👨‍💼' : 
                         user?.role === 'instructor' ? '👨‍🏫' : '🎓'}
                      </div>
                      <div>
                        <div className="user-name">{user?.full_name || user?.email}</div>
                        <div className="user-email">{user?.email}</div>
                      </div>
                    </td>
                    <td className="session-info">
                      <div className="session-title">{session?.title || `Session ${booking.session_id}`}</div>
                      <div className="session-location">{session?.location}</div>
                    </td>
                    <td>{new Date(booking.created_at).toLocaleDateString()}</td>
                    <td>
                      <div>{new Date(session?.date_start).toLocaleDateString()}</div>
                      <div className="session-time">
                        {new Date(session?.date_start).toLocaleTimeString()}
                      </div>
                    </td>
                    <td>
                      <span className={`status-badge ${booking.status}`}>
                        {booking.status?.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      {booking.attended === null ? (
                        <span className="attendance-pending">Pending</span>
                      ) : booking.attended ? (
                        <span className="attendance-present">✅ Attended</span>
                      ) : (
                        <span className="attendance-absent">❌ Missed</span>
                      )}
                    </td>
                    <td className="table-actions">
                      {booking.status === 'confirmed' && (
                        <button
                          onClick={() => handleCancelBooking(booking.id)}
                          disabled={cancellingBooking === booking.id}
                          className="cancel-btn"
                          title="Cancel Booking"
                        >
                          {cancellingBooking === booking.id ? '⏳' : '❌'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default BookingManagement;