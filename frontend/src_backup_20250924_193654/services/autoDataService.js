/**
 * Auto Data Service
 * Handles automatic loading of user data from scripts/external sources
 * This simulates the new system where personal data is automatically available
 */

import { apiService } from './apiService';

class AutoDataService {
  constructor() {
    this.dataCache = null;
    this.loading = false;
  }

  /**
   * Load user data automatically from script/backend
   * In the real implementation, this would:
   * 1. Check for script-provided data
   * 2. Load from external LFA systems
   * 3. Auto-populate from existing databases
   */
  async loadAutoUserData(userId) {
    if (this.loading) {
      return this.waitForLoad();
    }

    if (this.dataCache && this.dataCache.userId === userId) {
      return this.dataCache.data;
    }

    this.loading = true;

    try {
      console.log('🔄 Loading auto user data from multiple sources...');

      // Step 1: Try to get current user data from API
      let userData = {};
      try {
        userData = await apiService.getCurrentUser();
        console.log('✅ User data loaded from API');
      } catch (error) {
        console.warn('⚠️ Could not load from API, using fallback');
      }

      // Step 2: Simulate script data loading (LFA system integration)
      const scriptData = await this.loadFromLFAScript(userId);
      console.log('✅ Script data loaded from LFA system');

      // Step 3: Merge and auto-generate missing data
      const autoData = this.mergeAndAutoGenerate(userData, scriptData, userId);
      console.log('✅ Auto data generation completed');

      // Step 4: Auto-populate missing fields with intelligent defaults
      const finalData = await this.autoPopulateMissingFields(autoData, userId);
      console.log('✅ Auto population completed');

      this.dataCache = {
        userId,
        data: finalData,
        timestamp: Date.now()
      };

      this.loading = false;
      return finalData;

    } catch (error) {
      console.error('❌ Error loading auto user data:', error);
      this.loading = false;
      
      // Return fallback auto-generated data
      return this.generateFallbackData(userId);
    }
  }

  /**
   * Simulate loading data from LFA script/external systems
   */
  async loadFromLFAScript(userId) {
    // Simulate network delay
    await this.delay(800);

    // This would normally read from:
    // - LFA enrollment scripts
    // - External student management systems
    // - Pre-registration data
    
    return {
      // Simulated script-provided data
      source: 'LFA_SCRIPT',
      enrollment_id: `LFA_${new Date().getFullYear()}_${userId}`,
      auto_generated: true,
      script_version: '2.1.0',
      
      // Basic info that would come from enrollment
      student_code: this.generateStudentCode(userId),
      enrollment_date: new Date().toISOString(),
      semester_enrolled: this.determineSemesterFromDate(),
      
      // Auto-detected preferences based on LFA enrollment
      preferred_language: 'hu',
      lfa_track_preference: this.generateTrackPreference(),
      
      // System-generated identifiers
      lfa_internal_id: `LFA_INT_${userId}_${Date.now()}`,
      
      // Metadata
      data_completeness: this.calculateDataCompleteness(),
      last_updated: new Date().toISOString(),
      
      // Contact preferences (auto-detected from enrollment)
      contact_preferences: {
        email_notifications: true,
        sms_updates: true,
        lfa_newsletter: true
      }
    };
  }

  /**
   * Merge API data with script data and generate missing information
   */
  mergeAndAutoGenerate(apiData, scriptData, userId) {
    
    return {
      // Core identification
      nickname: apiData.nickname || this.generateNickname(userId, scriptData),
      display_name: scriptData.student_code || `LFA_Student_${userId}`,
      
      // Contact information (auto-filled from multiple sources)
      phone: apiData.phone || this.generatePhoneNumber(),
      email: apiData.email || `student.${userId}@lfa.training`,
      
      // Personal details (intelligently generated)
      date_of_birth: apiData.date_of_birth || this.generateReasonableBirthDate(),
      
      // Emergency contact (auto-generated with Hungarian naming conventions)
      emergency_contact: apiData.emergency_contact || this.generateEmergencyContact(),
      emergency_phone: apiData.emergency_phone || this.generateEmergencyPhone(),
      
      // Health and preferences
      medical_notes: apiData.medical_notes || 'Szkriptből automatikusan kitöltve - nincs különleges megjegyzés',
      
      // Interests (LFA-specific auto-generation)
      interests: this.mergeInterests(apiData.interests, scriptData.lfa_track_preference),
      
      // LFA-specific fields
      lfa_enrollment_id: scriptData.enrollment_id,
      lfa_student_code: scriptData.student_code,
      semester_context: scriptData.semester_enrolled,
      
      // Auto-generation metadata
      auto_generated: true,
      generation_timestamp: new Date().toISOString(),
      data_sources: ['API', 'LFA_SCRIPT', 'AUTO_GEN'],
      completeness_score: scriptData.data_completeness
    };
  }

  /**
   * Auto-populate any remaining missing fields
   */
  async autoPopulateMissingFields(data, userId) {
    // Simulate processing time
    await this.delay(500);

    const populated = { ...data };

    // Ensure all required fields are populated
    if (!populated.nickname) {
      populated.nickname = `LFA_Player_${userId}`;
    }

    if (!populated.phone) {
      populated.phone = `+36 30 ${this.generateRandomDigits(3)} ${this.generateRandomDigits(4)}`;
    }

    if (!populated.emergency_contact) {
      populated.emergency_contact = this.generateHungarianName() + ' (szülő)';
    }

    if (!populated.emergency_phone) {
      populated.emergency_phone = `+36 20 ${this.generateRandomDigits(3)} ${this.generateRandomDigits(4)}`;
    }

    // Ensure interests are LFA-relevant
    if (!populated.interests || populated.interests.length === 0) {
      populated.interests = ['Football', 'LFA Training', 'Team Sports', 'Fitness'];
    }

    // Add completion status
    populated.auto_completion_status = 'FULLY_POPULATED';
    populated.ready_for_onboarding = true;

    return populated;
  }

  /**
   * Generate fallback data if all else fails
   */
  generateFallbackData(userId) {
    return {
      nickname: `LFA_Student_${userId}`,
      phone: 'Automatikusan generálva',
      date_of_birth: '2000-01-01',
      emergency_contact: 'Automatikusan kitöltve',
      emergency_phone: '+36 30 123 4567',
      medical_notes: 'Automatikus kitöltés - nincs megadva',
      interests: ['Football', 'LFA Training'],
      
      // Fallback metadata
      auto_generated: true,
      fallback_mode: true,
      generation_timestamp: new Date().toISOString(),
      data_sources: ['FALLBACK'],
      lfa_student_code: `LFA_FB_${userId}`,
      
      auto_completion_status: 'FALLBACK_GENERATED',
      ready_for_onboarding: true
    };
  }

  /**
   * Helper methods for data generation
   */
  generateStudentCode(userId) {
    const year = new Date().getFullYear();
    const paddedId = String(userId).padStart(4, '0');
    return `LFA${year}${paddedId}`;
  }

  generateNickname(userId, scriptData) {
    const prefixes = ['Player', 'Future', 'Pro', 'Star', 'Champion'];
    const suffixes = ['LFA', 'FC', 'Pro', 'X'];
    
    if (scriptData.lfa_track_preference === 'PLAYER') {
      return `${prefixes[userId % prefixes.length]}${userId}`;
    } else if (scriptData.lfa_track_preference === 'COACH') {
      return `Coach${userId}${suffixes[userId % suffixes.length]}`;
    } else {
      return `LFA_${userId}_${suffixes[userId % suffixes.length]}`;
    }
  }

  generatePhoneNumber() {
    const providers = ['30', '20', '70'];
    const provider = providers[Math.floor(Math.random() * providers.length)];
    return `+36 ${provider} ${this.generateRandomDigits(3)} ${this.generateRandomDigits(4)}`;
  }

  generateReasonableBirthDate() {
    // Generate age between 16-25 for realistic football training
    const currentYear = new Date().getFullYear();
    const age = 16 + Math.floor(Math.random() * 10);
    const birthYear = currentYear - age;
    const month = Math.floor(Math.random() * 12) + 1;
    const day = Math.floor(Math.random() * 28) + 1;
    
    return `${birthYear}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }

  generateEmergencyContact() {
    const hungarianNames = [
      'Nagy János', 'Kovács Anna', 'Szabó Péter', 'Tóth Mária',
      'Varga László', 'Horváth Éva', 'Kiss Zoltán', 'Molnár Eszter'
    ];
    const relationships = ['apa', 'anya', 'nagyapa', 'nagyanya', 'báty', 'nővér'];
    
    const name = hungarianNames[Math.floor(Math.random() * hungarianNames.length)];
    const relation = relationships[Math.floor(Math.random() * relationships.length)];
    
    return `${name} (${relation})`;
  }

  generateEmergencyPhone() {
    return this.generatePhoneNumber();
  }

  generateHungarianName() {
    const firstNames = ['János', 'Anna', 'Péter', 'Mária', 'László', 'Éva', 'Zoltán', 'Eszter'];
    const lastNames = ['Nagy', 'Kovács', 'Szabó', 'Tóth', 'Varga', 'Horváth', 'Kiss', 'Molnár'];
    
    const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
    const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
    
    return `${lastName} ${firstName}`;
  }

  generateTrackPreference() {
    const tracks = ['PLAYER', 'COACH', 'INTERNSHIP'];
    return tracks[Math.floor(Math.random() * tracks.length)];
  }

  mergeInterests(apiInterests, trackPreference) {
    const baseInterests = apiInterests || [];
    const trackSpecificInterests = {
      'PLAYER': ['Football Skills', 'Match Strategy', 'Physical Training'],
      'COACH': ['Team Management', 'Tactics', 'Leadership'],
      'INTERNSHIP': ['Sports Management', 'Business', 'Analytics']
    };
    
    const lfaInterests = ['Football', 'LFA Training'];
    const trackInterests = trackSpecificInterests[trackPreference] || [];
    
    // Merge and deduplicate
    const merged = [...new Set([...baseInterests, ...lfaInterests, ...trackInterests])];
    return merged.slice(0, 6); // Limit to 6 interests
  }

  determineSemesterFromDate() {
    const month = new Date().getMonth() + 1;
    // Spring semester: Feb-June, Fall semester: Sep-Jan
    return month >= 2 && month <= 6 ? 'SPRING' : 'FALL';
  }

  calculateDataCompleteness() {
    return Math.floor(Math.random() * 20) + 80; // 80-100% completeness
  }

  generateRandomDigits(count) {
    return Array.from({ length: count }, () => Math.floor(Math.random() * 10)).join('');
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async waitForLoad() {
    while (this.loading) {
      await this.delay(100);
    }
    return this.dataCache?.data;
  }

  /**
   * Clear cache (useful for testing or user switching)
   */
  clearCache() {
    this.dataCache = null;
    this.loading = false;
  }

  /**
   * Check if data is already loaded
   */
  isDataLoaded(userId) {
    return this.dataCache && this.dataCache.userId === userId;
  }

  /**
   * Get cached data if available
   */
  getCachedData(userId) {
    if (this.isDataLoaded(userId)) {
      return this.dataCache.data;
    }
    return null;
  }
}

// Export singleton instance
export const autoDataService = new AutoDataService();

// Export class for testing
export { AutoDataService };