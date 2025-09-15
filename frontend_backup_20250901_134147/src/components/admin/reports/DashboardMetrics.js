import React from 'react';

const DashboardMetrics = ({ metrics, loading }) => {
  const metricCards = [
    {
      title: 'Total Users',
      value: metrics.totalUsers || 0,
      icon: '👥',
      color: '#2196f3',
      trend: metrics.userGrowth || null,
      description: 'Active users in system'
    },
    {
      title: 'Active Semester',
      value: metrics.activeSemester?.name || 'N/A',
      icon: '📅',
      color: '#4caf50',
      description: 'Current active semester'
    },
    {
      title: 'Total Sessions',
      value: metrics.totalSessions || 0,
      icon: '📚',
      color: '#ff9800',
      trend: metrics.sessionGrowth || null,
      description: 'All scheduled sessions'
    },
    {
      title: 'Active Sessions',
      value: metrics.activeSessions || 0,
      icon: '🟢',
      color: '#4caf50',
      description: 'Sessions today/this week'
    },
    {
      title: 'Completed Sessions',
      value: metrics.completedSessions || 0,
      icon: '✅',
      color: '#9c27b0',
      description: 'Sessions finished'
    },
    {
      title: 'Average Attendance',
      value: `${metrics.averageAttendance || 0}%`,
      icon: '📊',
      color: '#2196f3',
      trend: metrics.attendanceTrend || null,
      description: 'Average session attendance'
    },
    {
      title: 'Booking Rate',
      value: `${metrics.bookingRate || 0}%`,
      icon: '📈',
      color: '#4caf50',
      trend: metrics.bookingTrend || null,
      description: 'Bookings vs capacity'
    },
    {
      title: 'System Utilization',
      value: `${metrics.systemUtilization || 0}%`,
      icon: '⚙️',
      color: '#ff5722',
      trend: metrics.utilizationTrend || null,
      description: 'Overall system usage'
    }
  ];

  const formatTrend = (trend) => {
    if (!trend || trend === 0) return null;
    
    const isPositive = trend > 0;
    const arrow = isPositive ? '↗️' : '↘️';
    const color = isPositive ? '#4caf50' : '#f44336';
    
    return (
      <span className="trend-indicator" style={{ color }}>
        {arrow} {Math.abs(trend)}%
      </span>
    );
  };

  const formatValue = (value) => {
    if (typeof value === 'number' && value > 1000) {
      return (value / 1000).toFixed(1) + 'k';
    }
    return value;
  };

  if (loading) {
    return (
      <div className="dashboard-metrics loading">
        <div className="metrics-grid">
          {Array(8).fill(0).map((_, index) => (
            <div key={index} className="metric-card loading-card">
              <div className="loading-placeholder">
                <div className="loading-icon"></div>
                <div className="loading-text"></div>
                <div className="loading-value"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-metrics">
      <div className="metrics-header">
        <h3>System Overview</h3>
        <p>Key performance indicators and metrics</p>
      </div>
      
      <div className="metrics-grid">
        {metricCards.map((card, index) => (
          <div key={index} className="metric-card" style={{ borderTopColor: card.color }}>
            <div className="metric-header">
              <div className="metric-icon" style={{ backgroundColor: card.color + '15' }}>
                {card.icon}
              </div>
              <div className="metric-title">
                {card.title}
              </div>
            </div>
            
            <div className="metric-content">
              <div className="metric-value-container">
                <span className="metric-value">
                  {formatValue(card.value)}
                </span>
                {card.trend && formatTrend(card.trend)}
              </div>
              <div className="metric-description">
                {card.description}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Additional Summary Row */}
      <div className="metrics-summary">
        <div className="summary-item">
          <span className="summary-label">Online Sessions:</span>
          <span className="summary-value">{metrics.onlineSessions || 0}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Offline Sessions:</span>
          <span className="summary-value">{metrics.offlineSessions || 0}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Weekly Growth:</span>
          <span className="summary-value">{formatTrend(metrics.weeklyGrowth)}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Monthly Bookings:</span>
          <span className="summary-value">{metrics.monthlyBookings || 0}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">User Engagement:</span>
          <span className="summary-value">{metrics.userEngagement || 0}%</span>
        </div>
      </div>
      
      <style>{`
        .dashboard-metrics {
          margin-bottom: 20px;
        }
        
        .metrics-header {
          margin-bottom: 20px;
          text-align: center;
        }
        
        .metrics-header h3 {
          margin: 0 0 8px 0;
          color: #333;
          font-size: 1.5rem;
          font-weight: 600;
        }
        
        .metrics-header p {
          margin: 0;
          color: #666;
          font-size: 14px;
        }
        
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
          margin-bottom: 25px;
        }
        
        .metric-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          border-top: 4px solid transparent;
          transition: all 0.2s ease;
          position: relative;
        }
        
        .metric-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }
        
        .loading-card {
          pointer-events: none;
        }
        
        .metric-header {
          display: flex;
          align-items: center;
          margin-bottom: 15px;
          gap: 12px;
        }
        
        .metric-icon {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          flex-shrink: 0;
        }
        
        .metric-title {
          font-size: 14px;
          font-weight: 600;
          color: #333;
          line-height: 1.2;
        }
        
        .metric-content {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .metric-value-container {
          display: flex;
          align-items: baseline;
          gap: 12px;
        }
        
        .metric-value {
          font-size: 2rem;
          font-weight: 700;
          color: #333;
          line-height: 1;
        }
        
        .trend-indicator {
          font-size: 12px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 2px;
        }
        
        .metric-description {
          font-size: 12px;
          color: #666;
          line-height: 1.3;
        }
        
        .metrics-summary {
          display: flex;
          justify-content: space-around;
          background: white;
          padding: 20px;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          flex-wrap: wrap;
          gap: 15px;
        }
        
        .summary-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          gap: 4px;
          min-width: 120px;
        }
        
        .summary-label {
          font-size: 12px;
          color: #666;
          font-weight: 500;
        }
        
        .summary-value {
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }
        
        /* Loading states */
        .loading-placeholder {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .loading-icon,
        .loading-text,
        .loading-value {
          background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
          background-size: 200% 100%;
          animation: loading 1.5s infinite;
          border-radius: 4px;
        }
        
        .loading-icon {
          width: 40px;
          height: 40px;
          border-radius: 10px;
        }
        
        .loading-text {
          height: 16px;
          width: 60%;
        }
        
        .loading-value {
          height: 24px;
          width: 80%;
        }
        
        @keyframes loading {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
          .metrics-grid {
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
          }
          
          .metric-card {
            padding: 15px;
          }
          
          .metric-value {
            font-size: 1.5rem;
          }
          
          .metrics-summary {
            padding: 15px;
            flex-direction: column;
            align-items: center;
          }
          
          .summary-item {
            flex-direction: row;
            justify-content: space-between;
            width: 100%;
            max-width: 200px;
          }
        }
        
        @media (max-width: 480px) {
          .metrics-grid {
            grid-template-columns: 1fr;
          }
          
          .metric-header {
            gap: 8px;
          }
          
          .metric-icon {
            width: 32px;
            height: 32px;
            font-size: 16px;
          }
          
          .metric-title {
            font-size: 13px;
          }
          
          .metric-value {
            font-size: 1.25rem;
          }
        }
      `}</style>
    </div>
  );
};

export default DashboardMetrics;