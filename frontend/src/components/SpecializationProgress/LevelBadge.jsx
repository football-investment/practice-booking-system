import React from 'react';
import './LevelBadge.css';

/**
 * LevelBadge Component
 * Displays a visual badge/icon representing the student's current level
 */
const LevelBadge = ({ specializationId, level, levelName, color }) => {
  const getBeltEmoji = (level) => {
    const belts = {
      1: '🤍', // White
      2: '💛', // Yellow
      3: '💚', // Green
      4: '💙', // Blue
      5: '🤎', // Brown
      6: '🩶', // Grey
      7: '🖤', // Black
      8: '❤️'  // Red
    };
    return belts[level] || '⭐';
  };

  const getSpecializationIcon = () => {
    const icons = {
      PLAYER: getBeltEmoji(level),
      COACH: '⚽',
      INTERNSHIP: '💼'
    };
    return icons[specializationId] || '⭐';
  };

  // Convert hex color to rgba with 20% opacity for background
  const hexToRgba = (hex, alpha = 0.2) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  return (
    <div
      className="level-badge"
      style={{
        '--badge-color': color,
        backgroundColor: hexToRgba(color, 0.2)
      }}
    >
      <div className="level-badge__icon">
        <span className="level-badge__emoji">{getSpecializationIcon()}</span>
        <div className="level-badge__level-number">{level}</div>
      </div>
      <div className="level-badge__info">
        <div className="level-badge__level-text">Level {level}</div>
        <div className="level-badge__name">{levelName}</div>
      </div>
    </div>
  );
};

export default LevelBadge;
