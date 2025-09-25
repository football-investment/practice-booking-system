/**
 * 🎯 LFA ACADEMY - USER TYPE & BUSINESS LOGIC SERVICE
 * Handles complex student categorization and journey mapping
 */

// User type constants
export const USER_TYPES = {
  JUNIOR: 'junior',     // 8-14 years
  SENIOR: 'senior',     // 15-18 years  
  ADULT: 'adult'        // 18+ years
};

// Skill categories for multi-track progression
export const SKILL_CATEGORIES = {
  TECHNICAL: 'technical',   // Ball control, passing, shooting
  PHYSICAL: 'physical',     // Strength, speed, endurance
  TACTICAL: 'tactical',     // Positioning, teamwork
  MENTAL: 'mental'          // Focus, stress management
};

// XP progression levels
export const PROGRESSION_LEVELS = {
  BEGINNER: { min: 0, max: 500, label: 'Beginner' },
  INTERMEDIATE: { min: 500, max: 1500, label: 'Intermediate' },
  ADVANCED: { min: 1500, max: 3500, label: 'Advanced' },
  ELITE: { min: 3500, max: 6000, label: 'Elite' },
  PRO: { min: 6000, max: 10000, label: 'Professional' }
};

// Achievement types
export const ACHIEVEMENT_TYPES = {
  SKILL_BADGE: 'skill_badge',
  TOURNAMENT_MEDAL: 'tournament_medal', 
  LEADERSHIP_RANK: 'leadership_rank',
  STREAK_AWARD: 'streak_award'
};

/**
 * Determine user type based on user data
 * @param {Object} user - User object from AuthContext
 * @returns {string} - User type (junior/senior/adult)
 */
export const determineUserType = (user) => {
  if (!user) return USER_TYPES.ADULT;
  
  // Check if age is explicitly set
  if (user.age) {
    if (user.age >= 8 && user.age <= 14) return USER_TYPES.JUNIOR;
    if (user.age >= 15 && user.age <= 18) return USER_TYPES.SENIOR;
    return USER_TYPES.ADULT;
  }
  
  // Check birth date if available
  if (user.birth_date || user.birthDate) {
    const birthDate = new Date(user.birth_date || user.birthDate);
    const age = Math.floor((Date.now() - birthDate.getTime()) / (1000 * 60 * 60 * 24 * 365.25));
    
    if (age >= 8 && age <= 14) return USER_TYPES.JUNIOR;
    if (age >= 15 && age <= 18) return USER_TYPES.SENIOR;
    return USER_TYPES.ADULT;
  }
  
  // Check role-based hints
  if (user.role === 'student') {
    // Check email domain for school indicators
    if (user.email?.includes('.edu') || user.email?.includes('school')) {
      return USER_TYPES.SENIOR;
    }
    // Check name patterns (Jr., Sr., etc.)
    if (user.name?.includes('Jr') || user.name?.includes('Junior')) {
      return USER_TYPES.JUNIOR;
    }
  }
  
  // Default to adult for safety
  return USER_TYPES.ADULT;
};

/**
 * Get user type specific configuration
 * @param {string} userType - junior/senior/adult
 * @returns {Object} - Configuration object
 */
export const getUserTypeConfig = (userType) => {
  const configs = {
    [USER_TYPES.JUNIOR]: {
      theme: 'playful',
      primaryColor: '#10B981', // Green - fun and energetic
      welcomeMessage: 'Ready to become a football superstar? 🌟',
      focusAreas: ['Fun Drills', 'Basic Skills', 'Team Play', 'Confidence'],
      sessionFrequency: '2-3 times per week',
      parentalInvolvement: true,
      gamificationLevel: 'high',
      achievementStyle: 'badges',
      dashboardLayout: 'colorful',
      maxSessionDuration: 60, // minutes
      skillTracking: 'simplified'
    },
    
    [USER_TYPES.SENIOR]: {
      theme: 'professional',
      primaryColor: '#3B82F6', // Blue - focused and serious
      welcomeMessage: 'Time to take your game to the next level! ⚽',
      focusAreas: ['Advanced Tactics', 'Physical Training', 'Competition Prep', 'Leadership'],
      sessionFrequency: 'Daily training',
      parentalInvolvement: false,
      gamificationLevel: 'medium',
      achievementStyle: 'performance',
      dashboardLayout: 'data-rich',
      maxSessionDuration: 120, // minutes
      skillTracking: 'detailed'
    },
    
    [USER_TYPES.ADULT]: {
      theme: 'flexible',
      primaryColor: '#F59E0B', // Orange - warm and accessible
      welcomeMessage: 'Great to see you continuing your football journey! 👍',
      focusAreas: ['Fitness', 'Social Play', 'Stress Relief', 'Skill Maintenance'],
      sessionFrequency: 'Flexible schedule',
      parentalInvolvement: false,
      gamificationLevel: 'low',
      achievementStyle: 'milestones',
      dashboardLayout: 'minimal',
      maxSessionDuration: 90, // minutes
      skillTracking: 'goal-oriented'
    }
  };
  
  return configs[userType] || configs[USER_TYPES.ADULT];
};

/**
 * Calculate skill progression level
 * @param {number} xp - Experience points in skill category
 * @returns {Object} - Level info with progress percentage
 */
export const calculateSkillLevel = (xp = 0) => {
  for (const [levelName, levelInfo] of Object.entries(PROGRESSION_LEVELS)) {
    if (xp >= levelInfo.min && xp < levelInfo.max) {
      const progress = ((xp - levelInfo.min) / (levelInfo.max - levelInfo.min)) * 100;
      return {
        level: levelName.toLowerCase(),
        label: levelInfo.label,
        progress: Math.round(progress),
        currentXP: xp,
        minXP: levelInfo.min,
        maxXP: levelInfo.max,
        nextLevelXP: levelInfo.max - xp
      };
    }
  }
  
  // Max level reached
  return {
    level: 'pro',
    label: 'Professional',
    progress: 100,
    currentXP: xp,
    minXP: 6000,
    maxXP: 10000,
    nextLevelXP: 0
  };
};

/**
 * Generate skill categories with mock data based on user type
 * @param {string} userType - User type
 * @param {Object} userData - Optional real user data
 * @returns {Array} - Array of skill objects
 */
export const generateSkillCategories = (userType, userData = {}) => {
  const baseSkills = [
    {
      id: SKILL_CATEGORIES.TECHNICAL,
      name: 'Technical Skills',
      icon: '⚽',
      description: 'Ball control, passing, shooting accuracy'
    },
    {
      id: SKILL_CATEGORIES.PHYSICAL,
      name: 'Physical Fitness', 
      icon: '💪',
      description: 'Strength, speed, endurance, agility'
    },
    {
      id: SKILL_CATEGORIES.TACTICAL,
      name: 'Tactical Awareness',
      icon: '🧠',
      description: 'Positioning, teamwork, game reading'
    },
    {
      id: SKILL_CATEGORIES.MENTAL,
      name: 'Mental Game',
      icon: '🎯',
      description: 'Focus, confidence, stress management'
    }
  ];
  
  // Mock XP values based on user type
  const mockXPRanges = {
    [USER_TYPES.JUNIOR]: [200, 800],   // Beginner to Intermediate
    [USER_TYPES.SENIOR]: [800, 2500],  // Intermediate to Advanced
    [USER_TYPES.ADULT]: [300, 1800]    // Beginner to Advanced
  };
  
  const [minXP, maxXP] = mockXPRanges[userType];
  
  return baseSkills.map(skill => {
    // Use real data if available, otherwise generate mock data
    const realXP = userData.skills?.[skill.id]?.xp;
    const mockXP = realXP || Math.floor(Math.random() * (maxXP - minXP)) + minXP;
    
    return {
      ...skill,
      xp: mockXP,
      level: calculateSkillLevel(mockXP)
    };
  });
};

/**
 * Generate daily challenges based on user type and current skills
 * @param {string} userType - User type
 * @param {Array} skills - User's current skills
 * @returns {Array} - Array of daily challenges
 */
