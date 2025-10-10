import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';

const ProtectedStudentRoute = ({ children }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [onboardingStatus, setOnboardingStatus] = useState({
    suggested: false,
    hasBasicData: false,
    isCompleted: false
  });

  const checkOnboardingStatus = useCallback(async () => {
    try {
      // Check essential onboarding data
      const hasNickname = user?.nickname && user?.nickname.trim().length > 0;
      const hasProfileData = user?.phone && user?.emergency_contact;
      const onboardingCompleted = user?.onboarding_completed === true;
      const hasBasicData = hasNickname && hasProfileData;
      
      // Set onboarding status for dashboard display (but don't block access)
      setOnboardingStatus({
        suggested: !onboardingCompleted && !hasBasicData, // Only suggest if really incomplete
        hasBasicData: hasBasicData,
        isCompleted: onboardingCompleted
      });
      
      console.log('🔍 Non-blocking onboarding check:', {
        hasNickname,
        hasProfileData, 
        onboardingCompleted,
        suggested: !onboardingCompleted && !hasBasicData,
        user: user?.email
      });
      
    } catch (err) {
      console.error('Failed to check onboarding status:', err);
      // On error, allow access but suggest onboarding
      const hasBasicData = user?.phone && user?.emergency_contact && user?.nickname;
      setOnboardingStatus({
        suggested: !hasBasicData,
        hasBasicData: hasBasicData,
        isCompleted: false
      });
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    checkOnboardingStatus();
  }, [checkOnboardingStatus]);

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div className="loading-spinner"></div>
        <p>Profil ellenőrzése...</p>
      </div>
    );
  }

  // Always render children - no more blocking redirects!
  // Pass onboarding status to children for dashboard notifications
  return React.cloneElement(children, { 
    onboardingStatus 
  });
};

export default ProtectedStudentRoute;