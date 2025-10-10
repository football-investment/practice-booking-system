import React from 'react';
import './NextLevelInfo.css';

/**
 * NextLevelInfo Component
 * Shows requirements and progress toward the next level
 */
const NextLevelInfo = ({ nextLevel, currentProgress, specializationId }) => {
  if (!nextLevel) {
    return (
      <div className="next-level-info next-level-info--max">
        <div className="next-level-info__crown">👑</div>
        <h3>Maximum Level Reached!</h3>
        <p>You've mastered this specialization. Keep practicing to maintain your skills!</p>
      </div>
    );
  }

  const xpRemaining = Math.max(0, nextLevel.required_xp - currentProgress.total_xp);
  const sessionsRemaining = Math.max(0, nextLevel.required_sessions - currentProgress.completed_sessions);
  const projectsRemaining = specializationId === 'INTERNSHIP'
    ? Math.max(0, (nextLevel.required_projects || 0) - currentProgress.completed_projects)
    : 0;

  const xpProgress = Math.min(100, (currentProgress.total_xp / nextLevel.required_xp) * 100);
  const sessionProgress = Math.min(100, (currentProgress.completed_sessions / nextLevel.required_sessions) * 100);

  return (
    <div className="next-level-info">
      <div className="next-level-info__header">
        <h3 className="next-level-info__title">
          🎯 Next Level: {nextLevel.level} - {nextLevel.name}
        </h3>
      </div>

      <div className="next-level-info__requirements">
        {/* XP Requirement */}
        <div className="next-level-info__requirement">
          <div className="next-level-info__requirement-header">
            <span className="next-level-info__requirement-icon">⚡</span>
            <span className="next-level-info__requirement-label">Experience Points</span>
            <span className={`next-level-info__requirement-status ${
              xpRemaining === 0 ? 'next-level-info__requirement-status--complete' : ''
            }`}>
              {xpRemaining === 0 ? '✅ Complete' : `${xpRemaining.toLocaleString()} needed`}
            </span>
          </div>
          <div className="next-level-info__requirement-bar">
            <div
              className="next-level-info__requirement-fill"
              style={{ width: `${xpProgress}%` }}
            ></div>
          </div>
          <div className="next-level-info__requirement-text">
            {currentProgress.total_xp.toLocaleString()} / {nextLevel.required_xp.toLocaleString()} XP
          </div>
        </div>

        {/* Sessions Requirement */}
        <div className="next-level-info__requirement">
          <div className="next-level-info__requirement-header">
            <span className="next-level-info__requirement-icon">📚</span>
            <span className="next-level-info__requirement-label">Training Sessions</span>
            <span className={`next-level-info__requirement-status ${
              sessionsRemaining === 0 ? 'next-level-info__requirement-status--complete' : ''
            }`}>
              {sessionsRemaining === 0 ? '✅ Complete' : `${sessionsRemaining} more needed`}
            </span>
          </div>
          <div className="next-level-info__requirement-bar">
            <div
              className="next-level-info__requirement-fill"
              style={{ width: `${sessionProgress}%` }}
            ></div>
          </div>
          <div className="next-level-info__requirement-text">
            {currentProgress.completed_sessions} / {nextLevel.required_sessions} sessions
          </div>
        </div>

        {/* Projects Requirement (Internship only) */}
        {specializationId === 'INTERNSHIP' && nextLevel.required_projects > 0 && (
          <div className="next-level-info__requirement">
            <div className="next-level-info__requirement-header">
              <span className="next-level-info__requirement-icon">🚀</span>
              <span className="next-level-info__requirement-label">Projects</span>
              <span className={`next-level-info__requirement-status ${
                projectsRemaining === 0 ? 'next-level-info__requirement-status--complete' : ''
              }`}>
                {projectsRemaining === 0 ? '✅ Complete' : `${projectsRemaining} more needed`}
              </span>
            </div>
            <div className="next-level-info__requirement-bar">
              <div
                className="next-level-info__requirement-fill"
                style={{
                  width: `${Math.min(100, (currentProgress.completed_projects / nextLevel.required_projects) * 100)}%`
                }}
              ></div>
            </div>
            <div className="next-level-info__requirement-text">
              {currentProgress.completed_projects} / {nextLevel.required_projects} projects
            </div>
          </div>
        )}
      </div>

      {/* Level Up Ready */}
      {xpRemaining === 0 && sessionsRemaining === 0 && projectsRemaining === 0 && (
        <div className="next-level-info__ready">
          <div className="next-level-info__ready-icon">🎉</div>
          <div className="next-level-info__ready-text">
            <strong>Ready to Level Up!</strong>
            <p>Complete your next activity to advance to Level {nextLevel.level}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default NextLevelInfo;
