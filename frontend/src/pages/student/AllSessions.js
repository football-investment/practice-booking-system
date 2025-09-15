import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import SessionCard from '../../components/student/SessionCard';
import './AllSessions.css';

const AllSessions = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [bookingMessage, setBookingMessage] = useState('');
  const [bookingMessageType, setBookingMessageType] = useState(''); // 'success' or 'error'
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [bookingSession, setBookingSession] = useState(null);
  const [theme, setTheme] = useState(() =>
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme, setColorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadSessions();
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

  const loadSessions = async () => {
    setLoading(true);
    try {
      const response = await apiService.getSessions();
      console.log('Student sessions API response:', response);
      
      // Extract sessions array from API response object
      const sessionsData = response?.sessions || response?.data || response || [];
      
      setSessions(sessionsData);
      console.log('Student sessions loaded:', sessionsData.length, 'Total:', response?.total || 0);
      
      if (response?.total) {
        console.log(`Student sees ${sessionsData.length} of ${response.total} sessions`);
      }
    } catch (err) {
      console.error('Failed to load student sessions:', err);
      setError('Failed to load sessions: ' + (err.message || 'Unknown error'));
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleBooking = async (sessionId) => {
    setBookingSession(sessionId);
    setBookingMessage('');
    try {
      await apiService.createBooking({ session_id: sessionId });
      setBookingMessage('Session booked successfully!');
      setBookingMessageType('success');
      loadSessions(); // Refresh to update availability
      
      // Auto-hide success message after 5 seconds
      setTimeout(() => {
        setBookingMessage('');
        setBookingMessageType('');
      }, 5000);
    } catch (err) {
      console.error('Booking failed:', err);
      const errorMsg = err.message || 'Unknown error occurred';
      
      // Determine specific error type for testing
      let errorType = 'error';
      if (errorMsg.includes('limit') || errorMsg.includes('capacity') || errorMsg.includes('full')) {
        errorType = 'limit-error';
      } else if (errorMsg.includes('deadline') || errorMsg.includes('expired') || errorMsg.includes('time')) {
        errorType = 'deadline-error';
      }
      
      setBookingMessage(`Booking failed: ${errorMsg}`);
      setBookingMessageType(errorType);
      
      // Auto-hide error message after 8 seconds
      setTimeout(() => {
        setBookingMessage('');
        setBookingMessageType('');
      }, 8000);
    } finally {
      setBookingSession(null);
    }
  };

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = session.title?.toLowerCase().includes(search.toLowerCase()) ||
                         session.description?.toLowerCase().includes(search.toLowerCase());
    
    const now = new Date();
    const sessionStart = new Date(session.date_start);
    
    switch (filter) {
      case 'available':
        return !session.is_full && sessionStart > now && matchesSearch; // ✅ FIXED - exclude past events
      case 'upcoming':
        return sessionStart > now && matchesSearch;
      case 'today':
        const today = new Date().toDateString();
        return sessionStart.toDateString() === today && matchesSearch;
      default:
        return matchesSearch;
    }
  });

  return (
    <div className="all-sessions">
      {/* Navigation */}
      <div className="page-header">
        <div>
          <Link to="/student/dashboard" className="back-link">← Back to Dashboard</Link>
          <h1>All Sessions</h1>
        </div>
        <button onClick={() => logout()} className="logout-btn">Logout</button>
      </div>

      {/* Filters */}
      <div className="filters-section">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search sessions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="filter-tabs">
          <button 
            className={filter === 'all' ? 'tab active' : 'tab'}
            onClick={() => setFilter('all')}
          >
            All ({sessions.length})
          </button>
          <button 
            className={filter === 'available' ? 'tab active' : 'tab'}
            onClick={() => setFilter('available')}
          >
            Available ({sessions.filter(s => !s.is_full && new Date(s.date_start) > new Date()).length})
          </button>
          <button 
            className={filter === 'upcoming' ? 'tab active' : 'tab'}
            onClick={() => setFilter('upcoming')}
          >
            Upcoming ({sessions.filter(s => new Date(s.date_start) > new Date()).length})
          </button>
          <button 
            className={filter === 'today' ? 'tab active' : 'tab'}
            onClick={() => setFilter('today')}
          >
            Today ({sessions.filter(s => new Date(s.date_start).toDateString() === new Date().toDateString()).length})
          </button>
        </div>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}
      
      {/* Booking Status Messages */}
      {bookingMessage && (
        <div 
          className={`booking-message ${bookingMessageType}`}
          data-testid={
            bookingMessageType === 'success' ? 'booking-success' :
            bookingMessageType === 'limit-error' ? 'booking-limit-error' :
            bookingMessageType === 'deadline-error' ? 'booking-deadline-error' :
            'booking-error'
          }
        >
          {bookingMessageType === 'success' ? '✅' : '❌'} {bookingMessage}
        </div>
      )}

      {/* Sessions List */}
      <div className="sessions-container">
        {loading ? (
          <div className="loading-state" data-testid="loading-sessions">Loading sessions...</div>
        ) : filteredSessions.length === 0 ? (
          <div className="empty-state" data-testid="session-list">
            <h3>No sessions found</h3>
            <p>Try adjusting your filters or search terms</p>
          </div>
        ) : (
          <div className="sessions-grid" data-testid="session-list">
            {filteredSessions.map(session => (
              <SessionCard
                key={session.id}
                session={session}
                onViewDetails={(session) => {
                  navigate(`/student/sessions/${session.id}`);
                }}
                onBook={(session) => {
                  handleBooking(session.id);
                }}
                isBooking={bookingSession === session.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AllSessions;