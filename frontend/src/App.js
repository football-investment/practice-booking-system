import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import CleanDashboardHeader from './components/dashboard/CleanDashboardHeader';
import ErrorBoundary from './components/common/ErrorBoundary';
import BrowserWarning from './components/common/BrowserWarning';
import LoginPage from './pages/LoginPage';
import './utils/iosOptimizations';
import './utils/crossOriginErrorHandler';
import './utils/iosBrowserCompatibility';

// Student Pages
import StudentDashboard from './pages/student/StudentDashboard';
import AllSessions from './pages/student/AllSessions';
import MyBookings from './pages/student/MyBookings';
import StudentProfile from './pages/student/StudentProfile';
import FeedbackPage from './pages/student/FeedbackPage';
import SessionDetails from './pages/student/SessionDetails';
import GamificationProfile from './pages/student/GamificationProfile';
import QuizDashboard from './pages/student/QuizDashboard';
import QuizTaking from './pages/student/QuizTaking';
import QuizResult from './pages/student/QuizResult';
import Projects from './pages/student/Projects';
import MyProjects from './pages/student/MyProjects';
import ProjectDetails from './pages/student/ProjectDetails';
import ProjectProgress from './pages/student/ProjectProgress';
import ProjectEnrollmentQuiz from './pages/student/ProjectEnrollmentQuiz';
import StudentMessages from './pages/student/StudentMessages';
import StudentOnboarding from './pages/student/StudentOnboarding';
import AdaptiveLearning from './pages/student/AdaptiveLearning';
import CurriculumView from './pages/student/CurriculumView';
import LessonView from './pages/student/LessonView';
import ExerciseSubmission from './pages/student/ExerciseSubmission';
import StudentRouter from './components/student/StudentRouter';
import ProtectedStudentRoute from './components/student/ProtectedStudentRoute';

// NEW: Adaptive Learning & Competency Components
import LearningProfileView from './components/AdaptiveLearning/LearningProfileView';
import CompetencyDashboard from './components/Competency/CompetencyDashboard';
import ParallelSpecializationSelector from './components/onboarding/ParallelSpecializationSelector';

// Instructor Pages
import InstructorSessions from './pages/instructor/InstructorSessions';
import InstructorSessionDetails from './pages/instructor/InstructorSessionDetails';
import InstructorProjects from './pages/instructor/InstructorProjects';
import InstructorProjectDetails from './pages/instructor/InstructorProjectDetails';
import InstructorProjectStudents from './pages/instructor/InstructorProjectStudents';
import InstructorStudents from './pages/instructor/InstructorStudents';
import InstructorStudentDetails from './pages/instructor/InstructorStudentDetails';
import InstructorStudentProgress from './pages/instructor/InstructorStudentProgress';
import InstructorMessages from './pages/instructor/InstructorMessages';
import InstructorFeedback from './pages/instructor/InstructorFeedback';
import InstructorAttendance from './pages/instructor/InstructorAttendance';
import InstructorProfile from './pages/instructor/InstructorProfile';
import InstructorAnalytics from './pages/instructor/InstructorAnalytics';
import InstructorProgressReport from './pages/instructor/InstructorProgressReport';

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import UserManagement from './pages/admin/UserManagement';
import SessionManagement from './pages/admin/SessionManagement';
import SemesterManagement from './pages/admin/SemesterManagement';
import GroupManagement from './pages/admin/GroupManagement';
import BookingManagement from './pages/admin/BookingManagement';
import AttendanceTracking from './pages/admin/AttendanceTracking';
import FeedbackOverview from './pages/admin/FeedbackOverview';
import ProjectManagement from './pages/admin/ProjectManagement';
import HealthDashboard from './components/admin/HealthDashboard';

import './App.css';
import './styles/ios-responsive.css';
import './styles/chrome-ios-optimizations.css';

