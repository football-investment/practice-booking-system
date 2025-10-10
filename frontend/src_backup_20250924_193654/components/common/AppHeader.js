import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import './AppHeader.css';

const AppHeader = () => {
  const { user, logout } = useAuth();
  const { theme, colorScheme, setTheme, setColorScheme, themes, colorSchemes } = useTheme();
  const [isColorDropdownOpen, setIsColorDropdownOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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

  const getColorIcon = (color) => {
    switch(color) {
      case 'purple': return '🟣';
      case 'blue': return '🔵';
      case 'green': return '🟢';
      case 'red': return '🔴';
      case 'orange': return '🟠';
      case 'cyber': return '⚡';
      case 'ocean': return '🌊';
      case 'sunset': return '🌅';
      default: return '🎨';
    }
  };

  const getColorName = (color) => {
    switch(color) {
      case 'purple': return 'Purple';
      case 'blue': return 'Blue';
      case 'green': return 'Green';
      case 'red': return 'Red';
      case 'orange': return 'Orange';
      case 'cyber': return 'Cyber Sports';
      case 'ocean': return 'Ocean Breeze';
      case 'sunset': return 'Sunset Athletic';
      default: return color;
    }
  };

  const handleColorSelect = (color) => {
    setColorScheme(color);
    setIsColorDropdownOpen(false);
  };

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const trigger = document.querySelector('.color-dropdown-trigger');
      const menu = document.querySelector('.mobile-dropdown-menu');
      const mobileMenu = document.querySelector('.mobile-slide-menu');
      const hamburger = document.querySelector('.mobile-hamburger-btn');
      
      // Close color dropdown
      if (isColorDropdownOpen && 
          trigger && !trigger.contains(event.target) &&
          menu && !menu.contains(event.target)) {
        setIsColorDropdownOpen(false);
      }
      
      // Close mobile menu
      if (isMobileMenuOpen &&
          hamburger && !hamburger.contains(event.target) &&
          mobileMenu && !mobileMenu.contains(event.target)) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isColorDropdownOpen, isMobileMenuOpen]);

  return (
    <header className="app-header">
      <div className="header-content">
        {/* FLAT DOM STRUCTURE - ALL ELEMENTS SAME LEVEL */}
        
        {/* Logo */}
        <div className="header-logo">
          <span className="logo-icon">⚽</span>
          <h1 className="app-title">Practice Booking System</h1>
        </div>

        {/* User Info */}
        {user && (
          <div className="header-user">
            <span className="user-role-icon">{getRoleIcon(user.role)}</span>
            <span className="user-name">{user.full_name || user.name || user.email?.split('@')[0]}</span>
          </div>
        )}

        {/* Desktop/Wide Screen Controls - Hidden on Mobile */}
        <div className="desktop-controls">
          {/* Theme Buttons - DIRECT FLEX ITEMS */}
          {themes.map((themeOption) => (
            <button
              key={themeOption}
              className={`header-theme-btn ${theme === themeOption ? 'active' : ''}`}
              onClick={() => setTheme(themeOption)}
              title={
                themeOption === 'light' ? 'Light Mode' :
                themeOption === 'dark' ? 'Dark Mode' : 'Auto Mode'
              }
            >
              {themeOption === 'light' ? '☀️' : themeOption === 'dark' ? '🌙' : '🌗'}
            </button>
          ))}

          {/* Color Trigger Button - DIRECT FLEX ITEM */}
          <button
            className="header-color-trigger"
            onClick={() => setIsColorDropdownOpen(!isColorDropdownOpen)}
            title={`Current color: ${getColorName(colorScheme)}`}
          >
            <span className="color-icon">{getColorIcon(colorScheme)}</span>
            <span className="color-name">{getColorName(colorScheme)}</span>
            <span className="dropdown-arrow">{isColorDropdownOpen ? '▲' : '▼'}</span>
          </button>

          {/* Logout Button - DIRECT FLEX ITEM */}
          {user && (
            <button onClick={handleLogout} className="header-logout-btn">
              👋 <span>Logout</span>
            </button>
          )}
        </div>

        {/* INNOVATIVE MOBILE HAMBURGER - Smart Collapse */}
        <button 
          className="mobile-hamburger-btn"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          title="Menu"
        >
          <div className={`hamburger-lines ${isMobileMenuOpen ? 'open' : ''}`}>
            <span></span>
            <span></span>
            <span></span>
          </div>
        </button>

        {/* DESKTOP COLOR DROPDOWN - SAME DOM LEVEL AS OTHER HEADER ELEMENTS */}
        {isColorDropdownOpen && (
          <div className="color-dropdown-menu desktop-dropdown-menu">
            {colorSchemes.map((color) => (
              <button
                key={color}
                className={`color-dropdown-item ${colorScheme === color ? 'active' : ''}`}
                onClick={() => handleColorSelect(color)}
                data-color={color}
              >
                <span className="color-icon">{getColorIcon(color)}</span>
                <span className="color-name">{getColorName(color)}</span>
                {colorScheme === color && <span className="checkmark">✓</span>}
              </button>
            ))}
          </div>
        )}

        {/* INNOVATIVE MOBILE SLIDE-OUT MENU */}
        <div className={`mobile-slide-menu ${isMobileMenuOpen ? 'open' : ''}`}>
          <div className="mobile-menu-header">
            <h3>⚙️ Settings</h3>
            <button 
              className="close-menu-btn"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              ✕
            </button>
          </div>
          
          <div className="mobile-menu-section">
            <h4>🎨 Theme</h4>
            <div className="mobile-theme-grid">
              {themes.map((themeOption) => (
                <button
                  key={themeOption}
                  className={`mobile-theme-btn ${theme === themeOption ? 'active' : ''}`}
                  onClick={() => {
                    setTheme(themeOption);
                    setIsMobileMenuOpen(false);
                  }}
                >
                  <span className="theme-icon">
                    {themeOption === 'light' ? '☀️' : themeOption === 'dark' ? '🌙' : '🌗'}
                  </span>
                  <span className="theme-label">
                    {themeOption === 'light' ? 'Light' : themeOption === 'dark' ? 'Dark' : 'Auto'}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="mobile-menu-section">
            <h4>🎨 Colors</h4>
            <div className="mobile-color-grid">
              {colorSchemes.map((color) => (
                <button
                  key={color}
                  className={`mobile-color-btn ${colorScheme === color ? 'active' : ''}`}
                  onClick={() => {
                    setColorScheme(color);
                    setIsMobileMenuOpen(false);
                  }}
                  data-color={color}
                >
                  <span className="color-icon">{getColorIcon(color)}</span>
                  <span className="color-label">{getColorName(color)}</span>
                </button>
              ))}
            </div>
          </div>

          {user && (
            <div className="mobile-menu-section mobile-logout-section">
              <button 
                onClick={() => {
                  handleLogout();
                  setIsMobileMenuOpen(false);
                }}
                className="mobile-logout-btn"
              >
                👋 Logout
              </button>
            </div>
          )}
        </div>

        {/* Backdrop for mobile menu */}
        {isMobileMenuOpen && (
          <div 
            className="mobile-menu-backdrop"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}
      </div>
    </header>
  );
};

export default AppHeader;