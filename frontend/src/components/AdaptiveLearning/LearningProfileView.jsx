import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './LearningProfileView.css';

const LearningProfileView = () => {
  const [licenses, setLicenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadLicenses();
  }, []);

  const loadLicenses = async () => {
    try {
      setLoading(true);
      const response = await apiService.get('/licenses/my-licenses');
      setLicenses(response || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load licenses:', err);
      setError('Failed to load your learning profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getSpecializationTitle = (type) => {
    const titles = {
      GANCUJU_PLAYER: 'GānCuju Player',
      LFA_FOOTBALL_PLAYER: 'LFA Football Player',
      LFA_COACH: 'LFA Coach',
      INTERNSHIP: 'Internship Program'
    };
    return titles[type] || type;
  };

  const getSpecializationIcon = (type) => {
    const icons = {
      GANCUJU_PLAYER: '⚽',
      LFA_FOOTBALL_PLAYER: '🏃',
      LFA_COACH: '👨‍🏫',
      INTERNSHIP: '💼'
    };
    return icons[type] || '🎓';
  };

  const calculateXPProgress = (currentXP, xpRequired) => {
    if (!xpRequired || xpRequired === 0) return 0;
    return Math.min(100, Math.round((currentXP / xpRequired) * 100));
  };

  if (loading) {
    return (
      <div className="learning-profile-container">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading your learning profile...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="learning-profile-container">
        <div className="error-state">
          <span className="error-icon">⚠️</span>
          <p>{error}</p>
          <button onClick={loadLicenses} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (licenses.length === 0) {
    return (
      <div className="learning-profile-container">
        <div className="empty-state">
          <h2>🎓 Your Learning Profile</h2>
          <p>You don't have any active specializations yet.</p>
          <p>Start a specialization to begin your learning journey!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="learning-profile-container">
      <div className="profile-header">
        <h1>🎓 Your Learning Profile</h1>
        <p className="subtitle">Track your progress across all specializations</p>
      </div>

      <div className="licenses-grid">
        {licenses.map((license) => (
          <div key={license.id} className="license-card">
            <div className="license-header">
              <span className="license-icon">
                {getSpecializationIcon(license.specialization_type)}
              </span>
              <div className="license-title">
                <h3>{getSpecializationTitle(license.specialization_type)}</h3>
                <span className="level-badge">Level {license.level}</span>
              </div>
            </div>

            <div className="license-details">
              <div className="detail-row">
                <span className="label">License Number:</span>
                <span className="value">{license.license_number || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <span className="label">Issue Date:</span>
                <span className="value">
                  {license.issue_date
                    ? new Date(license.issue_date).toLocaleDateString('en-US')
                    : 'N/A'}
                </span>
              </div>
              {license.expiry_date && (
                <div className="detail-row">
                  <span className="label">Expiry Date:</span>
                  <span className="value">
                    {new Date(license.expiry_date).toLocaleDateString('en-US')}
                  </span>
                </div>
              )}
              <div className="detail-row">
                <span className="label">Status:</span>
                <span className={`status-badge ${license.status?.toLowerCase()}`}>
                  {license.status || 'ACTIVE'}
                </span>
              </div>
            </div>

            {license.current_xp !== undefined && license.xp_required_for_next_level !== undefined && (
              <div className="xp-progress-section">
                <div className="xp-header">
                  <span className="xp-label">Progress to Next Level</span>
                  <span className="xp-value">
                    {license.current_xp} / {license.xp_required_for_next_level} XP
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${calculateXPProgress(license.current_xp, license.xp_required_for_next_level)}%`
                    }}
                  ></div>
                </div>
                <div className="progress-percentage">
                  {calculateXPProgress(license.current_xp, license.xp_required_for_next_level)}% Complete
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="profile-footer">
        <button onClick={loadLicenses} className="refresh-button">
          🔄 Refresh
        </button>
      </div>
    </div>
  );
};

export default LearningProfileView;
