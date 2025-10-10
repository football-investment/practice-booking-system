import React from 'react';
import achievementService from '../../services/achievementService';
import './AchievementCard.css';

/**
 * AchievementCard Component
 * Displays detailed information about a single achievement
 */
const AchievementCard = ({ achievement, earned = false, earnedDate = null }) => {
  const badgeColor = achievementService.getBadgeColor(achievement.badge_type || achievement.id);

  return (
    <div
      className={`achievement-card ${earned ? 'achievement-card--earned' : 'achievement-card--locked'}`}
      style={{ '--badge-color': badgeColor }}
    >
      <div className="achievement-card__icon-container">
        <div className="achievement-card__icon">
          {earned ? achievement.icon : '🔒'}
        </div>
        {earned && (
          <div className="achievement-card__badge">✓</div>
        )}
      </div>

      <div className="achievement-card__content">
        <h4 className="achievement-card__title">{achievement.title}</h4>
        <p className="achievement-card__description">{achievement.description}</p>

        {achievement.requirement && (
          <div className="achievement-card__requirement">
            <span className="achievement-card__requirement-icon">🎯</span>
            <span className="achievement-card__requirement-text">{achievement.requirement}</span>
          </div>
        )}

        {earned && earnedDate && (
          <div className="achievement-card__earned-date">
            <span className="achievement-card__earned-icon">🎉</span>
            <span>Earned: {achievementService.formatEarnedDate(earnedDate)}</span>
          </div>
        )}

        {!earned && (
          <div className="achievement-card__locked-message">
            <span>🔒 Not yet unlocked</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default AchievementCard;
