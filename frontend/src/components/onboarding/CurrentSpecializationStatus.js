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
                                        <p className="spec-subtitle">{spec.subtitle || 'Specializáció'}</p>
                                    </div>
                                </div>
                                
                                <div className="spec-status">
                                    <p className="simple-status-text">
                                        {spec.can_start ? '✅ Elérhető' : '❌ Nem elérhető'}
                                    </p>
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
                    <h3>📈 A Te Fejlődési Útmutatód</h3>

                    {/* Personalized Current Status */}
                    <div className="current-semester-overview">
                        <div className="semester-indicator">
                            <span className="semester-number">{dashboardData.current_semester || 1}</span>
                            <div className="semester-info">
                                <h4>
                                    {dashboardData.parallel_progress?.total_active === 0 && "Kezdd el az utazásod!"}
                                    {dashboardData.parallel_progress?.total_active === 1 && "Remekül haladsz!"}
                                    {dashboardData.parallel_progress?.total_active === 2 && "Kiváló tempó!"}
                                    {dashboardData.parallel_progress?.total_active >= 3 && "Professzionális szinten!"}
                                </h4>
                                <p className="semester-description">
                                    {dashboardData.parallel_progress?.total_active === 0 && "Válaszd ki az első specializációdat és indulj el a fejlődési útvonalon!"}
                                    {dashboardData.parallel_progress?.total_active === 1 && dashboardData.current_semester >= 2
                                        ? "Készen állsz egy második specializáció hozzáadására!"
                                        : "Mélyítsd a tudásod az első specializációdban!"}
                                    {dashboardData.parallel_progress?.total_active === 2 && dashboardData.current_semester >= 3
                                        ? "Most már mind a 3 specializációt választhatod!"
                                        : "Két specializációban is fejlődsz párhuzamosan - fantasztikus!"}
                                    {dashboardData.parallel_progress?.total_active >= 3 && "Minden specializációban aktívan haladsz - lenyűgöző elkötelezettség!"}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Personalized Next Steps */}
                    <div className="next-steps-section">
                        <h4>🎯 A Te Következő Lépéseid</h4>

                        {/* If no specializations */}
                        {dashboardData.parallel_progress?.total_active === 0 && (
                            <div className="next-step-card highlight">
                                <div className="step-icon">🚀</div>
                                <div className="step-details">
                                    <h5>Válaszd ki az első specializációdat!</h5>
                                    <p>Lépj a "Szakirány" fülre és kezdj el bármelyik specializációval: Player, Coach vagy Internship</p>
                                    <div className="step-benefit">✨ Ez a kezdet - építsd fel a karriered alapjait!</div>
                                </div>
                            </div>
                        )}

                        {/* If 1 specialization and semester >= 2 */}
                        {dashboardData.parallel_progress?.total_active === 1 && dashboardData.current_semester >= 2 && (
                            <div className="next-step-card highlight">
                                <div className="step-icon">⚡</div>
                                <div className="step-details">
                                    <h5>Adj hozzá egy második specializációt!</h5>
                                    <p>A 2. szemesztertől párhuzamosan 2 specializációban fejlődhetsz. Nézd meg az elérhető specializációkat alább!</p>
                                    <div className="step-benefit">✨ Bővítsd a tudásod és növeld a lehetőségeidet!</div>
                                </div>
                            </div>
                        )}

                        {/* If 2 specializations and semester >= 3 */}
                        {dashboardData.parallel_progress?.total_active === 2 && dashboardData.current_semester >= 3 && (
                            <div className="next-step-card highlight">
                                <div className="step-icon">🏆</div>
                                <div className="step-details">
                                    <h5>Harmadik specializáció elérhető!</h5>
                                    <p>A 3. szemesztertől mind a 3 specializációt viheted egyszerre. Görgess le és nézd meg a harmadik opciót!</p>
                                    <div className="step-benefit">✨ Légy teljes körű szakember - Player + Coach + Internship!</div>
                                </div>
                            </div>
                        )}

                        {/* Current active specializations progress */}
                        {dashboardData.active_specializations && dashboardData.active_specializations.length > 0 && (
                            <div className="active-progress-summary">
                                <h5>📊 Jelenlegi Előrehaladásod</h5>
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
                                                💪 Következő: Level {spec.current_level + 1}
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