import apiService from './apiService';

/**
 * Specialization Service
 * Handles all API calls related to specializations and student progress
 */

const specializationService = {
  /**
   * Get all available specializations
   */
  getAllSpecializations: async () => {
    try {
      const response = await apiService.get('/specializations/all');
      return response.data;
    } catch (error) {
      console.error('Error fetching specializations:', error);
      throw error;
    }
  },

  /**
   * Get level requirements for a specific specialization
   * @param {string} specializationId - PLAYER, COACH, or INTERNSHIP
   */
  getLevelRequirements: async (specializationId) => {
    try {
      const response = await apiService.get(`/specializations/levels/${specializationId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching levels for ${specializationId}:`, error);
      throw error;
    }
  },

  /**
   * Get current student's progress in a specialization
   * @param {string} specializationId - PLAYER, COACH, or INTERNSHIP
   */
  getMyProgress: async (specializationId) => {
    try {
      const response = await apiService.get(`/specializations/progress/${specializationId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching progress for ${specializationId}:`, error);
      throw error;
    }
  },

  /**
   * Get specific student's progress (admin/instructor only)
   * @param {number} studentId
   * @param {string} specializationId
   */
  getStudentProgress: async (studentId, specializationId) => {
    try {
      const response = await apiService.get(`/specializations/progress/${specializationId}/${studentId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching student ${studentId} progress:`, error);
      throw error;
    }
  },

  /**
   * Update student progress (called after completing activities)
   * @param {string} specializationId
   * @param {Object} progressData - { xp_gained, sessions_completed, projects_completed }
   */
  updateProgress: async (specializationId, progressData) => {
    try {
      const response = await apiService.post(
        `/specializations/progress/${specializationId}/update`,
        progressData
      );
      return response.data;
    } catch (error) {
      console.error('Error updating progress:', error);
      throw error;
    }
  },

  /**
   * Get level-up requirements for next level
   * @param {string} specializationId
   * @param {number} currentLevel
   */
  getNextLevelRequirements: async (specializationId, currentLevel) => {
    try {
      const response = await apiService.get(
        `/specializations/levels/${specializationId}/${currentLevel + 1}`
      );
      return response.data;
    } catch (error) {
      console.error('Error fetching next level requirements:', error);
      throw error;
    }
  },

  /**
   * Helper: Calculate progress percentage
   */
  calculateProgressPercentage: (currentXP, requiredXP) => {
    if (!requiredXP || requiredXP === 0) return 100;
    return Math.min(100, Math.round((currentXP / requiredXP) * 100));
  },

  /**
   * Helper: Get specialization color theme
   */
  getSpecializationTheme: (specializationId) => {
    const themes = {
      PLAYER: {
        primary: '#FF6B35',
        secondary: '#FFA726',
        gradient: 'linear-gradient(135deg, #FF6B35 0%, #FFA726 100%)',
        icon: '⚽',
        name: 'GanCuju Player'
      },
      COACH: {
        primary: '#1976D2',
        secondary: '#42A5F5',
        gradient: 'linear-gradient(135deg, #1976D2 0%, #42A5F5 100%)',
        icon: '⚽',
        name: 'Football Coach'
      },
      INTERNSHIP: {
        primary: '#7B1FA2',
        secondary: '#AB47BC',
        gradient: 'linear-gradient(135deg, #7B1FA2 0%, #AB47BC 100%)',
        icon: '💼',
        name: 'Startup Spirit Intern'
      }
    };
    return themes[specializationId] || themes.PLAYER;
  },

  /**
   * Helper: Get level color (for belt/badge display)
   */
  getLevelColor: (specializationId, levelNumber) => {
    // PLAYER belt colors
    if (specializationId === 'PLAYER') {
      const colors = {
        1: '#FFFFFF', // White - Bambusz Tanítvány
        2: '#FDD835', // Yellow - Hajnali Harmat
        3: '#4CAF50', // Green - Rugalmas Nád
        4: '#2196F3', // Blue - Égi Folyó
        5: '#795548', // Brown - Erős Gyökér
        6: '#616161', // Dark Grey - Téli Hold
        7: '#212121', // Black - Éjfél Őrzője
        8: '#D32F2F'  // Red - Sárkány Bölcsesség
      };
      return colors[levelNumber] || '#9E9E9E';
    }

    // COACH/INTERNSHIP generic progression colors
    const progressColors = [
      '#9E9E9E', // Grey
      '#2196F3', // Blue
      '#4CAF50', // Green
      '#FF9800', // Orange
      '#F44336', // Red
      '#9C27B0', // Purple
      '#FFD700', // Gold
      '#FF1744'  // Deep Red
    ];
    return progressColors[levelNumber - 1] || '#9E9E9E';
  }
};

export default specializationService;
