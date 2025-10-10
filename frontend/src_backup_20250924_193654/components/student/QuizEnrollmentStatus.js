import React, { useState, useEffect } from 'react';
import './QuizEnrollmentStatus.css';

const QuizEnrollmentStatus = ({ projectId }) => {
  const [enrollmentStatus, setEnrollmentStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (projectId) {
      fetchEnrollmentStatus();
    }
  }, [projectId]);

  const fetchEnrollmentStatus = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/api/v1/projects/${projectId}/enrollment-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setEnrollmentStatus(data);
      } else {
        setError('Failed to load enrollment status');
      }
    } catch (err) {
      setError('Error loading enrollment status');
      console.error('Error fetching enrollment status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmEnrollment = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8000/api/v1/projects/${projectId}/confirm-enrollment`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        await fetchEnrollmentStatus(); // Refresh status
        // Trigger page refresh to update project data
        window.location.reload();
      } else {
        setError('Failed to confirm enrollment');
      }
    } catch (err) {
      setError('Error confirming enrollment');
      console.error('Error confirming enrollment:', err);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'eligible': return '✅';
      case 'waiting': return '⏳';
      case 'confirmed': return '🎉';
      case 'not_eligible': return '❌';
      default: return '❓';
    }
  };

  const getStatusMessage = (status) => {
    switch (status) {
      case 'eligible':
        return 'Congratulations! You are eligible to enroll in this project.';
      case 'waiting':
        return 'You are on the waiting list. We will notify you if a spot becomes available.';
      case 'confirmed':
        return 'Your enrollment has been confirmed! Welcome to the project.';
      case 'not_eligible':
        return 'Unfortunately, you did not meet the minimum requirements for this project.';
      default:
        return 'Unknown enrollment status.';
    }
  };

  const getPriorityColor = (priority, totalApplicants) => {
    const percentage = (priority / totalApplicants) * 100;
    if (percentage <= 25) return '#10b981'; // Top 25% - green
    if (percentage <= 50) return '#f59e0b'; // Top 50% - amber
    if (percentage <= 75) return '#ef4444'; // Top 75% - red
    return '#6b7280'; // Bottom 25% - gray
  };

  if (loading) {
    return (
      <div className="quiz-enrollment-status loading">
        <div className="loading-spinner"></div>
        <p>Loading enrollment status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="quiz-enrollment-status error">
        <p>⚠️ {error}</p>
      </div>
    );
  }

  if (!enrollmentStatus) {
    return (
      <div className="quiz-enrollment-status empty">
        <p>📝 Complete the enrollment quiz to see your status.</p>
      </div>
    );
  }

  return (
    <div className="quiz-enrollment-status">
      <div className="status-header">
        <h3>
          {getStatusIcon(enrollmentStatus.user_status)} Enrollment Status
        </h3>
      </div>

      <div className="status-content">
        <div className="status-message">
          <p>{getStatusMessage(enrollmentStatus.user_status)}</p>
        </div>

        {enrollmentStatus.quiz_score !== undefined && (
          <div className="score-section">
            <div className="score-display">
              <span className="score-label">Your Quiz Score:</span>
              <span className="score-value">{enrollmentStatus.quiz_score}%</span>
            </div>
            
            {enrollmentStatus.enrollment_priority && (
              <div className="priority-display">
                <span className="priority-label">Ranking:</span>
                <span 
                  className="priority-value"
                  style={{ 
                    color: getPriorityColor(
                      enrollmentStatus.enrollment_priority, 
                      enrollmentStatus.total_applicants
                    )
                  }}
                >
                  #{enrollmentStatus.enrollment_priority} of {enrollmentStatus.total_applicants}
                </span>
              </div>
            )}
          </div>
        )}

        {enrollmentStatus.can_confirm && !enrollmentStatus.enrollment_confirmed && (
          <div className="action-section">
            <p className="confirm-prompt">
              🎯 You have been selected for this project! 
              Please confirm your enrollment to secure your spot.
            </p>
            <button 
              onClick={handleConfirmEnrollment}
              className="confirm-btn"
            >
              ✅ Confirm Enrollment
            </button>
          </div>
        )}

        {enrollmentStatus.enrollment_confirmed && (
          <div className="confirmed-section">
            <div className="confirmed-badge">
              🎉 Enrollment Confirmed
            </div>
            <p>Welcome to the project! Check your dashboard for next steps.</p>
          </div>
        )}

        {enrollmentStatus.user_status === 'waiting' && (
          <div className="waiting-section">
            <p className="waiting-message">
              ⏳ You are on the waiting list. If other students decline their spots, 
              you may be offered enrollment based on your ranking.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuizEnrollmentStatus;