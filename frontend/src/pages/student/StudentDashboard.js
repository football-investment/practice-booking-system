import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import { detectOverflow } from '../../utils/overflowDetector';
import { LFAUserService } from '../../utils/userTypeService';
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
  const [aiSuggestions] = useState([
    {
      id: 'weak-foot-training',
      title: 'Improve Weak Foot Training',
      difficulty: 'Est.',
      type: 'training',
      priority: 'high'
    },
    {
      id: 'tactical-positioning', 
      title: 'Tactical Positioning',
      difficulty: 'Est.',
      type: 'tactical',
      priority: 'medium'
    }
  ]);

  useEffect(() => {
    // 🎯 Initialize user type and business logic first
    initializeUserProfile();
    
    loadLFADashboardData();
    loadNextSession();
    loadRecentFeedback();
    
    // 🚨 DEBUG: Auto-detect overflow after data loads
    setTimeout(() => {
      detectOverflow();
    }, 3000);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 🎯 NEW: Initialize user profile and business logic
  const initializeUserProfile = () => {
    if (!user) return;
    
    console.log('🎯 LFA: Initializing user profile for:', user.name);
    
    // Determine user type
    const detectedUserType = LFAUserService.determineUserType(user);
    setUserType(detectedUserType);
    
    // Get user type configuration
    const config = LFAUserService.getUserTypeConfig(detectedUserType);
    setUserConfig(config);
    
    // Generate skill categories with mock data
    const skills = LFAUserService.generateSkillCategories(detectedUserType);
    setSkillCategories(skills);
    
    // Generate daily challenges
    const challenges = LFAUserService.generateDailyChallenges(detectedUserType, skills);
    setDailyChallenges(challenges);
    
    // Get semester information
    const semesterData = LFAUserService.getSemesterInfo();
    setSemesterInfo(semesterData);
    
    console.log('🎯 LFA Profile initialized:', {
      userType: detectedUserType,
      config,
      skills: skills.length,
      challenges: challenges.length,
      semester: semesterData.currentSemester.name
    });
  };

  const loadLFADashboardData = async () => {
    setLoading(true);
    try {
      // Use the complete LFA dashboard API integration
      const lfaData = await apiService.getLFADashboardData();
      setDashboardData(lfaData);
    } catch (error) {
      console.error('LFA Dashboard loading failed:', error);
      // API service provides fallback data, just set minimal fallback
      setDashboardData({
        nextSession: null,
        progress: { skills: [], overall_progress: 0 },
        gamification: { points: 0, level: 1, achievements: [] },
        specialization: null,
        recommendations: { recommendations: [] },
        recentFeedback: { feedback: [] },
        performance: { overall_score: 0, recent_performance: [] },
        activeProjects: { projects: [] },
        pendingQuizzes: { quizzes: [] }
      });
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
        // MOCK FALLBACK based on the UI screenshot
        setNextSession({
          id: 'mock-1',
          date_start: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          date_end: new Date(Date.now() + 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000).toISOString(),
          location: 'Training Ground A',
          instructor: { name: 'Coach Martinez' },
          title: 'Advanced Football Tactics',
          type: 'training'
        });
      }
    } catch (error) {
      console.warn('Failed to load next session, using mock data:', error);
      // MOCK FALLBACK
      setNextSession({
        id: 'mock-1', 
        date_start: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        date_end: new Date(Date.now() + 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000).toISOString(),
        location: 'Training Ground A',
        instructor: { name: 'Coach Martinez' },
        title: 'Advanced Football Tactics',
        type: 'training'
      });
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadRecentFeedback = async () => {
    try {
      const feedback = await apiService.getMyFeedback();
      setRecentFeedback(feedback.slice(0, 3)); // Latest 3
    } catch (error) {
      // FALLBACK based on screenshot
      setRecentFeedback([
        {
          id: 1,
          coach: 'Coach Martinez',
          message: 'Great improvement in shooting accuracy this week',
          rating: 4.5,
          date: new Date().toISOString()
        }
      ]);
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

  const getInitials = (name) => {
    return name ? name.split(' ').map(n => n[0]).join('').toUpperCase() : 'ST';
  };

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

  // NEW COMPONENT: Quick Actions Grid
  const QuickActionsGrid = () => {
    const quickActions = [
      {
        id: 'schedule-session',
        title: 'Schedule Session', 
        description: 'Book a training session',
        color: 'primary',
        onClick: () => window.location.href = '/student/sessions'
      },
      {
        id: 'view-progress',
        title: 'View Progress',
        description: 'Check your improvement',
        color: 'secondary', 
        onClick: () => window.location.href = '/student/profile'
      },
      {
        id: 'detailed-progress',
        title: 'Detailed Progress',
        description: 'In-depth analysis',
        color: 'tertiary',
        onClick: () => window.location.href = '/student/profile'
      },
      {
        id: 'practice-drills',
        title: 'Practice Drills',
        description: 'Solo training exercises',
        color: 'primary',
        onClick: () => window.location.href = '/student/sessions'
      },
      {
        id: 'coach-reviews',
        title: 'Coach Reviews',
        description: 'View feedback',
        color: 'secondary',
        onClick: () => window.location.href = '/student/feedback'
      },
      {
        id: 'achievements',
        title: 'Achievements',
        description: 'Your progress badges',
        color: 'tertiary',
        onClick: () => window.location.href = '/student/profile'
      },
      {
        id: 'quick-drills',
        title: 'Quick Drills',
        description: '5-minute exercises',
        color: 'primary',
        onClick: () => window.location.href = '/student/sessions'
      },
      {
        id: 'progress-insights',
        title: 'Progress Insights',
        description: 'AI-powered analytics',
        color: 'secondary',
        onClick: () => window.location.href = '/student/profile'
      }
    ];

    return (
      <div className="quick-actions">
        <h2>Quick Actions</h2>
        <div className="actions-grid">
          {quickActions.map(action => (
            <button 
              key={action.id}
              className={`action-button ${action.color}`}
              onClick={action.onClick}
            >
              <div className="action-content">
                <h4>{action.title}</h4>
                <p>{action.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  };

  // NEW COMPONENT: AI Suggestions Section
  const AISuggestionsSection = () => (
    <div className="ai-suggestions">
      <h3>AI Suggested</h3>
      {aiSuggestions.map(suggestion => (
        <div key={suggestion.id} className="suggestion-card">
          <div className="suggestion-content">
            <h4>AI Suggested: {suggestion.title}</h4>
            <p>Difficulty: {suggestion.difficulty}</p>
          </div>
          <button className="start-button">Start</button>
        </div>
      ))}
    </div>
  );

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
    <div className="lfa-dashboard">
      
      {/* WELCOME HEADER SECTION - DYNAMIC BY USER TYPE */}
      <section className={`welcome-header welcome-header--${userType}`}>
        <div className="welcome-content">
          <div className="welcome-text">
            <h1>Welcome back, {user?.name || 'Student'}!</h1>
            <p>{userConfig.welcomeMessage || 'Ready to elevate your football skills today? Let\'s achieve greatness together.'}</p>
            {userType === 'junior' && (
              <div className="user-type-badge junior">
                🌟 Junior Academy (Ages 8-14)
              </div>
            )}
            {userType === 'senior' && (
              <div className="user-type-badge senior">
                ⚽ Senior Academy (Ages 15-18)
              </div>
            )}
            {userType === 'adult' && (
              <div className="user-type-badge adult">
                👍 Adult Programs (18+)
              </div>
            )}
          </div>
          <div className="welcome-stats">
            {userConfig.gamificationLevel === 'high' && (
              <>
                <div className="stat-item">
                  <div className="stat-value">{dashboardData.gamification?.totalPoints?.toLocaleString() || '2,847'}</div>
                  <div className="stat-label">XP Points</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{dashboardData.gamification?.level || '12'}</div>
                  <div className="stat-label">Level</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{dashboardData.progress?.overall_progress || '85'}%</div>
                  <div className="stat-label">Progress</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">#{dashboardData.gamification?.leaderboardPosition || '47'}</div>
                  <div className="stat-label">Rank</div>
                </div>
              </>
            )}
            {userConfig.gamificationLevel === 'medium' && (
              <>
                <div className="stat-item">
                  <div className="stat-value">{skillCategories.length}</div>
                  <div className="stat-label">Skills Tracking</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{userConfig.sessionFrequency}</div>
                  <div className="stat-label">Training</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{semesterInfo.currentSemester?.name || 'Current'}</div>
                  <div className="stat-label">Semester</div>
                </div>
              </>
            )}
            {userConfig.gamificationLevel === 'low' && (
              <>
                <div className="stat-item">
                  <div className="stat-value">{userConfig.sessionFrequency}</div>
                  <div className="stat-label">Schedule</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{userConfig.focusAreas?.[0] || 'Fitness'}</div>
                  <div className="stat-label">Primary Focus</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{semesterInfo.currentSemester?.name || 'Current'}</div>
                  <div className="stat-label">Session</div>
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      {/* XP AND LEVEL SYSTEM */}
      <section className="xp-level-container">
        <div className="xp-header">
          <h3>Experience Progress</h3>
          <div className="level-badge">
            ⭐ Level {dashboardData.gamification?.level || '12'}
          </div>
        </div>
        <div className="xp-progress">
          <div className="xp-bar">
            <div 
              className="xp-fill" 
              style={{ width: `${((dashboardData.gamification?.currentLevelXP || 750) / (dashboardData.gamification?.nextLevelXP || 1000)) * 100}%` }}
            ></div>
          </div>
          <div className="xp-text">
            {dashboardData.gamification?.currentLevelXP || '750'} / {dashboardData.gamification?.nextLevelXP || '1,000'} XP
          </div>
        </div>
      </section>

      {/* HEADER (LEGACY SUPPORT) */}
      <header className="header">
        <div className="header-left">
          <div className="logo">⚽ LFA</div>
          <div className="greeting">
            Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}!
          </div>
        </div>
        <div className="header-right">
          <div className="notification-badge">
            🔔
            <span className="badge">{dashboardData.gamification?.unread_notifications || 3}</span>
          </div>
          <div className="user-avatar">
            {getInitials(user?.name)}
          </div>
        </div>
      </header>

      {/* QUICK STATUS STRIP */}
      <div className="status-strip">
        <div className="status-item">
          <div className="status-icon"></div>
          <span><strong>Next Session:</strong> {dashboardData.nextSession ? 'Tomorrow 14:00' : 'None scheduled'}</span>
        </div>
        <div className="status-item">
          <div className="status-icon"></div>
          <span><strong>Progress:</strong> {dashboardData.progress?.overall_progress || 85}%</span>
        </div>
        <div className="status-item">
          <div className="status-icon"></div>
          <span><strong>Points:</strong> {dashboardData.gamification?.totalPoints?.toLocaleString() || '2,847'}</span>
        </div>
        <div className="status-item">
          <div className="status-icon"></div>
          <span><strong>Rank:</strong> #{dashboardData.gamification?.leaderboardPosition || '47'}</span>
        </div>
      </div>

      {/* MAIN DASHBOARD - NEW TWO-COLUMN LAYOUT */}
      <main className="dashboard">
        <div className="dashboard-content">
          {/* LEFT COLUMN - Main Content */}
          <div className="left-column">
            {/* Next Session Card */}
            <NextSessionCard />
            
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

              {/* Skill Categories Progress Bars */}
              <div className="skill-categories">
                {skillCategories.map((skill) => (
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
                ))}
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
                <div className="semester-timeline">
                  <div className="timeline-item">
                    <div className="timeline-marker completed"></div>
                    <div className="timeline-content">
                      <h4>Semester Started</h4>
                      <p>{semesterInfo.currentSemester?.start_date || 'September 1, 2025'}</p>
                    </div>
                  </div>
                  
                  <div className="timeline-item">
                    <div className="timeline-marker current"></div>
                    <div className="timeline-content">
                      <h4>Mid-Term Evaluation</h4>
                      <p>{semesterInfo.midtermDate || 'October 15, 2025'}</p>
                      <small>{userType === 'junior' ? 'Skill Assessment' : 'Performance Review'}</small>
                    </div>
                  </div>
                  
                  <div className="timeline-item">
                    <div className="timeline-marker pending"></div>
                    <div className="timeline-content">
                      <h4>Final Evaluation</h4>
                      <p>{semesterInfo.currentSemester?.end_date || 'December 15, 2025'}</p>
                      <small>Complete all requirements</small>
                    </div>
                  </div>
                </div>

                <div className="semester-stats">
                  <div className="semester-stat">
                    <div className="stat-icon">📚</div>
                    <div className="stat-details">
                      <span className="stat-number">
                        {semesterInfo.completedProjects || 2}/{semesterInfo.totalProjects || 4}
                      </span>
                      <span className="stat-text">Projects</span>
                    </div>
                  </div>
                  
                  <div className="semester-stat">
                    <div className="stat-icon">⚽</div>
                    <div className="stat-details">
                      <span className="stat-number">
                        {semesterInfo.attendedSessions || 18}/{semesterInfo.totalSessions || 24}
                      </span>
                      <span className="stat-text">Sessions</span>
                    </div>
                  </div>
                  
                  <div className="semester-stat">
                    <div className="stat-icon">🏆</div>
                    <div className="stat-details">
                      <span className="stat-number">
                        {semesterInfo.achievementsUnlocked || 7}
                      </span>
                      <span className="stat-text">Achievements</span>
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
          </div>
          
          {/* RIGHT COLUMN - Sidebar */}
          <div className="right-column">
            {/* Enhanced Achievement Badge System */}
            <div className="card enhanced-achievement-system">
              <div className="card-header">
                <h2 className="card-title">🏆 Achievement Progress</h2>
                <div className="achievement-summary">
                  {userConfig.gamificationLevel === 'high' && (
                    <span className="total-achievements">
                      {LFAUserService.getUserAchievements(userType, skillCategories).filter(a => a.unlocked).length}/
                      {LFAUserService.getUserAchievements(userType, skillCategories).length} Unlocked
                    </span>
                  )}
                </div>
              </div>

              {/* Achievement Categories */}
              <div className="achievement-categories">
                {userConfig.gamificationLevel === 'high' && (
                  <>
                    <div className="achievement-category">
                      <h4>🎯 Skill Mastery</h4>
                      <div className="category-achievements">
                        {LFAUserService.getUserAchievements(userType, skillCategories)
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
                                    Unlocked: {achievement.unlockedDate || 'Today'}
                                  </div>
                                )}
                                {!achievement.unlocked && achievement.progress && (
                                  <div className="achievement-progress">
                                    <div className="progress-bar">
                                      <div 
                                        className="progress-fill"
                                        style={{ width: `${(achievement.progress.current / achievement.progress.required) * 100}%` }}
                                      ></div>
                                    </div>
                                    <div className="progress-text">
                                      {achievement.progress.current}/{achievement.progress.required}
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
                        {LFAUserService.getUserAchievements(userType, skillCategories)
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
                                    Unlocked: {achievement.unlockedDate || 'This week'}
                                  </div>
                                )}
                                {!achievement.unlocked && achievement.progress && (
                                  <div className="achievement-progress">
                                    <div className="progress-bar">
                                      <div 
                                        className="progress-fill"
                                        style={{ width: `${(achievement.progress.current / achievement.progress.required) * 100}%` }}
                                      ></div>
                                    </div>
                                    <div className="progress-text">
                                      {achievement.progress.current}/{achievement.progress.required}
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

                {userConfig.gamificationLevel === 'medium' && (
                  <div className="simple-achievements">
                    <h4>🎖️ Recent Accomplishments</h4>
                    <div className="accomplishment-list">
                      {LFAUserService.getUserAchievements(userType, skillCategories)
                        .filter(a => a.unlocked)
                        .slice(0, 4)
                        .map((achievement, index) => (
                          <div key={index} className="accomplishment-item">
                            <span className="accomplishment-icon">{achievement.icon}</span>
                            <span className="accomplishment-text">{achievement.name}</span>
                            <span className="accomplishment-date">{achievement.unlockedDate || 'Recent'}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {userConfig.gamificationLevel === 'low' && (
                  <div className="minimal-progress">
                    <h4>✅ Progress Highlights</h4>
                    <div className="highlight-list">
                      <div className="highlight-item">
                        <span className="highlight-icon">📊</span>
                        <div className="highlight-content">
                          <div className="highlight-title">Skills Improved</div>
                          <div className="highlight-value">
                            {skillCategories.filter(skill => skill.level.progress > 50).length} areas
                          </div>
                        </div>
                      </div>
                      <div className="highlight-item">
                        <span className="highlight-icon">⭐</span>
                        <div className="highlight-content">
                          <div className="highlight-title">Training Consistency</div>
                          <div className="highlight-value">
                            {userConfig.sessionFrequency}
                          </div>
                        </div>
                      </div>
                      <div className="highlight-item">
                        <span className="highlight-icon">🎯</span>
                        <div className="highlight-content">
                          <div className="highlight-title">Focus Area</div>
                          <div className="highlight-value">
                            {userConfig.focusAreas?.[0] || 'General Fitness'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Next Achievement Preview */}
              {userConfig.gamificationLevel !== 'low' && (
                <div className="next-achievement">
                  <h4>🎯 Next Milestone</h4>
                  {(() => {
                    const nextAchievement = LFAUserService.getUserAchievements(userType, skillCategories)
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
                                style={{ width: `${(nextAchievement.progress.current / nextAchievement.progress.required) * 100}%` }}
                              ></div>
                            </div>
                            <div className="progress-text">
                              {nextAchievement.progress.current}/{nextAchievement.progress.required} 
                              ({Math.round((nextAchievement.progress.current / nextAchievement.progress.required) * 100)}%)
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

            {/* AI Suggestions - MOVED TO SIDEBAR */}
            <AISuggestionsSection />
            
            {/* Recent Feedback - MOVED TO SIDEBAR */}
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
                    {dailyChallenges.slice(0, 4).map((challenge, index) => (
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
                                style={{ width: `${(challenge.progress.current / challenge.progress.required) * 100}%` }}
                              ></div>
                            </div>
                            <div className="progress-text">
                              {challenge.progress.current}/{challenge.progress.required}
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
                    {dailyChallenges.slice(0, 3).map((challenge, index) => (
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
                              {challenge.progress.current}/{challenge.progress.required}
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
                      {dailyChallenges.slice(0, 2).map((challenge, index) => (
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

            {/* Quick Actions */}
            <QuickActionsGrid />
          </div>
        </div>
      </main>
    </div>
  );
};

export default StudentDashboard;