function ProtectedRoute({ children, requiredRole }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  if (requiredRole && user.role !== requiredRole) {
    const redirectPath = user.role === 'admin' ? '/admin/dashboard' : 
                        user.role === 'instructor' ? '/instructor/dashboard' :
                        '/student/dashboard';
    return <Navigate to={redirectPath} replace />;
  }
  
  return children;
}

// Unified Header for all authenticated routes
function UnifiedHeader() {
  const location = useLocation();
  const { user } = useAuth();
  const isLoginPage = location.pathname === '/login';
  const isDashboardRoute = location.pathname.includes('/dashboard');
  const isOnboardingRoute = location.pathname.includes('/onboarding');

  // Don't show header on login page
  if (isLoginPage || !user) return null;

  // Don't show header on dashboard routes (they have their own integrated header)
  if (isDashboardRoute) return null;

  // Don't show header on onboarding routes (they have their own header with theme toggle)
  if (isOnboardingRoute) return null;

  return (
    <CleanDashboardHeader
      user={user}
      notifications={[]} // Empty for now, non-dashboard pages don't need notifications
      onSidebarToggle={() => {}} // No sidebar on regular pages
      sidebarCollapsed={false}
      showSidebarToggle={false} // Hide sidebar toggle on non-dashboard pages
    />
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="loading-screen">Initializing...</div>;
  }
  
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      
      {/* Auto-redirect based on role */}
      <Route path="/" element={
        user?.role === 'admin' ? 
        <Navigate to="/admin/dashboard" replace /> : 
        user?.role === 'instructor' ?
        <Navigate to="/instructor/dashboard" replace /> :
        <StudentRouter targetPath="/student/dashboard" />
      } />
      
      {/* Legacy dashboard redirect */}
      <Route path="/dashboard" element={
        user?.role === 'admin' ? 
        <Navigate to="/admin/dashboard" replace /> : 
        user?.role === 'instructor' ?
        <Navigate to="/instructor/dashboard" replace /> :
        <StudentRouter targetPath="/student/dashboard" />
      } />
      
      {/* Student Routes */}
      <Route path="/student/onboarding" element={
        <ProtectedRoute requiredRole="student">
          <StudentOnboarding />
        </ProtectedRoute>
      } />
      <Route path="/student/dashboard" element={
        <ProtectedRoute requiredRole="student">
          <ProtectedStudentRoute>
            <StudentDashboard />
          </ProtectedStudentRoute>
        </ProtectedRoute>
      } />
      <Route path="/student/sessions" element={
        <ProtectedRoute requiredRole="student">
          <AllSessions />
        </ProtectedRoute>
      } />
      <Route path="/student/sessions/:id" element={
        <ProtectedRoute requiredRole="student">
          <SessionDetails />
        </ProtectedRoute>
      } />
      <Route path="/student/bookings" element={
        <ProtectedRoute requiredRole="student">
          <MyBookings />
        </ProtectedRoute>
      } />
      <Route path="/student/profile" element={
        <ProtectedRoute requiredRole="student">
          <StudentProfile />
        </ProtectedRoute>
      } />
      <Route path="/student/feedback" element={
        <ProtectedRoute requiredRole="student">
          <FeedbackPage />
        </ProtectedRoute>
      } />
      <Route path="/student/gamification" element={
        <ProtectedRoute requiredRole="student">
          <GamificationProfile />
        </ProtectedRoute>
      } />
      <Route path="/student/quiz" element={
        <ProtectedRoute requiredRole="student">
          <QuizDashboard />
        </ProtectedRoute>
      } />
      <Route path="/student/quiz/:id/take" element={
        <ProtectedRoute requiredRole="student">
          <QuizTaking />
        </ProtectedRoute>
      } />
      <Route path="/student/quiz/result" element={
        <ProtectedRoute requiredRole="student">
          <QuizResult />
        </ProtectedRoute>
      } />
      <Route path="/student/projects" element={
        <ProtectedRoute requiredRole="student">
          <Projects />
        </ProtectedRoute>
      } />
      <Route path="/student/projects/my" element={
        <ProtectedRoute requiredRole="student">
          <MyProjects />
        </ProtectedRoute>
      } />
      <Route path="/student/projects/:id" element={
        <ProtectedRoute requiredRole="student">
          <ProjectDetails />
        </ProtectedRoute>
      } />
      <Route path="/student/projects/:id/progress" element={
        <ProtectedRoute requiredRole="student">
          <ProjectProgress />
        </ProtectedRoute>
      } />
      <Route path="/student/projects/:projectId/enrollment-quiz" element={
        <ProtectedRoute requiredRole="student">
          <ProjectEnrollmentQuiz />
        </ProtectedRoute>
      } />
      <Route path="/student/messages" element={
        <ProtectedRoute requiredRole="student">
          <StudentMessages />
        </ProtectedRoute>
      } />
      <Route path="/student/adaptive-learning" element={
        <ProtectedRoute requiredRole="student">
          <AdaptiveLearning />
        </ProtectedRoute>
      } />
      {/* NEW: Learning Profile & Competency Routes */}
      <Route path="/student/learning-profile" element={
        <ProtectedRoute requiredRole="student">
          <LearningProfileView />
        </ProtectedRoute>
      } />
      <Route path="/student/competency" element={
        <ProtectedRoute requiredRole="student">
          <CompetencyDashboard />
        </ProtectedRoute>
      } />
      <Route path="/student/specialization-select" element={
        <ProtectedRoute requiredRole="student">
          <ParallelSpecializationSelector hideNavigation={false} />
        </ProtectedRoute>
      } />

      {/* 📚 Curriculum Routes */}
      <Route path="/student/curriculum/:specializationId" element={
        <ProtectedRoute requiredRole="student">
          <CurriculumView />
        </ProtectedRoute>
      } />
      <Route path="/student/curriculum/:specializationId/lesson/:lessonId" element={
        <ProtectedRoute requiredRole="student">
          <LessonView />
        </ProtectedRoute>
      } />
      <Route path="/student/curriculum/:specializationId/lesson/:lessonId/exercise/:exerciseId" element={
        <ProtectedRoute requiredRole="student">
          <ExerciseSubmission />
        </ProtectedRoute>
      } />
      
      {/* Instructor Routes */}
      <Route path="/instructor/dashboard" element={
        <ProtectedRoute requiredRole="instructor">
          <div>Instructor Dashboard - Coming Soon</div>
        </ProtectedRoute>
      } />
      <Route path="/instructor/sessions" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorSessions />
        </ProtectedRoute>
      } />
      <Route path="/instructor/sessions/:id" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorSessionDetails />
        </ProtectedRoute>
      } />
      <Route path="/instructor/projects" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorProjects />
        </ProtectedRoute>
      } />
      <Route path="/instructor/projects/:projectId" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorProjectDetails />
        </ProtectedRoute>
      } />
      <Route path="/instructor/projects/:projectId/students" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorProjectStudents />
        </ProtectedRoute>
      } />
      <Route path="/instructor/students" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorStudents />
        </ProtectedRoute>
      } />
      <Route path="/instructor/students/:studentId" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorStudentDetails />
        </ProtectedRoute>
      } />
      <Route path="/instructor/students/:studentId/progress" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorStudentProgress />
        </ProtectedRoute>
      } />
      <Route path="/instructor/messages" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorMessages />
        </ProtectedRoute>
      } />
      <Route path="/instructor/feedback" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorFeedback />
        </ProtectedRoute>
      } />
      <Route path="/instructor/attendance" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorAttendance />
        </ProtectedRoute>
      } />
      <Route path="/instructor/profile" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorProfile />
        </ProtectedRoute>
      } />
      <Route path="/instructor/analytics" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorAnalytics />
        </ProtectedRoute>
      } />
      <Route path="/instructor/reports" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorProgressReport />
        </ProtectedRoute>
      } />
      
      {/* Admin Routes */}
      <Route path="/admin/dashboard" element={
        <ProtectedRoute requiredRole="admin">
          <AdminDashboard />
        </ProtectedRoute>
      } />
      <Route path="/admin/health" element={
        <ProtectedRoute requiredRole="admin">
          <HealthDashboard />
        </ProtectedRoute>
      } />
      <Route path="/admin/users" element={
        <ProtectedRoute requiredRole="admin">
          <UserManagement />
        </ProtectedRoute>
      } />
      <Route path="/admin/sessions" element={
        <ProtectedRoute requiredRole="admin">
          <SessionManagement />
        </ProtectedRoute>
      } />
      <Route path="/admin/semesters" element={
        <ProtectedRoute requiredRole="admin">
          <SemesterManagement />
        </ProtectedRoute>
      } />
      <Route path="/admin/groups" element={
        <ProtectedRoute requiredRole="admin">
          <GroupManagement />
        </ProtectedRoute>
      } />
      <Route path="/admin/bookings" element={
        <ProtectedRoute requiredRole="admin">
          <BookingManagement />
        </ProtectedRoute>
      } />
      <Route path="/admin/attendance" element={
        <ProtectedRoute requiredRole="admin">
          <AttendanceTracking />
        </ProtectedRoute>
      } />
      <Route path="/admin/feedback" element={
        <ProtectedRoute requiredRole="admin">
          <FeedbackOverview />
        </ProtectedRoute>
      } />
      <Route path="/admin/projects" element={
        <ProtectedRoute requiredRole="admin">
          <ProjectManagement />
        </ProtectedRoute>
      } />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  React.useEffect(() => {
    // Chrome iOS Detection and Optimization Application
    const detectAndOptimizeForChrome = () => {
      const ua = navigator.userAgent.toLowerCase();
      const isChrome = ua.includes('chrome') && !ua.includes('edg');
      const isIOS = /ipad|iphone|ipod/.test(ua) && !window.MSStream;
      const isIPad = /ipad/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
      const isIPhone = /iphone/.test(ua);
      
      // Apply Chrome iOS optimizations
      if (isChrome && isIOS) {
        document.body.classList.add('chrome-ios-optimized');
        console.log('🌐 Chrome iOS optimizations applied');
        
        // Device-specific optimizations
        if (isIPad) {
          document.body.classList.add('ipad-chrome-optimized');
          console.log('📱 iPad Chrome optimizations applied');
        } else if (isIPhone) {
          document.body.classList.add('iphone-chrome-optimized');
          console.log('📱 iPhone Chrome optimizations applied');
        }
      }
      
      // Warning for non-Chrome browsers on iOS
      if (isIOS && !isChrome) {
        console.warn('⚠️ Non-Chrome browser detected on iOS. Chrome is recommended for optimal experience.');
        const isFirefox = ua.includes('firefox');
        const isSafari = ua.includes('safari') && !ua.includes('chrome');
        
        if (isFirefox) {
          console.warn('🔥 Firefox detected - known script compatibility issues on iOS');
        } else if (isSafari) {
          console.warn('🧭 Safari detected - Chrome recommended for better compatibility');
        }
      }
      
      // Apply safe area and memory optimizations
      document.body.classList.add('chrome-ios-safe-area', 'chrome-ios-memory-optimized');
    };
    
    detectAndOptimizeForChrome();
    
    // Reapply optimizations on orientation change
    const handleOrientationChange = () => {
      setTimeout(detectAndOptimizeForChrome, 100);
    };
    
    window.addEventListener('orientationchange', handleOrientationChange);
    
    return () => {
      window.removeEventListener('orientationchange', handleOrientationChange);
    };
  }, []);

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <Router future={{ 
            v7_startTransition: true, 
            v7_relativeSplatPath: true 
          }}>
            <ErrorBoundary>
              <BrowserWarning />
              <div className="app chrome-ios-stable">
                <UnifiedHeader />
                <main className="app-main chrome-ios-scroll">
                  <ErrorBoundary>
                    <AppRoutes />
                  </ErrorBoundary>
                </main>
              </div>
            </ErrorBoundary>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;