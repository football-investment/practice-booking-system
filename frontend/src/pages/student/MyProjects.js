import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import ProjectCard from '../../components/student/ProjectCard';
import MilestoneTracker from '../../components/student/MilestoneTracker';
import './MyProjects.css';

const MyProjects = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [projectSummary, setProjectSummary] = useState(null);
  const [projectProgress, setProjectProgress] = useState(null);
  const [error, setError] = useState('');
  const [theme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadMyProjects();
  }, []);

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

  const loadMyProjects = async () => {
    try {
      setLoading(true);
      setError('');
      
      const summary = await apiService.getMyProjectSummary();
      setProjectSummary(summary);
      
      // If user has a current project, load its detailed progress
      if (summary.current_project) {
        const progress = await apiService.getProjectProgress(summary.current_project.project_id);
        setProjectProgress(progress);
      }
    } catch (err) {
      console.error('Failed to load my projects:', err);
      setError(err.message || 'Failed to load your projects');
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = async (project) => {
    try {
      await apiService.withdrawFromProject(project.id);
      
      // Refresh data after withdrawal
      await loadMyProjects();
      
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
      dropped: 'Megszakított',
      not_eligible: 'Nem megfelelő'
    };
    return texts[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      active: '#10b981',
      completed: '#3b82f6',
      dropped: '#ef4444',
      not_eligible: '#ef4444'
    };
    return colors[status] || '#6b7280';
  };

  if (loading) {
    return (
      <div className="my-projects-page">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Projektek betöltése...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="my-projects-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/student/projects')} className="back-btn">
            ← Projektek
          </button>
          <h1>🎯 Saját Projektjeim</h1>
          <p>Üdvözöljük, {user?.name}! Itt követheti nyomon projektjei haladását.</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Current Project Section */}
      {projectSummary?.current_project ? (
        <>
          <section className="current-project-section">
            <div className="section-header">
              <h2>🚀 Jelenlegi Projekt</h2>
              <div className="project-status">
                <span 
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(projectSummary.current_project.status) }}
                >
                  {getStatusText(projectSummary.current_project.status)}
                </span>
              </div>
            </div>

            <div className="current-project-content">
              <div className="project-overview">
                <ProjectCard 
                  project={{
                    id: projectSummary.current_project.project_id,
                    title: projectSummary.current_project.project_title,
                    description: projectSummary.current_project.project_description,
                    deadline: projectSummary.current_project.project_deadline,
                    required_sessions: projectSummary.current_project.required_sessions,
                    xp_reward: projectSummary.current_project.xp_reward,
                    completion_percentage: projectSummary.current_project.completion_percentage
                  }}
                  isEnrolled={true}
                  onWithdraw={handleWithdraw}
                  showActions={projectSummary.current_project.status === 'active'}
                />
              </div>

              {projectProgress && (
                <div className="project-progress-section">
                  <h3>📊 Projekt Haladás</h3>
                  
                  {/* Overall Stats */}
                  <div className="progress-stats">
                    <div className="stat-card">
                      <div className="stat-number">{projectProgress.sessions_completed}</div>
                      <div className="stat-label">Befejezett Órák</div>
                      <div className="stat-detail">/ {projectProgress.required_sessions} szükséges</div>
                    </div>
                    
                    <div className="stat-card">
                      <div className="stat-number">{projectProgress.milestones_completed}</div>
                      <div className="stat-label">Teljesített Mérföldkövek</div>
                      <div className="stat-detail">/ {projectProgress.total_milestones} összes</div>
                    </div>
                    
                    <div className="stat-card">
                      <div className="stat-number">{Math.round(projectProgress.completion_percentage)}%</div>
                      <div className="stat-label">Összesített Haladás</div>
                      <div className="stat-detail">projekt befejezettség</div>
                    </div>
                  </div>

                  {/* Milestones */}
                  {projectProgress.milestones && (
                    <div className="milestones-section">
                      <MilestoneTracker 
                        milestones={projectProgress.milestones}
                        overallProgress={projectProgress.completion_percentage}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        </>
      ) : (
        <div className="no-current-project">
          <div className="empty-state">
            <div className="empty-icon">📂</div>
            <h3>Nincs aktív projekt</h3>
            <p>Jelenleg nincs aktív projektje. Böngésszen az elérhető projektek között és válasszon egyet!</p>
            <a href="/student/projects" className="action-link">
              🔍 Projektek böngészése
            </a>
          </div>
        </div>
      )}

      {/* Not Eligible Projects Section */}
      {projectSummary?.enrolled_projects && 
       projectSummary.enrolled_projects.filter(p => p.status === 'not_eligible').length > 0 && (
        <section className="not-eligible-projects-section">
          <h2>❌ Nem megfelelő projektek</h2>
          <p>Ezekben a projektekben a tudásfelmérő teszt nem sikerült.</p>
          
          <div className="not-eligible-projects-grid">
            {projectSummary.enrolled_projects
              .filter(project => project.status === 'not_eligible')
              .map(project => (
                <div key={project.project_id} className="not-eligible-project-card">
                  <div className="project-header">
                    <h4 className="project-title">{project.project_title}</h4>
                    <div className="status-info">
                      <span className="status-badge not-eligible">
                        ❌ {getStatusText(project.status)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="project-message">
                    <p>Sajnos nem teljesítette a projekt belépési feltételeit.</p>
                    <p>A tudásfelmérő teszten nem érte el a szükséges pontszámot.</p>
                  </div>
                </div>
              ))}
          </div>
        </section>
      )}

      {/* Completed Projects Section */}
      {projectSummary?.completed_projects && projectSummary.completed_projects.length > 0 && (
        <section className="completed-projects-section">
          <h2>✅ Befejezett Projektek</h2>
          
          <div className="completed-projects-grid">
            {projectSummary.completed_projects.map(project => (
              <div key={project.project_id} className="completed-project-card">
                <div className="completed-project-header">
                  <h4 className="completed-project-title">{project.project_title}</h4>
                  <div className="completion-info">
                    <span className="completion-date">
                      Befejezve: {formatDate(project.completion_date)}
                    </span>
                    <span className="earned-xp">
                      +{project.xp_reward} XP
                    </span>
                  </div>
                </div>
                
                <div className="completed-project-stats">
                  <div className="completed-stat">
                    <span className="stat-label">Órák:</span>
                    <span className="stat-value">{project.sessions_completed}</span>
                  </div>
                  <div className="completed-stat">
                    <span className="stat-label">Haladás:</span>
                    <span className="stat-value">{Math.round(project.completion_percentage)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Project History Summary */}
      {projectSummary && (
        <section className="project-summary-section">
          <h2>📈 Projekt Összesítő</h2>
          
          <div className="summary-cards">
            <div className="summary-card total">
              <div className="summary-icon">🎯</div>
              <div className="summary-content">
                <div className="summary-number">{projectSummary.total_projects}</div>
                <div className="summary-label">Összes Projekt</div>
              </div>
            </div>
            
            <div className="summary-card completed">
              <div className="summary-icon">✅</div>
              <div className="summary-content">
                <div className="summary-number">{projectSummary.completed_projects?.length || 0}</div>
                <div className="summary-label">Befejezett</div>
              </div>
            </div>
            
            <div className="summary-card xp">
              <div className="summary-icon">⭐</div>
              <div className="summary-content">
                <div className="summary-number">{projectSummary.total_xp_earned}</div>
                <div className="summary-label">Összesen XP</div>
              </div>
            </div>
            
            <div className="summary-card sessions">
              <div className="summary-icon">⏱️</div>
              <div className="summary-content">
                <div className="summary-number">{projectSummary.total_sessions}</div>
                <div className="summary-label">Összes Óra</div>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default MyProjects;