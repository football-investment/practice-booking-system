import React, { useState, useCallback, useMemo } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useNavigate } from 'react-router-dom';
import './CleanDashboardHeader.css';

/**
 * CLEAN Dashboard Header - MINIMAL DESIGN
 * ONLY: Sidebar toggle, Logo, Theme toggle, Notifications, Profile
 * NO: Welcome message, date, unnecessary text
 */
const CleanDashboardHeader = ({
  user,
  notifications = [],
  onSidebarToggle,
  sidebarCollapsed = false,
  showSidebarToggle = true
}) => {
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);

  // Unread notifications count
  const unreadCount = useMemo(() => {
    return notifications.filter(n => !n.read).length;
  }, [notifications]);

  // Handle logout
  const handleLogout = useCallback(async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }, [logout, navigate]);

  // Handle profile navigation
  const handleProfileClick = useCallback(() => {
    const profilePaths = {
      student: '/student/profile',
      instructor: '/instructor/profile', 
      admin: '/admin/profile'
    };
    navigate(profilePaths[user?.role] || '/profile');
    setShowProfileMenu(false);
  }, [user?.role, navigate]);

  return (
    <header className={`clean-header clean-header--${user?.role}`}>
      {/* LEFT: Menu + Logo */}
      <div className="header-left">
        {showSidebarToggle && (
          <button
            className="menu-toggle"
            onClick={onSidebarToggle}
            aria-label="Toggle menu"
          >
            ☰
          </button>
        )}

        <div className="header-logo">
          <span className="logo-icon">⚽</span>
          <span className="logo-text">LFA</span>
        </div>
      </div>

      {/* CENTER: Search Bar */}
      <div className="header-center">
        <div className="search-container">
          <input
            type="text"
            className="search-input"
            placeholder="Search..."
            aria-label="Search"
          />
          <span className="search-icon">🔍</span>
        </div>
      </div>

      {/* RIGHT: Theme Toggle + Notifications + Profile */}
      <div className="header-right">
        {/* Theme Toggle Button */}
        <button
          className="action-btn theme-toggle-btn"
          onClick={toggleTheme}
          aria-label="Toggle theme"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>

        {/* Notifications Button */}
        <button
          className="action-btn notification-btn"
          onClick={() => setShowNotifications(!showNotifications)}
          aria-label="Notifications"
        >
          🔔
          {unreadCount > 0 && (
            <span className="badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
          )}
        </button>

        {/* Profile Button */}
        <button
          className="action-btn profile-btn"
          onClick={() => setShowProfileMenu(!showProfileMenu)}
          aria-label="Profile menu"
        >
          <span className="avatar">
            {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'U'}
          </span>
        </button>
      </div>

      {/* Notifications Dropdown */}
      {showNotifications && (
        <div className="dropdown notifications-dropdown">
          <div className="dropdown-header">
            <h3>Notifications</h3>
          </div>
          <div className="dropdown-content">
            {notifications.length > 0 ? (
              notifications.slice(0, 3).map(notification => (
                <div key={notification.id} className="notification-item">
                  <div className="notification-title">{notification.title}</div>
                  <div className="notification-message">{notification.message}</div>
                </div>
              ))
            ) : (
              <div className="empty-state">No notifications</div>
            )}
          </div>
        </div>
      )}

      {/* Profile Dropdown */}
      {showProfileMenu && (
        <div className="dropdown profile-dropdown">
          <div className="dropdown-header">
            <div className="user-info">
              <div className="user-name">{user?.name || 'User'}</div>
              <div className="user-role">{user?.role || 'Role'}</div>
            </div>
          </div>
          <div className="dropdown-content">
            <button className="dropdown-item" onClick={handleProfileClick}>
              👤 Profile
            </button>
            <button className="dropdown-item logout" onClick={handleLogout}>
              🚪 Sign Out
            </button>
          </div>
        </div>
      )}

      {/* Overlay to close dropdowns */}
      {(showNotifications || showProfileMenu) && (
        <div
          className="overlay"
          onClick={() => {
            setShowNotifications(false);
            setShowProfileMenu(false);
          }}
        />
      )}
    </header>
  );
};

export default CleanDashboardHeader;