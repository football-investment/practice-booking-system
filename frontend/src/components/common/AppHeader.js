import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import './AppHeader.css';

const AppHeader = () => {
  const { user, logout } = useAuth();
  const { theme, colorScheme, setTheme, setColorScheme, themes, colorSchemes } = useTheme();

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  const getRoleIcon = (role) => {
    switch(role) {
      case 'student': return '🎓';
      case 'instructor': return '👨‍🏫';
      case 'admin': return '⚙️';
      default: return '👤';
    }
  };

  return (
    <header className="app-header">
      <div className="header-content">
        {/* Left side - Logo and Title */}
        <div className="header-left">
          <div className="app-logo">
            <span className="logo-icon">⚽</span>
            <h1 className="app-title">Practice Booking System</h1>
          </div>
        </div>

        {/* Center - User info (if logged in) */}
        {user && (
          <div className="header-center">
            <div className="user-info">
              <span className="user-role-icon">{getRoleIcon(user.role)}</span>
              <div className="user-details">
                <span className="user-name">{user.full_name || user.name || user.email?.split('@')[0]}</span>
              </div>
            </div>
          </div>
        )}

        {/* Right side - Theme controls and logout */}
        <div className="header-right">
          {/* Theme Switcher */}
          <div className="theme-controls">
            {/* Theme Mode Buttons */}
            <div className="theme-section">
              <span className="control-label">Theme:</span>
              <div className="theme-buttons">
                {themes.map((themeOption) => (
                  <button
                    key={themeOption}
                    className={`theme-btn ${theme === themeOption ? 'active' : ''}`}
                    onClick={() => setTheme(themeOption)}
                    title={
                      themeOption === 'light' ? 'Light Mode' :
                      themeOption === 'dark' ? 'Dark Mode' : 'Auto Mode'
                    }
                  >
                    {themeOption === 'light' ? '☀️' : themeOption === 'dark' ? '🌙' : '🌗'}
                  </button>
                ))}
              </div>
            </div>

            {/* Color Scheme Buttons */}
            <div className="color-section">
              <span className="control-label">Color:</span>
              <div className="color-buttons">
                {colorSchemes.map((color) => (
                  <button
                    key={color}
                    className={`color-btn ${colorScheme === color ? 'active' : ''}`}
                    onClick={() => setColorScheme(color)}
                    title={
                      color === 'purple' ? 'Purple' :
                      color === 'blue' ? 'Blue' :
                      color === 'green' ? 'Green' :
                      color === 'red' ? 'Red' :
                      color === 'orange' ? 'Orange' :
                      color === 'cyber' ? 'Cyber Sports' :
                      color === 'ocean' ? 'Ocean Breeze' :
                      color === 'sunset' ? 'Sunset Athletic' : color
                    }
                    data-color={color}
                  >
                    {color === 'purple' ? '🟣' : 
                     color === 'blue' ? '🔵' : 
                     color === 'green' ? '🟢' : 
                     color === 'red' ? '🔴' : 
                     color === 'orange' ? '🟠' :
                     color === 'cyber' ? '⚡' :
                     color === 'ocean' ? '🌊' :
                     color === 'sunset' ? '🌅' : '🎨'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Logout Button (if logged in) */}
          {user && (
            <button onClick={handleLogout} className="logout-btn">
              👋 Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default AppHeader;