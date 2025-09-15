import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

const BookingTrendsChart = ({ data, loading, dateRange }) => {
  // Format data for chart
  const formatData = (rawData) => {
    if (!rawData || !Array.isArray(rawData)) return [];
    
    return rawData.map(item => ({
      ...item,
      total: (item.online || 0) + (item.offline || 0),
      online: item.online || 0,
      offline: item.offline || 0
    }));
  };

  const chartData = formatData(data);
  
  const customTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const total = payload.reduce((sum, entry) => sum + (entry.value || 0), 0);
      
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{`${label}`}</p>
          <p className="tooltip-total">{`Total Bookings: ${total}`}</p>
          {payload.map((entry, index) => (
            <p key={index} className="tooltip-value" style={{ color: entry.color }}>
              {`${entry.dataKey === 'online' ? 'Online' : 'Offline'}: ${entry.value}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const getTitle = () => {
    switch (dateRange) {
      case 'today': return 'Today\'s Bookings';
      case 'this_week': return 'This Week\'s Booking Trends';
      case 'this_month': return 'Monthly Booking Trends';
      case 'this_semester': return 'Semester Booking Trends';
      default: return 'Booking Trends Over Time';
    }
  };

  const calculateStats = () => {
    if (!chartData.length) return { totalBookings: 0, onlinePercent: 0, offlinePercent: 0, growth: 0 };
    
    const totalOnline = chartData.reduce((sum, item) => sum + item.online, 0);
    const totalOffline = chartData.reduce((sum, item) => sum + item.offline, 0);
    const totalBookings = totalOnline + totalOffline;
    
    const onlinePercent = totalBookings ? Math.round((totalOnline / totalBookings) * 100) : 0;
    const offlinePercent = totalBookings ? Math.round((totalOffline / totalBookings) * 100) : 0;
    
    // Calculate growth (compare last period to previous)
    const growth = chartData.length >= 2 ? 
      Math.round(((chartData[chartData.length - 1].total - chartData[chartData.length - 2].total) / 
      chartData[chartData.length - 2].total) * 100) : 0;
    
    return { totalBookings, onlinePercent, offlinePercent, growth };
  };

  const stats = calculateStats();

  if (loading) {
    return (
      <div className="chart-container booking-trends-chart loading">
        <div className="chart-header">
          <h3>{getTitle()}</h3>
          <p>Loading booking trends...</p>
        </div>
        <div className="chart-loading">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="chart-container booking-trends-chart">
        <div className="chart-header">
          <h3>{getTitle()}</h3>
          <p>Monitor booking patterns and growth trends</p>
        </div>
        <div className="no-data">
          <div className="no-data-icon">📈</div>
          <p>No booking data available</p>
          <small>Booking trends will appear here as users make reservations</small>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-container booking-trends-chart">
      <div className="chart-header">
        <h3>{getTitle()}</h3>
        <p>Monitor booking patterns and growth trends</p>
      </div>
      
      {/* Quick Stats */}
      <div className="chart-stats">
        <div className="stat-item">
          <span className="stat-value">{stats.totalBookings}</span>
          <span className="stat-label">Total</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{stats.onlinePercent}%</span>
          <span className="stat-label">Online</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{stats.offlinePercent}%</span>
          <span className="stat-label">Offline</span>
        </div>
        <div className="stat-item">
          <span className={`stat-value ${stats.growth >= 0 ? 'positive' : 'negative'}`}>
            {stats.growth > 0 ? '+' : ''}{stats.growth}%
          </span>
          <span className="stat-label">Growth</span>
        </div>
      </div>

      <div className="chart-content">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 20,
            }}
          >
            <defs>
              <linearGradient id="colorOnline" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2196f3" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#2196f3" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="colorOffline" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4caf50" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#4caf50" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="week" 
              stroke="#666"
              fontSize={12}
              tick={{ fill: '#666' }}
            />
            <YAxis 
              stroke="#666"
              fontSize={12}
              tick={{ fill: '#666' }}
              label={{ value: 'Bookings', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip content={customTooltip} />
            <Legend />
            
            <Area
              type="monotone"
              dataKey="online"
              stackId="1"
              stroke="#2196f3"
              strokeWidth={2}
              fill="url(#colorOnline)"
              name="Online Bookings"
            />
            <Area
              type="monotone"
              dataKey="offline"
              stackId="1"
              stroke="#4caf50"
              strokeWidth={2}
              fill="url(#colorOffline)"
              name="Offline Bookings"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Trend Analysis */}
      <div className="trend-analysis">
        <div className="trend-item">
          <div className="trend-header">
            <span className="trend-icon">🔵</span>
            <span className="trend-title">Online Sessions</span>
          </div>
          <div className="trend-details">
            <span className="trend-percentage">{stats.onlinePercent}%</span>
            <span className="trend-description">of total bookings</span>
          </div>
        </div>
        
        <div className="trend-item">
          <div className="trend-header">
            <span className="trend-icon">🟢</span>
            <span className="trend-title">Offline Sessions</span>
          </div>
          <div className="trend-details">
            <span className="trend-percentage">{stats.offlinePercent}%</span>
            <span className="trend-description">of total bookings</span>
          </div>
        </div>
      </div>
      
      <style>{`
        .booking-trends-chart {
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
          color: #333;
        }
        
        .stat-value.positive {
          color: #4caf50;
        }
        
        .stat-value.negative {
          color: #f44336;
        }
        
        .stat-label {
          font-size: 11px;
          color: #666;
          text-transform: uppercase;
          font-weight: 500;
          letter-spacing: 0.5px;
        }
        
        .chart-content {
          height: 240px;
          margin: 10px 0;
        }
        
        .trend-analysis {
          display: flex;
          gap: 20px;
          margin-top: 15px;
          padding: 12px;
          background: #fafbfc;
          border-radius: 8px;
          border: 1px solid #f0f0f0;
        }
        
        .trend-item {
          flex: 1;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .trend-header {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .trend-icon {
          font-size: 16px;
        }
        
        .trend-title {
          font-size: 13px;
          font-weight: 500;
          color: #333;
        }
        
        .trend-details {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          text-align: right;
        }
        
        .trend-percentage {
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }
        
        .trend-description {
          font-size: 11px;
          color: #666;
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
          margin: 0 0 4px 0;
          font-size: 13px;
        }
        
        .tooltip-total {
          font-weight: 600;
          color: #2196f3;
          margin: 0 0 8px 0;
          font-size: 12px;
          border-bottom: 1px solid #eee;
          padding-bottom: 4px;
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
            min-width: 70px;
          }
          
          .trend-analysis {
            flex-direction: column;
            gap: 12px;
          }
          
          .chart-content {
            height: 220px;
          }
        }
        
        @media (max-width: 480px) {
          .chart-content {
            height: 200px;
          }
          
          .stat-value {
            font-size: 1rem;
          }
          
          .stat-label {
            font-size: 10px;
          }
          
          .trend-item {
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 8px;
          }
          
          .trend-details {
            align-items: center;
          }
        }
      `}</style>
    </div>
  );
};

export default BookingTrendsChart;