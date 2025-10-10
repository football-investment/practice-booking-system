import React from 'react';
import { Navigate } from 'react-router-dom';

const StudentRouter = ({ targetPath = '/student/dashboard' }) => {
  // FIXED: Simple non-blocking router
  // Just redirect to target path without onboarding checks
  // Onboarding logic is now handled by ProtectedStudentRoute with suggestion banners
  
  console.log('🚀 StudentRouter: Non-blocking redirect to', targetPath);
  
  return <Navigate to={targetPath} replace />;
};

export default StudentRouter;