export const generateDailyChallenges = (userType, skills = []) => {
  const challengeTemplates = {
    [USER_TYPES.JUNIOR]: [
      { id: 1, title: 'Rainbow Flicks', description: 'Practice 20 rainbow flicks', xp: 25, category: 'technical', icon: '🌈' },
      { id: 2, title: 'Sprint & Smile', description: '10 short sprints with big smiles!', xp: 20, category: 'physical', icon: '😄' },
      { id: 3, title: 'Pass to Friends', description: 'Complete 30 passes with teammates', xp: 30, category: 'tactical', icon: '👫' },
      { id: 4, title: 'Positive Thinking', description: 'Say 5 positive things about your game', xp: 15, category: 'mental', icon: '💭' }
    ],
    
    [USER_TYPES.SENIOR]: [
      { id: 5, title: 'Precision Shooting', description: 'Score 8/10 shots on target corners', xp: 50, category: 'technical', icon: '🎯' },
      { id: 6, title: 'Endurance Run', description: 'Complete 5km run under 22 minutes', xp: 60, category: 'physical', icon: '🏃' },
      { id: 7, title: 'Tactical Analysis', description: 'Study 3 professional plays and explain', xp: 45, category: 'tactical', icon: '📊' },
      { id: 8, title: 'Pressure Training', description: '20 decisions under 3-second pressure', xp: 40, category: 'mental', icon: '⏱️' }
    ],
    
    [USER_TYPES.ADULT]: [
      { id: 9, title: 'Skill Refresh', description: 'Practice basic juggling for 10 minutes', xp: 35, category: 'technical', icon: '⚽' },
      { id: 10, title: 'Fitness Goals', description: 'Complete your weekly fitness target', xp: 40, category: 'physical', icon: '🏋️' },
      { id: 11, title: 'Team Strategy', description: 'Discuss tactics with your team', xp: 30, category: 'tactical', icon: '👥' },
      { id: 12, title: 'Mindful Play', description: '15 minutes of focused, enjoyable play', xp: 25, category: 'mental', icon: '🧘' }
    ]
  };
  
  const userChallenges = challengeTemplates[userType] || challengeTemplates[USER_TYPES.ADULT];
  
  // Select 2-3 challenges randomly, with focus on weaker skills
  const weakestSkills = skills
    .sort((a, b) => a.xp - b.xp)
    .slice(0, 2)
    .map(skill => skill.id);
  
  const selectedChallenges = userChallenges
    .filter(challenge => {
      // Higher chance for challenges in weaker skill areas
      if (weakestSkills.includes(challenge.category)) {
        return Math.random() > 0.3; // 70% chance
      }
      return Math.random() > 0.7; // 30% chance
    })
    .slice(0, 3);
  
  return selectedChallenges.length > 0 ? selectedChallenges : userChallenges.slice(0, 2);
};

/**
 * Get semester information
 * @param {Date} currentDate - Current date
 * @returns {Object} - Current and upcoming semester info
 */
export const getSemesterInfo = (currentDate = new Date()) => {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1; // 1-based month
  
  let currentSemester, nextSemester;
  
  if (month >= 9 && month <= 12) {
    // Fall semester
    currentSemester = {
      id: `fall-${year}`,
      name: `Fall ${year}`,
      type: 'fall',
      startDate: new Date(year, 8, 1), // September 1
      endDate: new Date(year, 11, 31), // December 31
      focusAreas: ['Technical Skills', 'Physical Conditioning', 'Team Strategy', 'Mental Preparation']
    };
    nextSemester = {
      id: `spring-${year + 1}`,
      name: `Spring ${year + 1}`,
      type: 'spring',
      startDate: new Date(year + 1, 0, 1), // January 1
      endDate: new Date(year + 1, 4, 31), // May 31
      focusAreas: ['Advanced Tactics', 'Match Preparation', 'Leadership Skills', 'Tournament Ready']
    };
  } else if (month >= 1 && month <= 5) {
    // Spring semester
    currentSemester = {
      id: `spring-${year}`,
      name: `Spring ${year}`,
      type: 'spring',
      startDate: new Date(year, 0, 1),
      endDate: new Date(year, 4, 31),
      focusAreas: ['Advanced Tactics', 'Match Preparation', 'Leadership Skills', 'Tournament Ready']
    };
    nextSemester = {
      id: `summer-${year}`,
      name: `Summer ${year}`,
      type: 'summer',
      startDate: new Date(year, 5, 1), // June 1
      endDate: new Date(year, 7, 31), // August 31
      focusAreas: ['Intensive Training', 'International Exchange', 'Camp Programs', 'Tournament Play']
    };
  } else {
    // Summer intensive
    currentSemester = {
      id: `summer-${year}`,
      name: `Summer ${year}`,
      type: 'summer',
      startDate: new Date(year, 5, 1),
      endDate: new Date(year, 7, 31),
      focusAreas: ['Intensive Training', 'International Exchange', 'Camp Programs', 'Tournament Play']
    };
    nextSemester = {
      id: `fall-${year}`,
      name: `Fall ${year}`,
      type: 'fall',
      startDate: new Date(year, 8, 1),
      endDate: new Date(year, 11, 31),
      focusAreas: ['Technical Skills', 'Physical Conditioning', 'Team Strategy', 'Mental Preparation']
    };
  }
  
  return { currentSemester, nextSemester };
};

/**
 * Generate user achievements based on user type and skill progress
 */
