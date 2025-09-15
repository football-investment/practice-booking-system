import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiService from '../../services/apiService';
import './GamificationProfile.css';

const GamificationProfile = () => {
  const [gamificationData, setGamificationData] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme, setColorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );
  const navigate = useNavigate();

  useEffect(() => {
    loadGamificationProfile();
  }, []);

  useEffect(() => {
    // Apply theme and color scheme to document
    const root = document.documentElement;
    
    if (theme === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const applyAutoTheme = () => {
        root.setAttribute('data-theme', mediaQuery.matches ? 'dark' : 'light');
        root.setAttribute('data-color', colorScheme);
      };
      
      applyAutoTheme();
      mediaQuery.addListener(applyAutoTheme);
      
      return () => mediaQuery.removeListener(applyAutoTheme);
    } else {
      root.setAttribute('data-theme', theme);
      root.setAttribute('data-color', colorScheme);
    }
  }, [theme, colorScheme]);

  const loadGamificationProfile = async () => {
    try {
      setLoading(true);
      const [gamificationResponse, profileResponse] = await Promise.all([
        apiService.getMyGamificationData(),
        apiService.getCurrentUser()
      ]);
      
      setGamificationData(gamificationResponse);
      setUserProfile(profileResponse);
    } catch (err) {
      console.error('Failed to load gamification profile:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const calculateLevelProgress = () => {
    if (!gamificationData?.stats) return 0;
    const currentLevel = gamificationData.stats.level;
    const currentXP = gamificationData.stats.total_xp;
    const xpForCurrentLevel = (currentLevel - 1) * 1000;
    const xpForNextLevel = currentLevel * 1000;
    const progressInLevel = currentXP - xpForCurrentLevel;
    return (progressInLevel / (xpForNextLevel - xpForCurrentLevel)) * 100;
  };

  const getUpcomingAchievements = () => {
    if (!gamificationData?.stats) return [];
    
    const stats = gamificationData.stats;
    const achievements = gamificationData.achievements || [];
    const upcoming = [];

    // Check which new achievements are already earned
    const earnedBadgeTypes = achievements.map(a => a.badge_type);

    // First-time achievements - show if not earned yet
    if (!earnedBadgeTypes.includes('first_quiz_completed')) {
      upcoming.push({ 
        title: "🧠 First Quiz Master", 
        description: "Complete your very first quiz successfully", 
        type: "first_time", 
        requirement: "Pass any quiz", 
        icon: "🧠" 
      });
    }

    if (!earnedBadgeTypes.includes('first_project_enrolled')) {
      upcoming.push({ 
        title: "📝 Project Pioneer", 
        description: "Successfully enroll in your first project", 
        type: "first_time", 
        requirement: "Enroll in a project", 
        icon: "📝" 
      });
    }

    if (!earnedBadgeTypes.includes('quiz_enrollment_combo')) {
      upcoming.push({ 
        title: "🎯 Complete Journey", 
        description: "Complete quiz and enroll in project on the same day", 
        type: "combo", 
        requirement: "Quiz + enrollment same day", 
        icon: "🎯" 
      });
    }

    if (!earnedBadgeTypes.includes('newcomer_welcome')) {
      upcoming.push({ 
        title: "🌟 Welcome Newcomer", 
        description: "Welcome to the learning journey", 
        type: "welcome", 
        requirement: "First activity within 24h", 
        icon: "🌟" 
      });
    }

    // Semester-based achievements
    if (stats.semesters_participated === 0) {
      upcoming.push({ title: "First Steps", description: "Complete your first semester", type: "semester", requirement: "1 semester", icon: "🌱" });
    } else if (stats.semesters_participated < 2) {
      upcoming.push({ title: "Dedicated Student", description: "Complete 2 semesters", type: "semester", requirement: "2 semesters", icon: "📚" });
    } else if (stats.semesters_participated < 3) {
      upcoming.push({ title: "Regular Participant", description: "Complete 3 semesters", type: "semester", requirement: "3 semesters", icon: "🎯" });
    } else if (stats.semesters_participated < 5) {
      upcoming.push({ title: "Master Student", description: "Complete 5 semesters", type: "semester", requirement: "5 semesters", icon: "👑" });
    } else if (stats.semesters_participated < 7) {
      upcoming.push({ title: "Elite Learner", description: "Complete 7 semesters", type: "semester", requirement: "7 semesters", icon: "💎" });
    }

    // Attendance-based achievements
    if (stats.attendance_rate < 90) {
      upcoming.push({ title: "Perfect Attendance", description: "Achieve 90%+ attendance rate", type: "attendance", requirement: "90% attendance", icon: "✅" });
    }

    // Level-based achievements
    const nextLevel = stats.level + 1;
    upcoming.push({ title: `Level ${nextLevel}`, description: `Reach level ${nextLevel}`, type: "level", requirement: `${nextLevel * 1000} XP`, icon: "⭐" });

    return upcoming.slice(0, 3); // Show top 3 upcoming
  };

  if (loading) {
    return (
      <div className="gamification-profile">
        <div className="loading">Loading gamification profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="gamification-profile">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  if (!gamificationData || !userProfile) {
    return (
      <div className="gamification-profile">
        <div className="no-data">No gamification data available</div>
      </div>
    );
  }

  const stats = gamificationData.stats;
  const achievements = gamificationData.achievements || [];
  const upcomingAchievements = getUpcomingAchievements();

  // Debug logging for semester journey
  console.log('🎓 Semester Journey Debug:', {
    semesters_participated: stats.semesters_participated,
    total_bookings: stats.total_bookings,
    total_attended: stats.total_attended,
    total_xp: stats.total_xp,
    level: stats.level,
    first_semester_date: stats.first_semester_date,
    semesters: gamificationData.semesters || [],
    current_semester: gamificationData.current_semester || null
  });

  return (
    <div className="gamification-profile">
      <div className="profile-header">
        <button className="back-button" onClick={() => navigate('/student/dashboard')}>
          ← Back to Dashboard
        </button>
        <div className="profile-title">
          <h1>Gamification Profile</h1>
          <p>Track your learning journey and achievements</p>
        </div>
      </div>

      {/* Player Card */}
      <div className="player-card">
        <div className="player-info">
          <div className="player-avatar">
            {userProfile.full_name?.charAt(0) || 'U'}
          </div>
          <div className="player-details">
            <h2>{userProfile.full_name}</h2>
            <p className="player-email">{userProfile.email}</p>
            {gamificationData.status.is_returning && (
              <div className="veteran-status">
                <span className="veteran-badge">
                  {gamificationData.status.icon} {gamificationData.status.title}
                </span>
              </div>
            )}
          </div>
        </div>
        
        <div className="player-stats">
          <div className="level-section">
            <div className="level-info">
              <span className="level-label">Level</span>
              <span className="level-number">{stats.level}</span>
            </div>
            <div className="xp-progress">
              <div className="xp-info">
                <span>{stats.total_xp} XP</span>
                <span>{stats.level * 1000} XP</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${calculateLevelProgress()}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">🎓</div>
          <div className="stat-info">
            <div className="stat-value">{stats.semesters_participated}</div>
            <div className="stat-label">Semesters</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">📅</div>
          <div className="stat-info">
            <div className="stat-value">{stats.total_bookings}</div>
            <div className="stat-label">Total Bookings</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <div className="stat-value">{stats.total_attended}</div>
            <div className="stat-label">Attended</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-info">
            <div className="stat-value">{stats.attendance_rate?.toFixed(1) || '0.0'}%</div>
            <div className="stat-label">Attendance Rate</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">💭</div>
          <div className="stat-info">
            <div className="stat-value">{stats.feedback_given || 0}</div>
            <div className="stat-label">Feedback Given</div>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">⏰</div>
          <div className="stat-info">
            <div className="stat-value">{stats.punctuality_score?.toFixed(1) || '100.0'}%</div>
            <div className="stat-label">Punctuality</div>
          </div>
        </div>
      </div>

      {/* Semester Timeline */}
      <div className="timeline-section">
        <h3>Semester Journey</h3>
        <div className="timeline">
          {Array.from({ length: Math.max(stats.semesters_participated + 1, 1) }, (_, i) => {
            // Determine the status of each semester
            let status, marker, text, semesterName, semesterTitle;
            
            // Get semester information
            const userSemesters = gamificationData.semesters || [];
            const currentSemester = gamificationData.current_semester;
            
            // Debug logging for each semester
            const isCompleted = i < stats.semesters_participated;
            const isCurrentWithActivity = i === stats.semesters_participated && (stats.total_bookings > 0 || stats.total_attended > 0 || stats.total_xp > 0);
            
            // Determine semester name and title - separate index from name
            let semesterIndex = `Semester ${i + 1}`;
            
            if (i < userSemesters.length) {
              // User has participated in this semester
              semesterName = userSemesters[i].name;
              semesterTitle = userSemesters[i].name;
            } else if (i === stats.semesters_participated && currentSemester) {
              // Current semester (user is participating now)
              semesterName = currentSemester.name;
              semesterTitle = currentSemester.name;
            } else {
              // Future/unknown semester
              semesterName = `Semester ${i + 1}`;
              semesterTitle = `Semester ${i + 1}`;
            }
            
            console.log(`📅 ${semesterTitle} Debug:`, {
              index: i,
              semesterName,
              semesterTitle,
              semesters_participated: stats.semesters_participated,
              total_bookings: stats.total_bookings,
              total_attended: stats.total_attended,
              total_xp: stats.total_xp,
              isCompleted,
              isCurrentWithActivity,
              condition1: i < stats.semesters_participated,
              condition2: i === stats.semesters_participated,
              condition3: stats.total_bookings > 0,
              condition4: stats.total_attended > 0,
              condition5: stats.total_xp > 0
            });
            
            if (i < stats.semesters_participated) {
              // Past semesters - completed
              status = 'completed';
              marker = '✅';
              text = 'Completed';
            } else if (i === stats.semesters_participated && (stats.total_bookings > 0 || stats.total_attended > 0 || stats.total_xp > 0)) {
              // Current semester with activity - active (including XP from quizzes)
              status = 'current'; // Use current styling
              marker = '🔄';
              text = 'Current';
            } else {
              // Future semesters - upcoming
              status = 'upcoming';
              marker = '⏳';
              text = 'Upcoming';
            }
            
            console.log(`📅 ${semesterTitle} Result:`, { status, marker, text });
            
            return (
              <div key={i} className="timeline-item-wrapper">
                <div className="semester-index">{semesterIndex}</div>
                <div className={`timeline-item ${status}`}>
                  <div className="timeline-marker">
                    {marker}
                  </div>
                  <div className="timeline-content">
                    <h4>{semesterTitle}</h4>
                    <p>{text}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Achievements Gallery */}
      <div className="achievements-section">
        <h3>Achievements Earned</h3>
        {achievements.length > 0 ? (
          <div className="achievements-grid">
            {achievements.map((achievement, index) => (
              <div key={index} className="achievement-card earned">
                <div className="achievement-icon">{achievement.icon}</div>
                <div className="achievement-info">
                  <h4>{achievement.title}</h4>
                  <p>{achievement.description}</p>
                  <div className="achievement-date">
                    Earned: {new Date(achievement.earned_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-achievements">
            <p>No achievements earned yet. Keep participating to unlock your first achievement!</p>
          </div>
        )}
      </div>

      {/* Upcoming Achievements */}
      {upcomingAchievements.length > 0 && (
        <div className="upcoming-section">
          <h3>Upcoming Achievements</h3>
          <div className="achievements-grid">
            {upcomingAchievements.map((achievement, index) => (
              <div key={index} className="achievement-card upcoming" data-type={achievement.type}>
                <div className="achievement-icon locked">{achievement.icon}</div>
                <div className="achievement-info">
                  <h4>{achievement.title}</h4>
                  <p>{achievement.description}</p>
                  <div className="achievement-requirement">
                    Requirement: {achievement.requirement}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress Tips */}
      <div className="tips-section">
        <h3>Progress Tips</h3>
        <div className="tips-grid">
          <div className="tip-card">
            <div className="tip-icon">📚</div>
            <div className="tip-content">
              <h4>Consistent Attendance</h4>
              <p>Attend sessions regularly to boost your XP and unlock attendance achievements</p>
            </div>
          </div>
          
          <div className="tip-card">
            <div className="tip-icon">💭</div>
            <div className="tip-content">
              <h4>Give Feedback</h4>
              <p>Provide feedback after sessions to help improve the system and earn bonus XP</p>
            </div>
          </div>
          
          <div className="tip-card">
            <div className="tip-icon">⏰</div>
            <div className="tip-content">
              <h4>Be Punctual</h4>
              <p>Arrive on time to maintain your punctuality score and show dedication</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GamificationProfile;