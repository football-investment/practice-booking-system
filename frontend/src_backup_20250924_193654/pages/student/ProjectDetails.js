import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import ProjectCard from '../../components/student/ProjectCard';
import EnrollmentQuizModal from '../../components/student/EnrollmentQuizModal';
import './ProjectDetails.css';

const ProjectDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState(null);
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [enrollmentDetails, setEnrollmentDetails] = useState(null);
  const [quizResults, setQuizResults] = useState([]);
  const [error, setError] = useState('');
  const [showEnrollmentModal, setShowEnrollmentModal] = useState(false);
  const [theme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadProjectDetails();
  }, [id]);

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

  const loadProjectDetails = async () => {
    try {
      setLoading(true);
      setError('');

      // Load project details
      const projectsResponse = await apiService.getProjects({ project_id: parseInt(id) });
      const projectData = projectsResponse.projects?.find(p => p.id === parseInt(id));
      
      if (!projectData) {
        setError('Project not found');
        return;
      }

      setProject(projectData);

      // Check enrollment status
      const summary = await apiService.getMyProjectSummary();
      const currentEnrollment = summary.current_project?.project_id === parseInt(id);
      
      setIsEnrolled(currentEnrollment);
      if (currentEnrollment) {
        setEnrollmentDetails(summary.current_project);
      }

      // Load quiz results if enrolled
      if (currentEnrollment) {
        try {
          const quizResponse = await apiService.getMyQuizAttempts();
          // Filter quiz attempts for this specific project
          const projectQuizzes = quizResponse.attempts?.filter(attempt => {
            // Check if this quiz is related to the current project
            // This might need adjustment based on your API response structure
            return attempt.project_id === parseInt(id) || attempt.quiz_type === 'enrollment';
          }) || [];
          setQuizResults(projectQuizzes);
        } catch (quizError) {
          console.warn('Failed to load quiz results:', quizError);
          // Don't set error state for quiz loading failure
        }
      }
      
    } catch (err) {
      console.error('Failed to load project details:', err);
      setError(err.message || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  const handleEnroll = (project) => {
    if (isEnrolled) {
      alert('Már jelentkezett ebbe a projektbe!');
      return;
    }
    setShowEnrollmentModal(true);
  };

  const handleEnrollmentModalClose = () => {
    setShowEnrollmentModal(false);
    // Refresh data after modal closes
    loadProjectDetails();
  };

  const handleWithdraw = async (project) => {
    try {
      await apiService.withdrawFromProject(project.id);
      
      // Refresh data after withdrawal
      await loadProjectDetails();
      
      alert(`Sikeresen kilépett a "${project.title}" projektből.`);
    } catch (err) {
      alert(`Hiba a kilépés során: ${err.message}`);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Nincs határidő';
    return new Date(dateString).toLocaleDateString('hu-HU');
  };

  const getStatusText = (status) => {
    const texts = {
      active: 'Aktív',
      completed: 'Befejezett', 
      archived: 'Archivált'
    };
    return texts[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      active: '#10b981',
      completed: '#3b82f6',
      archived: '#6b7280'
    };
    return colors[status] || '#6b7280';
  };

  if (loading) {
    return (
      <div className="project-details-page">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Projekt betöltése...</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="project-details-page">
        <div className="error-state">
          <h2>⚠️ Projekt nem található</h2>
          <p>{error || 'A keresett projekt nem található vagy nem érhető el.'}</p>
          <button onClick={() => navigate('/student/projects')} className="back-btn">
            ← Vissza a projektekhez
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="project-details-page">
      {/* Header */}
      <div className="page-header">
        <button onClick={() => navigate('/student/projects')} className="back-btn">
          ← Vissza a projektekhez
        </button>
        <div className="project-status-info">
          <span 
            className="status-badge"
            style={{ backgroundColor: getStatusColor(project.status) }}
          >
            {getStatusText(project.status)}
          </span>
          {isEnrolled && enrollmentDetails && (
            <span className="enrolled-badge">
              ✅ Jelentkezve
            </span>
          )}
        </div>
      </div>

      {/* Hero Section */}
      <div className="project-hero">
        <div className="hero-content">
          <h1>{project.title}</h1>
          <p className="project-intro">{project.description}</p>
          
          <div className="hero-stats">
            <div className="hero-stat">
              <span className="stat-number">{project.max_participants}</span>
              <span className="stat-label">Max résztvevő</span>
            </div>
            <div className="hero-stat">
              <span className="stat-number">{project.required_sessions}</span>
              <span className="stat-label">Szükséges órák</span>
            </div>
            <div className="hero-stat">
              <span className="stat-number">{project.xp_reward}</span>
              <span className="stat-label">XP jutalom</span>
            </div>
            <div className="hero-stat">
              <span className="stat-number">{formatDate(project.deadline)}</span>
              <span className="stat-label">Határidő</span>
            </div>
          </div>
        </div>
      </div>

      {/* Project Details Card */}
      <div className="project-card-section">
        <ProjectCard
          project={project}
          isEnrolled={isEnrolled}
          onEnroll={handleEnroll}
          onWithdraw={handleWithdraw}
          showActions={true}
        />
      </div>

      {/* Detailed Information */}
      <div className="detailed-info">
        <div className="info-grid">
          <div className="info-card">
            <h3>📋 Projekt Információk</h3>
            <div className="info-list">
              <div className="info-item">
                <span className="info-label">Azonosító:</span>
                <span className="info-value">#{project.id}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Szemeszter ID:</span>
                <span className="info-value">{project.semester_id}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Oktató ID:</span>
                <span className="info-value">{project.instructor_id}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Létrehozva:</span>
                <span className="info-value">
                  {new Date(project.created_at).toLocaleDateString('hu-HU')}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">Frissítve:</span>
                <span className="info-value">
                  {new Date(project.updated_at).toLocaleDateString('hu-HU')}
                </span>
              </div>
            </div>
          </div>

          {/* Quiz Results */}
          {isEnrolled && quizResults.length > 0 && (
            <div className="info-card">
              <h3>📝 Teszt Eredmények</h3>
              <div className="quiz-results-list">
                {quizResults.map((attempt, index) => (
                  <div key={attempt.id || index} className="quiz-result-item">
                    <div className="quiz-result-header">
                      <span className="quiz-title">
                        {attempt.quiz_title || `Teszt #${attempt.quiz_id}`}
                      </span>
                      <span className={`quiz-status ${attempt.passed ? 'passed' : 'failed'}`}>
                        {attempt.passed ? '✅ Sikeres' : '❌ Sikertelen'}
                      </span>
                    </div>
                    <div className="quiz-result-details">
                      <div className="quiz-detail">
                        <span className="detail-label">Pontszám:</span>
                        <span className={`detail-value ${attempt.passed ? 'success' : 'failure'}`}>
                          {attempt.score}%
                        </span>
                      </div>
                      <div className="quiz-detail">
                        <span className="detail-label">Helyes válaszok:</span>
                        <span className="detail-value">
                          {attempt.correct_answers}/{attempt.total_questions}
                        </span>
                      </div>
                      <div className="quiz-detail">
                        <span className="detail-label">Időtartam:</span>
                        <span className="detail-value">
                          {attempt.time_spent_minutes} perc
                        </span>
                      </div>
                      <div className="quiz-detail">
                        <span className="detail-label">Dátum:</span>
                        <span className="detail-value">
                          {new Date(attempt.completed_at).toLocaleDateString('hu-HU', {
                            year: 'numeric',
                            month: 'short', 
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      </div>
                    </div>
                    {attempt.xp_awarded > 0 && (
                      <div className="quiz-xp-award">
                        🏆 {attempt.xp_awarded} XP szerzett
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="info-card">
            <h3>👥 Résztvevők</h3>
            <div className="participants-info">
              <div className="participants-visual">
                <div className="progress-circle">
                  <div className="progress-inner">
                    <span className="progress-number">{project.enrolled_count}</span>
                    <span className="progress-total">/ {project.max_participants}</span>
                  </div>
                  <svg className="progress-ring" width="120" height="120">
                    <circle
                      className="progress-ring-background"
                      cx="60"
                      cy="60"
                      r="50"
                      strokeWidth="8"
                    />
                    <circle
                      className="progress-ring-progress"
                      cx="60"
                      cy="60"
                      r="50"
                      strokeWidth="8"
                      strokeDasharray={`${2 * Math.PI * 50}`}
                      strokeDashoffset={`${2 * Math.PI * 50 * (1 - project.enrolled_count / project.max_participants)}`}
                    />
                  </svg>
                </div>
              </div>
              
              <div className="participants-stats">
                <div className="participants-stat">
                  <span className="stat-value">{project.enrolled_count}</span>
                  <span className="stat-label">Jelenlegi résztvevők</span>
                </div>
                <div className="participants-stat">
                  <span className="stat-value">{project.available_spots || (project.max_participants - project.enrolled_count)}</span>
                  <span className="stat-label">Elérhető helyek</span>
                </div>
                <div className="participants-stat">
                  <span className="stat-value">
                    {Math.round((project.enrolled_count / project.max_participants) * 100)}%
                  </span>
                  <span className="stat-label">Betöltöttség</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Enrollment Details */}
      {isEnrolled && enrollmentDetails && (
        <div className="enrollment-details">
          <h3>🎯 Saját Jelentkezési Adatok</h3>
          <div className="enrollment-card">
            <div className="enrollment-info">
              <div className="enrollment-item">
                <span className="enrollment-label">Jelentkezés dátuma:</span>
                <span className="enrollment-value">
                  {new Date(enrollmentDetails.enrolled_at).toLocaleDateString('hu-HU')}
                </span>
              </div>
              <div className="enrollment-item">
                <span className="enrollment-label">Státusz:</span>
                <span className="enrollment-value">{getStatusText(enrollmentDetails.status)}</span>
              </div>
              <div className="enrollment-item">
                <span className="enrollment-label">Haladás:</span>
                <span className="enrollment-value">{Math.round(enrollmentDetails.completion_percentage)}%</span>
              </div>
            </div>
            
            <div className="enrollment-actions">
              <button
                onClick={() => navigate(`/student/projects/${project.id}/progress`)}
                className="progress-btn"
              >
                📊 Részletes Haladás
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="page-actions">
        <button onClick={() => navigate('/student/projects')} className="secondary-btn">
          📁 Összes Projekt
        </button>
        <button onClick={() => navigate('/student/projects/my')} className="secondary-btn">
          🎯 Saját Projektek
        </button>
        {isEnrolled && (
          <button
            onClick={() => navigate(`/student/projects/${project.id}/progress`)}
            className="primary-btn"
          >
            📈 Haladás Követése
          </button>
        )}
      </div>

      {/* Enrollment Quiz Modal */}
      <EnrollmentQuizModal
        isOpen={showEnrollmentModal}
        onClose={handleEnrollmentModalClose}
        project={project}
      />
    </div>
  );
};

export default ProjectDetails;