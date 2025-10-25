import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const ProtectedStudentRoute = ({ children }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [onboardingStatus, setOnboardingStatus] = useState({
    suggested: false,
    hasBasicData: false,
    isCompleted: false
  });

  const checkOnboardingStatus = useCallback(async () => {
    try {
      // Check essential onboarding data
      const onboardingCompleted = user?.onboarding_completed === true;
      const hasNickname = user?.nickname && user?.nickname.trim().length > 0;
      const hasProfileData = user?.phone && user?.emergency_contact;
      const hasBasicData = hasNickname && hasProfileData;

      console.log('🔍 BLOCKING onboarding check:', {
        onboardingCompleted,
        hasNickname,
        hasProfileData,
        user: user?.email
      });

      // BLOCK access if onboarding is NOT completed
      // NOTE: We don't check hasSpecialization because parallel specializations
      // are stored in user_licenses table, not in users.specialization field
      if (!onboardingCompleted) {
        console.log('❌ Onboarding INCOMPLETE - redirecting to /student/onboarding');
        navigate('/student/onboarding', { replace: true });
        return;
      }

      // Set onboarding status for dashboard display
      setOnboardingStatus({
        suggested: false,
        hasBasicData: hasBasicData,
        isCompleted: true
      });

    } catch (err) {
      console.error('Failed to check onboarding status:', err);
      // On error, redirect to onboarding for safety
      navigate('/student/onboarding', { replace: true });
    } finally {
      setLoading(false);
    }
  }, [user, navigate]);

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

  // Only render children if onboarding is completed
  return React.cloneElement(children, {
    onboardingStatus
  });
};

export default ProtectedStudentRoute;