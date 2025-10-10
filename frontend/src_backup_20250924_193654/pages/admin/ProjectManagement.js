import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './ProjectManagement.css';

const ProjectManagement = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [milestoneProgress, setMilestoneProgress] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('projects');
  const [theme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadData();
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

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const projectsData = await apiService.getProjects();
      setProjects(projectsData.projects || []);
      
    } catch (err) {
      console.error('Failed to load project management data:', err);
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadProjectDetails = async (projectId) => {
    try {
      // Load enrollments and milestone progress for selected project
      // Note: These would need specific API endpoints for admin/instructor access
      setSelectedProject(projectId);
      
      // For now, just mock some data structure
      setEnrollments([]);
      setMilestoneProgress([]);
      
    } catch (err) {
      console.error('Failed to load project details:', err);
      setError(err.message || 'Failed to load project details');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Nincs dátum';
    return new Date(dateString).toLocaleDateString('hu-HU');
  };

  const getStatusColor = (status) => {
    const colors = {
      active: '#10b981',
      completed: '#3b82f6',
      archived: '#6b7280'
    };
    return colors[status] || '#6b7280';
  };

  const getStatusText = (status) => {
    const texts = {
      active: 'Aktív',
      completed: 'Befejezett',
      archived: 'Archivált'
    };
    return texts[status] || status;
  };

  if (loading) {
    return (
      <div className="project-management-page">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Projekt adatok betöltése...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="project-management-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>📁 Projekt Menedzsment</h1>
          <p>Projektek, jelentkezések és mérföldkövek kezelése</p>
        </div>
        <div className="header-actions">
          <button 
            onClick={loadData} 
            disabled={loading} 
            className="refresh-btn"
          >
            🔄 Frissítés
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button 
          className={`tab-btn ${activeTab === 'projects' ? 'active' : ''}`}
          onClick={() => setActiveTab('projects')}
        >
          📁 Projektek ({projects.length})
        </button>
        <button 
          className={`tab-btn ${activeTab === 'enrollments' ? 'active' : ''}`}
          onClick={() => setActiveTab('enrollments')}
        >
          👥 Jelentkezések
        </button>
        <button 
          className={`tab-btn ${activeTab === 'milestones' ? 'active' : ''}`}
          onClick={() => setActiveTab('milestones')}
        >
          🏁 Mérföldkövek
        </button>
      </div>

      {/* Projects Tab */}
      {activeTab === 'projects' && (
        <div className="projects-section">
          <div className="section-header">
            <h2>📁 Projektek Áttekintése</h2>
          </div>
          
          <div className="projects-grid">
            {projects.map(project => (
              <div key={project.id} className="project-admin-card">
                <div className="project-header">
                  <h3>{project.title}</h3>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(project.status) }}
                  >
                    {getStatusText(project.status)}
                  </span>
                </div>
                
                <div className="project-description">
                  <p>{project.description}</p>
                </div>
                
                <div className="project-stats">
                  <div className="stat-item">
                    <span className="stat-label">Jelentkezők:</span>
                    <span className="stat-value">
                      {project.enrolled_count} / {project.max_participants}
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Szükséges órák:</span>
                    <span className="stat-value">{project.required_sessions}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">XP jutalom:</span>
                    <span className="stat-value">{project.xp_reward}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Határidő:</span>
                    <span className="stat-value">{formatDate(project.deadline)}</span>
                  </div>
                </div>
                
                <div className="project-progress">
                  <div className="progress-info">
                    <span>Betöltöttség</span>
                    <span>{Math.round((project.enrolled_count / project.max_participants) * 100)}%</span>
                  </div>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ 
                        width: `${(project.enrolled_count / project.max_participants) * 100}%` 
                      }}
                    ></div>
                  </div>
                </div>
                
                <div className="project-actions">
                  <button 
                    onClick={() => loadProjectDetails(project.id)}
                    className="details-btn"
                  >
                    📊 Részletek
                  </button>
                  <button className="manage-btn">
                    ⚙️ Kezelés
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Enrollments Tab */}
      {activeTab === 'enrollments' && (
        <div className="enrollments-section">
          <div className="section-header">
            <h2>👥 Projekt Jelentkezések</h2>
          </div>
          
          <div className="enrollment-placeholder">
            <div className="placeholder-content">
              <div className="placeholder-icon">👥</div>
              <h3>Jelentkezések kezelése</h3>
              <p>Válasszon egy projektet a jelentkezések megtekintéséhez és kezeléséhez.</p>
              <div className="placeholder-features">
                <div className="feature-item">✅ Jelentkezések jóváhagyása</div>
                <div className="feature-item">❌ Jelentkezések elutasítása</div>
                <div className="feature-item">📊 Résztvevők haladásának követése</div>
                <div className="feature-item">💬 Visszajelzések küldése</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Milestones Tab */}
      {activeTab === 'milestones' && (
        <div className="milestones-section">
          <div className="section-header">
            <h2>🏁 Mérföldkövek Kezelése</h2>
          </div>
          
          <div className="milestone-placeholder">
            <div className="placeholder-content">
              <div className="placeholder-icon">🏁</div>
              <h3>Mérföldkövek értékelése</h3>
              <p>Itt kezelheti a diákok projekt mérföldköveinek státuszát és adhat visszajelzést.</p>
              <div className="placeholder-features">
                <div className="feature-item">✅ Mérföldkövek jóváhagyása</div>
                <div className="feature-item">❌ Mérföldkövek elutasítása</div>
                <div className="feature-item">💬 Részletes visszajelzés</div>
                <div className="feature-item">📈 Haladás követése</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Summary Statistics */}
      <div className="summary-statistics">
        <h2>📊 Összegzés</h2>
        <div className="stats-grid">
          <div className="summary-card">
            <div className="summary-icon">📁</div>
            <div className="summary-content">
              <span className="summary-number">{projects.length}</span>
              <span className="summary-label">Összes projekt</span>
            </div>
          </div>
          
          <div className="summary-card">
            <div className="summary-icon">✅</div>
            <div className="summary-content">
              <span className="summary-number">
                {projects.filter(p => p.status === 'active').length}
              </span>
              <span className="summary-label">Aktív projekt</span>
            </div>
          </div>
          
          <div className="summary-card">
            <div className="summary-icon">👥</div>
            <div className="summary-content">
              <span className="summary-number">
                {projects.reduce((sum, p) => sum + p.enrolled_count, 0)}
              </span>
              <span className="summary-label">Összes jelentkező</span>
            </div>
          </div>
          
          <div className="summary-card">
            <div className="summary-icon">📈</div>
            <div className="summary-content">
              <span className="summary-number">
                {Math.round(
                  projects.reduce((sum, p) => sum + (p.enrolled_count / p.max_participants), 0) / 
                  projects.length * 100
                )}%
              </span>
              <span className="summary-label">Átlag betöltöttség</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectManagement;