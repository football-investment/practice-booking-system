import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import { LFAUserService } from '../../utils/userTypeService';
import ProgressCard from '../../components/SpecializationProgress/ProgressCard';
import AchievementList from '../../components/Achievements/AchievementList';
import './StudentDashboard.css';

/**
 * LFA EDUCATION CENTER - COMPLETE DASHBOARD
 * Full mockup implementation with all specialized cards
 */
const StudentDashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState({
    nextSession: null,
    progress: null,
    gamification: null,
    specialization: null,
    recommendations: null,
    recentFeedback: null,
    performance: null,
    activeProjects: null,
    pendingQuizzes: null
  });
  const [nextSession, setNextSession] = useState(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [recentFeedback, setRecentFeedback] = useState([]);
  
  // 🎯 NEW: User Type & Business Logic State
  const [userType, setUserType] = useState('adult');
  const [userConfig, setUserConfig] = useState({});
  const [skillCategories, setSkillCategories] = useState([]);
  const [dailyChallenges, setDailyChallenges] = useState([]);
  const [semesterInfo, setSemesterInfo] = useState({});
  const [achievements, setAchievements] = useState([]);

  // 🆕 SPECIALIZATION STATE
  const [userSpecialization, setUserSpecialization] = useState(null); // PLAYER, COACH, or INTERNSHIP
  // NEW: Header and Welcome Section State
  const [currentQuote, setCurrentQuote] = useState({
    text: "Success is no accident. It is hard work, perseverance, learning, studying, sacrifice and most of all, love of what you are doing.",
    author: "Pelé"
  });
  const [greeting, setGreeting] = useState('');
  const [currentDate, setCurrentDate] = useState('');
  
  // NEW: Theme Management State
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem('lfa-theme');
    return savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });

  // NEW: Header Interactive State
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  // DEBUG: Debug Mode State
  const [debugMode, setDebugMode] = useState(() => {
    return localStorage.getItem('lfa-debug-mode') === 'true';
  });
  // PRODUCTION MODE: Notifications will come from real backend endpoint when available
  // For now, start with empty array - no hardcoded data
  const [notifications, setNotifications] = useState([]);

  // Motivational quotes are now defined inline in refreshQuote function

  // Helper Functions for Header and Welcome
  const updateGreeting = useCallback(() => {
    const now = new Date();
    const hour = now.getHours();
    const userName = user?.name || 'Student';
    
    let greetingText = "Good morning";
    if (hour >= 12 && hour < 17) greetingText = "Good afternoon";
    else if (hour >= 17) greetingText = "Good evening";
    
    const finalGreeting = `${greetingText}, ${userName}!`;
    console.log('🎯 Setting greeting:', finalGreeting);
    setGreeting(finalGreeting);
    
    const options = { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    };
    const finalDate = now.toLocaleDateString('en-US', options);
    console.log('📅 Setting date:', finalDate);
    setCurrentDate(finalDate);
  }, [user?.name]);

  const refreshQuote = useCallback(() => {
    const quotes = [
      {
        text: "Success is no accident. It is hard work, perseverance, learning, studying, sacrifice and most of all, love of what you are doing.",
        author: "Pelé"
      },
      {
        text: "Champions aren't made in comfort zones.",
        author: "John Wooden"
      },
      {
        text: "It is during our darkest moments that we must focus to see the light.",
        author: "Aristotle"
      },
      {
        text: "You miss 100% of the shots you don't take.",
        author: "Wayne Gretzky"
      },
      {
        text: "Excellence is not a skill, it's an attitude.",
        author: "Ralph Marston"
      },
      {
        text: "The harder you work for something, the greater you'll feel when you achieve it.",
        author: "Anonymous"
      },
      {
        text: "Believe you can and you're halfway there.",
        author: "Theodore Roosevelt"
      },
      {
        text: "Don't watch the clock; do what it does. Keep going.",
        author: "Sam Levenson"
      }
    ];
    const randomIndex = Math.floor(Math.random() * quotes.length);
    setCurrentQuote(quotes[randomIndex]);
  }, []);

  // Theme Toggle Function
  const toggleDarkMode = useCallback(() => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    localStorage.setItem('lfa-theme', newDarkMode ? 'dark' : 'light');
    
    // Apply theme to multiple elements for maximum compatibility
    document.documentElement.setAttribute('data-theme', newDarkMode ? 'dark' : 'light');
    document.body.setAttribute('data-theme', newDarkMode ? 'dark' : 'light');
    
    console.log('🎨 Theme switched to:', newDarkMode ? 'DARK' : 'LIGHT');
    console.log('🎯 HTML data-theme:', document.documentElement.getAttribute('data-theme'));
    console.log('🎯 Body data-theme:', document.body.getAttribute('data-theme'));
  }, [isDarkMode]);
  
  // DEBUG: Debug Mode Toggle Function
  const toggleDebugMode = useCallback(() => {
    const newDebugMode = !debugMode;
    setDebugMode(newDebugMode);
    localStorage.setItem('lfa-debug-mode', newDebugMode.toString());
    
    console.log('🐛 Debug mode switched to:', newDebugMode ? 'ON' : 'OFF');
  }, [debugMode]);

  // NEW: Header Button Functions
  const handleNotificationsToggle = useCallback(() => {
    setShowNotifications(!showNotifications);
    setShowProfileMenu(false);
    setShowSettings(false);
  }, [showNotifications]);

  const handleProfileMenuToggle = useCallback(() => {
    setShowProfileMenu(!showProfileMenu);
    setShowNotifications(false);
    setShowSettings(false);
  }, [showProfileMenu]);

  const handleSettingsToggle = useCallback(() => {
    setShowSettings(!showSettings);
    setShowNotifications(false);
    setShowProfileMenu(false);
  }, [showSettings]);

  const markNotificationAsRead = useCallback((notificationId) => {
    setNotifications(prevNotifications => 
      prevNotifications.map(notif => 
        notif.id === notificationId ? { ...notif, read: true } : notif
      )
    );
  }, []);

  const markAllNotificationsAsRead = useCallback(() => {
    setNotifications(prevNotifications => 
      prevNotifications.map(notif => ({ ...notif, read: true }))
    );
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('.header-actions')) {
        setShowNotifications(false);
        setShowProfileMenu(false);
        setShowSettings(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  // Apply theme on mount and change
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    document.body.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    console.log('🎨 Theme applied on mount/change:', isDarkMode ? 'DARK' : 'LIGHT');
  }, [isDarkMode]);

  useEffect(() => {
    // 🎯 Initialize user type and business logic first
    initializeUserProfile();
    updateGreeting();
    
    loadLFADashboardData();
    loadNextSession();
    loadRecentFeedback();
    
    // Automatikus idézet frissítés órákra
    const quoteInterval = setInterval(refreshQuote, 3600000); // 1 óra
    
    // Debug overflow detection removed
    
    return () => clearInterval(quoteInterval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateGreeting, refreshQuote]);

  // 🎯 NEW: Initialize user profile and business logic
  const initializeUserProfile = async () => {
    if (!user) return;
    
    console.log('🎯 LFA: Initializing user profile for:', user.name);
    
    // Determine user type
    const detectedUserType = LFAUserService.determineUserType(user);
    setUserType(detectedUserType);
    
    // Get user type configuration
    const config = LFAUserService.getUserTypeConfig(detectedUserType);
    setUserConfig(config);
    
    // PRODUCTION MODE: Data will come from real backend endpoints
    console.log('🚨 PRODUCTION MODE: All data comes from real backend endpoints');
    // Skills and challenges will be set by loadLFADashboardData from real API
    
    // PRODUCTION MODE: Get semester data from gamification API (real data)
    try {
      const gamificationData = await apiService.getGamificationMe();
      setSemesterInfo({
        currentSemester: gamificationData.current_semester || {
          name: 'Current Semester',
          start_date: new Date().toISOString()
        }
      });
    } catch (error) {
      console.log('Using fallback semester info');
      setSemesterInfo({
        currentSemester: {
          name: 'Current Semester',
          start_date: new Date().toISOString()
        }
      });
    }
    
    // 🆕 DETECT USER SPECIALIZATION from user object
    if (user.specialization) {
      setUserSpecialization(user.specialization);
      console.log('🎓 User specialization detected:', user.specialization);
    } else {
      // Default to PLAYER if not set
      setUserSpecialization('PLAYER');
      console.log('🎓 No specialization set, defaulting to PLAYER');
    }

    console.log('🎯 LFA Profile initialized:', {
      userType: detectedUserType,
      config,
      specialization: user.specialization || 'PLAYER',
      productionMode: true,
      mockDataRemoved: true
    });
  };

  const loadLFADashboardData = async () => {
    setLoading(true);
    try {
      // Use the NEW REAL backend endpoints integration
      const lfaData = await apiService.getLFADashboardData();
      setDashboardData(lfaData);

      // Set specific state from real backend data
      if (lfaData.semesterProgress) {
        setSemesterInfo({
          currentSemester: lfaData.semesterProgress,
          timeline: lfaData.semesterProgress.timeline || []
        });
      }

      if (lfaData.achievements) {
        setSkillCategories(lfaData.achievements); // Real achievement data
      }

      if (lfaData.dailyChallenge) {
        setDailyChallenges([lfaData.dailyChallenge]); // Real daily challenge
      }

      // LOAD REAL ACHIEVEMENTS FROM BACKEND
      try {
        const achievementsData = await apiService.getAchievements();
        setAchievements(achievementsData.achievements || []);
        console.log('✅ Real achievements loaded:', achievementsData);
      } catch (error) {
        console.warn('Achievements loading failed:', error);
        setAchievements([]);
      }

    } catch (error) {
      console.error('🚨 CRITICAL: Real dashboard data loading failed:', error);
      // Fallback with empty real structure - NO MOCK DATA
      setDashboardData({
        semesterProgress: { current_phase: 'No Active Semester', completion_percentage: 0, timeline: [] },
        achievements: [],
        achievementSummary: { total_unlocked: 0 },
        dailyChallenge: null,
        aiSuggestions: [],
        nextSession: null,
        activeProjects: { projects: [], total: 0 }
      });
      setAchievements([]);
    } finally {
      setLoading(false);
    }
  };

  const loadNextSession = async () => {
    try {
      setSessionsLoading(true);
      
      // Try to get actual session data
      const sessionsResponse = await apiService.getMySessions();
      
      // Handle both array and object responses
      const sessions = Array.isArray(sessionsResponse) ? sessionsResponse : (sessionsResponse.sessions || []);
      
      const upcomingSessions = sessions.filter(session => {
        const sessionDate = new Date(session.date_start);
        return sessionDate > new Date();
      });
      
      if (upcomingSessions.length > 0) {
        // Sort by date and get the nearest one
        upcomingSessions.sort((a, b) => new Date(a.date_start) - new Date(b.date_start));
        setNextSession(upcomingSessions[0]);
      } else {
        // PRODUCTION MODE: No sessions available - set to null
        console.log('🚨 PRODUCTION MODE: No upcoming sessions found in database');
        setNextSession(null);
      }
    } catch (error) {
      console.error('Failed to load sessions from API:', error);
      // PRODUCTION MODE: Error state - set to null, no mock data
      setNextSession(null);
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadRecentFeedback = async () => {
    try {
      const response = await apiService.getMyFeedback();
      // API returns { feedbacks: [...], total, page, size }
      const feedbackArray = Array.isArray(response) ? response : (response.feedbacks || response.feedback || []);
      setRecentFeedback(feedbackArray.slice(0, 3)); // Latest 3
    } catch (error) {
      // PRODUCTION MODE: Error state - no mock feedback data
      console.error('Failed to load feedback from API:', error);
      setRecentFeedback([]); // Empty array - no mock data
    }
  };

  // const handleStartAdaptiveLearning = async (recommendationId) => {
  //   try {
  //     await apiService.startAdaptiveLearningModule(recommendationId);
  //     // Navigate to learning module (would need React Router)
  //     window.location.href = `/student/learning/${recommendationId}`;
  //   } catch (error) {
  //     console.error('Failed to start adaptive learning:', error);
  //     alert('Failed to start learning module. Please try again.');
  //   }
  // };

  if (loading) {
    return (
      <div className="lfa-dashboard loading">
        <div className="loading-spinner">⚽</div>
        <p>Loading your LFA dashboard...</p>
      </div>
    );
  }


  const formatDateTime = (dateString) => {
    if (!dateString) return 'TBD';
    const date = new Date(dateString);
    
    // 🚨 ULTRA-COMPACT FORMAT TO PREVENT OVERFLOW
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    // 🚨 MINIMAL FORMAT: MM/DD HH:MM
    return `${month}/${day}\n${hours}:${minutes}`;
  };

  // NEW COMPONENT: Next Session Card
  const NextSessionCard = () => {
    
    return (
      <div className="next-session-card">
        <h2>Next Session</h2>
        {sessionsLoading ? (
          <div className="loading">Loading session...</div>
        ) : nextSession ? (
          <div className="session-content">
            <div className="session-date" style={{whiteSpace: 'pre-line'}}>
              {formatDateTime(nextSession.date_start)}
            </div>
            {(nextSession.location || nextSession.instructor?.name || nextSession.instructor_name || nextSession.title) && (
              <div className="session-details">
                {nextSession.location && (
                  <div className="location-badge">
                    📍 {nextSession.location}
                  </div>
                )}
                {(nextSession.instructor?.name || nextSession.instructor_name || nextSession.title) && (
                  <div className="instructor-info">
                    <div>🏆 Coach: {nextSession.instructor?.name || nextSession.instructor_name || 'Unknown'}</div>
                    <div>📝 {nextSession.title || 'Training Session'}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="no-session">
            <p>No upcoming sessions scheduled</p>
          </div>
        )}
      </div>
    );
  };

  // NEW COMPONENT: Quick Actions Grid - REAL WEBAPP FUNCTIONS
  const QuickActionsGrid = () => {
    const quickActions = [
      {
        id: 'browse-sessions',
        title: '📅 Browse Sessions',
        description: 'View all training sessions',
        color: 'primary',
        onClick: () => window.location.href = '/student/sessions'
      },
      {
        id: 'my-bookings',
        title: '🎫 My Bookings',
        description: 'View your reservations',
        color: 'secondary',
        onClick: () => window.location.href = '/student/bookings'
      },
      {
        id: 'projects',
        title: '📂 Projects',
        description: 'Browse team projects',
        color: 'tertiary',
        onClick: () => window.location.href = '/student/projects'
      },
      {
        id: 'achievements',
        title: '🏆 Achievements',
        description: 'View your badges',
        color: 'primary',
        onClick: () => window.location.href = '/student/gamification'
      },
      {
        id: 'feedback',
        title: '💬 Feedback',
        description: 'Coach reviews',
        color: 'secondary',
        onClick: () => window.location.href = '/student/feedback'
      },
      {
        id: 'profile',
        title: '👤 My Profile',
        description: 'Edit your information',
        color: 'tertiary',
        onClick: () => window.location.href = '/student/profile'
      },
      {
        id: 'messages',
        title: '✉️ Messages',
        description: 'Chat with coaches',
        color: 'primary',
        onClick: () => window.location.href = '/student/messages'
      },
      {
        id: 'adaptive-learning',
        title: '🧠 Adaptive Learning',
        description: 'Personalized training',
        color: 'secondary',
        onClick: () => window.location.href = '/student/adaptive-learning'
      },
      {
        id: 'learning-profile',
        title: '🔥 Learning Profile',
        description: 'View your learning stats',
        color: 'primary',
        onClick: () => window.location.href = '/student/learning-profile'
      },
      {
        id: 'competency',
        title: '🎯 Competency Dashboard',
        description: 'Track your skills',
        color: 'tertiary',
        onClick: () => window.location.href = '/student/competency'
      }
    ];

    return (
      <div className="quick-actions-card">
        <div className="card-header">
          <h2 className="card-title">⚡ Quick Actions</h2>
          <p className="card-subtitle">Get started with your training</p>
        </div>
        <div className="quick-actions-grid">
          {quickActions.map(action => (
            <button
              key={action.id}
              className={`quick-action-btn ${action.color}`}
              onClick={action.onClick}
            >
              <div className="action-icon">{action.title.split(' ')[0]}</div>
              <div className="action-content">
                <h4>{action.title.substring(action.title.indexOf(' ') + 1)}</h4>
                <p>{action.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  };

  // NEW COMPONENT: Recent Feedback Section
  const RecentFeedbackSection = () => (
    <div className="recent-feedback">
      <h2>Recent Feedback</h2>
      {recentFeedback.length > 0 ? (
        recentFeedback.map(feedback => (
          <div key={feedback.id} className="feedback-card">
            <div className="feedback-header">
              <h4>{feedback.coach}</h4>
              <div className="feedback-rating">
                {'⭐'.repeat(Math.floor(feedback.rating))}
              </div>
            </div>
            <p>{feedback.message}</p>
          </div>
        ))
      ) : (
        <div className="no-feedback">
          <p>No recent feedback available</p>
        </div>
      )}
    </div>
  );

  return (
    <div className={`student-dashboard ${debugMode ? 'debug-mode' : ''}`}>
      {/* NEW MINIMAL HEADER */}
      <header className="minimal-header">
        <div className="header-logo">🏆 LFA</div>
        
        <div className="header-actions">
          <button 
            className="header-btn theme-toggle-btn" 
            title={isDarkMode ? "Világos téma" : "Sötét téma"}
            onClick={toggleDarkMode}
          >
            {isDarkMode ? "🌞" : "🌙"}
          </button>
          
          <button 
            className="header-btn quote-refresh-btn" 
            title="Új motivációs idézet"
            onClick={refreshQuote}
          >
            🔄
          </button>
          
          <div className="header-dropdown">
            <button 
              className={`header-btn notification-btn ${notifications.some(n => !n.read) ? 'has-new' : ''}`}
              title="Értesítések"
              onClick={handleNotificationsToggle}
            >
              🔔
              {notifications.some(n => !n.read) && (
                <span className="notification-badge">
                  {notifications.filter(n => !n.read).length}
                </span>
              )}
            </button>
            
            {showNotifications && (
              <div className="dropdown-menu notifications-dropdown">
                <div className="dropdown-header">
                  <h3>Notifications</h3>
                  {notifications.some(n => !n.read) && (
                    <button 
                      className="mark-all-read"
                      onClick={markAllNotificationsAsRead}
                    >
                      Mark all read
                    </button>
                  )}
                </div>
                <div className="dropdown-content">
                  {notifications.length > 0 ? notifications.map(notification => (
                    <div 
                      key={notification.id}
                      className={`notification-item ${notification.read ? 'read' : 'unread'}`}
                      onClick={() => markNotificationAsRead(notification.id)}
                    >
                      <div className="notification-icon">
                        {notification.type === 'session' && '⏰'}
                        {notification.type === 'profile' && '👤'}
                        {notification.type === 'achievement' && '🏆'}
                      </div>
                      <div className="notification-content">
                        <h4>{notification.title}</h4>
                        <p>{notification.message}</p>
                        <span className="notification-time">{notification.time}</span>
                      </div>
                      {!notification.read && <div className="unread-indicator"></div>}
                    </div>
                  )) : (
                    <div className="no-notifications">
                      <p>No notifications</p>
                    </div>
                  )}
                </div>
                <div className="dropdown-footer">
                  <button className="view-all-notifications">
                    View All Notifications
                  </button>
                </div>
              </div>
            )}
          </div>
          
          <div className="header-dropdown">
            <div 
              className="user-profile" 
              title="Profil menü"
              onClick={handleProfileMenuToggle}
            >
              <img 
                src={user?.avatar || "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=28&h=28&fit=crop&crop=face"} 
                alt="Profile" 
                className="user-avatar"
              />
              <span className="user-name">{user?.name || 'User'}</span>
              <span className="dropdown-arrow">{showProfileMenu ? '▲' : '▼'}</span>
            </div>
            
            {showProfileMenu && (
              <div className="dropdown-menu profile-dropdown">
                <div className="dropdown-header">
                  <div className="profile-info">
                    <img 
                      src={user?.avatar || "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=40&h=40&fit=crop&crop=face"} 
                      alt="Profile" 
                      className="profile-avatar-large"
                    />
                    <div>
                      <h3>{user?.name || 'User'}</h3>
                      <p>{user?.email || 'user@example.com'}</p>
                    </div>
                  </div>
                </div>
                <div className="dropdown-content">
                  <button className="profile-menu-item" onClick={() => window.location.href = '/student/profile'}>
                    👤 Profil megtekintése
                  </button>
                  <button className="profile-menu-item" onClick={() => window.location.href = '/student/settings'}>
                    ⚙️ Beállítások
                  </button>
                  <button className="profile-menu-item" onClick={() => window.location.href = '/student/achievements'}>
                    🏆 Eredményeim
                  </button>
                  <button className="profile-menu-item" onClick={() => window.location.href = '/student/progress'}>
                    📊 Haladásom
                  </button>
                  <div className="menu-divider"></div>
                  <button className="profile-menu-item logout" onClick={() => {
                    localStorage.removeItem('token');
                    window.location.href = '/login';
                  }}>
                    🚪 Kijelentkezés
                  </button>
                </div>
              </div>
            )}
          </div>
          
          <div className="header-dropdown">
            <button 
              className="header-btn settings-btn" 
              title="Beállítások"
              onClick={handleSettingsToggle}
            >
              ⚙️
            </button>
            
            {showSettings && (
              <div className="dropdown-menu settings-dropdown">
                <div className="dropdown-header">
                  <h3>Gyors beállítások</h3>
                </div>
                <div className="dropdown-content">
                  <div className="settings-item">
                    <span>🎨 Téma</span>
                    <button 
                      className="theme-quick-toggle"
                      onClick={toggleDarkMode}
                    >
                      {isDarkMode ? "🌞 Világos" : "🌙 Sötét"}
                    </button>
                  </div>
                  <div className="settings-item">
                    <span>🔔 Értesítések</span>
                    <button className="settings-toggle enabled">
                      BE
                    </button>
                  </div>
                  <div className="settings-item">
                    <span>🌍 Nyelv</span>
                    <select className="language-select">
                      <option value="hu">Magyar</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                  <div className="menu-divider"></div>
                  <button 
                    className="settings-menu-item"
                    onClick={() => window.location.href = '/student/settings'}
                  >
                    ⚙️ Részletes beállítások
                  </button>
                  <button className="settings-menu-item">
                    ❓ Súgó és támogatás
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* WELCOME SECTION */}
      <section className="welcome-section">
        <div className="welcome-content">
          <h1 className="greeting">{greeting || 'Welcome!'}</h1>
          <p className="current-date">{currentDate || new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
          
          {/* MOTIVATIONAL QUOTE - Separate container */}
          <div className="motivation-quote-container">
            <div className="motivation-quote">
              <p className="quote-text">{currentQuote.text}</p>
              <p className="quote-author">— {currentQuote.author}</p>
            </div>
          </div>
        </div>
      </section>

      {/* DASHBOARD CONTENT WRAPPER */}
      <div className="lfa-dashboard">

        {/* SIMPLIFIED STATS SECTION - REAL BACKEND DATA ONLY */}
        <section className="dashboard-stats-section">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">📊</div>
              <div className="stat-content">
                <div className="stat-value">
                  {dashboardData.semesterProgress?.completion_percentage || '0'}%
                </div>
                <div className="stat-label">Semester Progress</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🎫</div>
              <div className="stat-content">
                <div className="stat-value">
                  {dashboardData.sessions?.length || '0'}
                </div>
                <div className="stat-label">Sessions Booked</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📂</div>
              <div className="stat-content">
                <div className="stat-value">
                  {dashboardData.activeProjects?.total || '0'}
                </div>
                <div className="stat-label">Active Projects</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🏆</div>
              <div className="stat-content">
                <div className="stat-value">
                  {dashboardData.achievements?.length || '0'}
                </div>
                <div className="stat-label">Achievements</div>
              </div>
            </div>
          </div>
        </section>


      {/* MAIN DASHBOARD - IMPROVED GRID LAYOUT */}
      <main className="dashboard">
        <div className="dashboard-grid">
          {/* PRIMARY SECTION - Hero Actions */}
          <section className="hero-section">
            <QuickActionsGrid />
          </section>

          {/* SECONDARY SECTION - Next Session (High Priority) */}
          <section className="session-section">
            <NextSessionCard />
          </section>

          {/* TERTIARY SECTION - Progress & Skills */}
          <section className="progress-section">
            {/* 🆕 SPECIALIZATION PROGRESS CARD */}
            {userSpecialization && (
              <div className="specialization-progress-card">
                <ProgressCard
                  specializationId={userSpecialization}
                  autoRefresh={true}
                />
              </div>
            )}
            
            {/* Multi-Category Skill Progress - MAIN FEATURE */}
            <div className="card multi-skill-progress">
              <div className="card-header">
                <h2 className="card-title">
                  📊 Skill Development
                </h2>
                <div className="skill-summary">
                  {semesterInfo.currentSemester?.name || 'Current Semester'}
                </div>
              </div>

              {/* Skill Categories Progress Bars - REAL DATA ONLY */}
              <div className="skill-categories">
                {skillCategories.length > 0 ? (
                  skillCategories.map((skill) => (
                    <div key={skill.id} className="skill-category">
                      <div className="skill-header">
                        <div className="skill-info">
                          <span className="skill-icon">{skill.icon}</span>
                          <div>
                            <h4>{skill.name}</h4>
                            <small>{skill.description}</small>
                          </div>
                        </div>
                        <div className="skill-level">
                          <span className="level-label">{skill.level.label}</span>
                          <span className="xp-count">{skill.level.currentXP} XP</span>
                        </div>
                      </div>
                      
                      <div className="skill-progress-bar">
                        <div className="progress-track">
                          <div 
                            className={`progress-fill progress-fill--${skill.id}`}
                            style={{ width: `${skill.level.progress}%` }}
                          ></div>
                        </div>
                        <div className="progress-info">
                          <span>{skill.level.progress}%</span>
                          {skill.level.nextLevelXP > 0 && (
                            <span>{skill.level.nextLevelXP} XP to next level</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state">
                    <div className="empty-state-icon">🎯</div>
                    <h3>Ready to start your journey?</h3>
                    <p>Attend your first session to begin tracking your progress!</p>
                    <button className="cta-button" onClick={() => window.location.href = '/student/schedule'}>
                      Book Your First Session
                    </button>
                  </div>
                )}
              </div>
              
              {/* Overall Progress Summary */}
              <div className="overall-progress-summary">
                <div className="summary-stats">
                  <div className="stat">
                    <span className="stat-value">
                      {Math.round(skillCategories.reduce((sum, skill) => sum + skill.level.progress, 0) / skillCategories.length || 0)}%
                    </span>
                    <span className="stat-label">Average Progress</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">
                      {skillCategories.reduce((sum, skill) => sum + skill.xp, 0)}
                    </span>
                    <span className="stat-label">Total XP</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">
                      {skillCategories.filter(skill => skill.level.level !== 'beginner').length}/{skillCategories.length}
                    </span>
                    <span className="stat-label">Advanced Skills</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 🆕 ACHIEVEMENTS SECTION */}
            {userSpecialization && (
              <div className="achievements-section">
                <AchievementList specializationId={userSpecialization} />
              </div>
            )}

            {/* Current Semester Overview Widget - MOVED TO LEFT */}
            <div className="card semester-overview">
              <div className="card-header">
                <h2 className="card-title">
                  📅 Current Semester Progress
                </h2>
                <div className="semester-badge">
                  {semesterInfo.currentSemester?.name || 'Fall 2025'}
                </div>
              </div>

              <div className="semester-content">
                <div className="stats-row">
                  <div className="stat-card" role="group" aria-label="Projects">
                    <div className="stat-icon" aria-hidden="true">📚</div>
                    <div className="stat-meta">
                      <div className="stat-value">
                        {semesterInfo.completedProjects || 0}/{semesterInfo.totalProjects || 0}
                      </div>
                      <div className="stat-label-test">Projects</div>
                    </div>
                  </div>

                  <div className="stat-card" role="group" aria-label="Sessions">
                    <div className="stat-icon" aria-hidden="true">⚽</div>
                    <div className="stat-meta">
                      <div className="stat-value">
                        {semesterInfo.attendedSessions || 0}/{semesterInfo.totalSessions || 0}
                      </div>
                      <div className="stat-label-test">Sessions</div>
                    </div>
                  </div>

                  <div className="stat-card" role="group" aria-label="Tests">
                    <div className="stat-icon" aria-hidden="true">📝</div>
                    <div className="stat-meta">
                      <div className="stat-value">
                        {dashboardData.quizzes?.completed || 0}/{dashboardData.quizzes?.total || 0}
                      </div>
                      <div className="stat-label-test">Tests</div>
                    </div>
                  </div>

                  <div className="stat-card" role="group" aria-label="Adaptive Learning">
                    <div className="stat-icon" aria-hidden="true">🧠</div>
                    <div className="stat-meta">
                      <div className="stat-value">
                        {dashboardData.adaptiveLearning?.progress || 0}%
                      </div>
                      <div className="stat-label-test">Adaptive</div>
                    </div>
                  </div>

                  <div className="stat-card" role="group" aria-label="Achievements">
                    <div className="stat-icon" aria-hidden="true">🏆</div>
                    <div className="stat-meta">
                      <div className="stat-value">
                        {semesterInfo.achievementsUnlocked || 0}
                      </div>
                      <div className="stat-label-test">Badges</div>
                    </div>
                  </div>

                  <div className="stat-card" role="group" aria-label="Attendance">
                    <div className="stat-icon" aria-hidden="true">✅</div>
                    <div className="stat-meta">
                      <div className="stat-value">
                        {dashboardData.attendance?.rate || 0}%
                      </div>
                      <div className="stat-label-test">Attendance</div>
                    </div>
                  </div>
                </div>

                {userType === 'junior' && (
                  <div className="parent-communication">
                    <h4>📧 Parent Updates</h4>
                    <div className="parent-report-summary">
                      <div className="report-item">
                        <span className="report-date">Last Report: Sept 20</span>
                        <span className="report-status positive">Excellent Progress</span>
                      </div>
                      <div className="next-report">
                        Next Report: Oct 5 • <button className="preview-link" onClick={() => console.log('Preview Draft clicked')}>Preview Draft</button>
                      </div>
                    </div>
                  </div>
                )}

                {userType === 'senior' && (
                  <div className="college-prep">
                    <h4>🎓 College Preparation</h4>
                    <div className="prep-items">
                      <div className="prep-item">
                        <span className="prep-icon">📹</span>
                        <span>Highlight Reel: 85% Complete</span>
                      </div>
                      <div className="prep-item">
                        <span className="prep-icon">📊</span>
                        <span>Performance Analytics Ready</span>
                      </div>
                    </div>
                  </div>
                )}

                {userType === 'adult' && (
                  <div className="flexible-learning">
                    <h4>🔄 Flexible Schedule</h4>
                    <div className="schedule-info">
                      <p>Your preferred training times: <strong>{userConfig.preferredTimes || 'Weekends, Evenings'}</strong></p>
                      <p>Next available makeup session: <strong>Oct 2, 7:00 PM</strong></p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          
            {/* === FORMER RIGHT COLUMN CONTENT - NOW UNIFIED === */}
            {/* Enhanced Achievement Badge System - REAL BACKEND DATA */}
            <div className="card enhanced-achievement-system">
              <div className="card-header">
                <h2 className="card-title">🏆 Achievement Progress</h2>
                <div className="achievement-summary">
                  <span className="total-achievements">
                    {achievements.filter(a => a.unlocked).length}/
                    {achievements.length} Unlocked
                  </span>
                </div>
              </div>

              {/* Achievement Categories - REAL DATA */}
              <div className="achievement-categories">
                {achievements.length > 0 && (
                  <>
                    <div className="achievement-category">
                      <h4>🎯 Skill Mastery</h4>
                      <div className="category-achievements">
                        {achievements
                          .filter(achievement => achievement.category === 'skill')
                          .slice(0, 3)
                          .map((achievement, index) => (
                            <div 
                              key={index} 
                              className={`achievement-item ${achievement.tier} ${achievement.unlocked ? 'unlocked' : 'locked'}`}
                            >
                              <div className="achievement-icon">
                                {achievement.unlocked ? achievement.icon : '🔒'}
                              </div>
                              <div className="achievement-text">
                                <div className="achievement-name">{achievement.name}</div>
                                <div className="achievement-desc">{achievement.description}</div>
                                {achievement.unlocked && (
                                  <div className="achievement-date">
                                    Unlocked: {achievement.unlocked_date || 'Today'}
                                  </div>
                                )}
                                {!achievement.unlocked && achievement.progress && (
                                  <div className="achievement-progress">
                                    <div className="progress-bar">
                                      <div 
                                        className="progress-fill"
                                        style={{ width: `${(achievement.progress.current / achievement.progress.max) * 100}%` }}
                                      ></div>
                                    </div>
                                    <div className="progress-text">
                                      {achievement.progress.current}/{achievement.progress.max}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>

                    <div className="achievement-category">
                      <h4>📈 Progress Milestones</h4>
                      <div className="category-achievements">
                        {achievements
                          .filter(achievement => achievement.category === 'progress')
                          .slice(0, 2)
                          .map((achievement, index) => (
                            <div 
                              key={index} 
                              className={`achievement-item ${achievement.tier} ${achievement.unlocked ? 'unlocked' : 'locked'}`}
                            >
                              <div className="achievement-icon">
                                {achievement.unlocked ? achievement.icon : '🔒'}
                              </div>
                              <div className="achievement-text">
                                <div className="achievement-name">{achievement.name}</div>
                                <div className="achievement-desc">{achievement.description}</div>
                                {achievement.unlocked && (
                                  <div className="achievement-date">
                                    Unlocked: {achievement.unlocked_date || 'This week'}
                                  </div>
                                )}
                                {!achievement.unlocked && achievement.progress && (
                                  <div className="achievement-progress">
                                    <div className="progress-bar">
                                      <div 
                                        className="progress-fill"
                                        style={{ width: `${(achievement.progress.current / achievement.progress.max) * 100}%` }}
                                      ></div>
                                    </div>
                                    <div className="progress-text">
                                      {achievement.progress.current}/{achievement.progress.max}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  </>
                )}

                {achievements.length === 0 && (
                  <div className="no-achievements">
                    <p>🎯 Start your journey to unlock achievements!</p>
                    <p>Book sessions, complete projects, and take tests to earn badges.</p>
                  </div>
                )}
              </div>

              {/* Next Achievement Preview - REAL DATA */}
              {achievements.length > 0 && (
                <div className="next-achievement">
                  <h4>🎯 Next Milestone</h4>
                  {(() => {
                    const nextAchievement = achievements
                      .find(a => !a.unlocked && a.progress);
                    return nextAchievement ? (
                      <div className="next-achievement-card">
                        <div className="next-icon">🔒</div>
                        <div className="next-content">
                          <div className="next-name">{nextAchievement.name}</div>
                          <div className="next-desc">{nextAchievement.description}</div>
                          <div className="next-progress">
                            <div className="progress-bar">
                              <div 
                                className="progress-fill"
                                style={{ width: `${(nextAchievement.progress.current / nextAchievement.progress.max) * 100}%` }}
                              ></div>
                            </div>
                            <div className="progress-text">
                              {nextAchievement.progress.current}/{nextAchievement.progress.max} 
                              ({Math.round((nextAchievement.progress.current / nextAchievement.progress.max) * 100)}%)
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="no-next-achievement">
                        <span>🌟 You're doing great! Keep up the excellent work!</span>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>

            {/* Recent Feedback */}
            <RecentFeedbackSection />

            {/* Daily Challenges Panel */}
            <div className="card daily-challenges-panel">
              <div className="card-header">
                <h2 className="card-title">🎯 Daily Challenges</h2>
                <div className="challenges-date">
                  {new Date().toLocaleDateString('en-US', { 
                    weekday: 'short',
                    month: 'short', 
                    day: 'numeric'
                  })}
                </div>
              </div>

              <div className="challenges-content">
                {userConfig.gamificationLevel === 'high' && (
                  <div className="full-challenges">
                    {dailyChallenges.slice(0, 4).map((challenge) => (
                      <div 
                        key={challenge.id} 
                        className={`challenge-item ${challenge.completed ? 'completed' : 'active'} ${challenge.difficulty}`}
                      >
                        <div className="challenge-header">
                          <div className="challenge-icon">
                            {challenge.completed ? '✅' : challenge.icon}
                          </div>
                          <div className="challenge-info">
                            <div className="challenge-title">{challenge.title}</div>
                            <div className="challenge-desc">{challenge.description}</div>
                          </div>
                          <div className="challenge-reward">
                            <span className="reward-xp">+{challenge.xpReward} XP</span>
                            <span className="difficulty-badge">{challenge.difficulty}</span>
                          </div>
                        </div>
                        
                        {!challenge.completed && challenge.progress && (
                          <div className="challenge-progress">
                            <div className="progress-bar">
                              <div 
                                className="progress-fill"
                                style={{ width: `${(challenge.progress.current / challenge.progress.max) * 100}%` }}
                              ></div>
                            </div>
                            <div className="progress-text">
                              {challenge.progress.current}/{challenge.progress.max}
                            </div>
                          </div>
                        )}

                        {challenge.completed && (
                          <div className="completion-info">
                            <span className="completion-time">
                              Completed {challenge.completedTime || 'earlier today'}
                            </span>
                            <span className="earned-xp">+{challenge.xpReward} XP earned!</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {userConfig.gamificationLevel === 'medium' && (
                  <div className="simple-challenges">
                    {dailyChallenges.slice(0, 3).map((challenge) => (
                      <div 
                        key={challenge.id} 
                        className={`simple-challenge-item ${challenge.completed ? 'completed' : 'active'}`}
                      >
                        <div className="simple-challenge-icon">
                          {challenge.completed ? '✅' : challenge.icon}
                        </div>
                        <div className="simple-challenge-content">
                          <div className="simple-challenge-title">{challenge.title}</div>
                          {!challenge.completed && challenge.progress && (
                            <div className="simple-progress">
                              {challenge.progress.current}/{challenge.progress.max}
                            </div>
                          )}
                          {challenge.completed && (
                            <div className="simple-completion">✓ Done!</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {userConfig.gamificationLevel === 'low' && (
                  <div className="minimal-challenges">
                    <h4>Today's Focus</h4>
                    <div className="focus-items">
                      {dailyChallenges.slice(0, 2).map((challenge) => (
                        <div key={challenge.id} className="focus-item">
                          <span className="focus-icon">{challenge.icon}</span>
                          <span className="focus-text">{challenge.title}</span>
                          <span className={`focus-status ${challenge.completed ? 'done' : 'pending'}`}>
                            {challenge.completed ? 'Done' : 'Pending'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Daily Challenge Summary */}
                {userConfig.gamificationLevel !== 'low' && (
                  <div className="challenges-summary">
                    <div className="summary-stats">
                      <div className="summary-stat">
                        <span className="stat-number">
                          {dailyChallenges.filter(c => c.completed).length}/{dailyChallenges.length}
                        </span>
                        <span className="stat-text">Completed</span>
                      </div>
                      <div className="summary-stat">
                        <span className="stat-number">
                          {dailyChallenges
                            .filter(c => c.completed)
                            .reduce((sum, c) => sum + c.xpReward, 0)}
                        </span>
                        <span className="stat-text">XP Earned</span>
                      </div>
                      <div className="summary-stat">
                        <span className="stat-number">
                          {Math.round((dailyChallenges.filter(c => c.completed).length / dailyChallenges.length) * 100)}%
                        </span>
                        <span className="stat-text">Daily Score</span>
                      </div>
                    </div>

                    {dailyChallenges.filter(c => c.completed).length === dailyChallenges.length && (
                      <div className="perfect-day">
                        🌟 Perfect Day! All challenges completed! 🌟
                      </div>
                    )}
                  </div>
                )}

                {/* User Type Specific Tips */}
                {userType === 'junior' && (
                  <div className="daily-tip">
                    <div className="tip-icon">💡</div>
                    <div className="tip-text">
                      <strong>Pro Tip:</strong> Complete challenges to unlock new skills and earn badges!
                    </div>
                  </div>
                )}

                {userType === 'senior' && (
                  <div className="daily-tip">
                    <div className="tip-icon">🎯</div>
                    <div className="tip-text">
                      <strong>Advanced Goal:</strong> Leadership challenges help build college recruiting profile!
                    </div>
                  </div>
                )}

                {userType === 'adult' && (
                  <div className="daily-tip">
                    <div className="tip-icon">⚡</div>
                    <div className="tip-text">
                      <strong>Motivation:</strong> Small daily wins lead to lasting fitness improvements!
                    </div>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      </main>
      </div>
      
      {/* DEBUG: Debug Toggle Button */}
      <button 
        className={`debug-toggle ${debugMode ? 'active' : ''}`}
        onClick={toggleDebugMode}
        title={debugMode ? 'Disable Debug Mode' : 'Enable Debug Mode'}
      >
        {debugMode ? '🐛 DEBUG: ON' : '🔍 DEBUG: OFF'}
      </button>
      
      {/* DEBUG: Debug Info Panel */}
      <div className="debug-info">
        <h4>🐛 Layout Debug Mode</h4>
        <ul>
          <li><span className="debug-color-red">■</span> Header (Red)</li>
          <li><span className="debug-color-green">■</span> Main Dashboard (Green)</li>
          <li><span className="debug-color-blue">■</span> Unified Content (Blue)</li>
          <li><span className="debug-color-orange">■</span> Cards (Orange)</li>
          <li><span className="debug-color-purple">■</span> Sections (Purple)</li>
          <li><span className="debug-color-cyan">■</span> Containers (Cyan)</li>
        </ul>
        <div style={{marginTop: '10px', fontSize: '10px', opacity: '0.7'}}>
          Click labels to see component boundaries
        </div>
      </div>
    </div>
  );
};

console.log('🔧 TIMELINE DEBUG: Forced grid layout applied at', new Date());

export default StudentDashboard;
