import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import DashboardMetrics from './reports/DashboardMetrics';
import AttendanceChart from './reports/AttendanceChart';
import BookingTrendsChart from './reports/BookingTrendsChart';
import UtilizationChart from './reports/UtilizationChart';
import ExportManager from './reports/ExportManager';
import './ReportingDashboard.css';

const ReportingDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  
  // Dashboard data states
  const [metrics, setMetrics] = useState({});
  const [attendanceData, setAttendanceData] = useState([]);
  const [bookingTrendsData, setBookingTrendsData] = useState([]);
  const [utilizationData, setUtilizationData] = useState([]);
  const [userActivityData, setUserActivityData] = useState([]);

  // Filter states
  const [dateRange, setDateRange] = useState('this_month');
  const [customDateRange, setCustomDateRange] = useState({
    start_date: '',
    end_date: ''
  });
  const [selectedSemester, setSelectedSemester] = useState('');
  const [semesters, setSemesters] = useState([]);
  
  // Auto-refresh state
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [dateRange, customDateRange, selectedSemester]);

  // Auto-refresh setup
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refreshDashboard();
      }, 5 * 60 * 1000); // Refresh every 5 minutes
      
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [semestersData] = await Promise.all([
        apiService.getSemesters()
      ]);
      
      setSemesters(semestersData || []);
      await loadDashboardData();
    } catch (err) {
      console.error('Error loading initial data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const loadDashboardData = async () => {
    try {
      const filters = getFilters();
      
      // Load all dashboard data in parallel
      const [
        metricsData,
        attendanceAnalytics,
        bookingAnalytics, 
        utilizationAnalytics,
        userAnalytics
      ] = await Promise.all([
        loadMetrics(filters),
        loadAttendanceData(filters),
        loadBookingTrends(filters),
        loadUtilizationData(filters),
        loadUserActivity(filters)
      ]);

      setMetrics(metricsData);
      setAttendanceData(attendanceAnalytics);
      setBookingTrendsData(bookingAnalytics);
      setUtilizationData(utilizationAnalytics);
      setUserActivityData(userAnalytics);
      
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('Failed to refresh dashboard data');
    }
  };

  const loadMetrics = async (filters) => {
    try {
      // Try to get analytics metrics, fallback to calculating from existing endpoints
      return await apiService.getAnalyticsMetrics(filters);
    } catch (err) {
      console.warn('Analytics endpoint not available, calculating metrics from existing data');
      // Fallback: Calculate metrics from existing endpoints
      return await calculateMetricsFromExistingData(filters);
    }
  };

  const calculateMetricsFromExistingData = async (filters) => {
    try {
      const [users, semesters, sessions, systemStats] = await Promise.all([
        apiService.getUsers(),
        apiService.getSemesters(), 
        apiService.getSessions(),
        apiService.getSystemStats().catch(() => ({}))
      ]);

      const activeSemester = semesters.find(s => s.is_active) || semesters[0];
      const activeSessions = sessions.filter(s => 
        s.status === 'scheduled' && 
        new Date(s.session_date) >= new Date()
      );
      
      return {
        totalUsers: users.length,
        totalSemesters: semesters.length,
        activeSemester: activeSemester,
        totalSessions: sessions.length,
        activeSessions: activeSessions.length,
        completedSessions: sessions.filter(s => s.status === 'completed').length,
        onlineSessions: sessions.filter(s => s.mode === 'online').length,
        offlineSessions: sessions.filter(s => s.mode === 'offline').length,
        averageAttendance: 75, // Placeholder - would come from booking data
        bookingRate: 68, // Placeholder
        systemUtilization: 82, // Placeholder
        weeklyGrowth: 12.5, // Placeholder
        monthlyBookings: 156, // Placeholder  
        userEngagement: 89 // Placeholder
      };
    } catch (err) {
      console.error('Error calculating metrics:', err);
      return {};
    }
  };

  const loadAttendanceData = async (filters) => {
    try {
      return await apiService.getAttendanceAnalytics(filters);
    } catch (err) {
      console.warn('Attendance analytics not available, using sample data');
      // Return sample data for demonstration
      return generateSampleAttendanceData();
    }
  };

  const loadBookingTrends = async (filters) => {
    try {
      return await apiService.getBookingAnalytics(filters);
    } catch (err) {
      console.warn('Booking analytics not available, using sample data');
      return generateSampleBookingData();
    }
  };

  const loadUtilizationData = async (filters) => {
    try {
      return await apiService.getUtilizationAnalytics(filters);
    } catch (err) {
      console.warn('Utilization analytics not available, using sample data');
      return generateSampleUtilizationData();
    }
  };

  const loadUserActivity = async (filters) => {
    try {
      return await apiService.getUserAnalytics(filters);
    } catch (err) {
      console.warn('User analytics not available, using sample data');
      return generateSampleUserActivityData();
    }
  };

  // Sample data generators for when API endpoints aren't available
  const generateSampleAttendanceData = () => {
    const data = [];
    const today = new Date();
    
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      
      data.push({
        date: date.toISOString().split('T')[0],
        attendance: Math.floor(Math.random() * 50) + 20,
        sessions: Math.floor(Math.random() * 8) + 2
      });
    }
    
    return data;
  };

  const generateSampleBookingData = () => {
    const weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
    return weeks.map(week => ({
      week,
      online: Math.floor(Math.random() * 30) + 10,
      offline: Math.floor(Math.random() * 20) + 5,
      total: 0 // Will be calculated in component
    })).map(item => ({ ...item, total: item.online + item.offline }));
  };

  const generateSampleUtilizationData = () => {
    return [
      { name: 'Fully Booked', value: 35, color: '#dc3545' },
      { name: 'Partially Booked', value: 45, color: '#ffc107' },  
      { name: 'Available', value: 20, color: '#28a745' }
    ];
  };

  const generateSampleUserActivityData = () => {
    return [
      { role: 'Students', bookings: 156, logins: 89, attendance: 134 },
      { role: 'Instructors', bookings: 12, logins: 45, attendance: 38 },
      { role: 'Admins', bookings: 8, logins: 67, attendance: 23 }
    ];
  };

  const getFilters = () => {
    const filters = {};
    
    if (selectedSemester) {
      filters.semester_id = selectedSemester;
    }
    
    // Handle date range
    if (dateRange === 'custom' && customDateRange.start_date && customDateRange.end_date) {
      filters.start_date = customDateRange.start_date;
      filters.end_date = customDateRange.end_date;
    } else if (dateRange !== 'custom') {
      // Convert preset to actual dates
      const now = new Date();
      switch (dateRange) {
        case 'today':
          filters.start_date = now.toISOString().split('T')[0];
          filters.end_date = now.toISOString().split('T')[0];
          break;
        case 'this_week':
          const weekStart = new Date(now.setDate(now.getDate() - now.getDay()));
          filters.start_date = weekStart.toISOString().split('T')[0];
          filters.end_date = new Date().toISOString().split('T')[0];
          break;
        case 'this_month':
          filters.start_date = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
          filters.end_date = new Date().toISOString().split('T')[0];
          break;
        default:
          // Default to last 30 days
          filters.start_date = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
          filters.end_date = new Date().toISOString().split('T')[0];
      }
    }
    
    return filters;
  };

  const refreshDashboard = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setLastRefresh(new Date());
    setRefreshing(false);
  };

  const handleDateRangeChange = (newRange) => {
    setDateRange(newRange);
    if (newRange !== 'custom') {
      setCustomDateRange({ start_date: '', end_date: '' });
    }
  };

  const handleCustomDateChange = (field, value) => {
    setCustomDateRange(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  };

  if (loading) {
    return (
      <div className="reporting-dashboard loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="reporting-dashboard error">
        <div className="error-message">
          <h3>Dashboard Error</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>
            Reload Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="reporting-dashboard">
      <div className="dashboard-header">
        <div className="header-title">
          <h2>System Reports & Analytics</h2>
          <p className="header-subtitle">
            Last updated: {lastRefresh.toLocaleString()}
            {autoRefresh && <span className="auto-refresh-indicator">🔄 Auto-refresh ON</span>}
          </p>
        </div>
        
        <div className="dashboard-controls">
          <div className="date-range-selector">
            <select 
              value={dateRange} 
              onChange={(e) => handleDateRangeChange(e.target.value)}
            >
              <option value="today">Today</option>
              <option value="this_week">This Week</option>
              <option value="this_month">This Month</option>
              <option value="this_semester">This Semester</option>
              <option value="custom">Custom Range</option>
            </select>
            
            {dateRange === 'custom' && (
              <div className="custom-date-inputs">
                <input
                  type="date"
                  value={customDateRange.start_date}
                  onChange={(e) => handleCustomDateChange('start_date', e.target.value)}
                  placeholder="Start Date"
                />
                <input
                  type="date"
                  value={customDateRange.end_date}
                  onChange={(e) => handleCustomDateChange('end_date', e.target.value)}
                  placeholder="End Date"
                />
              </div>
            )}
          </div>
          
          <select 
            value={selectedSemester} 
            onChange={(e) => setSelectedSemester(e.target.value)}
          >
            <option value="">All Semesters</option>
            {semesters.map(semester => (
              <option key={semester.id} value={semester.id}>
                {semester.name}
              </option>
            ))}
          </select>
          
          <button 
            className={`btn btn-toggle ${autoRefresh ? 'active' : ''}`}
            onClick={toggleAutoRefresh}
            title="Toggle auto-refresh"
          >
            🔄 Auto
          </button>
          
          <button 
            className={`btn btn-primary ${refreshing ? 'refreshing' : ''}`}
            onClick={refreshDashboard}
            disabled={refreshing}
          >
            {refreshing ? '⏳' : '🔄'} Refresh
          </button>
          
          <ExportManager 
            metrics={metrics}
            attendanceData={attendanceData}
            bookingTrendsData={bookingTrendsData}
            utilizationData={utilizationData}
            dateRange={dateRange}
            customDateRange={customDateRange}
          />
        </div>
      </div>

      {/* Key Metrics Overview */}
      <div className="metrics-section">
        <DashboardMetrics 
          metrics={metrics}
          loading={refreshing}
        />
      </div>

      {/* Charts Section */}
      <div className="charts-section">
        <div className="charts-grid">
          <div className="chart-container">
            <AttendanceChart 
              data={attendanceData}
              loading={refreshing}
              dateRange={dateRange}
            />
          </div>
          
          <div className="chart-container">
            <BookingTrendsChart 
              data={bookingTrendsData}
              loading={refreshing}
              dateRange={dateRange}
            />
          </div>
          
          <div className="chart-container">
            <UtilizationChart 
              data={utilizationData}
              loading={refreshing}
            />
          </div>
          
          <div className="chart-container user-activity">
            <div className="chart-header">
              <h3>User Activity</h3>
              <p>Activity breakdown by user role</p>
            </div>
            <div className="chart-content">
              {userActivityData.length > 0 ? (
                <div className="user-activity-grid">
                  {userActivityData.map((roleData, index) => (
                    <div key={index} className="activity-card">
                      <h4>{roleData.role}</h4>
                      <div className="activity-stats">
                        <div className="stat">
                          <span className="stat-value">{roleData.bookings}</span>
                          <span className="stat-label">Bookings</span>
                        </div>
                        <div className="stat">
                          <span className="stat-value">{roleData.logins}</span>
                          <span className="stat-label">Logins</span>
                        </div>
                        <div className="stat">
                          <span className="stat-value">{roleData.attendance}</span>
                          <span className="stat-label">Attendance</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-data">No user activity data available</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Reports Section */}
      <div className="reports-section">
        <div className="reports-header">
          <h3>Quick Reports</h3>
          <p>Generate detailed reports for further analysis</p>
        </div>
        
        <div className="reports-grid">
          <div className="report-card">
            <h4>📊 Semester Report</h4>
            <p>Complete semester overview with sessions, bookings, and attendance</p>
            <button className="btn btn-secondary btn-sm">Generate</button>
          </div>
          
          <div className="report-card">
            <h4>👥 User Activity Report</h4>
            <p>Detailed user engagement and activity patterns</p>
            <button className="btn btn-secondary btn-sm">Generate</button>
          </div>
          
          <div className="report-card">
            <h4>📈 Utilization Report</h4>
            <p>Session capacity utilization and booking efficiency</p>
            <button className="btn btn-secondary btn-sm">Generate</button>
          </div>
          
          <div className="report-card">
            <h4>⚙️ System Statistics</h4>
            <p>System-wide performance and usage metrics</p>
            <button className="btn btn-secondary btn-sm">Generate</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportingDashboard;