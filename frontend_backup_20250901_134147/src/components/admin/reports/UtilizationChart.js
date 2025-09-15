import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend
} from 'recharts';

const UtilizationChart = ({ data, loading }) => {
  // Default colors for utilization segments
  const COLORS = {
    'Fully Booked': '#dc3545',
    'Partially Booked': '#ffc107', 
    'Available': '#28a745',
    'fully_booked': '#dc3545',
    'partially_booked': '#ffc107',
    'available': '#28a745'
  };

  // Format data for chart
  const formatData = (rawData) => {
    if (!rawData || !Array.isArray(rawData)) return [];
    
    return rawData.map(item => ({
      name: item.name || item.label,
      value: item.value || item.count || 0,
      color: item.color || COLORS[item.name] || COLORS[item.label] || '#666'
    }));
  };

  const chartData = formatData(data);
  
  const customTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const percentage = chartData.length > 0 ? 
        Math.round((data.value / chartData.reduce((sum, item) => sum + item.value, 0)) * 100) : 0;
        
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{data.payload.name}</p>
          <p className="tooltip-value" style={{ color: data.payload.color }}>
            Sessions: {data.value}
          </p>
          <p className="tooltip-percentage">
            {percentage}% of total
          </p>
        </div>
      );
    }
    return null;
  };

  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    if (percent < 0.05) return null; // Don't show labels for segments < 5%
    
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize={12}
        fontWeight="600"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const calculateStats = () => {
    if (!chartData.length) return { total: 0, utilizationRate: 0, mostCommon: 'N/A' };
    
    const total = chartData.reduce((sum, item) => sum + item.value, 0);
    
    const bookedSessions = chartData.find(item => 
      item.name && item.name.toLowerCase && item.name.toLowerCase().includes('fully') || 
      (item.name && item.name.toLowerCase && item.name.toLowerCase().includes('full'))
    )?.value || 0;
    
    const partiallyBooked = chartData.find(item => 
      item.name && item.name.toLowerCase && item.name.toLowerCase().includes('partial')
    )?.value || 0;
    
    const utilizationRate = total > 0 ? Math.round(((bookedSessions + partiallyBooked * 0.5) / total) * 100) : 0;
    
    const mostCommon = chartData.reduce((max, item) => {
      if (!max || !max.value || (item.value > max.value)) {
        return item && item.name ? item : { name: 'N/A', value: 0 };
      }
      return max;
    }, chartData[0] || { name: 'N/A', value: 0 });

    return { 
      total, 
      utilizationRate, 
      mostCommon: mostCommon.name || 'N/A' 
    };
  };

  const stats = calculateStats();

  if (loading) {
    return (
      <div className="chart-container utilization-chart loading">
        <div className="chart-header">
          <h3>Session Utilization</h3>
          <p>Loading utilization data...</p>
        </div>
        <div className="chart-loading">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="chart-container utilization-chart">
        <div className="chart-header">
          <h3>Session Utilization</h3>
          <p>Track how efficiently sessions are being used</p>
        </div>
        <div className="no-data">
          <div className="no-data-icon">🥧</div>
          <p>No utilization data available</p>
          <small>Session utilization data will appear here once bookings are made</small>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-container utilization-chart">
      <div className="chart-header">
        <h3>Session Utilization</h3>
        <p>Track how efficiently sessions are being used</p>
      </div>
      
      {/* Quick Stats */}
      <div className="chart-stats">
        <div className="stat-item">
          <span className="stat-value">{stats.total}</span>
          <span className="stat-label">Total Sessions</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{stats.utilizationRate}%</span>
          <span className="stat-label">Utilization Rate</span>
        </div>
      </div>

      <div className="chart-content">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomizedLabel}
              outerRadius={80}
              innerRadius={30}
              fill="#8884d8"
              dataKey="value"
              paddingAngle={2}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color}
                  stroke={entry.color}
                  strokeWidth={2}
                />
              ))}
            </Pie>
            <Tooltip content={customTooltip} />
            <Legend 
              verticalAlign="bottom" 
              height={36}
              iconType="circle"
              formatter={(value, entry) => (
                <span style={{ color: entry.color, fontWeight: '500' }}>
                  {value}
                </span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed Breakdown */}
      <div className="utilization-breakdown">
        <h4>Detailed Breakdown</h4>
        <div className="breakdown-list">
          {chartData.map((item, index) => (
            <div key={index} className="breakdown-item">
              <div className="breakdown-indicator">
                <div 
                  className="color-dot" 
                  style={{ backgroundColor: item.color }}
                ></div>
                <span className="breakdown-label">{item.name}</span>
              </div>
              <div className="breakdown-values">
                <span className="breakdown-count">{item.value}</span>
                <span className="breakdown-percentage">
                  ({Math.round((item.value / stats.total) * 100)}%)
                </span>
              </div>
            </div>
          ))}
        </div>
        
        <div className="utilization-insights">
          <div className="insight-item">
            <span className="insight-label">Most Common Status:</span>
            <span className="insight-value">{stats.mostCommon}</span>
          </div>
          <div className="insight-item">
            <span className="insight-label">Overall Efficiency:</span>
            <span className={`insight-value ${stats.utilizationRate >= 75 ? 'good' : stats.utilizationRate >= 50 ? 'average' : 'low'}`}>
              {stats.utilizationRate >= 75 ? 'Excellent' : stats.utilizationRate >= 50 ? 'Good' : 'Needs Improvement'}
            </span>
          </div>
        </div>
      </div>
      
      <style>{`
        .utilization-chart {
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
        
        .stat-label {
          font-size: 11px;
          color: #666;
          text-transform: uppercase;
          font-weight: 500;
          letter-spacing: 0.5px;
        }
        
        .chart-content {
          height: 220px;
          margin: 10px 0;
        }
        
        .utilization-breakdown {
          margin-top: 15px;
          padding: 15px;
          background: #fafbfc;
          border-radius: 8px;
          border: 1px solid #f0f0f0;
        }
        
        .utilization-breakdown h4 {
          margin: 0 0 12px 0;
          color: #333;
          font-size: 14px;
          font-weight: 600;
        }
        
        .breakdown-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 15px;
        }
        
        .breakdown-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid #f0f0f0;
        }
        
        .breakdown-item:last-child {
          border-bottom: none;
        }
        
        .breakdown-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .color-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        
        .breakdown-label {
          font-size: 13px;
          font-weight: 500;
          color: #333;
        }
        
        .breakdown-values {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        
        .breakdown-count {
          font-size: 14px;
          font-weight: 600;
          color: #333;
        }
        
        .breakdown-percentage {
          font-size: 12px;
          color: #666;
        }
        
        .utilization-insights {
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding-top: 12px;
          border-top: 1px solid #f0f0f0;
        }
        
        .insight-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .insight-label {
          font-size: 12px;
          color: #666;
          font-weight: 500;
        }
        
        .insight-value {
          font-size: 12px;
          font-weight: 600;
          color: #333;
        }
        
        .insight-value.good {
          color: #4caf50;
        }
        
        .insight-value.average {
          color: #ff9800;
        }
        
        .insight-value.low {
          color: #f44336;
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
        
        .tooltip-value {
          margin: 4px 0;
          font-size: 12px;
          font-weight: 500;
        }
        
        .tooltip-percentage {
          margin: 4px 0;
          font-size: 12px;
          color: #666;
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
          .chart-content {
            height: 200px;
          }
          
          .breakdown-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 4px;
          }
          
          .breakdown-values {
            align-self: flex-end;
          }
          
          .utilization-insights {
            gap: 6px;
          }
          
          .insight-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 2px;
          }
        }
        
        @media (max-width: 480px) {
          .chart-content {
            height: 180px;
          }
          
          .stat-item {
            min-width: 80px;
          }
          
          .stat-value {
            font-size: 1rem;
          }
          
          .stat-label {
            font-size: 10px;
          }
          
          .utilization-breakdown {
            padding: 12px;
          }
        }
      `}</style>
    </div>
  );
};

export default UtilizationChart;