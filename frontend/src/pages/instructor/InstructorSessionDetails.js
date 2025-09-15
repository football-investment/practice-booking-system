import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import SessionModal from '../../components/instructor/SessionModal';
import './InstructorSessionDetails.css';

const InstructorSessionDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [notes, setNotes] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Modal states
  const [showEditModal, setShowEditModal] = useState(false);
  const [isModalLoading, setIsModalLoading] = useState(false);
  
  // Notes states
  const [newNote, setNewNote] = useState('');
  const [isAddingNote, setIsAddingNote] = useState(false);
  
  // Attendance states
  const [attendanceMap, setAttendanceMap] = useState({});
  const [isUpdatingAttendance, setIsUpdatingAttendance] = useState(false);

  useEffect(() => {
    if (id) {
      loadSessionDetails();
    }
  }, [id]);

  const loadSessionDetails = async () => {
    try {
      setLoading(true);
      setError('');

      // Load session details
      const sessionResponse = await apiService.getSessionDetails(id);
      setSession(sessionResponse);

      // Load bookings
      const bookingsResponse = await apiService.getSessionBookings(id).catch(() => ({ bookings: [] }));
      const bookingsData = Array.isArray(bookingsResponse) ? bookingsResponse : (bookingsResponse?.bookings || []);
      setBookings(bookingsData);

      // Load attendance
      const attendanceResponse = await apiService.getSessionAttendance(id).catch(() => ({ attendance: [] }));
      const attendanceData = Array.isArray(attendanceResponse) ? attendanceResponse : (attendanceResponse?.attendance || []);
      setAttendance(attendanceData);

      // Load notes
      const notesResponse = await apiService.getSessionNotes(id).catch(() => ({ notes: [] }));
      const notesData = Array.isArray(notesResponse) ? notesResponse : (notesResponse?.notes || []);
      setNotes(notesData);

      // Create attendance map for easy lookup
      const attendanceMapData = {};
      attendanceData.forEach(record => {
        attendanceMapData[record.user_id] = record.attended;
      });
      setAttendanceMap(attendanceMapData);

      console.log('Session details loaded:', { 
        session: sessionResponse,
        bookings: bookingsData.length, 
        attendance: attendanceData.length,
        notes: notesData.length
      });

    } catch (err) {
      console.error('Failed to load session details:', err);
      setError('Failed to load session details: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const handleEditSession = () => {
    setShowEditModal(true);
  };

  const handleSaveSession = async (sessionData) => {
    try {
      setIsModalLoading(true);
      await apiService.updateSession(id, sessionData);
      setShowEditModal(false);
      setSuccess('Session updated successfully!');
      await loadSessionDetails(); // Refresh data
    } catch (err) {
      console.error('Failed to update session:', err);
      setError('Failed to update session: ' + (err.message || 'Unknown error'));
    } finally {
      setIsModalLoading(false);
    }
  };

  const handleDeleteSession = async () => {
    if (!window.confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
      return;
    }

    try {
      await apiService.deleteSession(id);
      navigate('/instructor/sessions');
    } catch (err) {
      console.error('Failed to delete session:', err);
      setError('Failed to delete session: ' + (err.message || 'Unknown error'));
    }
  };

  const handleAddNote = async () => {
    if (!newNote.trim()) return;

    try {
      setIsAddingNote(true);
      await apiService.addSessionNote(id, newNote.trim());
      setNewNote('');
      setSuccess('Note added successfully!');
      await loadSessionDetails(); // Refresh notes
    } catch (err) {
      console.error('Failed to add note:', err);
      setError('Failed to add note: ' + (err.message || 'Unknown error'));
    } finally {
      setIsAddingNote(false);
    }
  };

  const handleAttendanceChange = async (userId, attended) => {
    try {
      setIsUpdatingAttendance(true);
      await apiService.markAttendance(id, userId, attended);
      
      // Update local state
      setAttendanceMap(prev => ({
        ...prev,
        [userId]: attended
      }));

      setSuccess('Attendance updated successfully!');
    } catch (err) {
      console.error('Failed to update attendance:', err);
      setError('Failed to update attendance: ' + (err.message || 'Unknown error'));
    } finally {
      setIsUpdatingAttendance(false);
    }
  };

  const getSessionStatus = () => {
    if (!session) return { label: 'Unknown', class: 'unknown', icon: '❓' };
    
    const now = new Date();
    const sessionStart = new Date(session.date_start);
    const sessionEnd = new Date(session.date_end);
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const sessionDateOnly = new Date(sessionStart.getFullYear(), sessionStart.getMonth(), sessionStart.getDate());

    if (sessionDateOnly.getTime() === today.getTime()) {
      if (sessionStart <= now && sessionEnd >= now) {
        return { label: 'LIVE NOW', class: 'live', icon: '🔴' };
      } else if (sessionStart > now) {
        return { label: 'Today', class: 'today', icon: '📅' };
      } else {
        return { label: 'Completed Today', class: 'completed', icon: '✅' };
      }
    } else if (sessionStart > now) {
      return { label: 'Upcoming', class: 'upcoming', icon: '🔜' };
    } else {
      return { label: 'Completed', class: 'completed', icon: '✅' };
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return {
      date: date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }),
      time: date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
      })
    };
  };

  const calculateDuration = () => {
    if (!session) return 0;
    const start = new Date(session.date_start);
    const end = new Date(session.date_end);
    return Math.round((end - start) / (1000 * 60)); // minutes
  };

  if (loading) {
    return (
      <div className="session-details">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading session details...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="session-details">
        <div className="error-state">
          <h2>Session Not Found</h2>
          <p>The requested session could not be found.</p>
          <button onClick={() => navigate('/instructor/sessions')} className="btn-primary">
            ← Back to Sessions
          </button>
        </div>
      </div>
    );
  }

  const statusInfo = getSessionStatus();
  const dateInfo = formatDate(session.date_start);
  const duration = calculateDuration();
  const attendanceRate = bookings.length > 0 
    ? Math.round((Object.values(attendanceMap).filter(Boolean).length / bookings.length) * 100)
    : 0;

  return (
    <div className="session-details">
      {/* Header */}
      <div className="session-header">
        <div className="header-content">
          <button onClick={() => navigate('/instructor/sessions')} className="back-btn">
            ← Back to Sessions
          </button>
          
          <div className="session-title-section">
            <div className="title-row">
              <h1>{session.title}</h1>
              <span className={`status-badge ${statusInfo.class}`}>
                {statusInfo.icon} {statusInfo.label}
              </span>
            </div>
            <div className="session-meta">
              <span>📅 {dateInfo.date}</span>
              <span>🕐 {dateInfo.time}</span>
              <span>⏱️ {duration} minutes</span>
              <span>📍 {session.location}</span>
            </div>
          </div>
        </div>

        <div className="header-actions">
          <button onClick={handleEditSession} className="btn-secondary">
            ✏️ Edit
          </button>
          <button onClick={handleDeleteSession} className="btn-danger">
            🗑️ Delete
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {success && (
        <div className="success-banner">✅ {success}</div>
      )}

      {/* Session Info Grid */}
      <div className="session-info-grid">
        {/* Session Details */}
        <div className="info-card">
          <h2>📋 Session Information</h2>
          <div className="info-content">
            <div className="info-row">
              <span className="label">Description:</span>
              <span className="value">{session.description || 'No description provided'}</span>
            </div>
            <div className="info-row">
              <span className="label">Sport Type:</span>
              <span className="value">{session.sport_type}</span>
            </div>
            <div className="info-row">
              <span className="label">Level:</span>
              <span className="value">{session.level}</span>
            </div>
            <div className="info-row">
              <span className="label">Capacity:</span>
              <span className="value">{session.current_bookings || 0}/{session.capacity}</span>
            </div>
            <div className="info-row">
              <span className="label">Duration:</span>
              <span className="value">{duration} minutes</span>
            </div>
          </div>
        </div>

        {/* Statistics */}
        <div className="info-card">
          <h2>📊 Statistics</h2>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-number">{bookings.length}</span>
              <span className="stat-label">Enrolled</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{Object.values(attendanceMap).filter(Boolean).length}</span>
              <span className="stat-label">Attended</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{attendanceRate}%</span>
              <span className="stat-label">Attendance Rate</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{notes.length}</span>
              <span className="stat-label">Notes</span>
            </div>
          </div>
        </div>
      </div>

      {/* Students and Attendance */}
      {bookings.length > 0 && (
        <div className="attendance-section">
          <h2>👥 Students & Attendance</h2>
          <div className="attendance-table">
            <div className="table-header">
              <span>Student</span>
              <span>Email</span>
              <span>Enrollment</span>
              <span>Attendance</span>
            </div>
            {bookings.map(booking => (
              <div key={booking.id} className="table-row">
                <span className="student-name">
                  {booking.user?.name || booking.user_name || 'Unknown Student'}
                </span>
                <span className="student-email">
                  {booking.user?.email || booking.user_email || '-'}
                </span>
                <span className="enrollment-date">
                  {new Date(booking.created_at || booking.booking_date).toLocaleDateString()}
                </span>
                <div className="attendance-toggle">
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={attendanceMap[booking.user_id] || false}
                      onChange={(e) => handleAttendanceChange(booking.user_id, e.target.checked)}
                      disabled={isUpdatingAttendance}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  <span className={`attendance-status ${attendanceMap[booking.user_id] ? 'present' : 'absent'}`}>
                    {attendanceMap[booking.user_id] ? '✅ Present' : '❌ Absent'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Session Notes */}
      <div className="notes-section">
        <h2>📝 Session Notes</h2>
        
        {/* Add Note */}
        <div className="add-note">
          <textarea
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
            placeholder="Add a note about this session..."
            rows="3"
            className="note-input"
          />
          <button 
            onClick={handleAddNote}
            disabled={!newNote.trim() || isAddingNote}
            className="btn-primary"
          >
            {isAddingNote ? 'Adding...' : '📝 Add Note'}
          </button>
        </div>

        {/* Notes List */}
        {notes.length > 0 ? (
          <div className="notes-list">
            {notes.map(note => (
              <div key={note.id} className="note-item">
                <div className="note-content">{note.note}</div>
                <div className="note-meta">
                  <span>By {note.author_name || user?.name}</span>
                  <span>{new Date(note.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-notes">
            <p>📝 No notes yet. Add the first note about this session!</p>
          </div>
        )}
      </div>

      {/* Edit Session Modal */}
      <SessionModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSave={handleSaveSession}
        session={session}
        isLoading={isModalLoading}
      />
    </div>
  );
};

export default InstructorSessionDetails;