import React, { useState } from 'react';

const ExportManager = ({ 
  metrics, 
  attendanceData, 
  bookingTrendsData, 
  utilizationData,
  dateRange,
  customDateRange 
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  // Export to CSV format
  const exportToCSV = (data, filename) => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      alert('No data available to export');
      return;
    }

    // Convert data to CSV format
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','), // Header row
      ...data.map(row => 
        headers.map(header => {
          const value = row[header];
          // Escape quotes and wrap in quotes if needed
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        }).join(',')
      )
    ].join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Export metrics as CSV
  const exportMetrics = async () => {
    setIsExporting(true);
    
    try {
      const metricsData = [
        {
          metric: 'Total Users',
          value: metrics.totalUsers || 0,
          description: 'Active users in system'
        },
        {
          metric: 'Total Sessions',
          value: metrics.totalSessions || 0,
          description: 'All scheduled sessions'
        },
        {
          metric: 'Active Sessions',
          value: metrics.activeSessions || 0,
          description: 'Sessions today/this week'
        },
        {
          metric: 'Completed Sessions',
          value: metrics.completedSessions || 0,
          description: 'Sessions finished'
        },
        {
          metric: 'Average Attendance',
          value: `${metrics.averageAttendance || 0}%`,
          description: 'Average session attendance'
        },
        {
          metric: 'Booking Rate',
          value: `${metrics.bookingRate || 0}%`,
          description: 'Bookings vs capacity'
        },
        {
          metric: 'System Utilization',
          value: `${metrics.systemUtilization || 0}%`,
          description: 'Overall system usage'
        },
        {
          metric: 'Online Sessions',
          value: metrics.onlineSessions || 0,
          description: 'Online mode sessions'
        },
        {
          metric: 'Offline Sessions',
          value: metrics.offlineSessions || 0,
          description: 'Offline mode sessions'
        }
      ];

      const timestamp = new Date().toISOString().split('T')[0];
      exportToCSV(metricsData, `dashboard-metrics-${timestamp}.csv`);
    } catch (error) {
      console.error('Error exporting metrics:', error);
      alert('Failed to export metrics');
    } finally {
      setIsExporting(false);
      setShowDropdown(false);
    }
  };

  // Export attendance data as CSV
  const exportAttendance = async () => {
    setIsExporting(true);
    
    try {
      if (!attendanceData || attendanceData.length === 0) {
        alert('No attendance data available');
        return;
      }

      const timestamp = new Date().toISOString().split('T')[0];
      exportToCSV(attendanceData, `attendance-data-${timestamp}.csv`);
    } catch (error) {
      console.error('Error exporting attendance:', error);
      alert('Failed to export attendance data');
    } finally {
      setIsExporting(false);
      setShowDropdown(false);
    }
  };

  // Export booking trends as CSV
  const exportBookingTrends = async () => {
    setIsExporting(true);
    
    try {
      if (!bookingTrendsData || bookingTrendsData.length === 0) {
        alert('No booking trends data available');
        return;
      }

      const timestamp = new Date().toISOString().split('T')[0];
      exportToCSV(bookingTrendsData, `booking-trends-${timestamp}.csv`);
    } catch (error) {
      console.error('Error exporting booking trends:', error);
      alert('Failed to export booking trends');
    } finally {
      setIsExporting(false);
      setShowDropdown(false);
    }
  };

  // Export utilization data as CSV
  const exportUtilization = async () => {
    setIsExporting(true);
    
    try {
      if (!utilizationData || utilizationData.length === 0) {
        alert('No utilization data available');
        return;
      }

      const timestamp = new Date().toISOString().split('T')[0];
      exportToCSV(utilizationData, `session-utilization-${timestamp}.csv`);
    } catch (error) {
      console.error('Error exporting utilization:', error);
      alert('Failed to export utilization data');
    } finally {
      setIsExporting(false);
      setShowDropdown(false);
    }
  };

  // Export comprehensive report
  const exportComprehensiveReport = async () => {
    setIsExporting(true);
    
    try {
      // Combine all data into a comprehensive report
      const reportData = {
        generated_at: new Date().toISOString(),
        date_range: dateRange,
        custom_range: customDateRange,
        metrics: metrics,
        attendance: attendanceData,
        booking_trends: bookingTrendsData,
        utilization: utilizationData
      };

      // Convert to CSV-friendly format
      const reportSummary = [
        {
          section: 'Report Information',
          generated_at: reportData.generated_at,
          date_range: reportData.date_range,
          custom_start: reportData.custom_range?.start_date || 'N/A',
          custom_end: reportData.custom_range?.end_date || 'N/A'
        },
        {
          section: 'System Metrics',
          total_users: metrics.totalUsers || 0,
          total_sessions: metrics.totalSessions || 0,
          active_sessions: metrics.activeSessions || 0,
          completed_sessions: metrics.completedSessions || 0,
          average_attendance: `${metrics.averageAttendance || 0}%`,
          booking_rate: `${metrics.bookingRate || 0}%`,
          system_utilization: `${metrics.systemUtilization || 0}%`
        }
      ];

      const timestamp = new Date().toISOString().split('T')[0];
      exportToCSV(reportSummary, `comprehensive-report-${timestamp}.csv`);
      
      // Also offer JSON export for complete data
      const jsonBlob = new Blob([JSON.stringify(reportData, null, 2)], { 
        type: 'application/json' 
      });
      const link = document.createElement('a');
      const url = URL.createObjectURL(jsonBlob);
      link.setAttribute('href', url);
      link.setAttribute('download', `comprehensive-report-${timestamp}.json`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (error) {
      console.error('Error exporting comprehensive report:', error);
      alert('Failed to export comprehensive report');
    } finally {
      setIsExporting(false);
      setShowDropdown(false);
    }
  };

  const toggleDropdown = () => {
    setShowDropdown(!showDropdown);
  };

  const closeDropdown = () => {
    setShowDropdown(false);
  };

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (showDropdown && !event.target.closest('.export-dropdown')) {
        closeDropdown();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDropdown]);

  return (
    <div className="export-manager">
      <div className="export-dropdown">
        <button 
          className={`btn btn-secondary export-button ${isExporting ? 'exporting' : ''}`}
          onClick={toggleDropdown}
          disabled={isExporting}
        >
          {isExporting ? '⏳ Exporting...' : '📥 Export'}
        </button>
        
        {showDropdown && (
          <div className="dropdown-menu">
            <div className="dropdown-header">
              <h4>Export Data</h4>
              <p>Download reports in CSV format</p>
            </div>
            
            <div className="dropdown-items">
              <button 
                className="dropdown-item"
                onClick={exportMetrics}
                disabled={isExporting}
              >
                <span className="item-icon">📊</span>
                <div className="item-content">
                  <span className="item-title">Dashboard Metrics</span>
                  <span className="item-description">Key performance indicators</span>
                </div>
              </button>
              
              <button 
                className="dropdown-item"
                onClick={exportAttendance}
                disabled={isExporting || !attendanceData?.length}
              >
                <span className="item-icon">📈</span>
                <div className="item-content">
                  <span className="item-title">Attendance Data</span>
                  <span className="item-description">Historical attendance records</span>
                </div>
              </button>
              
              <button 
                className="dropdown-item"
                onClick={exportBookingTrends}
                disabled={isExporting || !bookingTrendsData?.length}
              >
                <span className="item-icon">📋</span>
                <div className="item-content">
                  <span className="item-title">Booking Trends</span>
                  <span className="item-description">Booking patterns over time</span>
                </div>
              </button>
              
              <button 
                className="dropdown-item"
                onClick={exportUtilization}
                disabled={isExporting || !utilizationData?.length}
              >
                <span className="item-icon">🥧</span>
                <div className="item-content">
                  <span className="item-title">Session Utilization</span>
                  <span className="item-description">Capacity usage breakdown</span>
                </div>
              </button>
              
              <div className="dropdown-divider"></div>
              
              <button 
                className="dropdown-item featured"
                onClick={exportComprehensiveReport}
                disabled={isExporting}
              >
                <span className="item-icon">📑</span>
                <div className="item-content">
                  <span className="item-title">Comprehensive Report</span>
                  <span className="item-description">All data in CSV + JSON format</span>
                </div>
              </button>
            </div>
            
            <div className="dropdown-footer">
              <small>Files will be downloaded to your default download folder</small>
            </div>
          </div>
        )}
      </div>
      
      <style>{`
        .export-manager {
          position: relative;
        }
        
        .export-dropdown {
          position: relative;
        }
        
        .export-button {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        
        .export-button.exporting {
          opacity: 0.7;
          cursor: not-allowed;
        }
        
        .dropdown-menu {
          position: absolute;
          top: 100%;
          right: 0;
          margin-top: 8px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
          border: 1px solid #e0e0e0;
          min-width: 280px;
          z-index: 1000;
          overflow: hidden;
        }
        
        .dropdown-header {
          padding: 16px 20px;
          border-bottom: 1px solid #f0f0f0;
          background: #fafbfc;
        }
        
        .dropdown-header h4 {
          margin: 0 0 4px 0;
          color: #333;
          font-size: 16px;
          font-weight: 600;
        }
        
        .dropdown-header p {
          margin: 0;
          color: #666;
          font-size: 13px;
        }
        
        .dropdown-items {
          padding: 12px 0;
        }
        
        .dropdown-item {
          width: 100%;
          padding: 12px 20px;
          border: none;
          background: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 12px;
          transition: background-color 0.2s;
          text-align: left;
        }
        
        .dropdown-item:hover:not(:disabled) {
          background: #f8f9fa;
        }
        
        .dropdown-item:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .dropdown-item.featured {
          background: #f0f8ff;
          border-top: 1px solid #e3f2fd;
          border-bottom: 1px solid #e3f2fd;
        }
        
        .dropdown-item.featured:hover:not(:disabled) {
          background: #e8f4fd;
        }
        
        .item-icon {
          font-size: 18px;
          flex-shrink: 0;
        }
        
        .item-content {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        
        .item-title {
          font-size: 14px;
          font-weight: 500;
          color: #333;
        }
        
        .item-description {
          font-size: 12px;
          color: #666;
        }
        
        .dropdown-divider {
          height: 1px;
          background: #f0f0f0;
          margin: 8px 0;
        }
        
        .dropdown-footer {
          padding: 12px 20px;
          border-top: 1px solid #f0f0f0;
          background: #fafbfc;
        }
        
        .dropdown-footer small {
          color: #666;
          font-size: 11px;
        }
        
        /* Animation */
        .dropdown-menu {
          animation: dropdownSlide 0.2s ease-out;
        }
        
        @keyframes dropdownSlide {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
          .dropdown-menu {
            right: auto;
            left: 0;
            min-width: 260px;
          }
        }
        
        @media (max-width: 480px) {
          .dropdown-menu {
            position: fixed;
            top: 50%;
            left: 50%;
            right: auto;
            transform: translate(-50%, -50%);
            margin-top: 0;
            width: 90vw;
            max-width: 300px;
            max-height: 70vh;
            overflow-y: auto;
          }
          
          .dropdown-header,
          .dropdown-footer {
            padding: 12px 16px;
          }
          
          .dropdown-item {
            padding: 10px 16px;
          }
          
          .item-title {
            font-size: 13px;
          }
          
          .item-description {
            font-size: 11px;
          }
        }
      `}</style>
    </div>
  );
};

export default ExportManager;