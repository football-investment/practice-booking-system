import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import InstructorSessionCard from '../../components/instructor/InstructorSessionCard';
import SessionModal from '../../components/instructor/SessionModal';
import './InstructorSessions.css';

const InstructorSessions = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    status: 'all', // all, upcoming, past, today
    search: '',
    sport_type: 'all'
  });
  const [stats, setStats] = useState({
    total: 0,
    upcoming: 0,
    today: 0,
    past: 0
  });
  const [showModal, setShowModal] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [isModalLoading, setIsModalLoading] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [sessions, filters]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await apiService.getInstructorSessions();
      const sessionsData = Array.isArray(response) ? response : (response?.sessions || []);
      
      setSessions(sessionsData);
      calculateStats(sessionsData);
      
      console.log('Instructor sessions loaded:', sessionsData.length);
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError('Failed to load sessions: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (sessionsData) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const stats = {
      total: sessionsData.length,
      upcoming: 0,
      today: 0,
      past: 0
    };

    sessionsData.forEach(session => {
      const sessionDate = new Date(session.date_start);
      const sessionDateOnly = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());
      
      if (sessionDateOnly.getTime() === today.getTime()) {
        stats.today++;
      } else if (sessionDate > now) {
        stats.upcoming++;
      } else {
        stats.past++;
      }
    });

    setStats(stats);
  };

  const applyFilters = () => {
    let filtered = [...sessions];
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(session => {
        const sessionDate = new Date(session.date_start);
        const sessionDateOnly = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());
        
        switch (filters.status) {
          case 'today':
            return sessionDateOnly.getTime() === today.getTime();
          case 'upcoming':
            return sessionDate > now && sessionDateOnly.getTime() !== today.getTime();
          case 'past':
            return sessionDate < now && sessionDateOnly.getTime() !== today.getTime();
          default:
            return true;
        }
      });
    }

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(session =>
        session.title.toLowerCase().includes(filters.search.toLowerCase()) ||
        session.location.toLowerCase().includes(filters.search.toLowerCase()) ||
        session.description?.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Sport type filter
    if (filters.sport_type !== 'all') {
      filtered = filtered.filter(session => session.sport_type === filters.sport_type);
    }

    setFilteredSessions(filtered);
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
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const sessionDateOnly = new Date(sessionStart.getFullYear(), sessionStart.getMonth(), sessionStart.getDate());

    if (sessionDateOnly.getTime() === today.getTime()) {
      if (sessionStart <= now && sessionEnd >= now) {
        return { label: 'LIVE', class: 'live', icon: '🔴' };
      } else if (sessionStart > now) {
        return { label: 'Today', class: 'today', icon: '📅' };
      } else {
        return { label: 'Completed', class: 'completed', icon: '✅' };
      }
    } else if (sessionStart > now) {
      return { label: 'Upcoming', class: 'upcoming', icon: '🔜' };
    } else {
      return { label: 'Past', class: 'past', icon: '📋' };
    }
  };

  const getSportTypes = () => {
    const types = [...new Set(sessions.map(s => s.sport_type).filter(Boolean))];
    return types.sort();
  };

  // CRUD Operations
  const handleCreateSession = () => {
    setSelectedSession(null);
    setShowModal(true);
  };

  const handleEditSession = (session) => {
    setSelectedSession(session);
    setShowModal(true);
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
      return;
    }

    try {
      await apiService.deleteSession(sessionId);
      await loadSessions(); // Refresh the list
      console.log('Session deleted successfully');
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('Failed to delete session: ' + (err.message || 'Unknown error'));
    }
  };

  const handleSaveSession = async (sessionData) => {
    try {
      setIsModalLoading(true);
      
      if (selectedSession) {
        // Update existing session
        await apiService.updateSession(selectedSession.id, sessionData);
        console.log('Session updated successfully');
      } else {
        // Create new session
        await apiService.createSession(sessionData);
        console.log('Session created successfully');
      }
      
      setShowModal(false);
      setSelectedSession(null);
      await loadSessions(); // Refresh the list
      
    } catch (err) {
      console.error('Failed to save session:', err);
      alert('Failed to save session: ' + (err.message || 'Unknown error'));
    } finally {
      setIsModalLoading(false);
    }
  };

  const handleCloseModal = () => {
    if (!isModalLoading) {
      setShowModal(false);
      setSelectedSession(null);
    }
  };

  if (loading) {
    return (
      <div className="instructor-sessions">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading your sessions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-sessions">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>📅 My Sessions</h1>
          <p>Manage and track your teaching sessions</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-item">
          <span className="stat-number">{stats.total}</span>
          <span className="stat-label">Total Sessions</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.today}</span>
          <span className="stat-label">Today</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.upcoming}</span>
          <span className="stat-label">Upcoming</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.past}</span>
          <span className="stat-label">Past</span>
        </div>
      </div>

      {/* Actions & Filters */}
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
            <option value="all">All Sessions</option>
            <option value="today">Today</option>
            <option value="upcoming">Upcoming</option>
            <option value="past">Past</option>
          </select>

          <select
            value={filters.sport_type}
            onChange={(e) => handleFilterChange('sport_type', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Sports</option>
            {getSportTypes().map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <button 
            onClick={handleCreateSession}
            className="create-session-btn"
          >
            ➕ New Session
          </button>
        </div>
      </div>

      {/* Sessions List */}
      <div className="sessions-section">
        <div className="section-header">
          <h2>Sessions</h2>
          <span className="results-count">{filteredSessions.length} sessions</span>
        </div>

        {filteredSessions.length === 0 ? (
          <div className="empty-state">
            {filters.search || filters.status !== 'all' || filters.sport_type !== 'all' ? (
              <p>🔍 No sessions match your filters.</p>
            ) : (
              <p>📅 No sessions found.</p>
            )}
          </div>
        ) : (
          <div className="sessions-grid">
            {filteredSessions.map(session => (
              <InstructorSessionCard
                key={session.id}
                session={session}
                onViewDetails={(session) => {
                  navigate(`/instructor/sessions/${session.id}`);
                }}
                onEdit={handleEditSession}
                onDelete={handleDeleteSession}
                onAttendance={(session) => {
                  navigate(`/instructor/sessions/${session.id}/attendance`);
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Session Modal */}
      <SessionModal
        isOpen={showModal}
        onClose={handleCloseModal}
        onSave={handleSaveSession}
        session={selectedSession}
        isLoading={isModalLoading}
      />
    </div>
  );
};

export default InstructorSessions;