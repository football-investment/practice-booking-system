import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const AttendanceChart = ({ data, loading, dateRange }) => {
  // Format data for chart
  const formatData = (rawData) => {
    if (!rawData || !Array.isArray(rawData)) return [];
    
    return rawData.map(item => ({
      ...item,
      date: new Date(item.date).toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric' 
      }),
      attendance: item.attendance || 0,
      sessions: item.sessions || 0
    }));
  };

  const chartData = formatData(data);
  
  const customTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{`Date: ${label}`}</p>
          {payload.map((entry, index) => (
            <p key={index} className="tooltip-value" style={{ color: entry.color }}>
              {`${entry.dataKey === 'attendance' ? 'Attendance' : 'Sessions'}: ${entry.value}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const getTitle = () => {
    switch (dateRange) {
      case 'today': return 'Today\'s Attendance';
      case 'this_week': return 'This Week\'s Attendance';
      case 'this_month': return 'This Month\'s Attendance';
      case 'this_semester': return 'Semester Attendance Trends';
      default: return 'Session Attendance Over Time';
    }
  };

  const calculateStats = () => {
    if (!chartData.length) return { avg: 0, peak: 0, total: 0 };
    
    const total = chartData.reduce((sum, item) => sum + item.attendance, 0);
    const avg = Math.round(total / chartData.length);
    const peak = Math.max(...chartData.map(item => item.attendance));
    
    return { avg, peak, total };
  };

  const stats = calculateStats();

  if (loading) {
    return (
      <div className="chart-container attendance-chart loading">
        <div className="chart-header">
          <h3>{getTitle()}</h3>
          <p>Loading attendance data...</p>
        </div>
        <div className="chart-loading">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="chart-container attendance-chart">
        <div className="chart-header">
          <h3>{getTitle()}</h3>
          <p>Track session attendance patterns over time</p>
        </div>
        <div className="no-data">
          <div className="no-data-icon">📊</div>
          <p>No attendance data available</p>
          <small>Attendance data will appear here once sessions are completed</small>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-container attendance-chart">
      <div className="chart-header">
        <h3>{getTitle()}</h3>
        <p>Track session attendance patterns over time</p>
      </div>
      
      {/* Quick Stats */}
      <div className="chart-stats">
        <div className="stat-item">
          <span className="stat-value">{stats.avg}</span>
          <span className="stat-label">Avg Daily</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{stats.peak}</span>
          <span className="stat-label">Peak Day</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{stats.total}</span>
          <span className="stat-label">Total</span>
        </div>
      </div>

      <div className="chart-content">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 20,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="date" 
              stroke="#666"
              fontSize={12}
              tick={{ fill: '#666' }}
            />
            <YAxis 
              stroke="#666"
              fontSize={12}
              tick={{ fill: '#666' }}
              label={{ value: 'Attendees', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip content={customTooltip} />
            <Legend />
            
            <Line
              type="monotone"
              dataKey="attendance"
              stroke="#2196f3"
              strokeWidth={3}
              dot={{ fill: '#2196f3', strokeWidth: 2, r: 5 }}
              activeDot={{ r: 7, stroke: '#2196f3', strokeWidth: 2 }}
              name="Attendance"
            />
            
            <Line
              type="monotone"
              dataKey="sessions"
              stroke="#4caf50"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ fill: '#4caf50', strokeWidth: 2, r: 4 }}
              name="Sessions"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <style>{`
        .attendance-chart {
          position: relative;
        }
        
        .chart-stats {
          display: flex;
          justify-content: space-around;
          margin: 15px 0;
          padding: 12px;
          background: #f8f9fa;
          border-radius: 8px;
          border: 1px solid #e9ecef;
        }
        
        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          gap: 4px;
        }
        
        .stat-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: #2196f3;
        }
        
        .stat-label {
          font-size: 11px;
          color: #666;
          text-transform: uppercase;
          font-weight: 500;
          letter-spacing: 0.5px;
        }
        
        .chart-content {
          height: 280px;
          margin-top: 10px;
        }
        
        .chart-tooltip {
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 12px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .tooltip-label {
          font-weight: 600;
          color: #333;
          margin: 0 0 8px 0;
          font-size: 13px;
        }
        
        .tooltip-value {
          margin: 4px 0;
          font-size: 12px;
          font-weight: 500;
        }
        
        .chart-loading {
          height: 280px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .loading-spinner {
          width: 32px;
          height: 32px;
          border: 3px solid #f3f3f3;
          border-top: 3px solid #2196f3;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        .no-data {
          height: 280px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          color: #666;
          gap: 8px;
        }
        
        .no-data-icon {
          font-size: 3rem;
          opacity: 0.3;
          margin-bottom: 8px;
        }
        
        .no-data p {
          margin: 0;
          font-size: 16px;
          font-weight: 500;
        }
        
        .no-data small {
          font-size: 12px;
          opacity: 0.7;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
          .chart-stats {
            flex-wrap: wrap;
            gap: 12px;
          }
          
          .stat-item {
            flex: 1;
            min-width: 80px;
          }
          
          .chart-content {
            height: 250px;
          }
        }
        
        @media (max-width: 480px) {
          .chart-content {
            height: 220px;
          }
          
          .stat-value {
            font-size: 1rem;
          }
          
          .stat-label {
            font-size: 10px;
          }
        }
      `}</style>
    </div>
  );
};

export default AttendanceChart;