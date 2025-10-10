import React from 'react';
import AchievementCard from './AchievementCard';
import './AchievementModal.css';

/**
 * AchievementModal Component
 * Full-screen modal for viewing achievement details
 */
const AchievementModal = ({ achievement, earned, earnedDate, onClose }) => {
  if (!achievement) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="achievement-modal" onClick={handleBackdropClick}>
      <div className="achievement-modal__content">
        <button className="achievement-modal__close" onClick={onClose}>
          ✕
        </button>

        <div className="achievement-modal__header">
          <div className="achievement-modal__icon">
            {earned ? achievement.icon : '🔒'}
          </div>
          <h2 className="achievement-modal__title">{achievement.title}</h2>
        </div>

        <div className="achievement-modal__body">
          <AchievementCard
            achievement={achievement}
            earned={earned}
            earnedDate={earnedDate}
          />

          {!earned && achievement.requirement && (
            <div className="achievement-modal__hint">
              <h3>How to Unlock:</h3>
              <p>{achievement.description}</p>
              <div className="achievement-modal__requirement">
                <span className="achievement-modal__requirement-icon">🎯</span>
                <span>{achievement.requirement}</span>
              </div>
            </div>
          )}

          {earned && (
            <div className="achievement-modal__celebration">
              <div className="achievement-modal__confetti">🎊 🎉 ✨ 🌟 🎊</div>
              <p>Congratulations on earning this achievement!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AchievementModal;
