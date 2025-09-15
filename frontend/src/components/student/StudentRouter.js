import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const StudentRouter = ({ targetPath = '/student/dashboard' }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  useEffect(() => {
    checkOnboardingStatus();
  }, []);

  const checkOnboardingStatus = async () => {
    try {
      // Check if user has completed onboarding and has all required data
      if (user?.onboarding_completed === true && user?.nickname && user?.phone && user?.emergency_contact) {
        setNeedsOnboarding(false);
        setLoading(false);
        return;
      }

      // Check essential onboarding data
      const hasNickname = user?.nickname && user?.nickname.trim().length > 0;
      const hasProfileData = user?.phone && user?.emergency_contact;
      const onboardingCompleted = user?.onboarding_completed === true;
      
      // Needs onboarding if missing ANY of these critical fields:
      const needsOnboarding = !hasNickname || !hasProfileData || !onboardingCompleted;
      
      setNeedsOnboarding(needsOnboarding);
      
      console.log('🔍 StudentRouter onboarding check:', {
        hasNickname,
        hasProfileData, 
        onboardingCompleted,
        needsOnboarding,
        user: user?.email
      });
      
    } catch (err) {
      console.error('Failed to check onboarding status:', err);
      // On error, check if user has basic required data
      const hasBasicData = user?.nickname && user?.phone && user?.emergency_contact;
      setNeedsOnboarding(!hasBasicData);
    } finally {
      setLoading(false);
    }
  };

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

  // If already on onboarding page, don't redirect
  if (window.location.pathname === '/student/onboarding') {
    return null; // Let the current route render
  }

  // If needs onboarding and not already there, redirect to onboarding
  if (needsOnboarding) {
    return <Navigate to="/student/onboarding" replace />;
  }

  // Otherwise, redirect to target path
  return <Navigate to={targetPath} replace />;
};

export default StudentRouter;