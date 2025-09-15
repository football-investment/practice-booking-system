import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import AppHeader from './components/common/AppHeader';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoginPage from './pages/LoginPage';

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
import StudentRouter from './components/student/StudentRouter';
import ProtectedStudentRoute from './components/student/ProtectedStudentRoute';
import DebugPage from './pages/DebugPage';

// Instructor Pages
import InstructorDashboard from './pages/instructor/InstructorDashboard';
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

// Test Pages
import ModalTestPage from './pages/ModalTestPage';

import './App.css';

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
      
      {/* Instructor Routes */}
      <Route path="/instructor/dashboard" element={
        <ProtectedRoute requiredRole="instructor">
          <InstructorDashboard />
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
      
      {/* Test Routes - accessible to all authenticated users */}
      <Route path="/test/modal" element={
        <ProtectedRoute>
          <ModalTestPage />
        </ProtectedRoute>
      } />
      
      {/* Debug Route - accessible to everyone for debugging */}
      <Route path="/debug" element={<DebugPage />} />
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <Router future={{ 
            v7_startTransition: true, 
            v7_relativeSplatPath: true 
          }}>
            <ErrorBoundary>
              <div className="app">
                <AppHeader />
                <main className="app-main">
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