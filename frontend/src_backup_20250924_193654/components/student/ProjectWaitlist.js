import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './ProjectWaitlist.css';

const ProjectWaitlist = ({ projectId, isVisible, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [waitlistData, setWaitlistData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isVisible && projectId) {
      loadWaitlistData();
    }
  }, [isVisible, projectId]);

  const loadWaitlistData = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiService.request(`/api/v1/projects/${projectId}/waitlist`);
      setWaitlistData(data);
    } catch (err) {
      console.error('Failed to load waitlist:', err);
      setError('Nem sikerült betölteni a várólista adatokat');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'confirmed': return '🎉';
      case 'eligible': return '✅';
      case 'waiting': return '⏳';
      default: return '❓';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'confirmed': return 'Megerősítve';
      case 'eligible': return 'Jogosult';
      case 'waiting': return 'Várólista';
      default: return 'Ismeretlen';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed': return '#10b981';
      case 'eligible': return '#3b82f6';
      case 'waiting': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  const getPositionEmoji = (position) => {
    if (position === 1) return '🥇';
    if (position === 2) return '🥈';
    if (position === 3) return '🥉';
    return `#${position}`;
  };

  if (!isVisible) return null;

  return (
    <div className="waitlist-overlay" onClick={onClose}>
      <div className="waitlist-modal" onClick={(e) => e.stopPropagation()}>
        <div className="waitlist-header">
          <h2>📋 Projekt Várólista</h2>
          <button onClick={onClose} className="close-btn">✕</button>
        </div>

        <div className="waitlist-content">
          {loading ? (
            <div className="loading-section">
              <div className="loading-spinner"></div>
              <p>Várólista betöltése...</p>
            </div>
          ) : error ? (
            <div className="error-section">
              <p>⚠️ {error}</p>
              <button onClick={loadWaitlistData} className="retry-btn">
                🔄 Újrapróbálás
              </button>
            </div>
          ) : waitlistData ? (
            <>
              <div className="waitlist-summary">
                <h3>{waitlistData.project_title}</h3>
                <div className="summary-stats">
                  <div className="stat-item">
                    <span className="stat-number">{waitlistData.confirmed_count}</span>
                    <span className="stat-label">Megerősített</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-number">{waitlistData.max_participants}</span>
                    <span className="stat-label">Max hely</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-number">{waitlistData.total_applicants}</span>
                    <span className="stat-label">Összes jelentkező</span>
                  </div>
                </div>
              </div>

              <div className="waitlist-legend">
                <div className="legend-item">
                  <span style={{ color: getStatusColor('confirmed') }}>🎉 Megerősítve</span>
                </div>
                <div className="legend-item">
                  <span style={{ color: getStatusColor('eligible') }}>✅ Jogosult</span>
                </div>
                <div className="legend-item">
                  <span style={{ color: getStatusColor('waiting') }}>⏳ Várólista</span>
                </div>
              </div>

              <div className="waitlist-table">
                <div className="table-header">
                  <div className="col-position">Helyezés</div>
                  <div className="col-name">Becenév</div>
                  <div className="col-score">Pontszám</div>
                  <div className="col-status">Státusz</div>
                </div>

                <div className="table-body">
                  {waitlistData.waitlist.map((entry, index) => (
                    <div 
                      key={index}
                      className={`table-row ${entry.is_current_user ? 'current-user' : ''}`}
                    >
                      <div className="col-position">
                        <span className="position-badge">
                          {getPositionEmoji(entry.position)}
                        </span>
                      </div>
                      <div className="col-name">
                        <span className={`display-name ${entry.is_current_user ? 'highlight' : ''}`}>
                          {entry.display_name}
                          {entry.is_current_user && ' (Te)'}
                        </span>
                      </div>
                      <div className="col-score">
                        <span className="score-value">
                          {entry.score_percentage}%
                        </span>
                      </div>
                      <div className="col-status">
                        <span 
                          className="status-badge"
                          style={{ 
                            backgroundColor: getStatusColor(entry.status),
                            color: 'white'
                          }}
                        >
                          {getStatusIcon(entry.status)} {getStatusText(entry.status)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {waitlistData.user_position && (
                <div className="user-position-summary">
                  <div className="position-highlight">
                    <span className="position-text">
                      A te helyezésed: <strong>#{waitlistData.user_position}</strong> 
                      / {waitlistData.total_applicants}
                    </span>
                  </div>
                </div>
              )}

              <div className="waitlist-info">
                <div className="info-card">
                  <h4>🔒 Adatvédelem</h4>
                  <p>
                    A listában csak becenéveket láthatósz a személyes adatok védelme érdekében. 
                    Minden diák saját maga választotta meg a becenevet a regisztráció során.
                  </p>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <p>Nincsenek várólista adatok.</p>
            </div>
          )}
        </div>

        <div className="waitlist-footer">
          <button onClick={onClose} className="close-button">
            Bezárás
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProjectWaitlist;