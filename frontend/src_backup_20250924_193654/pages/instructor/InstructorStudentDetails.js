import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './InstructorStudentDetails.css';

const InstructorStudentDetails = () => {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [student, setStudent] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadStudentDetails();
  }, [studentId]);

  const loadStudentDetails = async () => {
    try {
      setLoading(true);
      const response = await apiService.getInstructorStudentDetails(studentId);
      setStudent(response);
    } catch (err) {
      console.error('Failed to load student details:', err);
      setError('Failed to load student details: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status) => {
    const colors = {
      'active': '#10b981',
      'completed': '#3b82f6',
      'cancelled': '#ef4444',
      'pending': '#f59e0b',
      'confirmed': '#10b981',
      'present': '#10b981',
      'absent': '#ef4444'
    };
    return colors[status] || '#6b7280';
  };

  const getStatusIcon = (status) => {
    const icons = {
      'active': '🟢',
      'completed': '✅',
      'cancelled': '❌',
      'pending': '⏳',
      'confirmed': '✅',
      'present': '✅',
      'absent': '❌'
    };
    return icons[status] || '⚪';
  };

  if (loading) {
    return (
      <div className="instructor-student-details">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading student details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="instructor-student-details">
        <div className="error-state">
          <h2>❌ Error</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/instructor/students')} className="btn-primary">
            ← Back to Students
          </button>
        </div>
      </div>
    );
  }

  if (!student) {
    return (
      <div className="instructor-student-details">
        <div className="error-state">
          <h2>👤 Student Not Found</h2>
          <p>The requested student could not be found.</p>
          <button onClick={() => navigate('/instructor/students')} className="btn-primary">
            ← Back to Students
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-student-details">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/students')} className="back-btn">
            ← Students
          </button>
          <h1>👤 {student.name}</h1>
          <p>Detailed student information and activity</p>
        </div>
        <div className="header-actions">
          <Link 
            to={`/instructor/students/${studentId}/progress`} 
            className="btn-primary"
          >
            📊 View Progress
          </Link>
        </div>
      </div>

      {/* Student Info */}
      <div className="student-info-section">
        <div className="info-card">
          <h2>Student Information</h2>
          <div className="info-grid">
            <div className="info-item">
              <label>Name</label>
              <span>{student.name}</span>
            </div>
            <div className="info-item">
              <label>Email</label>
              <span>{student.email}</span>
            </div>
            <div className="info-item">
              <label>Status</label>
              <span className={`status-badge ${student.is_active ? 'active' : 'inactive'}`}>
                {student.is_active ? '🟢 Active' : '🔴 Inactive'}
              </span>
            </div>
            <div className="info-item">
              <label>Member Since</label>
              <span>{formatDate(student.created_at)}</span>
            </div>
          </div>
        </div>

        {/* Statistics */}
        <div className="stats-card">
          <h3>Quick Statistics</h3>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-number">{student.stats.total_enrollments}</span>
              <span className="stat-label">Total Enrollments</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{student.stats.active_enrollments}</span>
              <span className="stat-label">Active Enrollments</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{student.stats.total_bookings}</span>
              <span className="stat-label">Session Bookings</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{student.stats.present_sessions}</span>
              <span className="stat-label">Sessions Attended</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{student.stats.feedback_given}</span>
              <span className="stat-label">Feedback Given</span>
            </div>
          </div>
        </div>
      </div>

      {/* Project Enrollments */}
      <div className="section">
        <div className="section-header">
          <h2>📚 Project Enrollments</h2>
          <span className="count-badge">{student.enrollments.length}</span>
        </div>
        
        {student.enrollments.length === 0 ? (
          <div className="empty-state">
            <p>📚 No project enrollments found.</p>
          </div>
        ) : (
          <div className="enrollments-list">
            {student.enrollments.map(enrollment => (
              <div key={enrollment.id} className="enrollment-card">
                <div className="enrollment-header">
                  <h3>{enrollment.project.title}</h3>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(enrollment.status) }}
                  >
                    {getStatusIcon(enrollment.status)} {enrollment.status}
                  </span>
                </div>
                <p className="enrollment-description">{enrollment.project.description}</p>
                <div className="enrollment-meta">
                  <span>📅 Enrolled: {formatDate(enrollment.enrolled_at)}</span>
                  <span>📊 Progress: {enrollment.project.completion_percentage}%</span>
                </div>
                {enrollment.project.completion_percentage > 0 && (
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${enrollment.project.completion_percentage}%` }}
                    ></div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Session Bookings */}
      <div className="section">
        <div className="section-header">
          <h2>📅 Session Bookings</h2>
          <span className="count-badge">{student.bookings.length}</span>
        </div>
        
        {student.bookings.length === 0 ? (
          <div className="empty-state">
            <p>📅 No session bookings found.</p>
          </div>
        ) : (
          <div className="bookings-list">
            {student.bookings.map(booking => (
              <div key={booking.id} className="booking-card">
                <div className="booking-header">
                  <h4>{booking.session.title}</h4>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(booking.status) }}
                  >
                    {getStatusIcon(booking.status)} {booking.status}
                  </span>
                </div>
                <div className="booking-details">
                  <span>📅 {formatDateTime(booking.session.date_start)} - {new Date(booking.session.date_end).toLocaleTimeString()}</span>
                  <span>📍 {booking.session.location}</span>
                  <span>🎟️ Booked: {formatDateTime(booking.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Attendance Records */}
      <div className="section">
        <div className="section-header">
          <h2>✅ Attendance Records</h2>
          <span className="count-badge">{student.attendance.length}</span>
        </div>
        
        {student.attendance.length === 0 ? (
          <div className="empty-state">
            <p>✅ No attendance records found.</p>
          </div>
        ) : (
          <div className="attendance-list">
            {student.attendance.map(record => (
              <div key={record.id} className="attendance-card">
                <div className="attendance-header">
                  <h4>{record.session.title}</h4>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(record.status) }}
                  >
                    {getStatusIcon(record.status)} {record.status}
                  </span>
                </div>
                <div className="attendance-details">
                  <span>📅 {formatDateTime(record.session.date_start)}</span>
                  {record.checked_in_at && (
                    <span>✅ Checked in: {formatDateTime(record.checked_in_at)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Feedback Given */}
      <div className="section">
        <div className="section-header">
          <h2>💬 Feedback Given</h2>
          <span className="count-badge">{student.feedback.length}</span>
        </div>
        
        {student.feedback.length === 0 ? (
          <div className="empty-state">
            <p>💬 No feedback given yet.</p>
          </div>
        ) : (
          <div className="feedback-list">
            {student.feedback.map(feedback => (
              <div key={feedback.id} className="feedback-card">
                <div className="feedback-header">
                  <h4>{feedback.session.title}</h4>
                  <div className="rating">
                    {'⭐'.repeat(feedback.rating)}
                    <span className="rating-number">({feedback.rating}/5)</span>
                  </div>
                </div>
                <div className="feedback-content">
                  <p>"{feedback.comment}"</p>
                  <div className="feedback-meta">
                    <span>📅 {formatDateTime(feedback.session.date_start)}</span>
                    <span>💬 Given: {formatDateTime(feedback.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default InstructorStudentDetails;