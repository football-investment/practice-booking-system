import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import AdminPage from './pages/AdminPage';
import StudentDashboard from './components/student/StudentDashboard';
import config from './config/environment';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <header className="app-header">
            <h1>🎯 Practice Booking System</h1>
            <span className="app-subtitle">Backend Testing Frontend</span>
          </header>
          
          <main className="app-main">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute adminOnly><AdminPage /></ProtectedRoute>} />
              <Route path="/student" element={<ProtectedRoute studentOnly><StudentDashboard /></ProtectedRoute>} />
              <Route path="/" element={<Navigate to="/login" />} />
            </Routes>
          </main>
          
          <footer className="app-footer">
            <p>🔧 Minimal Frontend for Backend Testing</p>
            {config.enableDebug && (
              <p>API: {config.apiUrl} | Frontend: {window.location.origin}</p>
            )}
          </footer>
        </div>
      </Router>
    </AuthProvider>
  );
}

// Protected Route Component
function ProtectedRoute({ children, adminOnly = false, studentOnly = false }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="loading">🔄 Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  if (adminOnly && user.role !== 'admin') {
    return <div className="error">❌ Admin access required</div>;
  }
  
  if (studentOnly && user.role !== 'student') {
    return <div className="error">❌ Student access required</div>;
  }
  
  return children;
}

export default App;