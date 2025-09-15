import React from 'react';
import './MilestoneTracker.css';

const MilestoneTracker = ({ milestones = [], overallProgress = 0, compact = false }) => {
  const getStatusIcon = (status) => {
    const icons = {
      pending: '⏳',
      in_progress: '🔄',
      submitted: '📤',
      approved: '✅',
      rejected: '❌'
    };
    return icons[status] || '⏳';
  };

  const getStatusText = (status) => {
    const texts = {
      pending: 'Függőben',
      in_progress: 'Folyamatban',
      submitted: 'Beküldve',
      approved: 'Jóváhagyva',
      rejected: 'Elutasítva'
    };
    return texts[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#6b7280',
      in_progress: '#f59e0b',
      submitted: '#3b82f6',
      approved: '#10b981',
      rejected: '#ef4444'
    };
    return colors[status] || '#6b7280';
  };

  const formatDate = (dateString) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString('hu-HU');
  };

  if (compact) {
    return (
      <div className="milestone-tracker compact">
        <div className="overall-progress">
          <div className="progress-header">
            <span className="progress-label">Projekt haladás</span>
            <span className="progress-percentage">{Math.round(overallProgress)}%</span>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${overallProgress}%` }}
            ></div>
          </div>
        </div>
        
        <div className="milestones-summary">
          {milestones.slice(0, 3).map((milestone, index) => (
            <div key={milestone.id} className="milestone-chip">
              <span className="milestone-icon">{getStatusIcon(milestone.status)}</span>
              <span className="milestone-title-short">{milestone.milestone_title}</span>
            </div>
          ))}
          {milestones.length > 3 && (
            <div className="milestone-chip more">
              <span>+{milestones.length - 3} további</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="milestone-tracker">
      <div className="tracker-header">
        <h3>📋 Projekt mérföldkövek</h3>
        <div className="overall-progress">
          <span className="progress-label">Összesített haladás:</span>
          <div className="progress-container">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${overallProgress}%` }}
              ></div>
            </div>
            <span className="progress-text">{Math.round(overallProgress)}%</span>
          </div>
        </div>
      </div>

      <div className="milestones-list">
        {milestones.map((milestone, index) => (
          <div 
            key={milestone.id} 
            className={`milestone-item ${milestone.status}`}
          >
            <div className="milestone-indicator">
              <div className="milestone-number">{index + 1}</div>
              <div 
                className="milestone-status-icon"
                style={{ color: getStatusColor(milestone.status) }}
              >
                {getStatusIcon(milestone.status)}
              </div>
            </div>
            
            <div className="milestone-content">
              <div className="milestone-header">
                <h4 className="milestone-title">{milestone.milestone_title}</h4>
                <div 
                  className="milestone-status-badge"
                  style={{ backgroundColor: getStatusColor(milestone.status) }}
                >
                  {getStatusText(milestone.status)}
                </div>
              </div>
              
              <div className="milestone-details">
                <div className="milestone-progress">
                  <div className="detail-item">
                    <span className="detail-label">Befejezett órák:</span>
                    <span className="detail-value">
                      {milestone.sessions_completed} / {milestone.sessions_required}
                    </span>
                  </div>
                  
                  {milestone.submitted_at && (
                    <div className="detail-item">
                      <span className="detail-label">Beküldve:</span>
                      <span className="detail-value">{formatDate(milestone.submitted_at)}</span>
                    </div>
                  )}
                </div>
                
                <div className="sessions-progress">
                  <div className="sessions-bar">
                    <div 
                      className="sessions-fill"
                      style={{ 
                        width: `${(milestone.sessions_completed / milestone.sessions_required) * 100}%`,
                        backgroundColor: getStatusColor(milestone.status)
                      }}
                    ></div>
                  </div>
                </div>
                
                {milestone.instructor_feedback && (
                  <div className="instructor-feedback">
                    <div className="feedback-header">
                      <span className="feedback-icon">💬</span>
                      <span className="feedback-label">Oktató visszajelzés:</span>
                    </div>
                    <p className="feedback-text">{milestone.instructor_feedback}</p>
                  </div>
                )}
              </div>
            </div>
            
            {index < milestones.length - 1 && (
              <div className="milestone-connector"></div>
            )}
          </div>
        ))}
      </div>
      
      {milestones.length === 0 && (
        <div className="no-milestones">
          <p>📋 Még nincsenek mérföldkövek ehhez a projekthez.</p>
        </div>
      )}
    </div>
  );
};

export default MilestoneTracker;