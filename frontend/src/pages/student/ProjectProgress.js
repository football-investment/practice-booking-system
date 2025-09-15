import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import MilestoneTracker from '../../components/student/MilestoneTracker';
import './ProjectProgress.css';

const ProjectProgress = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState('');
  const [theme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadProjectProgress();
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

  const loadProjectProgress = async () => {
    try {
      setLoading(true);
      setError('');
      
      const progressData = await apiService.getProjectProgress(parseInt(id));
      setProgress(progressData);
      
    } catch (err) {
      console.error('Failed to load project progress:', err);
      setError(err.message || 'Failed to load project progress');
    } finally {
      setLoading(false);
    }
  };

  const getProgressStatusText = (status) => {
    const texts = {
      planning: 'Tervezés',
      in_progress: 'Folyamatban', 
      review: 'Értékelés alatt',
      completed: 'Befejezett',
      on_hold: 'Felfüggesztve'
    };
    return texts[status] || status;
  };

  const getProgressStatusColor = (status) => {
    const colors = {
      planning: '#6b7280',
      in_progress: '#f59e0b',
      review: '#3b82f6',
      completed: '#10b981',
      on_hold: '#ef4444'
    };
    return colors[status] || '#6b7280';
  };

  const getEnrollmentStatusText = (status) => {
    const texts = {
      active: 'Aktív',
      completed: 'Befejezett',
      dropped: 'Megszakított'
    };
    return texts[status] || status;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Nincs dátum';
    return new Date(dateString).toLocaleDateString('hu-HU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="project-progress-page">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Projekt haladás betöltése...</p>
        </div>
      </div>
    );
  }

  if (error || !progress) {
    return (
      <div className="project-progress-page">
        <div className="error-state">
          <h2>⚠️ Projekt haladás nem található</h2>
          <p>{error || 'A keresett projekt haladása nem található vagy nem érhető el.'}</p>
          <div className="error-actions">
            <button onClick={() => navigate('/student/projects')} className="back-btn">
              ← Vissza a projektekhez
            </button>
            <button onClick={() => navigate('/student/projects/my')} className="back-btn">
              🎯 Saját Projektek
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="project-progress-page">
      {/* Header */}
      <div className="page-header">
        <div className="header-navigation">
          <button onClick={() => navigate('/student/projects/my')} className="back-btn">
            ← Saját Projektek
          </button>
          <button onClick={() => navigate(`/student/projects/${id}`)} className="details-btn">
            📖 Projekt Részletek
          </button>
        </div>
        <div className="progress-status-info">
          <span 
            className="enrollment-status-badge"
            style={{ backgroundColor: progress.enrollment_status === 'active' ? '#10b981' : '#6b7280' }}
          >
            {getEnrollmentStatusText(progress.enrollment_status)}
          </span>
          <span 
            className="progress-status-badge"
            style={{ backgroundColor: getProgressStatusColor(progress.progress_status) }}
          >
            {getProgressStatusText(progress.progress_status)}
          </span>
        </div>
      </div>

      {/* Project Title */}
      <div className="project-title-section">
        <h1>📊 {progress.project_title}</h1>
        <p>Projekt haladásának részletes követése és mérföldkövek áttekintése</p>
      </div>

      {/* Progress Overview */}
      <div className="progress-overview">
        <div className="overview-card overall-progress">
          <h3>🎯 Összesített Haladás</h3>
          <div className="progress-visual">
            <div className="progress-circle-large">
              <div className="progress-inner-large">
                <span className="progress-percentage">{Math.round(progress.overall_progress)}%</span>
                <span className="progress-label">befejezve</span>
              </div>
              <svg className="progress-ring-large" width="160" height="160">
                <circle
                  className="progress-ring-background"
                  cx="80"
                  cy="80"
                  r="70"
                  strokeWidth="12"
                />
                <circle
                  className="progress-ring-progress"
                  cx="80"
                  cy="80"
                  r="70"
                  strokeWidth="12"
                  strokeDasharray={`${2 * Math.PI * 70}`}
                  strokeDashoffset={`${2 * Math.PI * 70 * (1 - progress.overall_progress / 100)}`}
                />
              </svg>
            </div>
          </div>
        </div>

        <div className="overview-stats">
          <div className="overview-card">
            <h3>⏱️ Órák Állapota</h3>
            <div className="stats-content">
              <div className="stat-item">
                <span className="stat-number">{progress.sessions_completed}</span>
                <span className="stat-label">Befejezett</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">{progress.sessions_remaining}</span>
                <span className="stat-label">Hátralévő</span>
              </div>
              <div className="sessions-progress-bar">
                <div className="sessions-bar">
                  <div 
                    className="sessions-fill"
                    style={{ 
                      width: `${(progress.sessions_completed / (progress.sessions_completed + progress.sessions_remaining)) * 100}%` 
                    }}
                  ></div>
                </div>
                <span className="sessions-text">
                  {progress.sessions_completed} / {progress.sessions_completed + progress.sessions_remaining}
                </span>
              </div>
            </div>
          </div>

          <div className="overview-card">
            <h3>🏁 Mérföldkövek</h3>
            <div className="stats-content">
              <div className="milestones-summary">
                {progress.milestone_progress.map(milestone => {
                  const getStatusIcon = (status) => {
                    const icons = {
                      pending: '⏳',
                      in_progress: '🔄',
                      submitted: '📤',
                      approved: '✅',
                      rejected: '❌'
                    };
                    return icons[status] || '⏳';
                  };

                  return (
                    <div key={milestone.id} className="milestone-summary-item">
                      <span className="milestone-icon">{getStatusIcon(milestone.status)}</span>
                      <span className="milestone-name">{milestone.milestone_title}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Next Milestone Highlight */}
      {progress.next_milestone && (
        <div className="next-milestone-section">
          <h2>🎯 Következő Mérföldkő</h2>
          <div className="next-milestone-card">
            <div className="milestone-info">
              <h3>{progress.next_milestone.title}</h3>
              <p className="milestone-description">{progress.next_milestone.description}</p>
              
              <div className="milestone-details">
                <div className="milestone-detail">
                  <span className="detail-icon">⏱️</span>
                  <span className="detail-text">
                    {progress.next_milestone.required_sessions} óra szükséges
                  </span>
                </div>
                <div className="milestone-detail">
                  <span className="detail-icon">⭐</span>
                  <span className="detail-text">
                    {progress.next_milestone.xp_reward} XP jutalom
                  </span>
                </div>
                <div className="milestone-detail">
                  <span className="detail-icon">📅</span>
                  <span className="detail-text">
                    Határidő: {formatDate(progress.next_milestone.deadline)}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="milestone-action">
              <div className="milestone-progress-indicator">
                <span className="progress-text">Kezdésre vár</span>
                <div className="action-arrow">→</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detailed Milestones */}
      <div className="milestones-section">
        <h2>📋 Részletes Mérföldkövek</h2>
        <MilestoneTracker 
          milestones={progress.milestone_progress}
          overallProgress={progress.overall_progress}
        />
      </div>

      {/* Progress Statistics */}
      <div className="progress-statistics">
        <h2>📈 Statisztikák</h2>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🎯</div>
            <div className="stat-content">
              <span className="stat-value">{Math.round(progress.completion_percentage)}%</span>
              <span className="stat-title">Befejezettség</span>
              <span className="stat-subtitle">Személyes haladás</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-content">
              <span className="stat-value">{Math.round(progress.overall_progress)}%</span>
              <span className="stat-title">Összesített</span>
              <span className="stat-subtitle">Teljes projekt állapot</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <span className="stat-value">
                {progress.milestone_progress.filter(m => m.status === 'approved').length}
              </span>
              <span className="stat-title">Jóváhagyott</span>
              <span className="stat-subtitle">Mérföldkövek</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">🔄</div>
            <div className="stat-content">
              <span className="stat-value">
                {progress.milestone_progress.filter(m => m.status === 'in_progress').length}
              </span>
              <span className="stat-title">Folyamatban</span>
              <span className="stat-subtitle">Mérföldkövek</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="page-actions">
        <button onClick={() => navigate('/student/projects/my')} className="secondary-btn">
          🎯 Saját Projektek
        </button>
        <button onClick={() => navigate(`/student/projects/${id}`)} className="secondary-btn">
          📖 Projekt Részletek
        </button>
        <button onClick={() => navigate('/student/projects')} className="secondary-btn">
          📁 Összes Projekt
        </button>
        <button onClick={loadProjectProgress} className="primary-btn">
          🔄 Frissítés
        </button>
      </div>
    </div>
  );
};

export default ProjectProgress;