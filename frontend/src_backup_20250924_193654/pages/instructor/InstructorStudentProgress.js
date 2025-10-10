import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './InstructorStudentProgress.css';

const InstructorStudentProgress = () => {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [progressData, setProgressData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadStudentProgress();
  }, [studentId]);

  const loadStudentProgress = async () => {
    try {
      setLoading(true);
      const response = await apiService.getInstructorStudentProgress(studentId);
      setProgressData(response);
    } catch (err) {
      console.error('Failed to load student progress:', err);
      setError('Failed to load student progress: ' + (err.message || 'Unknown error'));
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

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return '#10b981'; // green
    if (percentage >= 60) return '#f59e0b'; // amber
    if (percentage >= 40) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const getStatusColor = (status) => {
    const colors = {
      'active': '#10b981',
      'completed': '#3b82f6',
      'cancelled': '#ef4444',
      'pending': '#f59e0b'
    };
    return colors[status] || '#6b7280';
  };

  const getStatusIcon = (status) => {
    const icons = {
      'active': '🟢',
      'completed': '✅',
      'cancelled': '❌',
      'pending': '⏳'
    };
    return icons[status] || '⚪';
  };

  if (loading) {
    return (
      <div className="instructor-student-progress">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading student progress...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="instructor-student-progress">
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

  if (!progressData) {
    return (
      <div className="instructor-student-progress">
        <div className="error-state">
          <h2>📊 No Progress Data</h2>
          <p>No progress data found for this student.</p>
          <button onClick={() => navigate('/instructor/students')} className="btn-primary">
            ← Back to Students
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-student-progress">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/students')} className="back-btn">
            ← Students
          </button>
          <h1>📊 {progressData.student.name} - Progress Report</h1>
          <p>Comprehensive progress tracking and analytics</p>
        </div>
        <div className="header-actions">
          <Link 
            to={`/instructor/students/${studentId}`} 
            className="btn-secondary"
          >
            📋 View Details
          </Link>
        </div>
      </div>

      {/* Overall Metrics */}
      <div className="metrics-section">
        <h2>📈 Overall Performance</h2>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon">📚</div>
            <div className="metric-content">
              <span className="metric-value">{progressData.overall_metrics.avg_project_completion}%</span>
              <span className="metric-label">Avg Project Completion</span>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-icon">📊</div>
            <div className="metric-content">
              <span className="metric-value">{progressData.overall_metrics.avg_quiz_score}%</span>
              <span className="metric-label">Avg Quiz Score</span>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-icon">✅</div>
            <div className="metric-content">
              <span className="metric-value">{progressData.attendance.attendance_rate}%</span>
              <span className="metric-label">Attendance Rate</span>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-icon">🎯</div>
            <div className="metric-content">
              <span className="metric-value">{progressData.overall_metrics.quiz_pass_rate}%</span>
              <span className="metric-label">Quiz Pass Rate</span>
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-icon">🏆</div>
            <div className="metric-content">
              <span className="metric-value">{progressData.overall_metrics.total_achievements}</span>
              <span className="metric-label">Achievements Earned</span>
            </div>
          </div>
        </div>
      </div>

      {/* Project Progress */}
      <div className="section">
        <div className="section-header">
          <h2>📚 Project Progress</h2>
          <span className="count-badge">{progressData.project_progress.length}</span>
        </div>
        
        {progressData.project_progress.length === 0 ? (
          <div className="empty-state">
            <p>📚 No projects found.</p>
          </div>
        ) : (
          <div className="projects-grid">
            {progressData.project_progress.map(project => (
              <div key={project.project_id} className="project-progress-card">
                <div className="project-header">
                  <h3>{project.project_title}</h3>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(project.status) }}
                  >
                    {getStatusIcon(project.status)} {project.status}
                  </span>
                </div>
                
                <div className="progress-section">
                  <div className="progress-info">
                    <span className="progress-label">Completion Progress</span>
                    <span className="progress-percentage">{project.completion_percentage}%</span>
                  </div>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ 
                        width: `${project.completion_percentage}%`,
                        backgroundColor: getProgressColor(project.completion_percentage)
                      }}
                    ></div>
                  </div>
                </div>
                
                <div className="project-meta">
                  <span>📅 Enrolled: {formatDate(project.enrolled_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Attendance Progress */}
      <div className="section">
        <div className="section-header">
          <h2>✅ Attendance Overview</h2>
        </div>
        
        <div className="attendance-summary">
          <div className="attendance-stats">
            <div className="attendance-stat">
              <span className="stat-number">{progressData.attendance.present_sessions}</span>
              <span className="stat-label">Sessions Attended</span>
            </div>
            <div className="attendance-stat">
              <span className="stat-number">{progressData.attendance.total_sessions}</span>
              <span className="stat-label">Total Sessions</span>
            </div>
            <div className="attendance-stat">
              <span className="stat-number">{progressData.attendance.attendance_rate}%</span>
              <span className="stat-label">Attendance Rate</span>
            </div>
          </div>
          
          <div className="attendance-visual">
            <div className="attendance-bar">
              <div 
                className="attendance-fill" 
                style={{ 
                  width: `${progressData.attendance.attendance_rate}%`,
                  backgroundColor: getProgressColor(progressData.attendance.attendance_rate)
                }}
              ></div>
            </div>
            <p className="attendance-description">
              {progressData.attendance.present_sessions} out of {progressData.attendance.total_sessions} sessions attended
            </p>
          </div>
        </div>
      </div>

      {/* Quiz Performance */}
      <div className="section">
        <div className="section-header">
          <h2>📝 Quiz Performance</h2>
          <span className="count-badge">{progressData.quiz_progress.length}</span>
        </div>
        
        {progressData.quiz_progress.length === 0 ? (
          <div className="empty-state">
            <p>📝 No quiz attempts found.</p>
          </div>
        ) : (
          <div className="quiz-list">
            {progressData.quiz_progress.map((quiz, index) => (
              <div key={index} className="quiz-card">
                <div className="quiz-header">
                  <div className="quiz-info">
                    <h4>{quiz.quiz_title}</h4>
                    <p className="session-title">{quiz.session_title}</p>
                  </div>
                  <div className="quiz-result">
                    <span className={`score ${quiz.passed ? 'passed' : 'failed'}`}>
                      {quiz.score}%
                    </span>
                    <span className={`pass-status ${quiz.passed ? 'passed' : 'failed'}`}>
                      {quiz.passed ? '✅ Passed' : '❌ Failed'}
                    </span>
                  </div>
                </div>
                
                <div className="quiz-progress">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ 
                        width: `${quiz.score}%`,
                        backgroundColor: quiz.passed ? '#10b981' : '#ef4444'
                      }}
                    ></div>
                  </div>
                </div>
                
                <div className="quiz-meta">
                  <span>⏱️ Time: {quiz.time_spent_minutes} min</span>
                  <span>📅 Completed: {formatDateTime(quiz.completed_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Achievements */}
      <div className="section">
        <div className="section-header">
          <h2>🏆 Achievements</h2>
          <span className="count-badge">{progressData.achievements.length}</span>
        </div>
        
        {progressData.achievements.length === 0 ? (
          <div className="empty-state">
            <p>🏆 No achievements earned yet.</p>
          </div>
        ) : (
          <div className="achievements-grid">
            {progressData.achievements.map((achievement, index) => (
              <div key={index} className="achievement-card">
                <div className="achievement-icon">🏆</div>
                <div className="achievement-content">
                  <h4>{achievement.achievement_name}</h4>
                  <p>{achievement.achievement_description}</p>
                  <span className="earned-date">
                    Earned: {formatDate(achievement.earned_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default InstructorStudentProgress;