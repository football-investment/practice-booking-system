import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const ProtectedStudentRoute = ({ children }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  useEffect(() => {
    checkOnboardingStatus();
  }, []);

  const checkOnboardingStatus = async () => {
    try {
      // If onboarding is explicitly completed and has nickname, allow access
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
      
      console.log('🔍 Onboarding check:', {
        hasNickname,
        hasProfileData, 
        onboardingCompleted,
        needsOnboarding,
        user: user?.email
      });
      
    } catch (err) {
      console.error('Failed to check onboarding status:', err);
      // On API error, assume needs onboarding if missing basic data
      const hasBasicData = user?.phone && user?.emergency_contact && user?.nickname;
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

  // If needs onboarding, redirect there
  if (needsOnboarding) {
    return <Navigate to="/student/onboarding" replace />;
  }

  // Otherwise, render the protected content
  return children;
};

export default ProtectedStudentRoute;