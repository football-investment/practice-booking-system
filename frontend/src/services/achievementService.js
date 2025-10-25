import apiService from './apiService';

/**
 * Achievement Service
 * Handles all API calls related to achievements and gamification
 */

const achievementService = {
  /**
   * Get all achievements for current user
   */
  getMyAchievements: async () => {
    try {
      // Use the gamification/me endpoint which exists
      const response = await apiService.get('/gamification/me');
      // Return achievements in expected format
      return {
        success: true,
        data: response.achievements || []
      };
    } catch (error) {
      console.error('Error fetching achievements:', error);
      // Return empty array instead of throwing to prevent UI errors
      return {
        success: true,
        data: []
      };
    }
  },

  /**
   * Get achievements for a specific specialization
   * @param {string} specializationId - PLAYER, COACH, or INTERNSHIP
   */
  getSpecializationAchievements: async (specializationId) => {
    try {
      // This endpoint doesn't exist yet, return empty for now
      console.warn(`Specialization achievements endpoint not implemented for ${specializationId}`);
      return {
        success: true,
        data: []
      };
    } catch (error) {
      console.error(`Error fetching ${specializationId} achievements:`, error);
      return {
        success: true,
        data: []
      };
    }
  },

  /**
   * Get current user's gamification profile
   */
  getMyProfile: async () => {
    try {
      const response = await apiService.get('/gamification/profile/me');
      return response.data;
    } catch (error) {
      console.error('Error fetching gamification profile:', error);
      throw error;
    }
  },

  /**
   * Get available (not yet earned) achievements for a specialization
   * @param {string} specializationId
   */
  getAvailableAchievements: (specializationId) => {
    // Define all possible achievements per specialization
    const allAchievements = {
      PLAYER: [
        {
          id: 'first_level_up',
          title: '⚽ First Belt Promotion',
          description: 'Reach level 2 as GanCuju Player',
          icon: '⚽',
          requirement: 'Level 2+',
          type: 'level'
        },
        {
          id: 'skill_milestone',
          title: '🥋 Yellow Belt Warrior',
          description: 'Achieve Rugalmas Nád level',
          icon: '🥋',
          requirement: 'Level 3',
          type: 'level'
        },
        {
          id: 'advanced_skill',
          title: '🏆 Technical Excellence',
          description: 'Reach Erős Gyökér level',
          icon: '🏆',
          requirement: 'Level 5',
          type: 'level'
        },
        {
          id: 'master_level',
          title: '🐉 Sárkány Bölcsesség Master',
          description: 'Achieve the highest GanCuju Player level',
          icon: '🐉',
          requirement: 'Level 8',
          type: 'level'
        },
        {
          id: 'player_dedication',
          title: '⚡ Player Development',
          description: 'Complete 5+ player sessions',
          icon: '⚡',
          requirement: '5 sessions',
          type: 'activity'
        }
      ],
      COACH: [
        {
          id: 'first_level_up',
          title: '🎓 Coaching Journey Begins',
          description: 'Reach level 2 as Football Coach',
          icon: '🎓',
          requirement: 'Level 2+',
          type: 'level'
        },
        {
          id: 'skill_milestone',
          title: '📋 Licensed Assistant',
          description: 'Achieve Assistant Coach level',
          icon: '📋',
          requirement: 'Level 3',
          type: 'level'
        },
        {
          id: 'advanced_skill',
          title: '🏅 Professional Coach',
          description: 'Reach Professional level',
          icon: '🏅',
          requirement: 'Level 5',
          type: 'level'
        },
        {
          id: 'master_level',
          title: '👔 PRO Vezetőedző',
          description: 'Achieve the highest coaching level',
          icon: '👔',
          requirement: 'Level 8',
          type: 'level'
        },
        {
          id: 'coach_dedication',
          title: '♟️ Coach Development',
          description: 'Complete 5+ coaching sessions',
          icon: '♟️',
          requirement: '5 sessions',
          type: 'activity'
        }
      ],
      INTERNSHIP: [
        {
          id: 'first_level_up',
          title: '🚀 Career Launch',
          description: 'Reach level 2 as Intern',
          icon: '🚀',
          requirement: 'Level 2+',
          type: 'level'
        },
        {
          id: 'master_level',
          title: '💡 Startup Leader',
          description: 'Achieve Startup Leader level',
          icon: '💡',
          requirement: 'Level 3',
          type: 'level'
        },
        {
          id: 'internship_dedication',
          title: '💼 Professional Growth',
          description: 'Complete 3+ internship sessions',
          icon: '💼',
          requirement: '3 sessions',
          type: 'activity'
        },
        {
          id: 'project_complete',
          title: '🌟 Real World Experience',
          description: 'Complete your first internship project',
          icon: '🌟',
          requirement: '1 project',
          type: 'activity'
        }
      ]
    };

    return allAchievements[specializationId] || [];
  },

  /**
   * Filter unlocked vs locked achievements
   * @param {Array} earnedAchievements - User's earned achievements
   * @param {string} specializationId
   */
  categorizeAchievements: (earnedAchievements, specializationId) => {
    const allPossible = achievementService.getAvailableAchievements(specializationId);

    // ✨ FIX: Filter out level-type items (they belong in ProgressCard, not Achievement list)
    // Only show activity-based achievements (sessions, projects, etc.)
    const actualAchievements = allPossible.filter(a => a.type === 'activity');

    const earnedIds = new Set(
      earnedAchievements
        .filter(a => a.specialization_id === specializationId)
        .map(a => a.badge_type)
    );

    const unlocked = actualAchievements.filter(a => earnedIds.has(a.id));
    const locked = actualAchievements.filter(a => !earnedIds.has(a.id));

    return { unlocked, locked };
  },

  /**
   * Calculate achievement completion percentage
   * @param {Array} earnedAchievements
   * @param {string} specializationId
   */
  getCompletionPercentage: (earnedAchievements, specializationId) => {
    const allPossible = achievementService.getAvailableAchievements(specializationId);

    // ✨ FIX: Only count activity-based achievements (not level milestones)
    const actualAchievements = allPossible.filter(a => a.type === 'activity');

    const earnedCount = earnedAchievements.filter(
      a => a.specialization_id === specializationId
    ).length;

    if (actualAchievements.length === 0) return 0;
    return Math.round((earnedCount / actualAchievements.length) * 100);
  },

  /**
   * Get achievement badge color based on type
   */
  getBadgeColor: (badgeType) => {
    const colors = {
      first_level_up: '#4CAF50',
      skill_milestone: '#2196F3',
      advanced_skill: '#FF9800',
      master_level: '#F44336',
      player_dedication: '#9C27B0',
      coach_dedication: '#9C27B0',
      internship_dedication: '#9C27B0',
      project_complete: '#FFD700'
    };
    return colors[badgeType] || '#9E9E9E';
  },

  /**
   * Format achievement earned date
   */
  formatEarnedDate: (earnedAt) => {
    if (!earnedAt) return 'Not earned yet';
    const date = new Date(earnedAt);
    return date.toLocaleDateString('hu-HU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }
};

export default achievementService;
