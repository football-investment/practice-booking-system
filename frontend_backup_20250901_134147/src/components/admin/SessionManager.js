import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './SessionManager.css';

const SessionManager = () => {
  const [sessions, setSessions] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [groups, setGroups] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Modal states
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [showBookingModal, setShowBookingModal] = useState(false);
  const [editingSession, setEditingSession] = useState(null);
  const [selectedSessionForBookings, setSelectedSessionForBookings] = useState(null);
  
  // Filters
  const [filters, setFilters] = useState({
    semester_id: '',
    status: '',
    mode: '',
    search: '',
    date_from: '',
    date_to: ''
  });
  
  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    session_date: '',
    start_time: '',
    end_time: '',
    semester_id: '',
    group_id: '',
    instructor_id: '',
    max_participants: 10,
    mode: 'online',
    location: '',
    meeting_link: '',
    meeting_password: '',
    status: 'scheduled',
    is_active: true
  });

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadSessions();
  }, [filters]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [semestersData, instructorsData] = await Promise.all([
        apiService.getSemesters(),
        apiService.getUsersByRole('instructor')
      ]);
      
      
      setSemesters(semestersData || []);
      setInstructors(instructorsData || []);
      
      await loadSessions();
    } catch (err) {
      console.error('Error loading initial data:', err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadSessions = async () => {
    try {
      const data = await apiService.getSessionsWithFilters(filters);
      setSessions(data || []);
    } catch (err) {
      console.error('Error loading sessions:', err);
      setError('Failed to load sessions');
    }
  };

  const loadGroupsForSemester = async (semesterId) => {
    if (!semesterId) {
      setGroups([]);
      return;
    }
    
    try {
      const data = await apiService.getGroups(semesterId);
      setGroups(data || []);
    } catch (err) {
      console.error('Error loading groups:', err);
      setGroups([]);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleFormChange = (key, value) => {
    setFormData(prev => {
      const newData = { ...prev, [key]: value };
      
      // Load groups when semester changes
      if (key === 'semester_id') {
        loadGroupsForSemester(value);
        newData.group_id = ''; // Reset group selection
      }
      
      return newData;
    });
  };

  const validateForm = () => {
    const errors = [];
    
    if (!formData.title.trim()) errors.push('Title is required');
    if (!formData.session_date) errors.push('Session date is required');
    if (!formData.start_time) errors.push('Start time is required');
    if (!formData.end_time) errors.push('End time is required');
    if (!formData.semester_id) errors.push('Semester is required');
    if (formData.max_participants < 1) errors.push('Max participants must be at least 1');
    
    // Validate time logic
    if (formData.start_time && formData.end_time && formData.start_time >= formData.end_time) {
      errors.push('End time must be after start time');
    }
    
    // Validate mode-specific fields
    if (formData.mode === 'offline' && !formData.location.trim()) {
      errors.push('Location is required for offline sessions');
    }
    if (formData.mode === 'online' && !formData.meeting_link.trim()) {
      errors.push('Meeting link is required for online sessions');
    }
    
    // Validate future date
    const sessionDateTime = new Date(`${formData.session_date}T${formData.start_time}`);
    if (sessionDateTime <= new Date()) {
      errors.push('Session must be scheduled in the future');
    }
    
    if (errors.length > 0) {
      alert(errors.join('\n'));
      return false;
    }
    
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    try {
      // Convert frontend format to backend API format
      const sessionData = {
        title: formData.title,
        description: formData.description || null,
        date_start: `${formData.session_date}T${formData.start_time}:00`,
        date_end: `${formData.session_date}T${formData.end_time}:00`,
        mode: formData.mode,
        capacity: formData.max_participants,
        location: formData.mode === 'offline' ? formData.location : null,
        meeting_link: formData.mode === 'online' ? formData.meeting_link : null,
        semester_id: parseInt(formData.semester_id),
        group_id: formData.group_id ? parseInt(formData.group_id) : null,
        instructor_id: formData.instructor_id ? parseInt(formData.instructor_id) : null
      };
      
      if (editingSession) {
        await apiService.updateSession(editingSession.id, sessionData);
      } else {
        await apiService.createSession(sessionData);
      }
      
      await loadSessions();
      closeSessionModal();
    } catch (err) {
      console.error('Error saving session:', err);
      alert('Failed to save session');
    }
  };

  const handleEdit = (session) => {
    setEditingSession(session);
    
    // Load groups for the session's semester
    if (session.semester_id) {
      loadGroupsForSemester(session.semester_id);
    }
    
    setFormData({
      title: session.title || '',
      description: session.description || '',
      session_date: session.session_date?.split('T')[0] || '',
      start_time: session.start_time || '',
      end_time: session.end_time || '',
      semester_id: session.semester_id || '',
      group_id: session.group_id || '',
      instructor_id: session.instructor_id || '',
      max_participants: session.max_participants || 10,
      mode: session.mode || 'online',
      location: session.location || '',
      meeting_link: session.meeting_link || '',
      meeting_password: session.meeting_password || '',
      status: session.status || 'scheduled',
      is_active: session.is_active !== false
    });
    
    setShowSessionModal(true);
  };

  const handleDelete = async (sessionId) => {
    if (!window.confirm('Are you sure you want to delete this session?')) return;
    
    try {
      await apiService.deleteSession(sessionId);
      await loadSessions();
    } catch (err) {
      console.error('Error deleting session:', err);
      alert('Failed to delete session');
    }
  };

  const openCreateModal = () => {
    setEditingSession(null);
    setFormData({
      title: '',
      description: '',
      session_date: '',
      start_time: '',
      end_time: '',
      semester_id: '',
      group_id: '',
      instructor_id: '',
      max_participants: 10,
      mode: 'online',
      location: '',
      meeting_link: '',
      meeting_password: '',
      status: 'scheduled',
      is_active: true
    });
    setGroups([]);
    setShowSessionModal(true);
  };

  const closeSessionModal = () => {
    setShowSessionModal(false);
    setEditingSession(null);
  };

  const viewBookings = (session) => {
    setSelectedSessionForBookings(session);
    setShowBookingModal(true);
  };

  const formatDateTime = (date, time) => {
    if (!date || !time) return 'N/A';
    return new Date(`${date}T${time}`).toLocaleString();
  };

  const calculateDuration = (startTime, endTime) => {
    if (!startTime || !endTime) return 'N/A';
    
    const start = new Date(`2000-01-01T${startTime}`);
    const end = new Date(`2000-01-01T${endTime}`);
    const diffMs = end - start;
    const diffMins = Math.floor(diffMs / 60000);
    const hours = Math.floor(diffMins / 60);
    const minutes = diffMins % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'scheduled': return 'status-scheduled';
      case 'cancelled': return 'status-cancelled';
      case 'completed': return 'status-completed';
      default: return 'status-unknown';
    }
  };

  const getSemesterName = (semesterId) => {
    const semester = semesters.find(s => s.id === semesterId);
    return semester ? semester.name : 'N/A';
  };

  const getGroupName = (groupId) => {
    if (!groupId) return 'No Group';
    const group = groups.find(g => g.id === groupId);
    return group ? group.name : 'Unknown Group';
  };

  const getInstructorName = (instructorId) => {
    if (!instructorId) return 'No Instructor';
    const instructor = instructors.find(i => i.id === instructorId);
    return instructor ? instructor.name : 'Unknown Instructor';
  };

  if (loading) return <div className="loading">Loading sessions...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="session-manager">
      <div className="session-header">
        <h2>Session Management</h2>
        <button className="btn btn-primary" onClick={openCreateModal}>
          Create New Session
        </button>
      </div>

      <div className="session-filters">
        <div className="filter-row">
          <select 
            value={filters.semester_id} 
            onChange={(e) => handleFilterChange('semester_id', e.target.value)}
          >
            <option value="">All Semesters</option>
            {semesters.map(semester => (
              <option key={semester.id} value={semester.id}>
                {semester.name}
              </option>
            ))}
          </select>

          <select 
            value={filters.status} 
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="scheduled">Scheduled</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>

          <select 
            value={filters.mode} 
            onChange={(e) => handleFilterChange('mode', e.target.value)}
          >
            <option value="">All Modes</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>

          <input
            type="text"
            placeholder="Search sessions..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>

        <div className="filter-row">
          <input
            type="date"
            placeholder="From Date"
            value={filters.date_from}
            onChange={(e) => handleFilterChange('date_from', e.target.value)}
          />
          <input
            type="date"
            placeholder="To Date" 
            value={filters.date_to}
            onChange={(e) => handleFilterChange('date_to', e.target.value)}
          />
        </div>
      </div>

      <div className="session-list">
        {sessions.length === 0 ? (
          <p>No sessions found</p>
        ) : (
          <div className="session-table">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Date & Time</th>
                  <th>Duration</th>
                  <th>Mode</th>
                  <th>Location/Link</th>
                  <th>Semester</th>
                  <th>Group</th>
                  <th>Instructor</th>
                  <th>Participants</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map(session => (
                  <tr key={session.id}>
                    <td>
                      <div className="session-title">
                        {session.title}
                        {session.description && (
                          <small className="session-description">
                            {session.description}
                          </small>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="session-datetime">
                        <div>{new Date(session.session_date).toLocaleDateString()}</div>
                        <div>{session.start_time} - {session.end_time}</div>
                      </div>
                    </td>
                    <td>{calculateDuration(session.start_time, session.end_time)}</td>
                    <td>
                      <span className={`mode-badge mode-${session.mode}`}>
                        {session.mode}
                      </span>
                    </td>
                    <td>
                      {session.mode === 'online' ? (
                        <a 
                          href={session.meeting_link} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="meeting-link"
                        >
                          Join Meeting
                        </a>
                      ) : (
                        session.location
                      )}
                    </td>
                    <td>{getSemesterName(session.semester_id)}</td>
                    <td>{getGroupName(session.group_id)}</td>
                    <td>{getInstructorName(session.instructor_id)}</td>
                    <td>
                      <div className="participants-info">
                        <span>{session.current_participants || 0}/{session.max_participants}</span>
                        {(session.current_participants || 0) >= session.max_participants && (
                          <span className="full-indicator">FULL</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`status-badge ${getStatusBadgeClass(session.status)}`}>
                        {session.status}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button 
                          className="btn btn-sm btn-secondary"
                          onClick={() => handleEdit(session)}
                        >
                          Edit
                        </button>
                        <button 
                          className="btn btn-sm btn-info"
                          onClick={() => viewBookings(session)}
                        >
                          Bookings
                        </button>
                        <button 
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(session.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Session Modal */}
      {showSessionModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>{editingSession ? 'Edit Session' : 'Create New Session'}</h3>
              <button className="modal-close" onClick={closeSessionModal}>×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-row">
                <div className="form-group">
                  <label>Title *</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => handleFormChange('title', e.target.value)}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Semester *</label>
                  <select
                    value={formData.semester_id}
                    onChange={(e) => handleFormChange('semester_id', e.target.value)}
                    required
                  >
                    <option value="">Select Semester</option>
                    {semesters.map(semester => (
                      <option key={semester.id} value={semester.id}>
                        {semester.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleFormChange('description', e.target.value)}
                  rows={3}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Session Date *</label>
                  <input
                    type="date"
                    value={formData.session_date}
                    onChange={(e) => handleFormChange('session_date', e.target.value)}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Start Time *</label>
                  <input
                    type="time"
                    value={formData.start_time}
                    onChange={(e) => handleFormChange('start_time', e.target.value)}
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>End Time *</label>
                  <input
                    type="time"
                    value={formData.end_time}
                    onChange={(e) => handleFormChange('end_time', e.target.value)}
                    required
                  />
                </div>
              </div>

              {formData.start_time && formData.end_time && (
                <div className="duration-display">
                  Duration: {calculateDuration(formData.start_time, formData.end_time)}
                </div>
              )}

              <div className="form-row">
                <div className="form-group">
                  <label>Group</label>
                  <select
                    value={formData.group_id}
                    onChange={(e) => handleFormChange('group_id', e.target.value)}
                  >
                    <option value="">No specific group</option>
                    {groups.map(group => (
                      <option key={group.id} value={group.id}>
                        {group.name}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Instructor</label>
                  <select
                    value={formData.instructor_id}
                    onChange={(e) => handleFormChange('instructor_id', e.target.value)}
                  >
                    <option value="">No instructor assigned</option>
                    {instructors.map(instructor => (
                      <option key={instructor.id} value={instructor.id}>
                        {instructor.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Max Participants *</label>
                  <input
                    type="number"
                    value={formData.max_participants}
                    onChange={(e) => handleFormChange('max_participants', parseInt(e.target.value))}
                    min="1"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>Mode *</label>
                  <select
                    value={formData.mode}
                    onChange={(e) => handleFormChange('mode', e.target.value)}
                    required
                  >
                    <option value="online">Online</option>
                    <option value="offline">Offline</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label>Status *</label>
                  <select
                    value={formData.status}
                    onChange={(e) => handleFormChange('status', e.target.value)}
                    required
                  >
                    <option value="scheduled">Scheduled</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              </div>

              {/* Conditional fields based on mode */}
              {formData.mode === 'online' ? (
                <div className="form-row">
                  <div className="form-group">
                    <label>Meeting Link *</label>
                    <input
                      type="url"
                      value={formData.meeting_link}
                      onChange={(e) => handleFormChange('meeting_link', e.target.value)}
                      placeholder="https://zoom.us/j/..."
                      required
                    />
                  </div>
                  
                  <div className="form-group">
                    <label>Meeting Password</label>
                    <input
                      type="text"
                      value={formData.meeting_password}
                      onChange={(e) => handleFormChange('meeting_password', e.target.value)}
                    />
                  </div>
                </div>
              ) : (
                <div className="form-group">
                  <label>Location *</label>
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => handleFormChange('location', e.target.value)}
                    placeholder="Room number, address, etc."
                    required
                  />
                </div>
              )}

              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => handleFormChange('is_active', e.target.checked)}
                  />
                  Active
                </label>
              </div>
            </form>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={closeSessionModal}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" onClick={handleSubmit}>
                {editingSession ? 'Update Session' : 'Create Session'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Booking Modal */}
      {showBookingModal && selectedSessionForBookings && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Bookings for: {selectedSessionForBookings.title}</h3>
              <button className="modal-close" onClick={() => setShowBookingModal(false)}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="booking-info">
                <p><strong>Date:</strong> {new Date(selectedSessionForBookings.session_date).toLocaleDateString()}</p>
                <p><strong>Time:</strong> {selectedSessionForBookings.start_time} - {selectedSessionForBookings.end_time}</p>
                <p><strong>Participants:</strong> {selectedSessionForBookings.current_participants || 0}/{selectedSessionForBookings.max_participants}</p>
                <p><strong>Mode:</strong> {selectedSessionForBookings.mode}</p>
                {selectedSessionForBookings.mode === 'online' ? (
                  <p><strong>Meeting Link:</strong> {selectedSessionForBookings.meeting_link}</p>
                ) : (
                  <p><strong>Location:</strong> {selectedSessionForBookings.location}</p>
                )}
              </div>
              
              <div className="booking-list">
                <h4>Current Bookings</h4>
                <p><em>Booking details will be implemented in the next phase</em></p>
              </div>
            </div>
            
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowBookingModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionManager;