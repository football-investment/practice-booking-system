import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const SessionManagement = () => {
  const { logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSession, setEditingSession] = useState(null);
  const [deletingSession, setDeletingSession] = useState(null);
  const [sessionForm, setSessionForm] = useState({
    title: '',
    description: '',
    date_start: '',
    date_end: '',
    location: '',
    capacity: 20,
    mode: 'offline',
    requirements: '',
    notes: '',
    is_active: true,
    semester_id: 18, // Default to active Fall 2025 semester
    group_id: null,
    instructor_id: null,
    meeting_link: ''
  });

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const response = await apiService.getSessions();
      console.log('Raw API response:', response);
      
      // Extract sessions array from API response object
      const sessionsData = response?.sessions || response || [];
      
      setSessions(sessionsData);
      console.log('Sessions loaded for admin:', sessionsData.length, 'Total:', response?.total || 0);
      
      if (response?.total) {
        console.log(`Showing ${sessionsData.length} of ${response.total} sessions`);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError('Failed to load sessions: ' + (err.message || 'Unknown error'));
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    // Enhanced validation
    const validationErrors = [];
    
    if (!sessionForm.title?.trim()) {
      validationErrors.push('Title is required');
    }
    
    if (!sessionForm.date_start) {
      validationErrors.push('Start date/time is required');
    }
    
    if (!sessionForm.date_end) {
      validationErrors.push('End date/time is required');
    }
    
    if (sessionForm.capacity < 1) {
      validationErrors.push('Capacity must be at least 1');
    }
    
    if (!sessionForm.mode) {
      validationErrors.push('Session mode is required');
    }
    
    if (new Date(sessionForm.date_start) >= new Date(sessionForm.date_end)) {
      validationErrors.push('End time must be after start time');
    }
    
    if (validationErrors.length > 0) {
      setError('Validation failed: ' + validationErrors.join(', '));
      return;
    }
    
    try {
      console.log('Session creation payload:', sessionForm);
      
      // Prepare payload for API (convert datetime-local to ISO format)
      const payload = {
        ...sessionForm,
        date_start: new Date(sessionForm.date_start).toISOString(),
        date_end: new Date(sessionForm.date_end).toISOString(),
        // Ensure required fields are properly set
        title: sessionForm.title.trim(),
        description: sessionForm.description?.trim() || '',
        location: sessionForm.location?.trim() || null,
        requirements: sessionForm.requirements?.trim() || null,
        notes: sessionForm.notes?.trim() || null
      };
      
      console.log('Calling createSession API with payload:', payload);
      const result = await apiService.createSession(payload);
      console.log('Session creation result:', result);
      
      setSuccess('Session created successfully!');
      setShowCreateModal(false);
      resetForm();
      loadSessions();
    } catch (err) {
      console.error('Session creation failed:', err);
      console.error('Error details:', err.response?.data);
      setError('Session creation failed: ' + (err.message || 'Unknown error'));
    }
  };

  const handleUpdateSession = async (e) => {
    e.preventDefault();
    if (!editingSession) return;
    
    setError('');
    setSuccess('');
    
    // Validate dates
    if (new Date(sessionForm.date_start) >= new Date(sessionForm.date_end)) {
      setError('End time must be after start time');
      return;
    }
    
    try {
      await apiService.updateSession(editingSession.id, sessionForm);
      setSuccess('Session updated successfully!');
      setEditingSession(null);
      resetForm();
      loadSessions();
    } catch (err) {
      console.error('Session update failed:', err);
      setError(`Failed to update session: ${err.message}`);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm('Are you sure you want to delete this session? All associated bookings will be cancelled.')) {
      return;
    }
    
    setDeletingSession(sessionId);
    try {
      await apiService.deleteSession(sessionId);
      setSuccess('Session deleted successfully');
      loadSessions();
    } catch (err) {
      console.error('Session deletion failed:', err);
      setError(`Failed to delete session: ${err.message}`);
    } finally {
      setDeletingSession(null);
    }
  };

  const resetForm = () => {
    setSessionForm({
      title: '',
      description: '',
      date_start: '',
      date_end: '',
      location: '',
      capacity: 20,
      mode: 'offline',
      requirements: '',
      notes: '',
      is_active: true,
      semester_id: 18, // Default to active Fall 2025 semester
      group_id: null,
      instructor_id: null,
      meeting_link: ''
    });
  };

  const openEditModal = (session) => {
    setEditingSession(session);
    setSessionForm({
      title: session.title || '',
      description: session.description || '',
      date_start: session.date_start ? new Date(session.date_start).toISOString().slice(0, 16) : '',
      date_end: session.date_end ? new Date(session.date_end).toISOString().slice(0, 16) : '',
      location: session.location || '',
      capacity: session.capacity || 20,
      mode: session.mode || 'offline',
      requirements: session.requirements || '',
      notes: session.notes || '',
      is_active: session.is_active !== false
    });
  };

  const closeModal = () => {
    setShowCreateModal(false);
    setEditingSession(null);
    resetForm();
    setError('');
  };

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = 
      session.title?.toLowerCase().includes(search.toLowerCase()) ||
      session.description?.toLowerCase().includes(search.toLowerCase()) ||
      session.location?.toLowerCase().includes(search.toLowerCase());
    
    let matchesStatus = true;
    const now = new Date();
    const sessionStart = new Date(session.date_start);
    
    switch (statusFilter) {
      case 'upcoming':
        matchesStatus = sessionStart > now;
        break;
      case 'past':
        matchesStatus = sessionStart < now;
        break;
      case 'full':
        matchesStatus = session.is_full;
        break;
      case 'available':
        matchesStatus = !session.is_full && sessionStart > now;
        break;
    }
    
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="session-management">
      {/* Navigation */}
      <div className="admin-page-header">
        <div>
          <Link to="/admin/dashboard" className="back-link">← Admin Dashboard</Link>
          <h1>Session Management</h1>
        </div>
        <div className="header-actions">
          <button 
            onClick={() => setShowCreateModal(true)}
            className="create-btn primary"
          >
            ➕ Create Session
          </button>
          <button onClick={() => logout()} className="logout-btn">Logout</button>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Filters */}
      <div className="session-filters">
        <div className="search-section">
          <input
            type="text"
            placeholder="Search sessions by title, description, or location..."
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
            <option value="all">All Sessions ({sessions.length})</option>
            <option value="upcoming">Upcoming</option>
            <option value="past">Past</option>
            <option value="available">Available</option>
            <option value="full">Full</option>
          </select>
        </div>
      </div>

      {/* Sessions Table */}
      <div className="sessions-table-container">
        {loading ? (
          <div className="table-loading">Loading sessions...</div>
        ) : filteredSessions.length === 0 ? (
          <div className="table-empty">
            <h3>No sessions found</h3>
            <p>Try adjusting your search or filters</p>
          </div>
        ) : (
          <table className="sessions-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Date & Time</th>
                <th>Location</th>
                <th>Capacity</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.map(session => (
                <tr key={session.id}>
                  <td className="session-info">
                    <div className="session-title">{session.title || `Session ${session.id}`}</div>
                    {session.description && (
                      <div className="session-desc">{session.description.substring(0, 50)}...</div>
                    )}
                    <div className="session-mode">{session.mode?.toUpperCase()}</div>
                  </td>
                  <td className="session-datetime">
                    <div>{new Date(session.date_start).toLocaleDateString()}</div>
                    <div className="time-range">
                      {new Date(session.date_start).toLocaleTimeString()} - 
                      {new Date(session.date_end).toLocaleTimeString()}
                    </div>
                  </td>
                  <td>{session.location || 'TBD'}</td>
                  <td>
                    <div className="capacity-info">
                      {session.current_bookings || 0}/{session.capacity}
                      <div className="capacity-bar">
                        <div 
                          className="capacity-fill"
                          style={{width: `${((session.current_bookings || 0) / session.capacity) * 100}%`}}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="status-badges">
                      <span className={`status-badge ${session.is_full ? 'full' : 'available'}`}>
                        {session.is_full ? 'FULL' : 'AVAILABLE'}
                      </span>
                      {new Date(session.date_start) < new Date() && (
                        <span className="status-badge past">COMPLETED</span>
                      )}
                    </div>
                  </td>
                  <td className="table-actions">
                    <button
                      onClick={() => openEditModal(session)}
                      className="edit-btn"
                      title="Edit Session"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDeleteSession(session.id)}
                      disabled={deletingSession === session.id}
                      className="delete-btn"
                      title="Delete Session"
                    >
                      {deletingSession === session.id ? '⏳' : '🗑️'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create/Edit Session Modal */}
      {(showCreateModal || editingSession) && (
        <div className="modal-overlay">
          <div className="modal-content large">
            <div className="modal-header">
              <h3>{editingSession ? 'Edit Session' : 'Create New Session'}</h3>
              <button onClick={closeModal} className="close-btn">✕</button>
            </div>
            
            <form onSubmit={editingSession ? handleUpdateSession : handleCreateSession}>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label>Session Title *</label>
                  <input
                    type="text"
                    value={sessionForm.title}
                    onChange={(e) => setSessionForm({...sessionForm, title: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group full-width">
                  <label>Description</label>
                  <textarea
                    value={sessionForm.description}
                    onChange={(e) => setSessionForm({...sessionForm, description: e.target.value})}
                    className="form-textarea"
                    rows="3"
                  />
                </div>

                <div className="form-group">
                  <label>Start Date & Time *</label>
                  <input
                    type="datetime-local"
                    value={sessionForm.date_start}
                    onChange={(e) => setSessionForm({...sessionForm, date_start: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>End Date & Time *</label>
                  <input
                    type="datetime-local"
                    value={sessionForm.date_end}
                    onChange={(e) => setSessionForm({...sessionForm, date_end: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Location</label>
                  <input
                    type="text"
                    value={sessionForm.location}
                    onChange={(e) => setSessionForm({...sessionForm, location: e.target.value})}
                    className="form-input"
                    placeholder="e.g. Gym A, Field 1"
                  />
                </div>

                <div className="form-group">
                  <label>Capacity *</label>
                  <input
                    type="number"
                    value={sessionForm.capacity}
                    onChange={(e) => setSessionForm({...sessionForm, capacity: parseInt(e.target.value)})}
                    className="form-input"
                    min="1"
                    max="100"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Mode *</label>
                  <select
                    value={sessionForm.mode}
                    onChange={(e) => setSessionForm({...sessionForm, mode: e.target.value})}
                    className="form-select"
                    required
                  >
                    <option value="offline">Offline</option>
                    <option value="online">Online</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>

                <div className="form-group full-width">
                  <label>Requirements</label>
                  <textarea
                    value={sessionForm.requirements}
                    onChange={(e) => setSessionForm({...sessionForm, requirements: e.target.value})}
                    className="form-textarea"
                    rows="2"
                    placeholder="Equipment needed, skill level, etc."
                  />
                </div>

                <div className="form-group full-width">
                  <label>Notes (Internal)</label>
                  <textarea
                    value={sessionForm.notes}
                    onChange={(e) => setSessionForm({...sessionForm, notes: e.target.value})}
                    className="form-textarea"
                    rows="2"
                    placeholder="Internal notes for staff"
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={sessionForm.is_active}
                      onChange={(e) => setSessionForm({...sessionForm, is_active: e.target.checked})}
                    />
                    Active Session
                  </label>
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" onClick={closeModal} className="cancel-btn">
                  Cancel
                </button>
                <button type="submit" className="save-btn">
                  {editingSession ? 'Update Session' : 'Create Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionManagement;