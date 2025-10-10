import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import ProjectWaitlist from './ProjectWaitlist';
import './ProjectCard.css';

const ProjectCard = ({ project, onEnroll, onWithdraw, isEnrolled = false, enrollmentStatus = null, showActions = true }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showWaitlist, setShowWaitlist] = useState(false);

  const handleEnroll = () => {
    if (!showActions || isEnrolled) return;
    
    // Check if user is not eligible (failed quiz)
    if (enrollmentStatus === 'not_eligible') {
      alert('❌ Jelentkezés nem lehetséges!\n\nSajnos nem teljesítette a projekt belépési feltételeit a tudásfelmérő teszten.');
      return;
    }
    
    // 🔒 CRITICAL: Check semester validity before enrollment
    if (!canEnroll) {
      if (!semesterEnrollmentAllowed) {
        alert(`❌ Jelentkezés nem lehetséges!\n\n${getSemesterStatusMessage()}`);
      } else if (project.available_spots <= 0) {
        alert('❌ Jelentkezés nem lehetséges!\n\nA projekt betelt.');
      }
      return;
    }
    
    // Navigate directly to the enrollment quiz page
    navigate(`/student/projects/${project.id}/enrollment-quiz`);
  };

  const handleWithdraw = async () => {
    if (!showActions) return;
    
    if (!window.confirm('Biztosan ki szeretne lépni ebből a projektből?')) {
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      await apiService.withdrawFromProject(project.id);
      if (onWithdraw) onWithdraw(project);
    } catch (err) {
      setError(err.message || 'Failed to withdraw from project');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Nincs határidő';
    return new Date(dateString).toLocaleDateString('hu-HU');
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return '#10b981'; // green
    if (percentage >= 50) return '#f59e0b'; // amber
    if (percentage >= 25) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  // 🔒 CRITICAL: Semester validation function - allow enrollment for current and future semesters
  const isSemesterAvailableForEnrollment = (semester) => {
    try {
      if (!semester || !semester.start_date || !semester.end_date) {
        return false;
      }
      
      const now = new Date();
      // Handle iOS Safari date parsing issues
      const endDateStr = semester.end_date.includes('T') ? semester.end_date : `${semester.end_date}T23:59:59`;
      const end = new Date(endDateStr);
      
      // Check for invalid dates (common iOS issue)
      if (isNaN(now.getTime()) || isNaN(end.getTime())) {
        console.warn('Invalid date in semester validation:', { 
          semester, 
          now: now.toString(), 
          end: end.toString() 
        });
        return false;
      }
      
      // Allow enrollment if semester hasn't ended yet (current or future semester)
      // Only block if semester has already ended
      return now <= end;
    } catch (error) {
      console.error('Error in semester validation:', error, { semester });
      return false;
    }
  };

  // Check if enrollment is allowed based on semester status
  const semesterEnrollmentAllowed = isSemesterAvailableForEnrollment(project.semester);
  const canEnroll = showActions && !isEnrolled && semesterEnrollmentAllowed && project.available_spots > 0;

  // Get semester status message
  const getSemesterStatusMessage = () => {
    try {
      if (!project.semester) return null;
      
      if (!semesterEnrollmentAllowed) {
        const now = new Date();
        const endDateStr = project.semester.end_date.includes('T') ? 
          project.semester.end_date : `${project.semester.end_date}T23:59:59`;
        const end = new Date(endDateStr);
        
        // Check for invalid dates
        if (isNaN(end.getTime())) {
          return 'Szemeszter dátum hiba';
        }
        
        if (now > end) {
          return `Szemeszter véget ért (Befejezés: ${end.toLocaleDateString('hu-HU')})`;
        }
      }
      
      return null;
    } catch (error) {
      console.error('Error in getSemesterStatusMessage:', error);
      return 'Szemeszter státusz nem elérhető';
    }
  };

  const getDifficultyIcon = (difficulty) => {
    switch (difficulty) {
      case 'beginner': return '🟢';
      case 'intermediate': return '🟡';
      case 'advanced': return '🔴';
      default: return '⚪';
    }
  };

  const getDifficultyLabel = (difficulty) => {
    switch (difficulty) {
      case 'beginner': return 'Kezdő';
      case 'intermediate': return 'Haladó';
      case 'advanced': return 'Profi';
      default: return 'Ismeretlen';
    }
  };

  // Specialization indicator functions
  const getSpecializationIcon = (specialization) => {
    switch(specialization?.toUpperCase()) {
      case 'PLAYER': return '⚽';
      case 'COACH': return '🎓';
      default: return null;
    }
  };

  const getSpecializationLabel = (specialization) => {
    switch(specialization?.toUpperCase()) {
      case 'PLAYER': return 'Játékos';
      case 'COACH': return 'Edző';
      default: return null;
    }
  };

  const getSpecializationColors = (specialization) => {
    switch(specialization?.toUpperCase()) {
      case 'PLAYER': return { bg: '#4f46e5', text: '#ffffff' }; // Blue
      case 'COACH': return { bg: '#059669', text: '#ffffff' }; // Green
      default: return { bg: '#6b7280', text: '#ffffff' }; // Gray
    }
  };

  return (
    <div className="project-card">
      <div className="project-header">
        <div className="project-title-section">
          <h3 className="project-title">{project.title}</h3>
          <div className="project-meta">
            <span 
              className="meta-badge participants"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                whiteSpace: 'nowrap'
              }}
            >
              <span style={{ marginRight: '8px' }}>👥</span>
              <span>{project.enrolled_count || 0}/{project.max_participants}</span>
            </span>
            <span 
              className="meta-badge sessions"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                whiteSpace: 'nowrap'
              }}
            >
              <span style={{ marginRight: '8px' }}>⏱️</span>
              <span>{project.required_sessions} óra</span>
            </span>
            <span 
              className="meta-badge xp"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                whiteSpace: 'nowrap'
              }}
            >
              <span style={{ marginRight: '8px' }}>⭐</span>
              <span>{project.xp_reward} XP</span>
            </span>
            {project.difficulty && (
              <span 
                className={`meta-badge difficulty ${project.difficulty}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  whiteSpace: 'nowrap'
                }}
              >
                <span style={{ marginRight: '8px' }}>{getDifficultyIcon(project.difficulty)}</span>
                <span>{getDifficultyLabel(project.difficulty)}</span>
              </span>
            )}
            {project.has_enrollment_quiz && (
              <span 
                className="meta-badge quiz-required"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  whiteSpace: 'nowrap'
                }}
              >
                <span style={{ marginRight: '8px' }}>📝</span>
                <span>Teszt szükséges</span>
              </span>
            )}
            {/* Specialization indicator */}
            {project.target_specialization && (
              <span 
                className="meta-badge specialization"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  whiteSpace: 'nowrap',
                  backgroundColor: getSpecializationColors(project.target_specialization).bg,
                  color: getSpecializationColors(project.target_specialization).text
                }}
                title={`Célcsoport: ${getSpecializationLabel(project.target_specialization)}`}
              >
                <span style={{ marginRight: '8px' }}>{getSpecializationIcon(project.target_specialization)}</span>
                <span>{getSpecializationLabel(project.target_specialization)}</span>
              </span>
            )}
            {project.mixed_specialization && (
              <span 
                className="meta-badge specialization mixed"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  whiteSpace: 'nowrap',
                  backgroundColor: '#8b5cf6',
                  color: '#ffffff'
                }}
                title="Vegyes szakirány - Játékosok és edzők számára"
              >
                <span style={{ marginRight: '8px' }}>🤝</span>
                <span>Vegyes</span>
              </span>
            )}
          </div>
        </div>
        
        {project.available_spots !== undefined && (
          <div className="availability-indicator">
            <span className={`availability-badge ${project.available_spots > 0 ? 'available' : 'full'}`}>
              {project.available_spots > 0 ? `${project.available_spots} hely` : 'Betelt'}
            </span>
          </div>
        )}
      </div>

      {project.description && (
        <div className="project-description">
          <p>{project.description}</p>
        </div>
      )}

      <div className="project-details">
        <div className="detail-row">
          <span className="detail-label">Határidő:</span>
          <span className="detail-value">{formatDate(project.deadline)}</span>
        </div>
        
        {project.completion_percentage !== undefined && (
          <div className="detail-row">
            <span className="detail-label">Haladás:</span>
            <div className="progress-container">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ 
                    width: `${project.completion_percentage}%`,
                    backgroundColor: getProgressColor(project.completion_percentage)
                  }}
                ></div>
              </div>
              <span className="progress-text">{project.completion_percentage.toFixed(0)}%</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          <span>⚠️ {error}</span>
        </div>
      )}

      {/* 🔒 Semester Status Warning */}
      {!semesterEnrollmentAllowed && getSemesterStatusMessage() && (
        <div className="semester-warning">
          <span>⚠️ {getSemesterStatusMessage()}</span>
        </div>
      )}

      {/* Spacer to push actions to bottom */}
      <div className="content-spacer"></div>

      {showActions && (
        <div className="project-actions">
          {isEnrolled ? (
            <>
              <Link 
                to={`/student/projects/${project.id}/progress`} 
                className="action-btn primary"
              >
                📊 Haladás megtekintése
              </Link>
              <button 
                onClick={() => setShowWaitlist(true)}
                className="action-btn tertiary"
                style={{ fontSize: '0.85rem' }}
              >
                📋 Várólista
              </button>
              <button 
                onClick={handleWithdraw}
                disabled={loading}
                className="action-btn secondary"
              >
                {loading ? '⏳ Törlés...' : '🚪 Kilépés'}
              </button>
            </>
          ) : (
            <>
              <Link 
                to={`/student/projects/${project.id}`} 
                className="action-btn secondary"
              >
                📖 Részletek
              </Link>
              <button 
                onClick={() => setShowWaitlist(true)}
                className="action-btn tertiary"
                style={{ fontSize: '0.85rem' }}
              >
                📋 Várólista
              </button>
              <button 
                onClick={handleEnroll}
                disabled={loading || !canEnroll || enrollmentStatus === 'not_eligible'}
                className={`action-btn ${
                  enrollmentStatus === 'not_eligible' ? 'not-eligible' :
                  canEnroll ? 'primary' : 'disabled'
                }`}
                title={
                  enrollmentStatus === 'not_eligible' ? 'Nem felel meg a projekt belépési feltételeinek' :
                  !semesterEnrollmentAllowed ? getSemesterStatusMessage() : 
                  project.available_spots <= 0 ? 'Nincs szabad hely' : 
                  'Kattintson a jelentkezéshez'
                }
              >
                {loading ? '⏳ Jelentkezés...' : 
                 enrollmentStatus === 'not_eligible' ? '❌ Nem jogosult' :
                 !semesterEnrollmentAllowed ? '🚫 Jelentkezés lezárva' :
                 project.available_spots <= 0 ? '⛔ Betelt' :
                 '🚀 Jelentkezés'}
              </button>
            </>
          )}
        </div>
      )}

      {/* Project Waitlist Modal */}
      <ProjectWaitlist
        projectId={project.id}
        isVisible={showWaitlist}
        onClose={() => setShowWaitlist(false)}
      />

    </div>
  );
};

export default ProjectCard;