const getUserAchievements = (userType, skillCategories = []) => {
  const baseAchievements = {
    junior: [
      {
        id: 'first-goal',
        name: 'First Goal!',
        description: 'Score your first goal in training',
        icon: '⚽',
        tier: 'bronze',
        category: 'skill',
        unlocked: true,
        unlockedDate: 'Sep 15',
        progress: null
      },
      {
        id: 'team-player',
        name: 'Team Player',
        description: 'Make 5 assists in one session',
        icon: '🤝',
        tier: 'silver',
        category: 'skill',
        unlocked: true,
        unlockedDate: 'Sep 20',
        progress: null
      },
      {
        id: 'perfect-attendance',
        name: 'Perfect Attendance',
        description: 'Attend 10 sessions in a row',
        icon: '🏆',
        tier: 'gold',
        category: 'progress',
        unlocked: false,
        progress: { current: 7, required: 10 }
      },
      {
        id: 'skill-master',
        name: 'Skill Master',
        description: 'Master 3 different skills',
        icon: '🎯',
        tier: 'gold',
        category: 'skill',
        unlocked: false,
        progress: { 
          current: skillCategories.filter(s => s.level.progress > 80).length, 
          required: 3 
        }
      },
      {
        id: 'improvement-streak',
        name: 'Getting Better!',
        description: 'Improve skills for 5 weeks straight',
        icon: '📈',
        tier: 'silver',
        category: 'progress',
        unlocked: true,
        unlockedDate: 'Sep 18'
      }
    ],
    senior: [
      {
        id: 'tactical-genius',
        name: 'Tactical Genius',
        description: 'Master advanced tactical concepts',
        icon: '🧠',
        tier: 'gold',
        category: 'skill',
        unlocked: true,
        unlockedDate: 'Sep 12',
        progress: null
      },
      {
        id: 'leadership',
        name: 'Team Captain',
        description: 'Lead the team in 3 training sessions',
        icon: '👑',
        tier: 'gold',
        category: 'progress',
        unlocked: true,
        unlockedDate: 'Sep 22',
        progress: null
      },
      {
        id: 'fitness-peak',
        name: 'Peak Fitness',
        description: 'Achieve top fitness level',
        icon: '💪',
        tier: 'silver',
        category: 'skill',
        unlocked: false,
        progress: { current: 85, required: 95 }
      },
      {
        id: 'mentor',
        name: 'Junior Mentor',
        description: 'Help 5 junior players improve',
        icon: '🎓',
        tier: 'gold',
        category: 'progress',
        unlocked: false,
        progress: { current: 2, required: 5 }
      },
      {
        id: 'college-ready',
        name: 'College Ready',
        description: 'Complete college preparation program',
        icon: '🏛️',
        tier: 'gold',
        category: 'progress',
        unlocked: false,
        progress: { current: 78, required: 100 }
      }
    ],
    adult: [
      {
        id: 'consistency',
        name: 'Consistency Champion',
        description: 'Maintain regular training schedule',
        icon: '📅',
        tier: 'bronze',
        category: 'progress',
        unlocked: true,
        unlockedDate: 'Sep 10',
        progress: null
      },
      {
        id: 'fitness-goal',
        name: 'Fitness Goal Achieved',
        description: 'Reach your personal fitness target',
        icon: '🎯',
        tier: 'silver',
        category: 'skill',
        unlocked: true,
        unlockedDate: 'Sep 25',
        progress: null
      },
      {
        id: 'team-spirit',
        name: 'Team Spirit',
        description: 'Participate in 3 team events',
        icon: '🤝',
        tier: 'bronze',
        category: 'progress',
        unlocked: false,
        progress: { current: 2, required: 3 }
      },
      {
        id: 'weekend-warrior',
        name: 'Weekend Warrior',
        description: 'Complete all weekend training sessions',
        icon: '⚡',
        tier: 'silver',
        category: 'progress',
        unlocked: false,
        progress: { current: 6, required: 8 }
      },
      {
        id: 'stress-relief',
        name: 'Stress Relief Master',
        description: 'Use football for mental wellness',
        icon: '🧘',
        tier: 'gold',
        category: 'skill',
        unlocked: true,
        unlockedDate: 'Sep 5',
        progress: null
      }
    ]
  };

  return baseAchievements[userType] || baseAchievements.adult;
};

// Export utility function for easy access
export const LFAUserService = {
  determineUserType,
  getUserTypeConfig,
  calculateSkillLevel,
  generateSkillCategories,
  generateDailyChallenges,
  getUserAchievements,
  getSemesterInfo
};