import React from 'react';
import './InstructorProjectCard.css';

const InstructorProjectCard = ({ 
  project, 
  onViewDetails,
  onEdit, 
  onDelete,
  onManageStudents,
  onConfigureQuizzes
}) => {
  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'draft': return '📋';
      case 'active': return '🚀';
      case 'archived': return '📁';
      default: return '📁';
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'draft': return '#f59e0b';
      case 'active': return '#10b981';
      case 'archived': return '#6b7280';
      default: return '#6b7280';
    }
  };


  const formatDeadline = (deadline) => {
    if (!deadline) return 'No deadline';
    const date = new Date(deadline);
    const now = new Date();
    const diffTime = date - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) {
      return `Overdue by ${Math.abs(diffDays)} days`;
    } else if (diffDays === 0) {
      return 'Due today';
    } else if (diffDays === 1) {
      return 'Due tomorrow';
    } else {
      return `${diffDays} days remaining`;
    }
  };

  const getDeadlineColor = (deadline) => {
    if (!deadline) return '#6b7280';
    const date = new Date(deadline);
    const now = new Date();
    const diffTime = date - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return '#ef4444'; // Overdue
    if (diffDays <= 7) return '#f97316'; // Due soon
    return '#10b981'; // Good time
  };

  // Specialization indicator functions
  const getSpecializationIcon = (specialization) => {
    switch(specialization?.toUpperCase()) {
      case 'PLAYER': return '⚽';
      case 'COACH': return '🎓';
      default: return null;
    }
  };

  const getSpecializationLabel = (specialization) => {
    switch(specialization?.toUpperCase()) {
      case 'PLAYER': return 'Játékos';
      case 'COACH': return 'Edző';
      default: return null;
    }
  };

  const getSpecializationColors = (specialization) => {
    switch(specialization?.toUpperCase()) {
      case 'PLAYER': return { bg: '#4f46e5', text: '#ffffff' }; // Blue
      case 'COACH': return { bg: '#059669', text: '#ffffff' }; // Green
      default: return { bg: '#6b7280', text: '#ffffff' }; // Gray
    }
  };

  return (
    <div className="instructor-project-card">
      <div className="project-header">
        <div className="project-title-section">
          <h3 className="project-title">{project.title}</h3>
          <div className="project-badges">
            <span 
              className="status-badge"
              style={{ backgroundColor: getStatusColor(project.status) }}
            >
              {getStatusIcon(project.status)} {project.status}
            </span>
            {/* Specialization indicator */}
            {project.target_specialization && (
              <span 
                className="specialization-badge"
                style={{ 
                  backgroundColor: getSpecializationColors(project.target_specialization).bg,
                  color: getSpecializationColors(project.target_specialization).text 
                }}
                title={`Célcsoport: ${getSpecializationLabel(project.target_specialization)}`}
              >
                {getSpecializationIcon(project.target_specialization)} {getSpecializationLabel(project.target_specialization)}
              </span>
            )}
            {project.mixed_specialization && (
              <span 
                className="specialization-badge mixed"
                style={{ 
                  backgroundColor: '#8b5cf6',
                  color: '#ffffff'
                }}
                title="Vegyes szakirány - Játékosok és edzők számára"
              >
                🤝 Vegyes
              </span>
            )}
          </div>
        </div>
        
      </div>

      <div className="project-description">
        <p>{project.description}</p>
      </div>

      <div className="project-stats">
        <div className="stat-item">
          <span className="stat-icon">👥</span>
          <span className="stat-text">
            {project.enrolled_count || 0}/{project.max_participants} students
          </span>
        </div>
        
        <div className="stat-item">
          <span className="stat-icon">📚</span>
          <span className="stat-text">{project.required_sessions || 0} sessions</span>
        </div>
        
        <div className="stat-item">
          <span className="stat-icon">⭐</span>
          <span className="stat-text">{project.xp_reward || 0} XP</span>
        </div>
        
        <div className="stat-item">
          <span className="stat-icon">📅</span>
          <span 
            className="stat-text deadline-text"
            style={{ color: getDeadlineColor(project.deadline) }}
          >
            {formatDeadline(project.deadline)}
          </span>
        </div>
      </div>

      <div className="project-footer">
        
        <div className="project-actions-unified">
          <button 
            onClick={() => onViewDetails(project)}
            className="action-btn-unified details"
          >
            📋 Details
          </button>
          
          <button 
            onClick={() => onEdit(project)}
            className="action-btn-unified edit"
          >
            ✏️ Edit
          </button>
          
          <button 
            onClick={() => onDelete(project.id)}
            className="action-btn-unified delete"
          >
            🗑️ Delete
          </button>
          
          <button 
            onClick={() => onManageStudents(project)}
            className="action-btn-unified manage"
          >
            👥 Students
          </button>
          
          <button 
            onClick={() => onConfigureQuizzes(project)}
            className="action-btn-unified quiz"
          >
            🧠 Quizzes
          </button>
        </div>
      </div>
    </div>
  );
};

export default InstructorProjectCard;