import api from './apiService';

class ProgressionService {
  // Get user's current progression status
  async getUserProgress() {
    try {
      const response = await api.get('/api/v1/progression/progress');
      // apiService already returns parsed JSON, not axios-style response.data
      return response;
    } catch (error) {
      console.error('Error fetching user progress:', error);
      throw error;
    }
  }

  // Update user's progression
  async updateProgress(track, level, specializations = null) {
    try {
      const response = await api.post('/api/v1/progression/progress/update', {
        track,
        level,
        specializations
      });
      return response;
    } catch (error) {
      console.error('Error updating progress:', error);
      throw error;
    }
  }

  // Get progression system definitions
  async getProgressionSystems() {
    try {
      const response = await api.get('/api/v1/progression/systems');
      // apiService already returns parsed JSON, not axios-style response.data
      return response;
    } catch (error) {
      console.error('Error fetching progression systems:', error);
      throw error;
    }
  }

  // Validate if user can access a level
  validatePrerequisite(track, level, currentProgress, systems) {
    const system = systems[track];
    if (!system) return false;

    const prerequisites = system.prerequisites || {};
    const requiredLevel = prerequisites[level];
    
    if (!requiredLevel) return true; // No prerequisite needed

    if (track === 'internship') {
      const currentLevel = currentProgress.internship_level;
      const levels = system.levels;
      const currentIndex = levels.indexOf(currentLevel);
      const requiredIndex = levels.indexOf(requiredLevel);
      return currentIndex >= requiredIndex;
    } 
    else if (track === 'coach') {
      if (system.specializations && system.specializations.includes(level)) {
        // Specialization requires pre_lead
        const currentLevel = currentProgress.coach_foundation_level;
        if (!currentLevel) return false;
        const foundationLevels = system.foundation_levels;
        const currentIndex = foundationLevels.indexOf(currentLevel);
        const requiredIndex = foundationLevels.indexOf(system.specialization_prerequisite);
        return currentIndex >= requiredIndex;
      } else {
        // Foundation level
        const currentLevel = currentProgress.coach_foundation_level;
        const levels = system.foundation_levels;
        const currentIndex = levels.indexOf(currentLevel);
        const requiredIndex = levels.indexOf(requiredLevel);
        return currentIndex >= requiredIndex;
      }
    } 
    else if (track === 'gancuju') {
      const currentLevel = currentProgress.gancuju_level;
      const levels = system.levels;
      const currentIndex = levels.indexOf(currentLevel);
      const requiredIndex = levels.indexOf(requiredLevel);
      return currentIndex >= requiredIndex;
    }

    return false;
  }

  // Calculate progress percentage for a track
  calculateTrackProgress(track, currentProgress, systems) {
    const system = systems[track];
    if (!system) return 0;

    if (track === 'internship') {
      const currentLevel = currentProgress.internship_level;
      const levels = system.levels;
      const currentIndex = levels.indexOf(currentLevel);
      return ((currentIndex + 1) / levels.length) * 100;
    } 
    else if (track === 'coach') {
      const currentLevel = currentProgress.coach_foundation_level;
      const levels = system.foundation_levels;
      const currentIndex = levels.indexOf(currentLevel);
      const foundationProgress = ((currentIndex + 1) / levels.length) * 80; // 80% for foundation
      
      // Add specialization bonus (20% total, divided by 3 specializations)
      const specializationBonus = (currentProgress.coach_specializations?.length || 0) * (20 / 3);
      
      return Math.min(foundationProgress + specializationBonus, 100);
    } 
    else if (track === 'gancuju') {
      const currentLevel = currentProgress.gancuju_level;
      const levels = system.levels;
      const currentIndex = levels.indexOf(currentLevel);
      return ((currentIndex + 1) / levels.length) * 100;
    }

    return 0;
  }

  // Get next available levels for a track
  getNextLevels(track, currentProgress, systems) {
    const system = systems[track];
    if (!system) return [];

    const nextLevels = [];

    if (track === 'internship') {
      const currentLevel = currentProgress.internship_level;
      const levels = system.levels;
      const currentIndex = levels.indexOf(currentLevel);
      if (currentIndex < levels.length - 1) {
        nextLevels.push(levels[currentIndex + 1]);
      }
    } 
    else if (track === 'coach') {
      const currentLevel = currentProgress.coach_foundation_level;
      const levels = system.foundation_levels;
      const currentIndex = levels.indexOf(currentLevel);
      
      // Next foundation level
      if (currentIndex < levels.length - 1) {
        nextLevels.push(levels[currentIndex + 1]);
      }
      
      // Available specializations (if pre_lead is completed)
      if (currentIndex >= 1) { // pre_lead is index 1
        const currentSpecs = currentProgress.coach_specializations || [];
        system.specializations.forEach(spec => {
          if (!currentSpecs.includes(spec)) {
            nextLevels.push(spec);
          }
        });
      }
    } 
    else if (track === 'gancuju') {
      const currentLevel = currentProgress.gancuju_level;
      const levels = system.levels;
      const currentIndex = levels.indexOf(currentLevel);
      if (currentIndex < levels.length - 1) {
        nextLevels.push(levels[currentIndex + 1]);
      }
    }

    return nextLevels;
  }
}

const progressionService = new ProgressionService();
export default progressionService;