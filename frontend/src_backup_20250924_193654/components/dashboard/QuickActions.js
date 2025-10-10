import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import './QuickActions.css';

/**
 * Quick Actions Component
 * Role-adaptive quick action panel with contextual buttons
 */
const QuickActions = ({
  actions = [],
  config = {},
  userRole = 'student',
  onActionClick
}) => {
  const navigate = useNavigate();

  // Handle action click
  const handleActionClick = useCallback((action) => {
    console.log('Quick action clicked:', action);
    
    if (onActionClick) {
      onActionClick(action);
    }

    // Handle different action types
    switch (action.action) {
      case 'navigate':
        if (action.target) {
          navigate(action.target);
        }
        break;
        
      case 'modal':
        // TODO: Implement modal opening
        console.log('Open modal:', action.target);
        break;
        
      case 'external':
        if (action.target) {
          window.open(action.target, '_blank', 'noopener,noreferrer');
        }
        break;
        
      case 'function':
        if (action.handler && typeof action.handler === 'function') {
          action.handler();
        }
        break;
        
      default:
        console.warn('Unknown action type:', action.action);
    }
  }, [navigate, onActionClick]);

  // Get color class for action
  const getActionColorClass = (color) => {
    const colorMap = {
      primary: 'action-primary',
      secondary: 'action-secondary',
      success: 'action-success',
      warning: 'action-warning',
      error: 'action-error',
      info: 'action-info'
    };
    return colorMap[color] || 'action-primary';
  };

  if (!actions || actions.length === 0) {
    return (
      <div className={`quick-actions quick-actions--${userRole} quick-actions--empty`}>
        <div className="quick-actions-header">
          <h3>Quick Actions</h3>
        </div>
        <div className="no-actions">
          <span className="material-icons">touch_app</span>
          <p>No quick actions available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`quick-actions quick-actions--${userRole}`}>
      <div className="quick-actions-header">
        <h3>Quick Actions</h3>
        <span className="actions-count">{actions.length}</span>
      </div>
      
      <div className="actions-grid">
        {actions.map((action, index) => (
          <button
            key={action.id || index}
            className={`action-button ${getActionColorClass(action.color)}`}
            onClick={() => handleActionClick(action)}
            title={action.description || action.label}
            disabled={action.disabled}
          >
            <div className="action-content">
              <div className="action-icon-container">
                <span className="material-icons action-icon">
                  {action.icon}
                </span>
                {action.badge && (
                  <span className="action-badge">
                    {typeof action.badge === 'boolean' ? '!' : action.badge}
                  </span>
                )}
              </div>
              
              <div className="action-details">
                <div className="action-label">
                  {action.label}
                </div>
                {action.subtitle && (
                  <div className="action-subtitle">
                    {action.subtitle}
                  </div>
                )}
              </div>

              {action.shortcut && (
                <div className="action-shortcut">
                  {action.shortcut}
                </div>
              )}
            </div>

            {/* Loading state */}
            {action.loading && (
              <div className="action-loading">
                <div className="loading-spinner-small"></div>
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Role-specific action suggestions */}
      {userRole === 'student' && (
        <div className="action-suggestions">
          <p>💡 <strong>Tip:</strong> Use keyboard shortcuts to access actions faster!</p>
        </div>
      )}
      
      {userRole === 'instructor' && (
        <div className="action-suggestions">
          <p>🚀 <strong>Pro tip:</strong> Batch operations can save you time with multiple students.</p>
        </div>
      )}
      
      {userRole === 'admin' && (
        <div className="action-suggestions">
          <p>⚡ <strong>Admin tip:</strong> System shortcuts are available in the configuration panel.</p>
        </div>
      )}
    </div>
  );
};

export default QuickActions;