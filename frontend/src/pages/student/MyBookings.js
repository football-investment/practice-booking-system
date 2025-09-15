import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './MyBookings.css';

const MyBookings = () => {
  const { user, logout } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cancellingBooking, setCancellingBooking] = useState(null);
  const [checkingInBooking, setCheckingInBooking] = useState(null);
  const [filter, setFilter] = useState('all');
  const [theme, setTheme] = useState(() =>
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme, setColorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadBookings();
  }, []);

  useEffect(() => {
    // Apply theme and color scheme to document
    const root = document.documentElement;

    if (theme === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const applyAutoTheme = () => {
        root.setAttribute('data-theme', mediaQuery.matches ? 'dark' : 'light');
        root.setAttribute('data-color', colorScheme);
      };

      applyAutoTheme();
      mediaQuery.addListener(applyAutoTheme);

      return () => mediaQuery.removeListener(applyAutoTheme);
    } else {
      root.setAttribute('data-theme', theme);
      root.setAttribute('data-color', colorScheme);
    }
  }, [theme, colorScheme]);

  const loadBookings = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await apiService.getMyBookings();
      console.log('My bookings API response:', response);
      
      // Extract bookings array from API response object
      const bookingsData = response?.bookings || response?.data || response || [];
      
      setBookings(bookingsData);
      console.log('My bookings loaded:', bookingsData.length, 'Total:', response?.total || 0);
      
      if (response?.total) {
        console.log(`Student has ${bookingsData.length} of ${response.total} bookings`);
      }
    } catch (err) {
      console.error('Failed to load student bookings:', err);
      setError('Failed to load your bookings: ' + (err.message || 'Unknown error'));
      setBookings([]);
    } finally {
      setLoading(false);
    }
  };

  const getBookingStatusInfo = (booking) => {
    const now = new Date();
    const sessionStart = new Date(booking.session?.date_start);
    const sessionEnd = new Date(booking.session?.date_end);
    
    // Session timing
    const isUpcoming = sessionStart > now;
    const isActive = sessionStart <= now && sessionEnd >= now;  
    const isPast = sessionEnd < now;
    
    // Enhanced attendance info from backend
    const hasAttendanceRecord = booking.attendance !== null && booking.attendance !== undefined;
    const attendanceStatus = booking.attendance?.status;
    
    // Use backend computed properties
    const canGiveFeedback = booking.can_give_feedback || false;
    const feedbackSubmitted = booking.feedback_submitted || false;
    const attended = booking.attended || false;
    
    return {
        isUpcoming,
        isActive, 
        isPast,
        sessionStart,
        sessionEnd,
        hasAttendanceRecord,
        hasAttendance: hasAttendanceRecord,
        attendanceStatus,
        attended,
        canGiveFeedback,
        feedbackSubmitted,
        showAttendanceStatus: hasAttendanceRecord || isPast
    };
  };

  const getAttendanceBadge = (statusInfo) => {
    if (!statusInfo.showAttendanceStatus) return null;
    
    if (statusInfo.hasAttendanceRecord) {
        const statusMap = {
            'present': { icon: '✅', text: 'Attended', class: 'present' },
            'late': { icon: '🟡', text: 'Late', class: 'late' },
            'absent': { icon: '❌', text: 'Missed', class: 'absent' },
            'excused': { icon: '💙', text: 'Excused', class: 'excused' }
        };
        
        const status = statusMap[statusInfo.attendanceStatus] || 
                      { icon: '⚪', text: 'Unknown', class: 'unknown' };
        
        return (
            <span className={`attendance-badge ${status.class}`}>
                {status.icon} {status.text}
            </span>
        );
    } else if (statusInfo.isPast) {
        // Check if session is currently active for check-in
        const now = new Date();
        const sessionStart = new Date(statusInfo.sessionStart);
        const sessionEnd = new Date(statusInfo.sessionEnd);
        const isSessionActive = now >= sessionStart && now <= sessionEnd;
        
        if (isSessionActive && !statusInfo.hasAttendance) {
            return (
                <span className="attendance-badge checkin-available" style={{
                    background: 'linear-gradient(135deg, #10b981, #059669)',
                    color: 'white'
                }}>
                    ✅ Can Check In
                </span>
            );
        }
        
        return (
            <span className="attendance-badge pending">
                ⏳ Attendance Pending
            </span>
        );
    }
    
    return null;
  };

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to cancel this booking?')) {
      return;
    }
    
    setCancellingBooking(bookingId);
    try {
      await apiService.cancelBooking(bookingId);
      alert('Booking cancelled successfully');
      loadBookings(); // Refresh list
    } catch (err) {
      console.error('Cancel failed:', err);
      alert(`Failed to cancel booking: ${err.message}`);
    } finally {
      setCancellingBooking(null);
    }
  };

  const handleCheckIn = async (bookingId) => {
    setCheckingInBooking(bookingId);
    try {
      await apiService.checkIn(bookingId);
      alert('Successfully checked in!');
      loadBookings(); // Refresh to update attendance status
    } catch (err) {
      console.error('Check-in failed:', err);
      alert(`Check-in failed: ${err.message}`);
    } finally {
      setCheckingInBooking(null);
    }
  };

  const getBookingsByFilter = () => {
    const now = new Date();
    
    switch (filter) {
      case 'upcoming':
        return bookings.filter(booking => 
          new Date(booking.session?.date_start) > now
        );
      case 'past':
        return bookings.filter(booking => 
          new Date(booking.session?.date_start) < now
        );
      case 'cancelled':
        return bookings.filter(booking => booking.status === 'cancelled');
      default:
        return bookings;
    }
  };

  const filteredBookings = getBookingsByFilter();

  const canCancelBooking = (booking) => {
    if (booking.status === 'cancelled') return false;
    const sessionStart = new Date(booking.session?.date_start);
    const now = new Date();
    const hoursUntilSession = (sessionStart - now) / (1000 * 60 * 60);
    return hoursUntilSession > 24; // Can cancel up to 24 hours before
  };

  if (loading) {
    return <div className="page-loading">Loading your bookings...</div>;
  }

  return (
    <div className="my-bookings">
      {/* Navigation */}
      <div className="page-header">
        <div>
          <Link to="/student/dashboard" className="back-link">← Dashboard</Link>
          <h1>My Bookings</h1>
        </div>
        <button onClick={() => logout()} className="logout-btn">Logout</button>
      </div>

      {/* Filter Tabs */}
      <div className="filter-tabs">
        <button 
          className={filter === 'all' ? 'tab active' : 'tab'}
          onClick={() => setFilter('all')}
        >
          All ({bookings.length})
        </button>
        <button 
          className={filter === 'upcoming' ? 'tab active' : 'tab'}
          onClick={() => setFilter('upcoming')}
        >
          Upcoming ({bookings.filter(b => new Date(b.session?.date_start) > new Date()).length})
        </button>
        <button 
          className={filter === 'past' ? 'tab active' : 'tab'}
          onClick={() => setFilter('past')}
        >
          Past ({bookings.filter(b => new Date(b.session?.date_start) < new Date()).length})
        </button>
        <button 
          className={filter === 'cancelled' ? 'tab active' : 'tab'}
          onClick={() => setFilter('cancelled')}
        >
          Cancelled ({bookings.filter(b => b.status === 'cancelled').length})
        </button>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* Bookings List */}
      <div className="bookings-container">
        {filteredBookings.length === 0 ? (
          <div className="empty-state">
            <h3>No bookings found</h3>
            <p>
              {filter === 'all' ? 
                "You haven't booked any sessions yet" : 
                `No ${filter} bookings found`
              }
            </p>
            <Link to="/student/sessions" className="cta-button">Browse Sessions</Link>
          </div>
        ) : (
          <div className="bookings-list">
            {filteredBookings.map(booking => {
              const statusInfo = getBookingStatusInfo(booking);
              return (
              <div key={booking.id} className="booking-card">
                <div className="booking-header">
                  <h3>{booking.session?.title || `Session ${booking.session?.id}`}</h3>
                  <div className="booking-badges">
                    <span className={`status-badge ${booking.status.toLowerCase()}`}>
                      {booking.status.toUpperCase()}
                    </span>
                    
                    {/* NEW: Show attendance badge */}
                    {getAttendanceBadge(statusInfo)}
                    
                    {statusInfo.feedbackSubmitted && (
                      <span className="feedback-badge">✅ Feedback Given</span>
                    )}
                  </div>
                </div>

                <div className="booking-details">
                  <p className="booking-date">
                    📅 {new Date(booking.session?.date_start).toLocaleDateString()}
                  </p>
                  <p className="booking-time">
                    🕒 {new Date(booking.session?.date_start).toLocaleTimeString()} - 
                    {new Date(booking.session?.date_end).toLocaleTimeString()}
                  </p>
                  <p className="booking-location">
                    📍 {booking.session?.location || 'Location TBD'}
                  </p>
                  <p className="booking-created">
                    📝 Booked: {new Date(booking.created_at).toLocaleDateString()}
                  </p>
                </div>

                {/* Action Buttons - ENHANCED VERSION */}
                <div className="booking-actions">
                    {statusInfo.isUpcoming && booking.status === 'confirmed' && (
                        <button 
                            onClick={() => handleCancelBooking(booking.id)}
                            className="btn btn-cancel"
                            disabled={cancellingBooking === booking.id}
                        >
                            {cancellingBooking === booking.id ? (
                                <>
                                    <span className="btn-spinner">⏳</span>
                                    Cancelling...
                                </>
                            ) : (
                                <>
                                    <span className="btn-icon">❌</span>
                                    Cancel Booking
                                </>
                            )}
                        </button>
                    )}
                    
                    {/* NEW: Check-in button for active sessions */}
                    {(() => {
                        const now = new Date();
                        const sessionStart = new Date(booking.session?.date_start);
                        const sessionEnd = new Date(booking.session?.date_end);
                        const isSessionActive = now >= sessionStart && now <= sessionEnd;
                        const canCheckIn = isSessionActive && booking.status === 'confirmed' && 
                                          statusInfo.isPast && !statusInfo.hasAttendance;
                        
                        return canCheckIn && (
                            <button 
                                onClick={() => handleCheckIn(booking.id)}
                                className="btn btn-checkin"
                                disabled={checkingInBooking === booking.id}
                                style={{
                                    background: 'linear-gradient(135deg, #10b981, #059669)',
                                    color: 'white',
                                    border: '1px solid #047857'
                                }}
                            >
                                {checkingInBooking === booking.id ? (
                                    <>
                                        <span className="btn-spinner">⏳</span>
                                        Checking In...
                                    </>
                                ) : (
                                    <>
                                        <span className="btn-icon">✅</span>
                                        Check In
                                    </>
                                )}
                            </button>
                        );
                    })()}
                    
                    {/* CRITICAL: Enhanced feedback button logic */}
                    {statusInfo.canGiveFeedback && (
                        <Link 
                            to={`/student/feedback?session=${booking.session?.id}&booking=${booking.id}`}
                            className="btn btn-feedback"
                        >
                            <span className="btn-icon">📝</span>
                            Give Feedback
                        </Link>
                    )}
                    
                    {statusInfo.feedbackSubmitted && (
                        <span className="feedback-badge submitted">
                            ⭐ Feedback Given
                        </span>
                    )}
                    
                    <Link 
                        to={`/student/sessions/${booking.session?.id}`}
                        className="btn btn-details"
                    >
                        <span className="btn-icon">👁️</span>
                        View Session
                    </Link>
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-footer">
        <Link to="/student/sessions" className="action-btn primary">
          📅 Browse More Sessions
        </Link>
        <Link to="/student/dashboard" className="action-btn secondary">
          🏠 Back to Dashboard
        </Link>
      </div>
    </div>
  );
};

export default MyBookings;