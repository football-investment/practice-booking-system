import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './GamificationProfile.css';

const GamificationProfile = () => {
  const [achievements, setAchievements] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadGamificationData();
  }, []);

  const loadGamificationData = async () => {
    try {
      setLoading(true);
      const response = await apiService.get('/gamification/my-achievements');
      setAchievements(response.achievements || []);
      setStats(response.stats || { total_xp: 0, level: 1 });
      setError(null);
    } catch (err) {
      console.error('Failed to load achievements:', err);
      setError('Failed to load achievements. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const calculateLevel = (totalXP) => {
    return Math.floor(totalXP / 1000) + 1;
  };

  const calculateLevelProgress = (totalXP) => {
    const currentLevel = calculateLevel(totalXP);
    const xpForCurrentLevel = (currentLevel - 1) * 1000;
    const xpForNextLevel = currentLevel * 1000;
    const progressInLevel = totalXP - xpForCurrentLevel;
    const percentage = (progressInLevel / (xpForNextLevel - xpForCurrentLevel)) * 100;
    return Math.min(100, Math.max(0, percentage));
  };

  const getAchievementIcon = (badgeType) => {
    const icons = {
      FIRST_STEPS: '👶',
      EARLY_BIRD: '🌅',
      RISING_STAR: '⭐',
      QUIZ_MASTER: '🎓',
      PROJECT_PIONEER: '🚀',
      ATTENDANCE_ACE: '📅',
      FEEDBACK_GURU: '💬',
      STREAK_KEEPER: '🔥',
      MILESTONE_50: '🎯',
      MILESTONE_100: '🏆',
      COMMUNITY_HELPER: '🤝',
      PERFECT_SCORE: '💯',
      FAST_LEARNER: '⚡',
      ACHIEVEMENT_HUNTER: '🎖️'
    };
    return icons[badgeType] || '🏅';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="gamification-container">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading achievements...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="gamification-container">
        <div className="error-state">
          <span className="error-icon">⚠️</span>
          <p>{error}</p>
          <button onClick={loadGamificationData} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const totalXP = stats?.total_xp || 0;
  const currentLevel = calculateLevel(totalXP);
  const levelProgress = calculateLevelProgress(totalXP);
  const earnedAchievements = achievements.filter(a => a.earned_at);
  const unlockedAchievements = achievements.filter(a => !a.earned_at);

  return (
    <div className="gamification-container">
      <div className="gamification-header">
        <h1>🏆 Your Achievements</h1>
        <p className="subtitle">Track your progress and unlock rewards</p>
      </div>

      <div className="stats-overview">
        <div className="stat-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-content">
            <div className="stat-value">{totalXP.toLocaleString()}</div>
            <div className="stat-label">Total XP</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-content">
            <div className="stat-value">Level {currentLevel}</div>
            <div className="stat-label">Current Level</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🏅</div>
          <div className="stat-content">
            <div className="stat-value">{earnedAchievements.length}</div>
            <div className="stat-label">Achievements</div>
          </div>
        </div>
      </div>

      <div className="level-progress-section">
        <div className="progress-header">
          <span className="progress-label">Progress to Level {currentLevel + 1}</span>
          <span className="progress-value">
            {totalXP % 1000} / 1000 XP
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${levelProgress}%` }}
          ></div>
        </div>
        <div className="progress-percentage">
          {Math.round(levelProgress)}% Complete
        </div>
      </div>

      {earnedAchievements.length > 0 && (
        <div className="achievements-section">
          <h2>🎖️ Earned Achievements ({earnedAchievements.length})</h2>
          <div className="achievements-grid">
            {earnedAchievements.map((achievement) => (
              <div key={achievement.id} className="achievement-card earned">
                <div className="achievement-icon">
                  {getAchievementIcon(achievement.badge_type)}
                </div>
                <h3>{achievement.title}</h3>
                <p className="achievement-description">{achievement.description}</p>
                <div className="achievement-footer">
                  <span className="xp-reward">+{achievement.xp_reward} XP</span>
                  <span className="earned-date">
                    {formatDate(achievement.earned_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {unlockedAchievements.length > 0 && (
        <div className="achievements-section">
          <h2>🔒 Locked Achievements ({unlockedAchievements.length})</h2>
          <div className="achievements-grid">
            {unlockedAchievements.map((achievement) => (
              <div key={achievement.id} className="achievement-card locked">
                <div className="achievement-icon grayscale">
                  {getAchievementIcon(achievement.badge_type)}
                </div>
                <h3>{achievement.title}</h3>
                <p className="achievement-description">{achievement.description}</p>
                <div className="achievement-footer">
                  <span className="xp-reward">+{achievement.xp_reward} XP</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {achievements.length === 0 && (
        <div className="empty-state">
          <h2>No achievements yet</h2>
          <p>Start learning to unlock achievements and earn XP!</p>
        </div>
      )}

      <div className="gamification-footer">
        <button onClick={loadGamificationData} className="refresh-button">
          🔄 Refresh
        </button>
      </div>
    </div>
  );
};

export default GamificationProfile;
