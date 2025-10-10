import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './InstructorAttendance.css';

const InstructorAttendance = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [attendance, setAttendance] = useState([]);
  const [filteredAttendance, setFilteredAttendance] = useState([]);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    search: '',
    session: 'all',
    status: 'all',
    dateRange: 'all'
  });
  const [stats, setStats] = useState({
    totalSessions: 0,
    totalAttendees: 0,
    averageAttendance: 0,
    attendanceRate: 0
  });

  useEffect(() => {
    loadAttendance();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [attendance, filters]);

  const loadAttendance = async () => {
    try {
      setLoading(true);
      const response = await apiService.getInstructorAttendance();
      const attendanceData = Array.isArray(response) ? response : (response?.sessions || []);
      
      setAttendance(attendanceData);
      calculateStats(attendanceData);
      
      console.log('Instructor attendance loaded:', attendanceData.length);
    } catch (err) {
      console.error('Failed to load attendance:', err);
      setError('Failed to load attendance data: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (attendanceData) => {
    const stats = {
      totalSessions: attendanceData.length,
      totalAttendees: 0,
      averageAttendance: 0,
      attendanceRate: 0
    };

    if (attendanceData.length > 0) {
      let totalBookings = 0;
      let totalAttended = 0;

      attendanceData.forEach(session => {
        const attended = session.attendance_count || 0;
        const capacity = session.capacity || 0;
        const bookings = session.current_bookings || 0;

        stats.totalAttendees += attended;
        totalBookings += bookings;
        totalAttended += attended;
      });

      stats.averageAttendance = Math.round(stats.totalAttendees / attendanceData.length);
      stats.attendanceRate = totalBookings > 0 ? Math.round((totalAttended / totalBookings) * 100) : 0;
    }

    setStats(stats);
  };

  const applyFilters = () => {
    let filtered = [...attendance];

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(session =>
        session.title?.toLowerCase().includes(filters.search.toLowerCase()) ||
        session.location?.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Status filter
    if (filters.status !== 'all') {
      const now = new Date();
      filtered = filtered.filter(session => {
        const sessionDate = new Date(session.date_start);
        const sessionEnd = new Date(session.date_end);
        
        switch (filters.status) {
          case 'completed':
            return sessionEnd < now;
          case 'ongoing':
            return sessionDate <= now && sessionEnd >= now;
          case 'upcoming':
            return sessionDate > now;
          default:
            return true;
        }
      });
    }

    // Date range filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      let dateThreshold;
      
      switch (filters.dateRange) {
        case 'week':
          dateThreshold = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case 'month':
          dateThreshold = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          break;
        case 'quarter':
          dateThreshold = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
          break;
        default:
          dateThreshold = null;
      }
      
      if (dateThreshold) {
        filtered = filtered.filter(session => new Date(session.date_start) >= dateThreshold);
      }
    }

    setFilteredAttendance(filtered);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const getSessionStatus = (session) => {
    const now = new Date();
    const sessionStart = new Date(session.date_start);
    const sessionEnd = new Date(session.date_end);

    if (sessionStart <= now && sessionEnd >= now) {
      return { label: 'LIVE', class: 'live', icon: '🔴' };
    } else if (sessionEnd < now) {
      return { label: 'Completed', class: 'completed', icon: '✅' };
    } else {
      return { label: 'Upcoming', class: 'upcoming', icon: '🔜' };
    }
  };

  const getAttendanceRate = (session) => {
    const attended = session.attendance_count || 0;
    const bookings = session.current_bookings || 0;
    
    if (bookings === 0) return 0;
    return Math.round((attended / bookings) * 100);
  };

  const getAttendanceColor = (rate) => {
    if (rate >= 80) return '#10b981'; // green
    if (rate >= 60) return '#f59e0b'; // amber
    if (rate >= 40) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleMarkAttendance = async (sessionId, userId, attended) => {
    try {
      await apiService.markAttendance(sessionId, userId, attended);
      // Reload attendance data
      loadAttendance();
    } catch (error) {
      console.error('Failed to mark attendance:', error);
      setError('Failed to update attendance: ' + error.message);
    }
  };

  if (loading) {
    return (
      <div className="instructor-attendance">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading attendance data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-attendance">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>📊 Attendance Tracking</h1>
          <p>Monitor and manage student attendance across your sessions</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-item">
          <span className="stat-number">{stats.totalSessions}</span>
          <span className="stat-label">Total Sessions</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.totalAttendees}</span>
          <span className="stat-label">Total Attendees</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.averageAttendance}</span>
          <span className="stat-label">Average per Session</span>
        </div>
        <div className="stat-item">
          <span className="stat-number" style={{ color: getAttendanceColor(stats.attendanceRate) }}>
            {stats.attendanceRate}%
          </span>
          <span className="stat-label">Attendance Rate</span>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Search sessions..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filter-controls">
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="ongoing">Live/Ongoing</option>
            <option value="upcoming">Upcoming</option>
          </select>

          <select
            value={filters.dateRange}
            onChange={(e) => handleFilterChange('dateRange', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Time</option>
            <option value="week">Last Week</option>
            <option value="month">Last Month</option>
            <option value="quarter">Last 3 Months</option>
          </select>
        </div>
      </div>

      {/* Attendance List */}
      <div className="attendance-section">
        <div className="section-header">
          <h2>Session Attendance</h2>
          <span className="results-count">{filteredAttendance.length} sessions</span>
        </div>

        {filteredAttendance.length === 0 ? (
          <div className="empty-state">
            {filters.search || filters.status !== 'all' || filters.dateRange !== 'all' ? (
              <p>🔍 No sessions match your filters.</p>
            ) : (
              <p>📊 No attendance data available.</p>
            )}
          </div>
        ) : (
          <div className="attendance-grid">
            {filteredAttendance.map(session => {
              const statusInfo = getSessionStatus(session);
              const attendanceRate = getAttendanceRate(session);
              const attended = session.attendance_count || 0;
              const bookings = session.current_bookings || 0;
              
              return (
                <div key={session.id} className={`attendance-card ${statusInfo.class}`}>
                  <div className="attendance-header">
                    <div className="session-title-row">
                      <h3>{session.title}</h3>
                      <span className={`status-badge ${statusInfo.class}`}>
                        {statusInfo.icon} {statusInfo.label}
                      </span>
                    </div>
                    <div className="session-meta">
                      <span>📅 {formatDateTime(session.date_start)}</span>
                      <span>📍 {session.location}</span>
                    </div>
                  </div>

                  <div className="attendance-stats">
                    <div className="stat-row">
                      <div className="stat-item-small">
                        <span className="stat-value">{attended}</span>
                        <span className="stat-label">Attended</span>
                      </div>
                      <div className="stat-item-small">
                        <span className="stat-value">{bookings}</span>
                        <span className="stat-label">Booked</span>
                      </div>
                      <div className="stat-item-small">
                        <span className="stat-value">{session.capacity || 0}</span>
                        <span className="stat-label">Capacity</span>
                      </div>
                    </div>
                  </div>

                  <div className="attendance-progress">
                    <div className="progress-header">
                      <span>Attendance Rate</span>
                      <span 
                        className="progress-percentage"
                        style={{ color: getAttendanceColor(attendanceRate) }}
                      >
                        {attendanceRate}%
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div 
                        className="progress-fill" 
                        style={{ 
                          width: `${attendanceRate}%`,
                          backgroundColor: getAttendanceColor(attendanceRate)
                        }}
                      ></div>
                    </div>
                  </div>

                  <div className="attendance-actions">
                    <Link 
                      to={`/instructor/sessions/${session.id}/attendance`} 
                      className="btn-primary"
                    >
                      📋 Manage
                    </Link>
                    <Link 
                      to={`/instructor/sessions/${session.id}`} 
                      className="btn-secondary"
                    >
                      📝 Details
                    </Link>
                    {statusInfo.class === 'live' && (
                      <button className="btn-tertiary live-btn">
                        🔴 Take Attendance
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <div className="action-card">
            <div className="action-icon">📊</div>
            <h3>Attendance Reports</h3>
            <p>Generate detailed attendance reports and analytics</p>
            <button className="action-btn">Generate Report</button>
          </div>
          <div className="action-card">
            <div className="action-icon">📱</div>
            <h3>QR Code Check-in</h3>
            <p>Enable QR code-based attendance tracking</p>
            <button className="action-btn">Setup QR Codes</button>
          </div>
          <div className="action-card">
            <div className="action-icon">📧</div>
            <h3>Attendance Alerts</h3>
            <p>Set up alerts for low attendance sessions</p>
            <button className="action-btn">Configure Alerts</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InstructorAttendance;