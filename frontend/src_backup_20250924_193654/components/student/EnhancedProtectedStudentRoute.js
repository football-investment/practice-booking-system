import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { autoDataService } from '../../services/autoDataService';

/**
 * Enhanced Protected Student Route
 * Intelligently determines which onboarding flow to use based on:
 * 1. Whether auto-data is available (new semester-centric flow)
 * 2. User preferences and system configuration
 * 3. LFA context and enrollment status
 */
const EnhancedProtectedStudentRoute = ({ children }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [onboardingType, setOnboardingType] = useState('CLASSIC'); // 'CLASSIC' or 'SEMESTER_CENTRIC'
  const [autoDataAvailable, setAutoDataAvailable] = useState(false);

  useEffect(() => {
    checkOnboardingAndDataStatus();
  }, [user]);

  const checkOnboardingAndDataStatus = async () => {
    try {
      console.log('🔍 Enhanced onboarding check starting...');
      
      // Step 1: Check if user has completed onboarding
      const hasCompletedOnboarding = user?.onboarding_completed === true;
      const hasBasicData = user?.nickname && user?.phone && user?.emergency_contact;
      
      if (hasCompletedOnboarding && hasBasicData) {
        console.log('✅ User has completed onboarding with basic data');
        setNeedsOnboarding(false);
        setLoading(false);
        return;
      }

      // Step 2: Check for auto-data availability (LFA script integration)
      const autoDataCheck = await checkAutoDataAvailability();
      
      // Step 3: Determine onboarding strategy
      const onboardingStrategy = determineOnboardingStrategy(autoDataCheck);
      
      console.log('📊 Onboarding strategy determined:', {
        needsOnboarding: !hasCompletedOnboarding,
        onboardingType: onboardingStrategy,
        autoDataAvailable: autoDataCheck.available,
        user: user?.email
      });
      
      setNeedsOnboarding(!hasCompletedOnboarding);
      setOnboardingType(onboardingStrategy);
      setAutoDataAvailable(autoDataCheck.available);
      
    } catch (error) {
      console.error('❌ Error in enhanced onboarding check:', error);
      
      // Fallback to classic onboarding on error
      const hasBasicData = user?.phone && user?.emergency_contact && user?.nickname;
      setNeedsOnboarding(!hasBasicData);
      setOnboardingType('CLASSIC');
      setAutoDataAvailable(false);
      
    } finally {
      setLoading(false);
    }
  };

  /**
   * Check if auto-data is available from LFA scripts or external systems
   */
  const checkAutoDataAvailability = async () => {
    try {
      console.log('🔄 Checking auto-data availability...');
      
      // Check if auto-data service can load data
      const autoData = await autoDataService.loadAutoUserData(user?.id);
      
      const isAvailable = autoData && autoData.auto_generated === true;
      const dataQuality = autoData?.completeness_score || 0;
      const sources = autoData?.data_sources || [];
      
      console.log('📊 Auto-data check result:', {
        available: isAvailable,
        quality: dataQuality,
        sources: sources,
        lfaIntegration: sources.includes('LFA_SCRIPT')
      });
      
      return {
        available: isAvailable,
        quality: dataQuality,
        sources: sources,
        data: autoData,
        lfaIntegration: sources.includes('LFA_SCRIPT'),
        scriptGenerated: autoData?.lfa_student_code !== undefined
      };
      
    } catch (error) {
      console.warn('⚠️ Auto-data check failed, falling back to classic flow:', error);
      return {
        available: false,
        quality: 0,
        sources: [],
        data: null,
        lfaIntegration: false,
        scriptGenerated: false
      };
    }
  };

  /**
   * Determine which onboarding flow to use based on available data and context
   */
  const determineOnboardingStrategy = (autoDataCheck) => {
    // Priority 1: If LFA script integration is available, use semester-centric
    if (autoDataCheck.lfaIntegration && autoDataCheck.scriptGenerated) {
      console.log('🎓 Using SEMESTER_CENTRIC flow - LFA script integration detected');
      return 'SEMESTER_CENTRIC';
    }
    
    // Priority 2: If high-quality auto-data is available, use semester-centric
    if (autoDataCheck.available && autoDataCheck.quality >= 80) {
      console.log('📊 Using SEMESTER_CENTRIC flow - high-quality auto-data available');
      return 'SEMESTER_CENTRIC';
    }
    
    // Priority 3: Check for system configuration preference
    const systemPreference = getSemesterCentricPreference();
    if (systemPreference === 'ENABLED' && autoDataCheck.available) {
      console.log('⚙️ Using SEMESTER_CENTRIC flow - system preference enabled');
      return 'SEMESTER_CENTRIC';
    }
    
    // Priority 4: Check user agent for LFA context (if coming from LFA systems)
    if (isLFAContext() && autoDataCheck.available) {
      console.log('🏆 Using SEMESTER_CENTRIC flow - LFA context detected');
      return 'SEMESTER_CENTRIC';
    }
    
    // Default: Use classic onboarding
    console.log('📝 Using CLASSIC flow - fallback or no auto-data available');
    return 'CLASSIC';
  };

  /**
   * Check system configuration for semester-centric preference
   */
  const getSemesterCentricPreference = () => {
    // This could come from:
    // - Environment variables
    // - Backend configuration
    // - Local storage settings
    // - URL parameters
    
    const urlParams = new URLSearchParams(window.location.search);
    const urlPreference = urlParams.get('onboarding');
    
    if (urlPreference === 'semester') {
      return 'ENABLED';
    }
    
    // Check localStorage for admin override
    const adminOverride = localStorage.getItem('lfa_onboarding_preference');
    if (adminOverride === 'semester_centric') {
      return 'ENABLED';
    }
    
    // Check for environment configuration
    if (process.env.REACT_APP_ONBOARDING_STYLE === 'semester_centric') {
      return 'ENABLED';
    }
    
    return 'DEFAULT';
  };

  /**
   * Detect if user is coming from LFA systems
   */
  const isLFAContext = () => {
    // Check referrer
    const referrer = document.referrer;
    if (referrer.includes('lfa.') || referrer.includes('leading-football-academy')) {
      return true;
    }
    
    // Check URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('source') === 'lfa' || urlParams.get('from') === 'lfa') {
      return true;
    }
    
    // Check user agent or session storage for LFA context
    const lfaContext = sessionStorage.getItem('lfa_context');
    if (lfaContext === 'true') {
      return true;
    }
    
    return false;
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        flexDirection: 'column',
        gap: '1rem',
        fontFamily: 'Inter, sans-serif'
      }}>
        <div className="loading-spinner"></div>
        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
            {autoDataAvailable ? '🎓 LFA rendszer inicializálása...' : '📝 Profil ellenőrzése...'}
          </p>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.9rem', color: '#64748b' }}>
            {onboardingType === 'SEMESTER_CENTRIC' ? 
              'Automatikus adatok betöltése' : 
              'Onboarding állapot ellenőrzése'
            }
          </p>
        </div>
      </div>
    );
  }

  // If doesn't need onboarding, render protected content
  if (!needsOnboarding) {
    return children;
  }

  // Redirect to appropriate onboarding flow
  const targetPath = onboardingType === 'SEMESTER_CENTRIC' 
    ? '/student/semester-onboarding' 
    : '/student/onboarding';

  console.log(`🔄 Redirecting to ${onboardingType} onboarding:`, targetPath);
  
  return <Navigate to={targetPath} replace />;
};

export default EnhancedProtectedStudentRoute;