import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import QuizEnrollmentStatus from '../../components/student/QuizEnrollmentStatus';
import './ProjectEnrollmentQuiz.css';

const ProjectEnrollmentQuiz = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState(null);
  const [enrollmentInfo, setEnrollmentInfo] = useState(null);
  const [error, setError] = useState('');
  const [enrolling, setEnrolling] = useState(false);
  const [theme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadData();
  }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Load project details and enrollment info in parallel
      const [projectResponse, enrollmentResponse] = await Promise.all([
        apiService.request(`/api/v1/projects/${projectId}`),
        apiService.request(`/api/v1/projects/${projectId}/enrollment-quiz`)
      ]);
      
      setProject(projectResponse);
      setEnrollmentInfo(enrollmentResponse);
    } catch (err) {
      console.error('Failed to load enrollment data:', err);
      setError(err.message || 'Failed to load enrollment information');
    } finally {
      setLoading(false);
    }
  };

  const handleDirectEnrollment = async () => {
    try {
      setEnrolling(true);
      await apiService.request(`/api/v1/projects/${projectId}/enroll`, {
        method: 'POST'
      });
      
      // Show success message and navigate back to projects
      alert(`Sikeresen jelentkezett a "${project.title}" projektre!`);
      navigate('/student/projects');
    } catch (err) {
      console.error('Enrollment error:', err);
      setError(err.message || 'Failed to enroll in project');
    } finally {
      setEnrolling(false);
    }
  };

  const handleStartQuiz = () => {
    if (enrollmentInfo && enrollmentInfo.quiz) {
      // Navigate directly to the quiz taking page
      navigate(`/student/quiz/${enrollmentInfo.quiz.id}/take`, {
        state: { 
          isEnrollmentQuiz: true,
          projectId: projectId,
          returnTo: `/student/projects/${projectId}/enrollment-quiz`
        }
      });
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Nincs határidő';
    return new Date(dateString).toLocaleDateString('hu-HU');
  };

  if (loading) {
    return (
      <div className="project-enrollment-quiz">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Adatok betöltése...</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="project-enrollment-quiz">
        <div className="error-state">
          <h2>⚠️ Hiba történt</h2>
          <p>{error || 'A projekt adatok nem tölthetők be'}</p>
          <div className="error-actions">
            <button onClick={() => navigate('/student/projects')} className="back-btn">
              ← Vissza a projektekhez
            </button>
            <button onClick={loadData} className="retry-btn">
              🔄 Újrapróbálás
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="project-enrollment-quiz">
      {/* Header */}
      <div className="page-header">
        <button 
          onClick={() => navigate('/student/projects')} 
          className="back-btn"
        >
          ← Vissza a projektekhez
        </button>
        <div className="header-content">
          <h1>🎯 Jelentkezés</h1>
          <p>Jelentkezés a projektbe és előzetes tudásfelmérés</p>
        </div>
      </div>

      {/* Project Info Card */}
      <div className="project-info-card">
        <div className="project-header">
          <h2>{project.title}</h2>
          <div className="project-status">
            <span className="status-badge active">
              {project.available_spots > 0 ? 
                `${project.available_spots} szabad hely` : 
                'Betelt'
              }
            </span>
          </div>
        </div>
        
        {project.description && (
          <div className="project-description">
            <p>{project.description}</p>
          </div>
        )}

        <div className="project-details-grid">
          <div className="detail-item">
            <span className="detail-icon">👥</span>
            <div className="detail-content">
              <span className="detail-label">Résztvevők</span>
              <span className="detail-value">
                {project.enrolled_count || 0} / {project.max_participants}
              </span>
            </div>
          </div>
          
          <div className="detail-item">
            <span className="detail-icon">⏱️</span>
            <div className="detail-content">
              <span className="detail-label">Óraszám</span>
              <span className="detail-value">{project.required_sessions} óra</span>
            </div>
          </div>
          
          <div className="detail-item">
            <span className="detail-icon">⭐</span>
            <div className="detail-content">
              <span className="detail-label">XP jutalom</span>
              <span className="detail-value">{project.xp_reward} XP</span>
            </div>
          </div>
          
          <div className="detail-item">
            <span className="detail-icon">📅</span>
            <div className="detail-content">
              <span className="detail-label">Határidő</span>
              <span className="detail-value">{formatDate(project.deadline)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Enrollment Process */}
      {!enrollmentInfo ? (
        <div className="loading-section">
          <div className="loading-spinner"></div>
          <p>Jelentkezési információk betöltése...</p>
        </div>
      ) : !enrollmentInfo.has_enrollment_quiz ? (
        /* Direct Enrollment */
        <div className="enrollment-section">
          <div className="enrollment-card">
            <div className="card-header">
              <h3>📝 Közvetlen jelentkezés</h3>
              <p>
                Ehhez a projekthez nem szükséges tudásfelmérő teszt kitöltése. 
                Közvetlenül jelentkezhet a projektre.
              </p>
            </div>
            
            <div className="enrollment-actions">
              <button 
                onClick={handleDirectEnrollment}
                disabled={enrolling || project.available_spots === 0}
                className="enroll-btn primary large"
              >
                {enrolling ? '⏳ Jelentkezés...' : '🚀 Jelentkezés most'}
              </button>
            </div>
          </div>
        </div>
      ) : enrollmentInfo.user_completed ? (
        /* Quiz Already Completed - Split into two separate sections */
        <>
          {/* Quiz Completion Section */}
          <div className="enrollment-section">
            <div className="enrollment-card completed">
              <div className="card-header">
                <h3>✅ Tudásfelmérő befejezve</h3>
                <p>
                  Már kitöltötte a szükséges tudásfelmérő tesztet ehhez a projekthez.
                  Eredményét a projekt kiválasztási folyamat során veszik figyelembe.
                </p>
              </div>
            </div>
          </div>

          {/* Enrollment Status Section */}
          <div className="enrollment-section">
            <div className="enrollment-status-card">
              <QuizEnrollmentStatus 
                enrollmentInfo={enrollmentInfo}
                projectId={projectId}
              />
            </div>
          </div>
        </>
      ) : (
        /* Quiz Required */
        <div className="enrollment-section">
          <div className="quiz-requirement-card">
            <div className="card-header">
              <h3>🧠 Tudásfelmérő teszt szükséges</h3>
              <p>
                A projektbe való jelentkezéshez először ki kell töltenie egy tudásfelmérő tesztet. 
                Az eredmény alapján alakul ki a rangsor, és a legjobb eredményt elérők kapnak helyet a projektben.
              </p>
            </div>

            <div className="quiz-details">
              <div className="quiz-info-grid">
                <div className="quiz-info-item">
                  <span className="info-icon">📋</span>
                  <div className="info-content">
                    <span className="info-label">Teszt címe</span>
                    <span className="info-value">{enrollmentInfo.quiz.title}</span>
                  </div>
                </div>
                
                <div className="quiz-info-item">
                  <span className="info-icon">⏱️</span>
                  <div className="info-content">
                    <span className="info-label">Időkorlát</span>
                    <span className="info-value">{enrollmentInfo.quiz.time_limit_minutes} perc</span>
                  </div>
                </div>
                
                <div className="quiz-info-item">
                  <span className="info-icon">🎯</span>
                  <div className="info-content">
                    <span className="info-label">Minimum pontszám</span>
                    <span className="info-value">{enrollmentInfo.quiz.minimum_score}%</span>
                  </div>
                </div>
                
                <div className="quiz-info-item warning">
                  <span className="info-icon">⚠️</span>
                  <div className="info-content">
                    <span className="info-label">Fontos</span>
                    <span className="info-value">Csak egyetlen kísérlet lehetséges!</span>
                  </div>
                </div>
              </div>

              {enrollmentInfo.quiz.description && (
                <div className="quiz-description">
                  <h4>Teszt leírása</h4>
                  <p>{enrollmentInfo.quiz.description}</p>
                </div>
              )}
            </div>

            <div className="quiz-actions">
              <button 
                onClick={handleStartQuiz}
                className="start-quiz-btn primary large"
              >
                🧠 Tudásfelmérő teszt megkezdése
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Warning/Info Section */}
      <div className="info-section">
        <div className="info-card">
          <h4>📌 Fontos információk</h4>
          <ul>
            <li>A jelentkezés egy szemeszterre szól</li>
            <li>Csak az aktív jelentkezések kerülnek elbírálásra</li>
            <li>A projekt kiválasztása előzetes tudásfelmérés alapján történhet</li>
            <li>A projekt során részvételi kötelezettség áll fenn</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ProjectEnrollmentQuiz;