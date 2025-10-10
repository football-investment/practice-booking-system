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
            const dashboard = await apiService.get('/api/v1/parallel-specializations/dashboard');
            
            // Also get available specializations for current user
            try {
                const available = await apiService.get('/api/v1/parallel-specializations/available');
                dashboard.available_specializations = available;
            } catch (availError) {
                console.warn('Could not fetch available specializations:', availError);
                dashboard.available_specializations = [];
            }
            
            setDashboardData(dashboard);
            
        } catch (error) {
            console.error('Error fetching status data:', error);
            setError('Nem sikerült betölteni az állapot adatokat');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="status-loading">
                <div className="loading-spinner"></div>
                <p>Állapot adatok betöltése...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="status-error">
                <p>{error}</p>
                <button onClick={fetchStatusData} className="retry-button">
                    Újrapróbálás
                </button>
            </div>
        );
    }

    return (
        <div className="current-specialization-status">
            <div className="status-header">
                <h2>📋 Jelenlegi Állapot</h2>
                <p className="status-intro">
                    Itt áttekintheted a specializációid aktuális állását és fejlődési útvonaladat.
                </p>
            </div>

            {/* User Info */}
            {dashboardData && (
                <div className="user-overview">
                    <div className="overview-card">
                        <h3>👤 Felhasználói Információk</h3>
                        <div className="info-grid">
                            <div className="info-item">
                                <span className="info-label">Név:</span>
                                <span className="info-value">{dashboardData.user?.name || 'N/A'}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Email:</span>
                                <span className="info-value">{dashboardData.user?.email || 'N/A'}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">Jelenlegi szemeszter:</span>
                                <span className="info-value semester-badge">{dashboardData.current_semester || 1}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Active Specializations */}
            {dashboardData && dashboardData.active_specializations && dashboardData.active_specializations.length > 0 && (
                <div className="active-specializations-section">
                    <h3>✅ Aktív Specializációk</h3>
                    <div className="specializations-grid">
                        {dashboardData.active_specializations.map(spec => (
                            <div key={spec.specialization_type} className="specialization-status-card">
                                <div className="spec-header">
                                    <span className="spec-icon">
                                        {spec.current_level_metadata?.icon_emoji || '🎓'}
                                    </span>
                                    <div className="spec-title">
                                        <h4>{spec.current_level_metadata?.title || spec.specialization_type}</h4>
                                        <p className="spec-subtitle">{spec.current_level_metadata?.subtitle || 'Specializáció'}</p>
                                    </div>
                                </div>
                                
                                <div className="spec-progress">
                                    {/* Enhanced Level Display */}
                                    <div className="enhanced-level-display">
                                        <div className="level-badge-container">
                                            <div className="current-level-badge">
                                                <span className="level-number">{spec.current_level}</span>
                                                <span className="level-text">SZINT</span>
                                            </div>
                                            <div className="level-progress-info">
                                                <div className="level-status">
                                                    <span className="status-text">Jelenlegi track állapot</span>
                                                    <span className="track-position">
                                                        {spec.current_level}/8 szint teljesítve
                                                    </span>
                                                </div>
                                                <div className="achievement-info">
                                                    <span className="achievement-badge">
                                                        🏆 Max elért: Level {spec.max_achieved_level}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {/* Visual Progress Indicator */}
                                    <div className="visual-progress-container">
                                        <div className="progress-labels">
                                            <span className="progress-start">Kezdő</span>
                                            <span className="progress-current">
                                                {spec.current_level < 3 ? 'Alapszint' : 
                                                 spec.current_level < 6 ? 'Haladó' : 'Szakértő'}
                                            </span>
                                            <span className="progress-end">Mester</span>
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
                                                <span className="track-label">🏁 Track specializáció:</span>
                                                <span className="track-value">{spec.specialization_type}</span>
                                            </div>
                                            <div className="track-info-item">
                                                <span className="track-label">🎯 Jelenlegi fókusz:</span>
                                                <span className="track-value">
                                                    {spec.current_level_metadata?.description || 'Szakmai fejlődés'}
                                                </span>
                                            </div>
                                        </div>
                                        
                                        <div className="track-timeline">
                                            <div className="timeline-item start">
                                                <span className="timeline-icon">🚀</span>
                                                <div className="timeline-content">
                                                    <span className="timeline-label">Track kezdés</span>
                                                    <span className="timeline-date">
                                                        {new Date(spec.started_at).toLocaleDateString('hu-HU')}
                                                    </span>
                                                </div>
                                            </div>
                                            {spec.last_advanced_at && (
                                                <div className="timeline-item advance">
                                                    <span className="timeline-icon">⬆️</span>
                                                    <div className="timeline-content">
                                                        <span className="timeline-label">Utolsó szintlépés</span>
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
                        <h3>Még nincsenek aktív specializációid</h3>
                        <p>A következő lépésben választhatsz specializációkat a képzési útvonalad elindításához.</p>
                    </div>
                </div>
            )}

            {/* Available Specializations */}
            {dashboardData && dashboardData.available_specializations && dashboardData.available_specializations.length > 0 && (
                <div className="available-specializations-section">
                    <h3>🎯 Elérhető Specializációk</h3>
                    <p className="section-description">
                        Az alábbi specializációkat választhatod a jelenlegi szemeszterben:
                    </p>
                    <div className="specializations-grid">
                        {dashboardData.available_specializations.map(spec => (
                            <div key={spec.specialization_type} className={`specialization-availability-card ${spec.can_start ? 'available' : 'restricted'}`}>
                                <div className="spec-header">
                                    <span className="spec-icon">
                                        {spec.specialization_type === 'PLAYER' ? '⚽' : 
                                         spec.specialization_type === 'COACH' ? '👨‍🏫' : 
                                         spec.specialization_type === 'INTERNSHIP' ? '💼' : '🎓'}
                                    </span>
                                    <div className="spec-title">
                                        <h4>{spec.title || spec.specialization_type}</h4>
                                        <p className="spec-subtitle">{spec.subtitle || 'Specializáció'}</p>
                                    </div>
                                </div>
                                
                                <div className="spec-status">
                                    <div className={`status-indicator ${spec.can_start ? 'available' : 'restricted'}`}>
                                        {spec.can_start ? '✅ Elérhető' : '❌ Nem elérhető'}
                                    </div>
                                    <p className="status-reason">{spec.reason}</p>
                                    
                                    {/* Age Requirements */}
                                    {spec.age_requirement && (
                                        <div className="age-requirement-details">
                                            <div className="requirement-status">
                                                <span className={`requirement-badge ${spec.age_requirement.meets_requirement ? 'meets' : 'not-meets'}`}>
                                                    {spec.age_requirement.meets_requirement ? '✅' : '❌'} Korhatár
                                                </span>
                                            </div>
                                            <div className="requirement-info">
                                                <span className="current-age">
                                                    👤 Jelenlegi kor: <strong>{spec.age_requirement.user_age} év</strong>
                                                </span>
                                                <span className="required-age">
                                                    📋 Minimum kor: <strong>{spec.age_requirement.required_age} év</strong>
                                                </span>
                                            </div>
                                            {!spec.age_requirement.meets_requirement && (
                                                <div className="requirement-warning">
                                                    ⚠️ További {spec.age_requirement.required_age - spec.age_requirement.user_age} év szükséges
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Payment Requirements */}
                                    {spec.payment_requirement && (
                                        <div className="payment-requirement-details">
                                            <div className="requirement-status">
                                                <span className={`requirement-badge ${spec.payment_requirement.payment_verified ? 'meets' : 'not-meets'}`}>
                                                    {spec.payment_requirement.payment_verified ? '✅' : '❌'} Befizetés
                                                </span>
                                            </div>
                                            <div className="requirement-info">
                                                <span className="payment-status">
                                                    💳 Státusz: <strong>{spec.payment_requirement.payment_status_display}</strong>
                                                </span>
                                                {spec.payment_requirement.verified_at && (
                                                    <span className="verified-date">
                                                        📅 Ellenőrizve: <strong>{new Date(spec.payment_requirement.verified_at).toLocaleDateString('hu-HU')}</strong>
                                                    </span>
                                                )}
                                            </div>
                                            {!spec.payment_requirement.payment_verified && (
                                                <div className="requirement-warning">
                                                    ⚠️ Kérjük, vegye fel a kapcsolatot az adminisztrátorral a befizetés ellenőrzéséhez
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
                    <h3>📈 Félév és Fejlődési Útmutató</h3>
                    
                    {/* Current Status Summary */}
                    <div className="current-semester-overview">
                        <div className="semester-indicator">
                            <span className="semester-number">{dashboardData.current_semester || 1}</span>
                            <div className="semester-info">
                                <h4>Jelenlegi szemeszter</h4>
                                <p className="semester-description">
                                    {dashboardData.current_semester === 1 && "Alapoktatás - első lépések a specializációkban"}
                                    {dashboardData.current_semester === 2 && "Fejlett tudás - specializációk mélyítése"}
                                    {dashboardData.current_semester >= 3 && "Szakértői szint - összes specializáció elérhető"}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Semester Roadmap */}
                    <div className="semester-roadmap">
                        <div className="roadmap-step-wrapper">
                            <div className={`roadmap-step ${dashboardData.current_semester >= 1 ? 'completed' : 'pending'}`}>
                                <div className="step-marker">1</div>
                                <div className="step-content">
                                    <h5>🌱 Első szemeszter</h5>
                                    <p>Válassz 1 specializációt a háromból</p>
                                    <div className="step-options">Player • Coach • Internship</div>
                                </div>
                            </div>
                            
                            <div className={`roadmap-step ${dashboardData.current_semester >= 2 ? 'completed' : dashboardData.current_semester === 1 ? 'current' : 'pending'}`}>
                                <div className="step-marker">2</div>
                                <div className="step-content">
                                    <h5>🚀 Második szemeszter</h5>
                                    <p>Maximum 2 specializáció párhuzamosan</p>
                                    <div className="step-options">Player + Coach VAGY Player + Internship</div>
                                </div>
                            </div>
                            
                            <div className={`roadmap-step ${dashboardData.current_semester >= 3 ? 'completed' : dashboardData.current_semester === 2 ? 'current' : 'pending'}`}>
                                <div className="step-marker">3+</div>
                                <div className="step-content">
                                    <h5>⭐ Harmadik szemeszter+</h5>
                                    <p>Mind a 3 specializáció egyszerre lehetséges</p>
                                    <div className="step-options">Player + Coach + Internship</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="progress-stats">
                        <div className="stat-item">
                            <span className="stat-value">{dashboardData.parallel_progress?.total_active || 0}</span>
                            <span className="stat-label">Aktív specializációk</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">
                                {dashboardData.current_semester === 1 ? 1 : 
                                 dashboardData.current_semester === 2 ? 2 : 3}
                            </span>
                            <span className="stat-label">Maximum választható</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">
                                {dashboardData.parallel_progress?.can_add_more ? 'Igen' : 'Nem'}
                            </span>
                            <span className="stat-label">Új specializáció hozzáadható</span>
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
                        Tovább a Specializáció Választáshoz →
                    </button>
                </div>
            )}
        </div>
    );
};

export default CurrentSpecializationStatus;