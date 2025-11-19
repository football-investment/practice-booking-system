/**
 * Coupling Enforcer Health Dashboard
 *
 * P2 Sprint - Observability & Monitoring
 *
 * Displays real-time Progress-License consistency monitoring with:
 * - Color-coded status badge (green/yellow/red)
 * - Consistency rate gauge
 * - Violations table
 * - Auto-refresh every 30 seconds
 */

import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../../services/apiService';
import './HealthDashboard.css';

const HealthDashboard = () => {
  const [healthStatus, setHealthStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [isManualChecking, setIsManualChecking] = useState(false);

  // Fetch health data
  const fetchHealthData = useCallback(async () => {
    try {
      setError(null);

      // Fetch status and metrics in parallel
      const [statusResponse, metricsResponse, violationsResponse] = await Promise.all([
        apiService.getHealthStatus(),
        apiService.getHealthMetrics(),
        apiService.getHealthViolations()
      ]);

      setHealthStatus(statusResponse);
      setMetrics(metricsResponse);
      setViolations(violationsResponse || []);
      setLastRefresh(new Date());

    } catch (err) {
      console.error('Failed to load health data:', err);
      setError(err.message || 'Failed to load health monitoring data');
    } finally {
      setLoading(false);
    }
  }, []);

  // Manual health check trigger
  const triggerManualCheck = async () => {
    setIsManualChecking(true);
    try {
      const result = await apiService.triggerHealthCheck();

      // Refresh data after manual check
      await fetchHealthData();

      console.log('Manual health check completed:', result);
    } catch (err) {
      console.error('Manual health check failed:', err);
      setError('Manual health check failed: ' + err.message);
    } finally {
      setIsManualChecking(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchHealthData();
  }, [fetchHealthData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchHealthData();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [fetchHealthData]);

  if (loading && !healthStatus) {
    return (
      <div className="health-dashboard-loading">
        <div className="spinner"></div>
        <p>Loading health monitoring data...</p>
      </div>
    );
  }

  return (
    <div className="health-dashboard">
      {/* Header */}
      <div className="health-dashboard-header">
        <div>
          <h1>🏥 Progress-License Health Monitor</h1>
          <p className="subtitle">Real-time consistency monitoring for GānCuju™© system</p>
        </div>
        <div className="header-actions">
          <button
            onClick={triggerManualCheck}
            disabled={isManualChecking}
            className="btn-manual-check"
          >
            {isManualChecking ? '⏳ Checking...' : '🔍 Run Check Now'}
          </button>
          {lastRefresh && (
            <span className="last-refresh">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="health-error-banner">
          ⚠️ {error}
        </div>
      )}

      {/* Status Overview */}
      <div className="health-status-overview">
        <HealthStatusBadge status={healthStatus?.status} />
        <ConsistencyRateGauge
          rate={healthStatus?.consistency_rate || metrics?.consistency_rate}
          status={healthStatus?.status}
        />
        <MetricsCard metrics={metrics} />
      </div>

      {/* Violations Section */}
      {violations && violations.length > 0 && (
        <div className="violations-section">
          <h2>⚠️ Active Violations ({violations.length})</h2>
          <ViolationsTable violations={violations} />
        </div>
      )}

      {violations && violations.length === 0 && (
        <div className="no-violations-banner">
          <div className="success-icon">✅</div>
          <div>
            <h3>System Healthy</h3>
            <p>No consistency violations detected. All Progress-License records are in sync.</p>
          </div>
        </div>
      )}

      {/* System Info */}
      <div className="system-info">
        <h3>📊 Monitoring Info</h3>
        <ul>
          <li><strong>Total users monitored:</strong> {metrics?.total_users_monitored || 0}</li>
          <li><strong>Last scheduled check:</strong> {healthStatus?.last_check ? new Date(healthStatus.last_check).toLocaleString() : 'N/A'}</li>
          <li><strong>Auto-refresh:</strong> Every 30 seconds</li>
          <li><strong>Backend checks:</strong> Every 5 minutes</li>
        </ul>
      </div>
    </div>
  );
};

// Health Status Badge Component
const HealthStatusBadge = ({ status }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'healthy':
        return {
          icon: '🟢',
          label: 'HEALTHY',
          className: 'status-healthy',
          description: 'System operating normally (≥99% consistency)'
        };
      case 'degraded':
        return {
          icon: '🟡',
          label: 'DEGRADED',
          className: 'status-degraded',
          description: 'Minor issues detected (95-99% consistency)'
        };
      case 'critical':
        return {
          icon: '🔴',
          label: 'CRITICAL',
          className: 'status-critical',
          description: 'Immediate attention required (<95% consistency)'
        };
      default:
        return {
          icon: '⚪',
          label: 'UNKNOWN',
          className: 'status-unknown',
          description: 'Status unavailable'
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={`health-status-badge ${config.className}`}>
      <div className="badge-icon">{config.icon}</div>
      <div className="badge-content">
        <h3>System Status</h3>
        <div className="status-label">{config.label}</div>
        <p className="status-description">{config.description}</p>
      </div>
    </div>
  );
};

// Consistency Rate Gauge Component
const ConsistencyRateGauge = ({ rate, status }) => {
  const displayRate = rate !== null && rate !== undefined ? rate.toFixed(2) : 'N/A';

  const getGaugeColor = () => {
    if (rate >= 99) return '#10b981'; // green
    if (rate >= 95) return '#f59e0b'; // yellow/orange
    return '#ef4444'; // red
  };

  const gaugeRotation = rate !== null ? (rate / 100) * 180 : 0;

  return (
    <div className="consistency-rate-gauge">
      <h3>Consistency Rate</h3>
      <div className="gauge-container">
        <svg viewBox="0 0 200 120" className="gauge-svg">
          {/* Background arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="20"
            strokeLinecap="round"
          />
          {/* Colored arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={getGaugeColor()}
            strokeWidth="20"
            strokeLinecap="round"
            strokeDasharray={`${(gaugeRotation / 180) * 251.2} 251.2`}
            style={{ transition: 'stroke-dasharray 0.5s ease' }}
          />
          {/* Needle */}
          <line
            x1="100"
            y1="100"
            x2="100"
            y2="30"
            stroke="#374151"
            strokeWidth="3"
            strokeLinecap="round"
            transform={`rotate(${gaugeRotation - 90} 100 100)`}
            style={{ transition: 'transform 0.5s ease' }}
          />
          {/* Center dot */}
          <circle cx="100" cy="100" r="6" fill="#374151" />
        </svg>
        <div className="gauge-value">
          <span className="rate-number">{displayRate}</span>
          <span className="rate-percent">%</span>
        </div>
      </div>
      <div className="gauge-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#10b981' }}></span>
          <span>≥99% Healthy</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#f59e0b' }}></span>
          <span>95-99% Degraded</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#ef4444' }}></span>
          <span>&lt;95% Critical</span>
        </div>
      </div>
    </div>
  );
};

// Metrics Card Component
const MetricsCard = ({ metrics }) => {
  if (!metrics) {
    return (
      <div className="metrics-card">
        <h3>📈 Metrics</h3>
        <p>Loading metrics...</p>
      </div>
    );
  }

  return (
    <div className="metrics-card">
      <h3>📈 System Metrics</h3>
      <div className="metrics-grid">
        <div className="metric-item">
          <div className="metric-value">{metrics.total_users_monitored || 0}</div>
          <div className="metric-label">Users Monitored</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics.violations_count || 0}</div>
          <div className="metric-label">Active Violations</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">
            {metrics.consistency_rate !== null ? `${metrics.consistency_rate.toFixed(2)}%` : 'N/A'}
          </div>
          <div className="metric-label">Consistency Rate</div>
        </div>
        <div className="metric-item">
          <div className={`metric-value status-${metrics.status}`}>
            {metrics.requires_attention ? 'YES' : 'NO'}
          </div>
          <div className="metric-label">Requires Attention</div>
        </div>
      </div>
    </div>
  );
};

// Violations Table Component
const ViolationsTable = ({ violations }) => {
  return (
    <div className="violations-table-container">
      <table className="violations-table">
        <thead>
          <tr>
            <th>User ID</th>
            <th>Specialization</th>
            <th>Progress Level</th>
            <th>License Level</th>
            <th>Discrepancy</th>
            <th>Recommended Action</th>
          </tr>
        </thead>
        <tbody>
          {violations.map((violation, index) => {
            const discrepancy = violation.progress_level - violation.license_level;
            const discrepancyClass = discrepancy > 0 ? 'discrepancy-positive' : 'discrepancy-negative';

            return (
              <tr key={`${violation.user_id}-${violation.specialization}-${index}`}>
                <td className="user-id">{violation.user_id}</td>
                <td className="specialization">{violation.specialization}</td>
                <td className="level">{violation.progress_level}</td>
                <td className="level">{violation.license_level}</td>
                <td className={`discrepancy ${discrepancyClass}`}>
                  {discrepancy > 0 ? `+${discrepancy}` : discrepancy}
                </td>
                <td className="action">
                  <span className="action-badge">
                    {violation.recommended_action === 'sync_required' ? '🔄 Sync Required' : violation.recommended_action}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default HealthDashboard;
