import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './SessionDetails.css';

const SessionDetails = () => {
  const { id } = useParams();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [userBooking, setUserBooking] = useState(null);
  const [theme, setTheme] = useState(() =>
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme, setColorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadSessionDetails();
    checkUserBooking();
  }, [id]);

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

  const loadSessionDetails = async () => {
    setLoading(true);
    try {
      const response = await apiService.getSession(id);
      setSession(response);
      console.log('Session details loaded:', response);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError('Session not found');
    } finally {
      setLoading(false);
    }
  };

  const checkUserBooking = async () => {
    try {
      const response = await apiService.getMyBookings();
      // Extract bookings array from API response object
      const bookingsData = response?.bookings || response || [];
      console.log('Checking user bookings for session', id, 'in', bookingsData.length, 'bookings');
      
      // Find booking for this session that is NOT cancelled
      // Check both b.session.id and b.session_id patterns
      const existingBooking = bookingsData.find(b => 
        (b.session?.id === parseInt(id) || b.session_id === parseInt(id)) && 
        b.status !== 'cancelled' && 
        b.status !== 'CANCELLED'
      );
      
      console.log('Session ID we are looking for:', parseInt(id));
      console.log('Available bookings to check:', bookingsData.map(b => ({
        booking_id: b.id,
        session_id: b.session_id,
        session_obj_id: b.session?.id,
        status: b.status
      })));
      
      setUserBooking(existingBooking);
      console.log('Found active booking (excluding cancelled):', existingBooking);
      
      // Log all bookings for this session for debugging
      const allBookingsForSession = bookingsData.filter(b => b.session?.id === parseInt(id));
      if (allBookingsForSession.length > 0) {
        console.log('All bookings for this session:', allBookingsForSession);
        console.log('First booking details:', {
          id: allBookingsForSession[0].id,
          session_id: allBookingsForSession[0].session_id,
          session_obj: allBookingsForSession[0].session,
          status: allBookingsForSession[0].status,
          user_id: allBookingsForSession[0].user_id
        });
      }
    } catch (err) {
      console.warn('Could not check existing booking:', err);
    }
  };

  const handleBookSession = async () => {
    setBooking(true);
    setError('');
    setSuccess('');
    
    try {
      await apiService.createBooking({ session_id: parseInt(id) });
      setSuccess('Session booked successfully!');
      
      // Refresh data
      await Promise.all([loadSessionDetails(), checkUserBooking()]);
      
    } catch (err) {
      console.error('Booking failed:', err);
      setError(`Booking failed: ${err.message}`);
    } finally {
      setBooking(false);
    }
  };

  const handleCancelBooking = async () => {
    if (!userBooking || !window.confirm('Cancel this booking?')) {
      return;
    }
    
    setBooking(true);
    try {
      await apiService.cancelBooking(userBooking.id);
      setSuccess('Booking cancelled successfully');
      
      // Refresh data
      await Promise.all([loadSessionDetails(), checkUserBooking()]);
      
    } catch (err) {
      console.error('Cancel failed:', err);
      setError(`Failed to cancel: ${err.message}`);
    } finally {
      setBooking(false);
    }
  };

  if (loading) {
    return <div className="page-loading">Loading session details...</div>;
  }

  if (!session) {
    return (
      <div className="session-not-found">
        <h2>Session Not Found</h2>
        <p>The session you're looking for doesn't exist or has been removed.</p>
        <Link to="/student/sessions" className="back-btn">← Browse Sessions</Link>
      </div>
    );
  }

  const isSessionFull = session.is_full;
  const isSessionPast = new Date(session.date_start) < new Date();
  const hasUserBooking = !!userBooking;
  const canBook = !isSessionFull && !isSessionPast && !hasUserBooking;
  const canCancel = hasUserBooking && !isSessionPast && 
                    userBooking.status !== 'cancelled' && 
                    userBooking.status !== 'CANCELLED';

  return (
    <div className="session-details">
      {/* Navigation */}
      <div className="page-header">
        <div>
          <Link to="/student/sessions" className="back-link">← All Sessions</Link>
          <h1>Session Details</h1>
        </div>
        <button onClick={() => logout()} className="logout-btn">Logout</button>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Session Information */}
      <div className="session-details-content">
        <div className="session-header-section">
          <div className="session-title-area">
            <h2>{session.title || `Session ${session.id}`}</h2>
            <div className="session-status-badges">
              <span className={`status-badge ${isSessionFull ? 'full' : 'available'}`}>
                {isSessionFull ? 'FULL' : 'AVAILABLE'}
              </span>
              {isSessionPast && <span className="status-badge past">COMPLETED</span>}
              {hasUserBooking && (
                <span className={`status-badge ${userBooking.status}`}>
                  YOUR BOOKING: {userBooking.status?.toUpperCase()}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="session-content-grid">
          {/* Main Details */}
          <div className="session-main-details">
            <div className="detail-group">
              <h3>📅 Date & Time</h3>
              <p className="session-datetime">
                <strong>{new Date(session.date_start).toLocaleDateString()}</strong><br />
                {new Date(session.date_start).toLocaleTimeString()} - 
                {new Date(session.date_end).toLocaleTimeString()}
              </p>
            </div>

            <div className="detail-group">
              <h3>📍 Location</h3>
              <p>{session.location || 'Location TBD'}</p>
            </div>

            <div className="detail-group">
              <h3>👥 Capacity</h3>
              <p>{session.current_bookings || 0} / {session.capacity} registered</p>
              <div className="capacity-bar">
                <div 
                  className="capacity-fill" 
                  style={{width: `${((session.current_bookings || 0) / session.capacity) * 100}%`}}
                ></div>
              </div>
            </div>

            <div className="detail-group">
              <h3>🏃‍♂️ Mode</h3>
              <p>{session.mode?.toUpperCase() || 'OFFLINE'}</p>
            </div>

            {session.description && (
              <div className="detail-group">
                <h3>📋 Description</h3>
                <p className="session-description">{session.description}</p>
              </div>
            )}

            {session.requirements && (
              <div className="detail-group">
                <h3>📝 Requirements</h3>
                <p>{session.requirements}</p>
              </div>
            )}
          </div>

          {/* Booking Actions */}
          <div className="booking-actions-panel">
            <div className="booking-status">
              {hasUserBooking ? (
                <div className="booking-confirmed">
                  <h3>{userBooking.status === 'waitlisted' ? 'You\'re Waitlisted!' : userBooking.status === 'confirmed' ? 'You\'re Registered!' : 'Booking Status'}</h3>
                  <p>Booking ID: #{userBooking.id}</p>
                  <p>Status: {userBooking.status}</p>
                  <p>Booked: {new Date(userBooking.created_at).toLocaleDateString()}</p>
                </div>
              ) : isSessionFull ? (
                <div className="booking-unavailable">
                  <h3>Session Full</h3>
                  <p>This session has reached capacity</p>
                </div>
              ) : isSessionPast ? (
                <div className="booking-unavailable session-completed">
                  <h3>Session Completed</h3>
                  <p>This session has already taken place</p>
                </div>
              ) : (
                <div className="booking-available">
                  <h3>Available for Booking</h3>
                  <p>Secure your spot now!</p>
                </div>
              )}
            </div>

            <div className="action-buttons">
              {canBook && (
                <button
                  onClick={handleBookSession}
                  disabled={booking}
                  className="book-session-btn primary"
                >
                  {booking ? 'Booking...' : 'Book This Session'}
                </button>
              )}
              
              {canCancel && (
                <button
                  onClick={handleCancelBooking}
                  disabled={booking}
                  className="cancel-booking-btn secondary"
                >
                  {booking ? 'Cancelling...' : 'Cancel Booking'}
                </button>
              )}
              
              <Link to="/student/sessions" className="browse-more-btn">
                Browse More Sessions
              </Link>
              
              <Link to="/student/bookings" className="my-bookings-btn">
                View My Bookings
              </Link>
            </div>
          </div>
        </div>

        {/* Additional Information */}
        {session.notes && (
          <div className="session-notes">
            <h3>📋 Additional Notes</h3>
            <p>{session.notes}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionDetails;