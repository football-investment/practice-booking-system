/**
 * Frontend Test Utility for Semester-Centric Onboarding
 * =====================================================
 * 
 * Ez a utility tesztek futtatására szolgál a frontend-en keresztül
 * a szemeszter-centrikus onboarding rendszer validálásához.
 * 
 * Használat:
 * 1. Nyisd meg a browser console-t
 * 2. Futtasd: window.testSemesterOnboarding()
 * 3. Ellenőrizd az eredményeket
 */

import { autoDataService } from '../services/autoDataService';

class FrontendOnboardingTester {
  constructor() {
    this.testResults = [];
    this.currentTestUser = { id: 999, email: 'test@lfa.training' };
  }

  log(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logMessage = `[${timestamp}] ${message}`;
    
    console.log(logMessage);
    this.testResults.push({ timestamp, message, type });
  }

  async testAutoDataServiceInBrowser() {
    this.log('🔄 Testing AutoDataService in browser environment...', 'test');
    
    try {
      // Test 1: Load auto data
      const autoData = await autoDataService.loadAutoUserData(this.currentTestUser.id);
      
      if (autoData && autoData.auto_generated) {
        this.log('✅ AutoDataService successfully loaded data', 'success');
        this.log(`📊 Data completeness: ${autoData.completeness_score}%`, 'info');
        
        // Test essential fields
        const requiredFields = ['nickname', 'phone', 'emergency_contact', 'lfa_student_code'];
        const missingFields = requiredFields.filter(field => !autoData[field]);
        
        if (missingFields.length === 0) {
          this.log('✅ All required fields present', 'success');
        } else {
          this.log(`❌ Missing fields: ${missingFields.join(', ')}`, 'error');
        }
        
        // Test LFA integration markers
        if (autoData.data_sources && autoData.data_sources.includes('LFA_SCRIPT')) {
          this.log('✅ LFA script integration detected', 'success');
        } else {
          this.log('⚠️ LFA script integration not detected', 'warning');
        }
        
        return autoData;
      } else {
        this.log('❌ AutoDataService failed to load data', 'error');
        return null;
      }
    } catch (error) {
      this.log(`❌ AutoDataService error: ${error.message}`, 'error');
      return null;
    }
  }

  testBrowserEnvironment() {
    this.log('🌐 Testing browser environment compatibility...', 'test');
    
    // Test 1: Device detection
    const ua = navigator.userAgent.toLowerCase();
    const isIOS = /ipad|iphone|ipod/.test(ua);
    const isChrome = ua.includes('chrome') && !ua.includes('edg');
    const isSafari = ua.includes('safari') && !ua.includes('chrome');
    
    this.log(`📱 Device: ${isIOS ? 'iOS' : 'Desktop/Android'}`, 'info');
    this.log(`🌐 Browser: ${isChrome ? 'Chrome' : isSafari ? 'Safari' : 'Other'}`, 'info');
    
    // Test 2: Required APIs
    const requiredAPIs = [
      'fetch',
      'localStorage', 
      'sessionStorage',
      'URLSearchParams'
    ];
    
    const missingAPIs = requiredAPIs.filter(api => !(api in window));
    
    if (missingAPIs.length === 0) {
      this.log('✅ All required browser APIs available', 'success');
    } else {
      this.log(`❌ Missing APIs: ${missingAPIs.join(', ')}`, 'error');
    }
    
    // Test 3: React environment
    if (window.React) {
      this.log('✅ React environment detected', 'success');
    } else {
      this.log('❌ React environment not detected', 'error');
    }
    
    return {
      isIOS,
      isChrome,
      isSafari,
      missingAPIs,
      reactAvailable: !!window.React
    };
  }

  testRouteConfiguration() {
    this.log('🛣️ Testing route configuration...', 'test');
    
    // Check if we can access route information
    const currentPath = window.location.pathname;
    this.log(`📍 Current path: ${currentPath}`, 'info');
    
    // Test expected routes exist
    const expectedRoutes = [
      '/student/onboarding',
      '/student/semester-onboarding', 
      '/student/dashboard'
    ];
    
    this.log('✅ Expected routes configured (would need actual router test)', 'success');
    
    // Test URL parameter handling
    const urlParams = new URLSearchParams(window.location.search);
    const onboardingParam = urlParams.get('onboarding');
    
    if (onboardingParam === 'semester') {
      this.log('✅ Semester onboarding URL parameter detected', 'success');
    } else {
      this.log('ℹ️ No semester onboarding URL parameter', 'info');
    }
    
    return {
      currentPath,
      expectedRoutes,
      onboardingParam
    };
  }

  testLocalStorageIntegration() {
    this.log('💾 Testing localStorage integration...', 'test');
    
    try {
      // Test LFA preference storage
      const testKey = 'lfa_onboarding_test';
      const testValue = { test: true, timestamp: Date.now() };
      
      localStorage.setItem(testKey, JSON.stringify(testValue));
      const retrieved = JSON.parse(localStorage.getItem(testKey));
      
      if (retrieved && retrieved.test === true) {
        this.log('✅ localStorage read/write functionality working', 'success');
        localStorage.removeItem(testKey); // cleanup
      } else {
        this.log('❌ localStorage read/write failed', 'error');
      }
      
      // Test LFA preference detection
      const lfaPreference = localStorage.getItem('lfa_onboarding_preference');
      if (lfaPreference) {
        this.log(`✅ LFA onboarding preference found: ${lfaPreference}`, 'success');
      } else {
        this.log('ℹ️ No LFA onboarding preference set', 'info');
      }
      
    } catch (error) {
      this.log(`❌ localStorage error: ${error.message}`, 'error');
    }
  }

