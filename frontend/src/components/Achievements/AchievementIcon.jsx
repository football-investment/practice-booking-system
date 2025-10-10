import React from 'react';
import './AchievementIcon.css';

/**
 * AchievementIcon Component
 * Displays a single achievement icon (locked or unlocked)
 */
const AchievementIcon = ({ achievement, earned, onClick }) => {
  return (
    <div
      className={`achievement-icon ${earned ? 'achievement-icon--earned' : 'achievement-icon--locked'}`}
      onClick={onClick}
      title={achievement.title}
    >
      <div className="achievement-icon__container">
        <div className="achievement-icon__emoji">
          {earned ? achievement.icon : '🔒'}
        </div>
        {earned && (
          <div className="achievement-icon__checkmark">✓</div>
        )}
      </div>
      <div className="achievement-icon__label">
        {achievement.title.replace(/[⚽🥋🏆🐉⚡🎓📋🏅👔♟️🚀💡💼🌟]/g, '').trim()}
      </div>
    </div>
  );
};

export default AchievementIcon;
