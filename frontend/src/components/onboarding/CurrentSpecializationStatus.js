import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './CurrentSpecializationStatus.css';

const CurrentSpecializationStatus = ({ onNext, hideNavigation = false }) => {
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchStatusData();
    }, []);

    const fetchStatusData = async () => {
        try {
            setLoading(true);

            // Get comprehensive dashboard data
            const dashboard = await apiService.get('/parallel-specializations/dashboard');

            // Also get available specializations for current user
            try {
                const available = await apiService.get('/parallel-specializations/available');
                dashboard.available_specializations = available;
            } catch (availError) {
                console.warn('Could not fetch available specializations:', availError);
                dashboard.available_specializations = [];
            }

            setDashboardData(dashboard);

        } catch (error) {
            console.error('Error fetching status data:', error);
            setError('Failed to load status data');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="status-loading">
                <div className="loading-spinner"></div>
                <p>Loading status data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="status-error">
                <p>{error}</p>
                <button onClick={fetchStatusData} className="retry-button">
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="current-specialization-status">
            <div className="status-header">
                <h2>📋 Current Status</h2>
                <p className="status-intro">
                    Here you can overview the current status of your specializations and development path.
                </p>
            </div>

            {/* User Info */}
            {dashboardData && (
                <div className="user-overview">
                    <div className="overview-card">
                        <h3>👤 User Information</h3>
                        <div className="info-grid">
                            <div className="info-item">
                                <span className="info-label">Name:</span>
                                <span className="info-value">{dashboardData.user?.name || 'N/A'}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Email:</span>
                                <span className="info-value">{dashboardData.user?.email || 'N/A'}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Current Semester:</span>
                                <span className="info-value semester-badge">{dashboardData.current_semester || 1}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Active Specializations */}
            {dashboardData && dashboardData.active_specializations && dashboardData.active_specializations.length > 0 && (
                <div className="active-specializations-section">
                    <h3>✅ Active Specializations</h3>
                    <div className="specializations-grid">
                        {dashboardData.active_specializations.map(spec => (
                            <div key={spec.specialization_type} className="specialization-status-card">
                                <div className="spec-header">
                                    <span className="spec-icon">
                                        {spec.current_level_metadata?.icon_emoji || '🎓'}
                                    </span>
                                    <div className="spec-title">
                                        <h4>{spec.current_level_metadata?.title || spec.specialization_type}</h4>
                                        <p className="spec-subtitle">{spec.current_level_metadata?.subtitle || 'Specialization'}</p>
                                    </div>
                                </div>
                                
                                <div className="spec-progress">
                                    {/* Enhanced Level Display */}
                                    <div className="enhanced-level-display">
                                        <div className="level-badge-container">
                                            <div className="current-level-badge">
                                                <span className="level-number">{spec.current_level}</span>
                                                <span className="level-text">LEVEL</span>
                                            </div>
                                            <div className="level-progress-info">
                                                <div className="level-status">
                                                    <span className="status-text">Current track status</span>
                                                    <span className="track-position">
                                                        {spec.current_level}/8 levels completed
                                                    </span>
                                                </div>
                                                <div className="achievement-info">
                                                    <span className="achievement-badge">
                                                        🏆 Max Achieved: Level {spec.max_achieved_level}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {/* Visual Progress Indicator */}
                                    <div className="visual-progress-container">
                                        <div className="progress-labels">
                                            <span className="progress-start">Beginner</span>
                                            <span className="progress-current">
                                                {spec.current_level < 3 ? 'Intermediate' : 
                                                 spec.current_level < 6 ? 'Advanced' : 'Expert'}
                                            </span>
                                            <span className="progress-end">Master</span>
                                        </div>
                                        <div className="progress-track">
                                            <div 
                                                className="progress-fill enhanced"
                                                style={{ width: `${(spec.current_level / 8) * 100}%` }}
                                            >
                                                <span className="progress-percentage">
                                                    {Math.round((spec.current_level / 8) * 100)}%
                                                </span>
                                            </div>
                                            <div className="progress-markers">
                                                {[1,2,3,4,5,6,7,8].map(level => (
                                                    <div 
                                                        key={level} 
                                                        className={`progress-marker ${spec.current_level >= level ? 'completed' : 'pending'}`}
                                                        title={`Level ${level}`}
                                                    >
                                                        {spec.current_level >= level ? '✅' : '⭕'}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {/* Detailed Track Information */}
                                    <div className="track-details">
                                        <div className="track-metadata">
                                            <div className="track-info-item">
                                                <span className="track-label">🏁 Track Specialization:</span>
                                                <span className="track-value">{spec.specialization_type}</span>
                                            </div>
                                            <div className="track-info-item">
                                                <span className="track-label">🎯 Current Focus:</span>
                                                <span className="track-value">
                                                    {spec.current_level_metadata?.description || 'Professional Development'}
                                                </span>
                                            </div>
                                        </div>
                                        
                                        <div className="track-timeline">
                                            <div className="timeline-item start">
                                                <span className="timeline-icon">🚀</span>
                                                <div className="timeline-content">
                                                    <span className="timeline-label">Track Start</span>
                                                    <span className="timeline-date">
                                                        {new Date(spec.started_at).toLocaleDateString('hu-HU')}
                                                    </span>
                                                </div>
                                            </div>
                                            {spec.last_advanced_at && (
                                                <div className="timeline-item advance">
                                                    <span className="timeline-icon">⬆️</span>
                                                    <div className="timeline-content">
                                                        <span className="timeline-label">Last Level Up</span>
                                                        <span className="timeline-date">
                                                            {new Date(spec.last_advanced_at).toLocaleDateString('hu-HU')}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* No Active Specializations */}
            {dashboardData && (!dashboardData.active_specializations || dashboardData.active_specializations.length === 0) && (
                <div className="no-specializations">
                    <div className="empty-state">
                        <span className="empty-icon">📚</span>
                        <h3>You don't have any active specializations yet</h3>
                        <p>In the next step you can choose specializations to start your training path.</p>
                    </div>
                </div>
            )}

            {/* Available Specializations */}
            {dashboardData && dashboardData.available_specializations && dashboardData.available_specializations.length > 0 && (
                <div className="available-specializations-section">
                    <h3>🎯 Available Specializations</h3>
                    <p className="section-description">
                        You can choose from the following specializations in the current semester:
                    </p>
                    <div className="specializations-list-wrapper">
                        {dashboardData.available_specializations.map(spec => (
                            <div
                                key={spec.specialization_type}
                                className={`specialization-availability-card ${spec.can_start ? 'available' : 'restricted'}`}
                                style={{
                                    display: 'block',
                                    width: '100%',
                                    marginBottom: '25px'
                                }}
                            >
                                <div className="spec-header">
                                    <span className="spec-icon">
                                        {spec.specialization_type === 'PLAYER' ? '⚽' : 
                                         spec.specialization_type === 'COACH' ? '👨‍🏫' : 
                                         spec.specialization_type === 'INTERNSHIP' ? '💼' : '🎓'}
                                    </span>
                                    <div className="spec-title">
                                        <h4>{spec.title || spec.specialization_type}</h4>
                                        <p className="spec-subtitle">{spec.subtitle || 'Specialization'}</p>
                                    </div>
                                </div>
                                
                                <div className="spec-status">
                                    <p className="simple-status-text">
                                        {spec.can_start ? '✅ Available' : '❌ Not Available'}
                                    </p>
                                    <p className="status-reason">{spec.reason}</p>
                                    
                                    {/* Age Requirements */}
                                    {spec.age_requirement && (
                                        <div className="age-requirement-details">
                                            <div className="requirement-status">
                                                <span className={`requirement-badge ${spec.age_requirement.meets_requirement ? 'meets' : 'not-meets'}`}>
                                                    {spec.age_requirement.meets_requirement ? '✅' : '❌'} Age Requirement
                                                </span>
                                            </div>
                                            <div className="requirement-info">
                                                <span className="current-age">
                                                    👤 Current Age: <strong>{spec.age_requirement.user_age} years</strong>
                                                </span>
                                                <span className="required-age">
                                                    📋 Minimum Age: <strong>{spec.age_requirement.required_age} years</strong>
                                                </span>
                                            </div>
                                            {!spec.age_requirement.meets_requirement && (
                                                <div className="requirement-warning">
                                                    ⚠️ Additional years required
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Payment Requirements */}
                                    {spec.payment_requirement && (
                                        <div className="payment-requirement-details">
                                            <div className="requirement-status">
                                                <span className={`requirement-badge ${spec.payment_requirement.payment_verified ? 'meets' : 'not-meets'}`}>
                                                    {spec.payment_requirement.payment_verified ? '✅' : '❌'} Payment
                                                </span>
                                            </div>
                                            <div className="requirement-info">
                                                <span className="payment-status">
                                                    💳 Status: <strong>{spec.payment_requirement.payment_status_display}</strong>
                                                </span>
                                                {spec.payment_requirement.verified_at && (
                                                    <span className="verified-date">
                                                        📅 Verified: <strong>{new Date(spec.payment_requirement.verified_at).toLocaleDateString('hu-HU')}</strong>
                                                    </span>
                                                )}
                                            </div>
                                            {!spec.payment_requirement.payment_verified && (
                                                <div className="requirement-warning">
                                                    ⚠️ Please contact the administrator to verify payment
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Dynamic Semester Progress */}
            {dashboardData && (
                <div className="semester-progress-info">
                    <h3>📈 Your Development Guide</h3>

                    {/* Personalized Current Status */}
                    <div className="current-semester-overview">
                        <div className="semester-indicator">
                            <span className="semester-number">{dashboardData.current_semester || 1}</span>
                            <div className="semester-info">
                                <h4>
                                    {dashboardData.parallel_progress?.total_active === 0 && "Start your journey!"}
                                    {dashboardData.parallel_progress?.total_active === 1 && "Great progress!"}
                                    {dashboardData.parallel_progress?.total_active === 2 && "Excellent pace!"}
                                    {dashboardData.parallel_progress?.total_active >= 3 && "Professional level!"}
                                </h4>
                                <p className="semester-description">
                                    {dashboardData.parallel_progress?.total_active === 0 && "Choose your first specialization and start your development path!"}
                                    {dashboardData.parallel_progress?.total_active === 1 && dashboardData.current_semester >= 2
                                        ? "Ready to add a second specialization!"
                                        : "Deepen your knowledge in your first specialization!"}
                                    {dashboardData.parallel_progress?.total_active === 2 && dashboardData.current_semester >= 3
                                        ? "Now you can choose all 3 specializations!"
                                        : "You're developing in two specializations in parallel - fantastic!"}
                                    {dashboardData.parallel_progress?.total_active >= 3 && "You're actively progressing in all specializations - impressive commitment!"}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Personalized Next Steps */}
                    <div className="next-steps-section">
                        <h4>🎯 Your Next Steps</h4>

                        {/* If no specializations */}
                        {dashboardData.parallel_progress?.total_active === 0 && (
                            <div className="next-step-card highlight">
                                <div className="step-icon">🚀</div>
                                <div className="step-details">
                                    <h5>Choose your first specialization!</h5>
                                    <p>Go to the 'Specialization' tab and start with any specialization: Player, Coach or Internship</p>
                                    <div className="step-benefit">✨ This is the beginning - build the foundation of your career!</div>
                                </div>
                            </div>
                        )}

                        {/* If 1 specialization and semester >= 2 */}
                        {dashboardData.parallel_progress?.total_active === 1 && dashboardData.current_semester >= 2 && (
                            <div className="next-step-card highlight">
                                <div className="step-icon">⚡</div>
                                <div className="step-details">
                                    <h5>Add a second specialization!</h5>
                                    <p>From the 2nd semester you can develop in 2 specializations in parallel. Check the available specializations below!</p>
                                    <div className="step-benefit">✨ Expand your knowledge and increase your opportunities!</div>
                                </div>
                            </div>
                        )}

                        {/* If 2 specializations and semester >= 3 */}
                        {dashboardData.parallel_progress?.total_active === 2 && dashboardData.current_semester >= 3 && (
                            <div className="next-step-card highlight">
                                <div className="step-icon">🏆</div>
                                <div className="step-details">
                                    <h5>Third specialization available!</h5>
                                    <p>From the 3rd semester you can take all 3 specializations at once. Scroll down and check the third option!</p>
                                    <div className="step-benefit">✨ Become a complete professional - Player + Coach + Internship!</div>
                                </div>
                            </div>
                        )}

                        {/* Current active specializations progress */}
                        {dashboardData.active_specializations && dashboardData.active_specializations.length > 0 && (
                            <div className="active-progress-summary">
                                <h5>📊 Your Current Progress</h5>
                                {dashboardData.active_specializations.map(spec => (
                                    <div key={spec.specialization_type} className="progress-item">
                                        <span className="spec-name">
                                            {spec.current_level_metadata?.icon_emoji} {spec.specialization_type}
                                        </span>
                                        <span className="spec-progress">
                                            Level {spec.current_level}/8 ({Math.round((spec.current_level / 8) * 100)}%)
                                        </span>
                                        {spec.current_level < 8 && (
                                            <span className="next-level-hint">
                                                💪 Next: Level {spec.current_level + 1}
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Quick Stats */}
                    <div className="progress-stats">
                        <div className="stat-item">
                            <span className="stat-value">{dashboardData.parallel_progress?.total_active || 0}</span>
                            <span className="stat-label">Active Specializations</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">
                                {dashboardData.current_semester === 1 ? 1 : 
                                 dashboardData.current_semester === 2 ? 2 : 3}
                            </span>
                            <span className="stat-label">Maximum Selectable</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">
                                {dashboardData.parallel_progress?.can_add_more ? 'Igen' : 'Nem'}
                            </span>
                            <span className="stat-label">New Specialization Can Be Added</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Navigation */}
            {!hideNavigation && (
                <div className="status-actions">
                    <button 
                        onClick={onNext}
                        className="action-button primary forward-only"
                    >
                        Continue to Specialization Selection →
                    </button>
                </div>
            )}
        </div>
    );
};

export default CurrentSpecializationStatus;