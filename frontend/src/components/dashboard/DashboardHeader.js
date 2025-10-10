import React, { useState, useCallback, useMemo } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import './DashboardHeader.css';

/**
 * Unified Dashboard Header Component
 * Role-adaptive header with notifications, search, profile menu, and sidebar toggle
 */
const DashboardHeader = ({
  user,
  config,
  notifications = [],
  onSidebarToggle,
  sidebarCollapsed = false
}) => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  // Get role-based welcome message
  const welcomeMessage = useMemo(() => {
    const timeOfDay = new Date().getHours();
    let greeting = 'Good morning';
    if (timeOfDay >= 12 && timeOfDay < 17) greeting = 'Good afternoon';
    else if (timeOfDay >= 17) greeting = 'Good evening';

    const roleMessages = {
      student: `${greeting}, ${user?.name || 'Student'}! Ready to learn?`,
      instructor: `${greeting}, ${user?.name || 'Instructor'}! Your students await.`,
      admin: `${greeting}, ${user?.name || 'Admin'}! System at your command.`
    };

    return roleMessages[user?.role] || `${greeting}, ${user?.name || 'User'}!`;
  }, [user]);

  // Unread notifications count
  const unreadCount = useMemo(() => {
    return notifications.filter(n => !n.read).length;
  }, [notifications]);

  // Handle search
  const handleSearch = useCallback((e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      console.log('Searching for:', searchQuery);
      // TODO: Implement search functionality
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  }, [searchQuery, navigate]);

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

  // Handle notification click
  const handleNotificationClick = useCallback((notification) => {
    console.log('Notification clicked:', notification);
    // TODO: Mark as read and handle navigation
    setShowNotifications(false);
  }, []);

  return (
    <header className={`dashboard-header dashboard-header--${user?.role}`}>
      <div className="header-left">
        {/* Sidebar Toggle */}
        <button
          className={`sidebar-toggle ${sidebarCollapsed ? 'collapsed' : ''}`}
          onClick={onSidebarToggle}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <span className="hamburger-icon">
            <span></span>
            <span></span>
            <span></span>
          </span>
        </button>

        {/* LFA Logo & Title */}
        <div className="header-brand">
          <div className="brand-logo">
            <span className="logo-icon">⚽</span>
            <span className="logo-text">LFA</span>
          </div>
          <div className="brand-subtitle">
            {user?.role === 'student' && 'Learning Dashboard'}
            {user?.role === 'instructor' && 'Teaching Portal'}
            {user?.role === 'admin' && 'Admin Console'}
          </div>
        </div>
      </div>

      <div className="header-center">
        {/* Welcome Message */}
        <div className="welcome-message">
          <h1 className="welcome-text">{welcomeMessage}</h1>
          <div className="current-date">
            {new Date().toLocaleDateString('en-US', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
          </div>
        </div>

        {/* Search Bar */}
        {config?.showSearch && (
          <div className={`search-container ${showSearch ? 'expanded' : ''}`}>
            <button
              className="search-toggle"
              onClick={() => setShowSearch(!showSearch)}
              aria-label="Toggle search"
            >
              <span className="material-icons">search</span>
            </button>
            <form onSubmit={handleSearch} className="search-form">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search sessions, projects, users..."
                className="search-input"
              />
              <button type="submit" className="search-submit" aria-label="Search">
                🔍
              </button>
            </form>
          </div>
        )}
      </div>

      <div className="header-right">
        {/* Quick Actions */}
        <div className="header-actions">
          {/* Theme Toggle */}
          {config?.showThemeToggle && (
            <button
              className="header-action-btn theme-toggle"
              onClick={() => {
                // TODO: Implement theme toggle
                console.log('Toggle theme');
              }}
              aria-label="Toggle theme"
            >
              🌙
            </button>
          )}

          {/* Notifications */}
          <div className="notification-container">
            <button
              className={`header-action-btn notifications-toggle ${unreadCount > 0 ? 'has-notifications' : ''}`}
              onClick={() => setShowNotifications(!showNotifications)}
              aria-label={`Notifications ${unreadCount > 0 ? `(${unreadCount} unread)` : ''}`}
            >
              🔔
              {unreadCount > 0 && (
                <span className="notification-badge">{unreadCount}</span>
              )}
            </button>

              {/* Notifications Dropdown */}
              {showNotifications && (
                <div className="notifications-dropdown">
                  <div className="notifications-header">
                    <h3>Notifications</h3>
                    <button
                      className="mark-all-read"
                      onClick={() => {
                        // TODO: Mark all as read
                        console.log('Mark all as read');
                      }}
                    >
                      Mark all read
                    </button>
                  </div>
                  <div className="notifications-list">
                    {notifications.length > 0 ? (
                      notifications.slice(0, 5).map(notification => (
                        <div
                          key={notification.id}
                          className={`notification-item ${!notification.read ? 'unread' : ''}`}
                          onClick={() => handleNotificationClick(notification)}
                        >
                          <div className="notification-content">
                            <div className="notification-title">
                              {notification.title}
                            </div>
                            <div className="notification-message">
                              {notification.message}
                            </div>
                            <div className="notification-time">
                              {notification.created_at && 
                                new Date(notification.created_at).toLocaleString()
                              }
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="no-notifications">
                        🔕
                        <p>No new notifications</p>
                      </div>
                    )}
                  </div>
                  {notifications.length > 5 && (
                    <div className="notifications-footer">
                      <button
                        className="view-all-notifications"
                        onClick={() => {
                          navigate('/notifications');
                          setShowNotifications(false);
                        }}
                      >
                        View all notifications
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Profile Menu */}
          {config?.showProfileMenu && (
            <div className="profile-container">
              <button
                className="profile-toggle"
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                aria-label="Profile menu"
              >
                <div className="profile-avatar">
                  {user?.avatar ? (
                    <img src={user.avatar} alt={user.name} />
                  ) : (
                    <span className="avatar-initials">
                      {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'U'}
                    </span>
                  )}
                </div>
                <div className="profile-info">
                  <div className="profile-name">{user?.name || 'User'}</div>
                  <div className="profile-role">{user?.role || 'role'}</div>
                </div>
                <span className="dropdown-arrow">
                  ▼
                </span>
              </button>

              {/* Profile Dropdown */}
              {showProfileMenu && (
                <div className="profile-dropdown">
                  <div className="profile-dropdown-header">
                    <div className="profile-avatar-large">
                      {user?.avatar ? (
                        <img src={user.avatar} alt={user.name} />
                      ) : (
                        <span className="avatar-initials-large">
                          {user?.name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'U'}
                        </span>
                      )}
                    </div>
                    <div className="profile-details">
                      <h4>{user?.name || 'User'}</h4>
                      <p>{user?.email || 'No email'}</p>
                      <span className="role-badge">{user?.role || 'role'}</span>
                    </div>
                  </div>
                  <div className="profile-menu-items">
                    <button
                      className="profile-menu-item"
                      onClick={handleProfileClick}
                    >
                      👤
                      View Profile
                    </button>
                    <button
                      className="profile-menu-item"
                      onClick={() => {
                        navigate('/settings');
                        setShowProfileMenu(false);
                      }}
                    >
                      ⚙️
                      Settings
                    </button>
                    <hr className="menu-divider" />
                    <button
                      className="profile-menu-item logout-item"
                      onClick={handleLogout}
                    >
                      🚪
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Close dropdowns when clicking outside */}
      {(showNotifications || showProfileMenu || showSearch) && (
        <div
          className="header-overlay"
          onClick={() => {
            setShowNotifications(false);
            setShowProfileMenu(false);
            setShowSearch(false);
          }}
        />
      )}
    </header>
  );
};

export default DashboardHeader;