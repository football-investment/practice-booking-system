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

      console.log('🔍 ProgressCard: Fetching progress for specialization:', specializationId);
      const response = await specializationService.getMyProgress(specializationId);
      console.log('✅ ProgressCard: API Response:', response);

      // The response is the progress data object directly (not wrapped in { success, data })
      // because specializationService already extracts response.data
      if (response && response.student_id) {
        console.log('✅ ProgressCard: Progress data loaded:', response);
        setProgressData(response);
      } else {
        console.warn('⚠️ ProgressCard: Invalid response structure:', response);
        setError('No progress data available');
      }
    } catch (err) {
      console.error('❌ ProgressCard: Error fetching progress:', err);
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

  const {
    current_level,
    next_level,
    total_xp,
    completed_sessions,
    completed_projects,
    progress_percentage,
    theory_hours_completed = 0,
    practice_hours_completed = 0,
    theory_hours_needed = 0,
    practice_hours_needed = 0
  } = progressData;

  const levelColor = specializationService.getLevelColor(specializationId, current_level.level);

  // COACH-specific: Extract theory/practice hours requirements
  const theoryHoursRequired = current_level?.theory_hours || 0;
  const practiceHoursRequired = current_level?.practice_hours || 0;

  console.log('🎨 ProgressCard: Level color for', specializationId, 'Level', current_level.level, '=', levelColor);
  console.log('📚 ProgressCard: COACH hours -', {
    theory: `${theory_hours_completed}/${theoryHoursRequired}`,
    practice: `${practice_hours_completed}/${practiceHoursRequired}`
  });

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

      {/* Stats - Simple Text Only */}
      <div className="progress-card__stats">
        <div className="progress-card__stat">
          <span className="progress-card__stat-icon">⚡</span>
          <span className="progress-card__stat-value">{total_xp.toLocaleString()}</span>
          <span className="progress-card__stat-label">Total XP</span>
        </div>

        <div className="progress-card__stat">
          <span className="progress-card__stat-icon">📚</span>
          <span className="progress-card__stat-value">{completed_sessions}</span>
          <span className="progress-card__stat-label">Sessions</span>
        </div>

        {specializationId === 'INTERNSHIP' && (
          <div className="progress-card__stat">
            <span className="progress-card__stat-icon">🚀</span>
            <span className="progress-card__stat-value">{completed_projects}</span>
            <span className="progress-card__stat-label">Projects</span>
          </div>
        )}
      </div>

      {/* COACH-Specific: Theory/Practice Hours */}
      {specializationId === 'COACH' && theoryHoursRequired > 0 && practiceHoursRequired > 0 && (
        <div className="progress-card__hours-section">
          <h3 className="progress-card__hours-title">📖 Képzési Órák</h3>

          {/* Theory Hours */}
          <div className="progress-card__hours-item">
            <div className="progress-card__hours-header">
              <span className="progress-card__hours-icon">📚</span>
              <span className="progress-card__hours-label">Elméleti Képzés</span>
              <span className="progress-card__hours-value">
                {theory_hours_completed} / {theoryHoursRequired} óra
              </span>
            </div>
            <div className="progress-card__hours-bar">
              <div
                className="progress-card__hours-fill progress-card__hours-fill--theory"
                style={{
                  width: `${Math.min(100, (theory_hours_completed / theoryHoursRequired) * 100)}%`
                }}
              />
            </div>
          </div>

          {/* Practice Hours */}
          <div className="progress-card__hours-item">
            <div className="progress-card__hours-header">
              <span className="progress-card__hours-icon">⚽</span>
              <span className="progress-card__hours-label">Gyakorlati Képzés</span>
              <span className="progress-card__hours-value">
                {practice_hours_completed} / {practiceHoursRequired} óra
              </span>
            </div>
            <div className="progress-card__hours-bar">
              <div
                className="progress-card__hours-fill progress-card__hours-fill--practice"
                style={{
                  width: `${Math.min(100, (practice_hours_completed / practiceHoursRequired) * 100)}%`
                }}
              />
            </div>
          </div>
        </div>
      )}

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
