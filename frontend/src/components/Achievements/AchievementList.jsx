import React, { useState, useEffect } from 'react';
import AchievementIcon from './AchievementIcon';
import AchievementCard from './AchievementCard';
import AchievementModal from './AchievementModal';
import achievementService from '../../services/achievementService';
import './AchievementList.css';

/**
 * AchievementList Component
 * Displays all achievements for a specialization (earned and locked)
 */
const AchievementList = ({ specializationId }) => {
  const [loading, setLoading] = useState(true);
  const [earnedAchievements, setEarnedAchievements] = useState([]);
  const [unlockedList, setUnlockedList] = useState([]);
  const [lockedList, setLockedList] = useState([]);
  const [selectedAchievement, setSelectedAchievement] = useState(null);
  const [selectedEarned, setSelectedEarned] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'

  useEffect(() => {
    fetchAchievements();
  }, [specializationId]);

  const fetchAchievements = async () => {
    try {
      setLoading(true);
      const response = await achievementService.getMyAchievements();

      if (response.success) {
        const earned = response.data || [];
        setEarnedAchievements(earned);

        // Categorize achievements
        const { unlocked, locked } = achievementService.categorizeAchievements(
          earned,
          specializationId
        );

        // Match earned achievements with their data
        const unlockedWithData = unlocked.map(ach => {
          const earnedAch = earned.find(
            e => e.specialization_id === specializationId && e.badge_type === ach.id
          );
          return {
            ...ach,
            earnedDate: earnedAch?.earned_at
          };
        });

        setUnlockedList(unlockedWithData);
        setLockedList(locked);
      }
    } catch (error) {
      console.error('Error fetching achievements:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAchievementClick = (achievement, earned, earnedDate = null) => {
    setSelectedAchievement(achievement);
    setSelectedEarned(earned);
    setSelectedDate(earnedDate);
  };

  const closeModal = () => {
    setSelectedAchievement(null);
    setSelectedEarned(false);
    setSelectedDate(null);
  };

  const completionPercentage = achievementService.getCompletionPercentage(
    earnedAchievements,
    specializationId
  );

  if (loading) {
    return (
      <div className="achievement-list achievement-list--loading">
        <div className="achievement-list__loader">
          <div className="achievement-list__spinner"></div>
          <p>Loading achievements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="achievement-list">
      {/* Header */}
      <div className="achievement-list__header">
        <div className="achievement-list__title-section">
          <h2 className="achievement-list__title">
            🏆 Your Achievements
          </h2>
          <div className="achievement-list__progress">
            <span className="achievement-list__count">
              {unlockedList.length} / {unlockedList.length + lockedList.length}
            </span>
            <span className="achievement-list__percentage">({completionPercentage}%)</span>
          </div>
        </div>

        <div className="achievement-list__controls">
          <button
            className={`achievement-list__view-btn ${viewMode === 'grid' ? 'achievement-list__view-btn--active' : ''}`}
            onClick={() => setViewMode('grid')}
            title="Grid view"
          >
            ⊞
          </button>
          <button
            className={`achievement-list__view-btn ${viewMode === 'list' ? 'achievement-list__view-btn--active' : ''}`}
            onClick={() => setViewMode('list')}
            title="List view"
          >
            ☰
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="achievement-list__progress-bar">
        <div
          className="achievement-list__progress-fill"
          style={{ width: `${completionPercentage}%` }}
        ></div>
      </div>

      {/* Unlocked Achievements */}
      {unlockedList.length > 0 && (
        <div className="achievement-list__section">
          <h3 className="achievement-list__section-title">
            ✨ Unlocked ({unlockedList.length})
          </h3>

          {viewMode === 'grid' ? (
            <div className="achievement-list__grid">
              {unlockedList.map((ach, index) => (
                <AchievementIcon
                  key={index}
                  achievement={ach}
                  earned={true}
                  onClick={() => handleAchievementClick(ach, true, ach.earnedDate)}
                />
              ))}
            </div>
          ) : (
            <div className="achievement-list__cards">
              {unlockedList.map((ach, index) => (
                <div
                  key={index}
                  onClick={() => handleAchievementClick(ach, true, ach.earnedDate)}
                  style={{ cursor: 'pointer' }}
                >
                  <AchievementCard
                    achievement={ach}
                    earned={true}
                    earnedDate={ach.earnedDate}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Locked Achievements */}
      {lockedList.length > 0 && (
        <div className="achievement-list__section">
          <h3 className="achievement-list__section-title" style={{ marginBottom: '56px' }}>
            <span className="achievement-list__section-icon" style={{ position: 'relative', top: '2px', lineHeight: '1' }}>🔒</span>
            <span>Locked ({lockedList.length})</span>
          </h3>

          {viewMode === 'grid' ? (
            <div className="achievement-list__grid">
              {lockedList.map((ach, index) => (
                <AchievementIcon
                  key={index}
                  achievement={ach}
                  earned={false}
                  onClick={() => handleAchievementClick(ach, false)}
                />
              ))}
            </div>
          ) : (
            <div className="achievement-list__cards">
              {lockedList.map((ach, index) => (
                <div
                  key={index}
                  onClick={() => handleAchievementClick(ach, false)}
                  style={{ cursor: 'pointer' }}
                >
                  <AchievementCard achievement={ach} earned={false} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {unlockedList.length === 0 && lockedList.length === 0 && (
        <div className="achievement-list__empty">
          <div className="achievement-list__empty-icon">🎯</div>
          <p>No achievements available for this specialization yet.</p>
        </div>
      )}

      {/* Modal */}
      {selectedAchievement && (
        <AchievementModal
          achievement={selectedAchievement}
          earned={selectedEarned}
          earnedDate={selectedDate}
          onClose={closeModal}
        />
      )}
    </div>
  );
};

export default AchievementList;
