import React, { useState, useEffect } from 'react';
import LevelBadge from './LevelBadge';
import XPProgressBar from './XPProgressBar';
import NextLevelInfo from './NextLevelInfo';
import specializationService from '../../services/specializationService';
import './ProgressCard.css';

/**
 * ProgressCard Component
 * Main component displaying student's specialization progress
 */
const ProgressCard = ({ specializationId, autoRefresh = false }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [progressData, setProgressData] = useState(null);
  const [theme, setTheme] = useState(null);

  useEffect(() => {
    fetchProgress();
    setTheme(specializationService.getSpecializationTheme(specializationId));

    // Auto-refresh every 30 seconds if enabled
    if (autoRefresh) {
      const interval = setInterval(fetchProgress, 30000);
      return () => clearInterval(interval);
    }
  }, [specializationId, autoRefresh]);

  const fetchProgress = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await specializationService.getMyProgress(specializationId);

      if (response.success && response.data) {
        setProgressData(response.data);
      } else {
        setError('No progress data available');
      }
    } catch (err) {
      console.error('Error fetching progress:', err);
      setError('Failed to load progress data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="progress-card progress-card--loading">
        <div className="progress-card__loader">
          <div className="progress-card__spinner"></div>
          <p>Loading progress...</p>
        </div>
      </div>
    );
  }

  if (error || !progressData) {
    return (
      <div className="progress-card progress-card--error">
        <div className="progress-card__error">
          <span className="progress-card__error-icon">⚠️</span>
          <p>{error || 'No progress data available'}</p>
          <button onClick={fetchProgress} className="progress-card__retry-btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const { current_level, next_level, total_xp, completed_sessions, completed_projects, progress_percentage } = progressData;
  const levelColor = specializationService.getLevelColor(specializationId, current_level.level);

  return (
    <div
      className="progress-card"
      style={{
        '--theme-primary': theme?.primary || '#2196F3',
        '--theme-gradient': theme?.gradient || 'linear-gradient(135deg, #2196F3 0%, #42A5F5 100%)'
      }}
    >
      {/* Header */}
      <div className="progress-card__header">
        <div className="progress-card__header-icon">{theme?.icon || '⭐'}</div>
        <h2 className="progress-card__title">{theme?.name || 'Specialization'}</h2>
        <button
          className="progress-card__refresh-btn"
          onClick={fetchProgress}
          title="Refresh progress"
        >
          🔄
        </button>
      </div>

      {/* Current Level Badge */}
      <LevelBadge
        specializationId={specializationId}
        level={current_level.level}
        levelName={current_level.name}
        color={levelColor}
      />

      {/* XP Progress Bar */}
      {next_level && (
        <XPProgressBar
          currentXP={total_xp}
          requiredXP={next_level.required_xp}
          percentage={progress_percentage}
          color={theme?.primary || '#2196F3'}
        />
      )}

      {/* Stats Grid */}
      <div className="progress-card__stats">
        <div className="progress-card__stat">
          <div className="progress-card__stat-icon">⚡</div>
          <div className="progress-card__stat-content">
            <div className="progress-card__stat-value">{total_xp.toLocaleString()}</div>
            <div className="progress-card__stat-label">Total XP</div>
          </div>
        </div>

        <div className="progress-card__stat">
          <div className="progress-card__stat-icon">📚</div>
          <div className="progress-card__stat-content">
            <div className="progress-card__stat-value">{completed_sessions}</div>
            <div className="progress-card__stat-label">Sessions</div>
          </div>
        </div>

        {specializationId === 'INTERNSHIP' && (
          <div className="progress-card__stat">
            <div className="progress-card__stat-icon">🚀</div>
            <div className="progress-card__stat-content">
              <div className="progress-card__stat-value">{completed_projects}</div>
              <div className="progress-card__stat-label">Projects</div>
            </div>
          </div>
        )}
      </div>

      {/* Next Level Info */}
      <NextLevelInfo
        nextLevel={next_level}
        currentProgress={{ total_xp, completed_sessions, completed_projects }}
        specializationId={specializationId}
      />
    </div>
  );
};

export default ProgressCard;
