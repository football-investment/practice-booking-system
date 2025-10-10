import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './NavigationSidebar.css';

/**
 * Navigation Sidebar Component
 * Contextual navigation with role-based menu items and collapsible submenus
 */
const NavigationSidebar = ({
  config = [],
  activeSection,
  onSectionChange,
  collapsed = false,
  userRole = 'student'
}) => {
  console.log('🔧 NavigationSidebar loading with config:', config);
  const navigate = useNavigate();
  const location = useLocation();
  const [expandedItems, setExpandedItems] = useState(new Set());

  // Determine active navigation item based on current path
  const activeNavItem = useMemo(() => {
    const currentPath = location.pathname;
    
    // Find the matching nav item
    for (const item of config) {
      if (item.path && currentPath.startsWith(item.path)) {
        return item.id;
      }
      
      // Check submenu items
      if (item.submenu) {
        for (const subItem of item.submenu) {
          if (subItem.path && currentPath.startsWith(subItem.path)) {
            return item.id;
          }
        }
      }
    }
    
    return activeSection || 'overview';
  }, [location.pathname, config, activeSection]);

  // Handle navigation item click
  const handleNavItemClick = useCallback((item) => {
    if (item.submenu && item.submenu.length > 0) {
      // Toggle submenu expansion
      setExpandedItems(prev => {
        const newSet = new Set(prev);
        if (newSet.has(item.id)) {
          newSet.delete(item.id);
        } else {
          newSet.add(item.id);
        }
        return newSet;
      });
    } else {
      // Navigate to the item's path
      if (item.path) {
        navigate(item.path);
      }
      if (onSectionChange) {
        onSectionChange(item.id);
      }
    }
  }, [navigate, onSectionChange]);

  // Handle submenu item click
  const handleSubItemClick = useCallback((subItem) => {
    if (subItem.path) {
      navigate(subItem.path);
    }
    if (onSectionChange) {
      onSectionChange(subItem.id);
    }
  }, [navigate, onSectionChange]);

  // Auto-expand active parent menu
  React.useEffect(() => {
    const activeItem = config.find(item => 
      item.id === activeNavItem || 
      (item.submenu && item.submenu.some(sub => sub.id === activeNavItem))
    );
    
    if (activeItem && activeItem.submenu) {
      setExpandedItems(prev => new Set([...prev, activeItem.id]));
    }
  }, [activeNavItem, config]);

  // Render navigation icon
  const renderIcon = useCallback((iconName) => {
    return (
      <span className="material-icons nav-icon">
        {iconName}
      </span>
    );
  }, []);

  // Render badge for items with notifications
  const renderBadge = useCallback((item) => {
    if (item.badge && item.badgeCount > 0) {
      return (
        <span className="nav-badge">
          {item.badgeCount > 99 ? '99+' : item.badgeCount}
        </span>
      );
    }
    return null;
  }, []);

  return (
    <nav className={`navigation-sidebar navigation-sidebar--${userRole} ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-content">
        {/* Main Navigation */}
        <div className="nav-section">
          <ul className="nav-list">
            {config.map(item => (
              <li key={item.id} className="nav-item">
                <button
                  className={`nav-button ${
                    activeNavItem === item.id ? 'active' : ''
                  } ${
                    item.submenu && expandedItems.has(item.id) ? 'expanded' : ''
                  }`}
                  onClick={() => handleNavItemClick(item)}
                  title={collapsed ? item.label : undefined}
                >
                  <div className="nav-button-content">
                    {renderIcon(item.icon)}
                    {!collapsed && (
                      <>
                        <span className="nav-label">{item.label}</span>
                        {renderBadge(item)}
                        {item.submenu && (
                          <span className="material-icons nav-expand">
                            {expandedItems.has(item.id) ? 'expand_less' : 'expand_more'}
                          </span>
                        )}
                      </>
                    )}
                  </div>
                </button>

                {/* Submenu */}
                {item.submenu && !collapsed && expandedItems.has(item.id) && (
                  <ul className="nav-submenu">
                    {item.submenu.map(subItem => (
                      <li key={subItem.id} className="nav-subitem">
                        <button
                          className={`nav-subbutton ${
                            location.pathname.startsWith(subItem.path || '') ? 'active' : ''
                          }`}
                          onClick={() => handleSubItemClick(subItem)}
                        >
                          <div className="nav-subbutton-content">
                            <span className="nav-sublabel">{subItem.label}</span>
                            {renderBadge(subItem)}
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {/* Collapsed Submenu Tooltip */}
                {item.submenu && collapsed && (
                  <div className="nav-tooltip">
                    <div className="tooltip-header">{item.label}</div>
                    <ul className="tooltip-submenu">
                      {item.submenu.map(subItem => (
                        <li key={subItem.id}>
                          <button
                            className="tooltip-subitem"
                            onClick={() => handleSubItemClick(subItem)}
                          >
                            {subItem.label}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          {!collapsed && (
            <div className="sidebar-info">
              <div className="version-info">
                <span className="version-label">LFA v2.0</span>
              </div>
            </div>
          )}
          
          {/* Help & Support */}
          <div className="help-section">
            <button
              className="help-button"
              onClick={() => navigate('/help')}
              title={collapsed ? 'Help & Support' : undefined}
            >
              {renderIcon('help')}
              {!collapsed && <span className="help-label">Help & Support</span>}
            </button>
          </div>
        </div>
      </div>

      {/* Resize Handle (when not collapsed) */}
      {!collapsed && (
        <div className="sidebar-resize-handle">
          <div className="resize-indicator"></div>
        </div>
      )}
    </nav>
  );
};

export default NavigationSidebar;