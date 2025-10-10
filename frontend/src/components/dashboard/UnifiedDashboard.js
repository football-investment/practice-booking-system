import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import CleanDashboardHeader from './CleanDashboardHeader';
import NavigationSidebar from './NavigationSidebar';
import ContentArea from './ContentArea';
import QuickActions from './QuickActions';
import SimpleDashboard from './SimpleDashboard';
import { getDashboardConfig } from './config/dashboardConfigs';
import './UnifiedDashboard.css';

/**
 * Unified Dashboard Component
 * Role-adaptive dashboard that consolidates Student, Instructor, and Admin dashboards
 * into a single, configurable interface with dynamic content rendering
 */
const UnifiedDashboard = () => {
  console.log('🔧 UnifiedDashboard component loading...');
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState('');
  const [activeSection, setActiveSection] = useState('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Get role-based dashboard configuration
  const dashboardConfig = useMemo(() => {
    if (!user?.role) return null;
    return getDashboardConfig(user.role);
  }, [user?.role]);

  // Load unified dashboard data with performance optimization
  const loadDashboardData = useCallback(async () => {
    if (!user || !dashboardConfig) return;
    
    setLoading(true);
    setError('');
    
    try {
      console.log(`Loading ${user.role} dashboard data...`);
      
      // Parallel loading for better performance
      const promises = [
        apiService.getDashboardOverview({
          role: user.role,
          widgets: dashboardConfig.widgets?.map(w => w.id) || [],
          include_quick_actions: true,
          personalization: true
        })
      ];

      // Add learning journey only for student/instructor roles
      if (user.role === 'student' || user.role === 'instructor') {
        promises.push(apiService.getLearningJourneyOverview());
      }

      // Load data in parallel with timeout
      const results = await Promise.allSettled(promises);
      const [dashboardResult, learningJourneyResult] = results;

      // Handle dashboard data
      let dashboardResponse = {};
      if (dashboardResult.status === 'fulfilled') {
        dashboardResponse = dashboardResult.value;
      } else {
        console.warn('Dashboard data failed:', dashboardResult.reason?.message);
        setError(dashboardResult.reason?.message || 'Dashboard temporarily unavailable');
      }

      // Handle learning journey data
      let learningJourneyData = null;
      if (learningJourneyResult) {
        if (learningJourneyResult.status === 'fulfilled') {
          learningJourneyData = learningJourneyResult.value;
        } else {
          console.warn('Learning journey data unavailable:', learningJourneyResult.reason?.message);
        }
      }

      const consolidatedData = {
        overview: dashboardResponse.overview || {},
        widgets: dashboardResponse.widgets || [],
        quickActions: dashboardResponse.quick_actions || dashboardConfig.quickActions || [],
        notifications: dashboardResponse.notifications || [],
        learningJourney: learningJourneyData,
        performance: dashboardResponse.performance_metrics || {},
        user: dashboardResponse.user || user
      };

      setDashboardData(consolidatedData);
      
    } catch (err) {
      console.error('Dashboard data loading failed:', err);
      setError(err.message || 'Failed to load dashboard data');
      
      // Fallback to minimal dashboard with local data
      setDashboardData({
        overview: {},
        widgets: [],
        quickActions: dashboardConfig.quickActions || [],
        notifications: [],
        learningJourney: null,
        performance: {},
        user: user
      });
    } finally {
      setLoading(false);
    }
  }, [user, dashboardConfig]);

  // Load data on component mount and user change
  useEffect(() => {
    if (user && dashboardConfig) {
      loadDashboardData();
    }
  }, [user, dashboardConfig, loadDashboardData]);

  // Handle section navigation
  const handleSectionChange = useCallback((sectionId) => {
    setActiveSection(sectionId);
  }, []);

  // Handle sidebar toggle
  const handleSidebarToggle = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  // Render loading state
  if (loading) {
    return (
      <div className="unified-dashboard">
        <div className="dashboard-loading">
          <div className="loading-spinner"></div>
          <p>Loading {user?.role || 'your'} dashboard...</p>
        </div>
      </div>
    );
  }

  // Render error state with fallback
  if (error && !dashboardData) {
    return (
      <div className="unified-dashboard">
        <div className="dashboard-error">
          <h2>Dashboard Temporarily Unavailable</h2>
          <p>{error}</p>
          <button onClick={loadDashboardData} className="retry-button">
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  // Don't render if no config available
  if (!dashboardConfig || !dashboardData) {
    return (
      <div className="unified-dashboard">
        <div className="dashboard-error">
          <h2>Configuration Error</h2>
          <p>Unable to load dashboard configuration for your role.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`unified-dashboard unified-dashboard--${user.role} debug-unified-dashboard-2024`}>
      {/* CLEAN Dashboard Header */}
      <CleanDashboardHeader
        user={dashboardData.user}
        notifications={dashboardData.notifications}
        onSidebarToggle={handleSidebarToggle}
        sidebarCollapsed={sidebarCollapsed}
      />

      <div className="dashboard-main">
        {/* Navigation Sidebar */}
        <NavigationSidebar
          config={dashboardConfig.navigation}
          activeSection={activeSection}
          onSectionChange={handleSectionChange}
          collapsed={sidebarCollapsed}
          userRole={user.role}
        />

        {/* Main Content Area */}
        <div className={`dashboard-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
          {/* Simple Dashboard - Clean and working */}
          <SimpleDashboard
            data={dashboardData}
            userRole={user.role}
          />

          {/* Quick Actions Panel */}
          <QuickActions
            actions={dashboardData.quickActions}
            config={dashboardConfig.quickActions}
            userRole={user.role}
            onActionClick={(action) => {
              console.log('Quick action triggered:', action);
              // Handle quick action routing/execution
            }}
          />

          {/* Dynamic Content Area */}
          <ContentArea
            activeSection={activeSection}
            data={dashboardData}
            config={dashboardConfig}
            userRole={user.role}
            onDataRefresh={loadDashboardData}
          />

          {/* Error Overlay for partial failures */}
          {error && dashboardData && (
            <div className="dashboard-error-banner">
              <span>⚠️ Some data may be outdated: {error}</span>
              <button onClick={loadDashboardData} className="refresh-button">
                Refresh
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UnifiedDashboard;