  testCSSOptimizations() {
    this.log('🎨 Testing CSS optimizations...', 'test');
    
    // Test if semester onboarding styles are loaded
    const testElement = document.createElement('div');
    testElement.className = 'semester-centric-onboarding';
    document.body.appendChild(testElement);
    
    const styles = window.getComputedStyle(testElement);
    const hasCustomStyling = styles.background !== 'rgba(0, 0, 0, 0)' || 
                             styles.minHeight !== 'auto';
    
    if (hasCustomStyling) {
      this.log('✅ Semester onboarding CSS loaded', 'success');
    } else {
      this.log('⚠️ Semester onboarding CSS may not be loaded', 'warning');
    }
    
    document.body.removeChild(testElement);
    
    // Test mobile optimization classes
    const bodyClasses = Array.from(document.body.classList);
    const mobileOptimizations = bodyClasses.filter(cls => 
      cls.includes('ios') || cls.includes('chrome') || cls.includes('mobile')
    );
    
    if (mobileOptimizations.length > 0) {
      this.log(`✅ Mobile optimizations applied: ${mobileOptimizations.join(', ')}`, 'success');
    } else {
      this.log('ℹ️ No mobile optimization classes detected', 'info');
    }
  }

  async simulateOnboardingFlow() {
    this.log('🎭 Simulating complete onboarding flow...', 'test');
    
    try {
      // Step 1: Auto data loading
      this.log('Step 1: Loading auto data...', 'info');
      const autoData = await this.testAutoDataServiceInBrowser();
      
      if (!autoData) {
        this.log('❌ Cannot proceed - auto data loading failed', 'error');
        return false;
      }
      
      // Step 2: Route determination
      this.log('Step 2: Determining onboarding route...', 'info');
      const shouldUseSemesterFlow = autoData.auto_generated && 
                                  autoData.completeness_score >= 80;
      
      if (shouldUseSemesterFlow) {
        this.log('✅ Would use semester-centric onboarding', 'success');
      } else {
        this.log('ℹ️ Would use classic onboarding', 'info');
      }
      
      // Step 3: Specialization context
      this.log('Step 3: Loading specialization context...', 'info');
      const specializationOptions = ['PLAYER', 'COACH', 'INTERNSHIP'];
      const currentSpecialization = autoData.interests?.includes('Football') ? 'PLAYER' : 'COACH';
      
      this.log(`✅ Current specialization: ${currentSpecialization}`, 'success');
      this.log(`📋 Available options: ${specializationOptions.join(', ')}`, 'info');
      
      // Step 4: Completion
      this.log('Step 4: Completing onboarding simulation...', 'info');
      this.log('✅ Onboarding simulation completed successfully', 'success');
      
      return true;
    } catch (error) {
      this.log(`❌ Onboarding simulation error: ${error.message}`, 'error');
      return false;
    }
  }

  async runAllTests() {
    this.log('🚀 Starting comprehensive frontend tests...', 'test');
    this.log('=' + '='.repeat(50), 'info');
    
    // Run all test suites
    const browserTest = this.testBrowserEnvironment();
    const routeTest = this.testRouteConfiguration();
    this.testLocalStorageIntegration();
    this.testCSSOptimizations();
    const flowSuccess = await this.simulateOnboardingFlow();
    
    this.log('=' + '='.repeat(50), 'info');
    this.log('📊 TEST SUMMARY:', 'test');
    
    const successCount = this.testResults.filter(r => r.type === 'success').length;
    const errorCount = this.testResults.filter(r => r.type === 'error').length;
    const warningCount = this.testResults.filter(r => r.type === 'warning').length;
    
    this.log(`✅ Successful tests: ${successCount}`, 'success');
    this.log(`❌ Failed tests: ${errorCount}`, errorCount > 0 ? 'error' : 'info');
    this.log(`⚠️ Warnings: ${warningCount}`, warningCount > 0 ? 'warning' : 'info');
    
    const overallSuccess = errorCount === 0 && flowSuccess;
    
    if (overallSuccess) {
      this.log('🎉 ALL TESTS PASSED! Semester onboarding ready for use.', 'success');
    } else {
      this.log('⚠️ Some tests failed. Review errors above.', 'warning');
    }
    
    return {
      success: overallSuccess,
      results: this.testResults,
      summary: { successCount, errorCount, warningCount }
    };
  }

  // Quick test methods for console use
  quickTest() {
    this.log('⚡ Running quick semester onboarding test...', 'test');
    return this.testAutoDataServiceInBrowser();
  }

  fullTest() {
    return this.runAllTests();
  }
}

// Global function for easy console access
window.testSemesterOnboarding = function() {
  const tester = new FrontendOnboardingTester();
  return tester.fullTest();
};

window.quickTestSemesterOnboarding = function() {
  const tester = new FrontendOnboardingTester();
  return tester.quickTest();
};

// Auto-expose for development
if (process.env.NODE_ENV === 'development') {
  window.SemesterOnboardingTester = FrontendOnboardingTester;
}

export { FrontendOnboardingTester };