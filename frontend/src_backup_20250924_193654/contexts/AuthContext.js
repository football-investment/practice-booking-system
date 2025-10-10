import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService } from '../services/apiService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    const userData = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    
    if (userData && token) {
      try {
        // Validate token format (basic JWT check)
        const tokenParts = token.split('.');
        if (tokenParts.length !== 3) {
          throw new Error('Invalid token format');
        }
        
        const parsedUser = JSON.parse(userData);
        console.log('🔍 AuthContext loaded cached user:', parsedUser);
        
        // Check if cached user is missing critical onboarding fields
        const needsRefresh = parsedUser.onboarding_completed === undefined || 
                           parsedUser.phone === undefined ||
                           parsedUser.emergency_contact === undefined;
        
        if (needsRefresh) {
          console.log('🔄 User data needs refresh - fetching from API...');
          try {
            const freshUserData = await apiService.getCurrentUser();
            const updatedUser = {
              ...parsedUser,
              onboarding_completed: freshUserData?.onboarding_completed || false,
              phone: freshUserData?.phone || null,
              emergency_contact: freshUserData?.emergency_contact || null,
              emergency_phone: freshUserData?.emergency_phone || null,
              date_of_birth: freshUserData?.date_of_birth || null,
              medical_notes: freshUserData?.medical_notes || null,
              interests: freshUserData?.interests || [],
            };
            
            localStorage.setItem('user', JSON.stringify(updatedUser));
            setUser(updatedUser);
            console.log('✅ User data refreshed from API:', updatedUser);
          } catch (apiError) {
            console.warn('⚠️ Failed to refresh user data from API, using cached:', apiError);
            setUser(parsedUser);
          }
        } else {
          setUser(parsedUser);
        }
      } catch (error) {
        console.error('Invalid stored user data:', error);
        localStorage.removeItem('user');
        localStorage.removeItem('token');
      }
    }
    setLoading(false);
  };

  const login = async (credentials) => {
    try {
      const response = await apiService.login(credentials);
      
      // Validate response has required fields
      if (!response.access_token) {
        throw new Error("Invalid server response: missing access token");
      }
      
      // Store token temporarily to make /me request
      localStorage.setItem('token', response.access_token);
      
      // Fetch user data from /me endpoint
      let userResponse;
      try {
        userResponse = await apiService.getCurrentUser();
      } catch (error) {
        console.warn('Failed to fetch user data, using fallback:', error);
        userResponse = null;
      }
      
      const userData = {
        email: userResponse?.email || credentials.email,
        name: userResponse?.name || credentials.email.split('@')[0],
        nickname: userResponse?.nickname || null,
        role: userResponse?.role || (credentials.email.includes('admin') ? 'admin' : 'student'),
        full_name: userResponse?.name || 'User',
        id: userResponse?.id,
        onboarding_completed: userResponse?.onboarding_completed || false,
        phone: userResponse?.phone || null,
        emergency_contact: userResponse?.emergency_contact || null,
        emergency_phone: userResponse?.emergency_phone || null,
        date_of_birth: userResponse?.date_of_birth || null,
        medical_notes: userResponse?.medical_notes || null,
        interests: userResponse?.interests || [],
        raw_user_data: userResponse
      };

      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      
      console.log('🚀 AuthContext login successful:', userData);
      return { success: true, user: userData };
    } catch (error) {
      console.error('❌ AuthContext login failed:', error);
      return { success: false, error: error.message };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    console.log('👋 AuthContext logout completed');
  };

  const updateUser = (updatedData) => {
    console.log('🔄 AuthContext updating user:', updatedData);
    const updatedUser = { ...user, ...updatedData };
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
    console.log('✅ AuthContext user updated successfully');
  };

  const value = {
    user,
    login,
    logout,
    updateUser,
    updateUserProfile: updateUser, // Alias for onboarding component
    loading,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    isStudent: user?.role === 'student'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};