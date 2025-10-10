import React from 'react';
import './XPProgressBar.css';

/**
 * XPProgressBar Component
 * Animated progress bar showing XP progress towards next level
 */
const XPProgressBar = ({ currentXP, requiredXP, percentage, color }) => {
  const formatXP = (xp) => {
    if (xp >= 1000000) return `${(xp / 1000000).toFixed(1)}M`;
    if (xp >= 1000) return `${(xp / 1000).toFixed(1)}K`;
    return xp.toString();
  };

  return (
    <div className="xp-progress-bar">
      <div className="xp-progress-bar__header">
        <div className="xp-progress-bar__label">
          <span className="xp-progress-bar__icon">⚡</span>
          <span>Experience Points</span>
        </div>
        <div className="xp-progress-bar__stats">
          <span className="xp-progress-bar__current">{formatXP(currentXP)}</span>
          <span className="xp-progress-bar__separator">/</span>
          <span className="xp-progress-bar__required">{formatXP(requiredXP)}</span>
          <span className="xp-progress-bar__percentage">({percentage}%)</span>
        </div>
      </div>

      <div className="xp-progress-bar__track">
        <div
          className="xp-progress-bar__fill"
          style={{
            width: `${percentage}%`,
            background: `linear-gradient(90deg, ${color} 0%, ${color}dd 100%)`
          }}
        >
          <div className="xp-progress-bar__shine"></div>
        </div>
      </div>

      <div className="xp-progress-bar__milestones">
        {[0, 25, 50, 75, 100].map((milestone) => (
          <div
            key={milestone}
            className={`xp-progress-bar__milestone ${
              percentage >= milestone ? 'xp-progress-bar__milestone--reached' : ''
            }`}
            style={{ left: `${milestone}%` }}
          >
            <div className="xp-progress-bar__milestone-marker"></div>
            {milestone > 0 && milestone < 100 && (
              <div className="xp-progress-bar__milestone-label">{milestone}%</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default XPProgressBar;
