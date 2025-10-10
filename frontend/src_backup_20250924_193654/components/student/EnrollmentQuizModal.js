import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import QuizEnrollmentStatus from './QuizEnrollmentStatus';
import './EnrollmentQuizModal.css';

const EnrollmentQuizModal = ({ isOpen, onClose, project }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [enrollmentInfo, setEnrollmentInfo] = useState(null);

  useEffect(() => {
    if (isOpen && project) {
      fetchEnrollmentInfo();
    }
    
    // Lock body scroll when modal is open
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    // Cleanup on unmount
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, project]);

  const fetchEnrollmentInfo = async () => {
    try {
      setLoading(true);
      const data = await apiService.request(`/api/v1/projects/${project.id}/enrollment-quiz`);
      setEnrollmentInfo(data);
    } catch (error) {
      console.error('Error fetching enrollment info:', error);
      // Set fallback data for direct enrollment on API error
      setEnrollmentInfo({
        has_enrollment_quiz: false,
        user_completed: false,
        quiz: null
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStartQuiz = () => {
    if (enrollmentInfo && enrollmentInfo.quiz) {
      // Navigate to quiz taking page
      navigate(`/student/quiz/${enrollmentInfo.quiz.id}/take`, {
        state: { 
          returnTo: `enrollment-modal`,
          projectId: project.id,
          isEnrollmentQuiz: true,
          onComplete: () => {
            // Refresh enrollment info after quiz completion
            fetchEnrollmentInfo();
          }
        }
      });
      onClose();
    }
  };

  const handleDirectEnrollment = async () => {
    try {
      setLoading(true);
      await apiService.request(`/api/v1/projects/${project.id}/enroll`, {
        method: 'POST'
      });
      onClose();
      window.location.reload(); // Simple way to refresh the page
    } catch (error) {
      console.error('Enrollment error:', error);
      alert('Hiba történt a jelentkezés során: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClick = (e) => {
    // Close modal when clicking on overlay (not on modal content)
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e) => {
    // Close modal on Escape key
    if (e.key === 'Escape') {
      onClose();
    }
  };

  // Add keyboard event listener
  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className={`modal-overlay ${process.env.NODE_ENV === 'development' ? 'debug-visible' : ''}`} onClick={handleOverlayClick}>
      <div className={`enrollment-quiz-modal ${process.env.NODE_ENV === 'development' ? 'debug-visible' : ''}`}>
        <div className="modal-header">
          <h2>🎯 Jelentkezés - {project?.title}</h2>
          <button onClick={onClose} className="close-btn">✕</button>
        </div>

        <div className="modal-content">
          {loading ? (
            <div className="loading-section">
              <div className="loading-spinner"></div>
              <p>Adatok betöltése...</p>
            </div>
          ) : enrollmentInfo ? (
            <div className="enrollment-content">
              {!enrollmentInfo.has_enrollment_quiz ? (
                // No enrollment quiz - direct enrollment
                <div className="direct-enrollment">
                  <div className="enrollment-message">
                    <h3>📝 Közvetlen jelentkezés</h3>
                    <p>
                      Ehhez a projekthez nem szükséges felmérő teszt kitöltése. 
                      Közvetlenül jelentkezhet a projektre.
                    </p>
                  </div>
                  
                  <div className="project-info">
                    <div className="info-item">
                      <span className="info-icon">👥</span>
                      <span>Max résztvevő: {project.max_participants}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-icon">⭐</span>
                      <span>XP jutalom: {project.xp_reward}</span>
                    </div>
                  </div>

                  <div className="enrollment-actions">
                    <button 
                      onClick={handleDirectEnrollment}
                      disabled={loading}
                      className="enroll-btn primary"
                    >
                      {loading ? 'Jelentkezés...' : '🚀 Jelentkezés most'}
                    </button>
                    <button onClick={onClose} className="cancel-btn">
                      Mégse
                    </button>
                  </div>
                </div>
              ) : enrollmentInfo.user_completed ? (
                // User has completed the quiz - show status
                <div className="quiz-completed">
                  <QuizEnrollmentStatus projectId={project.id} />
                  
                  <div className="completed-actions">
                    <button onClick={onClose} className="close-btn-action">
                      Bezárás
                    </button>
                  </div>
                </div>
              ) : (
                // User needs to take the enrollment quiz
                <div className="quiz-required">
                  <div className="quiz-info">
                    <h3>🧠 Tudásfelmérő teszt szükséges</h3>
                    <p>
                      A projektbe való jelentkezéshez először ki kell töltenie egy tudásfelmérő tesztet. 
                      Az eredmény alapján alakul ki a rangsor, és a legjobb eredményt elérők kapnak helyet a projektben.
                    </p>
                  </div>

                  <div className="quiz-details">
                    <div className="quiz-card">
                      <h4>{enrollmentInfo.quiz.title}</h4>
                      <p>{enrollmentInfo.quiz.description}</p>
                      
                      <div className="quiz-requirements">
                        <div className="requirement-item">
                          <span className="req-icon">⏱️</span>
                          <span>Időkorlát: {enrollmentInfo.quiz.time_limit_minutes} perc</span>
                        </div>
                        <div className="requirement-item">
                          <span className="req-icon">🎯</span>
                          <span>Minimum: {enrollmentInfo.quiz.minimum_score}%</span>
                        </div>
                        <div className="requirement-item warning">
                          <span className="req-icon">⚠️</span>
                          <span>Csak egy kísérlet lehetséges!</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="quiz-actions">
                    <button 
                      onClick={handleStartQuiz}
                      className="start-quiz-btn primary"
                    >
                      🧠 Teszt megkezdése
                    </button>
                    <button onClick={onClose} className="cancel-btn">
                      Mégse
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="error-section">
              <p>⚠️ Hiba történt az adatok betöltése során</p>
              <div className="error-actions">
                <button 
                  onClick={fetchEnrollmentInfo} 
                  className="retry-btn"
                  disabled={loading}
                >
                  🔄 Újrapróbálás
                </button>
                <button onClick={onClose} className="cancel-btn">
                  Bezárás
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnrollmentQuizModal;