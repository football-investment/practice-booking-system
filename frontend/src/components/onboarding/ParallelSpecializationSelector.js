import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './ParallelSpecializationSelector.css';

// Helper function for semester-based specialization limits
const getMaxSpecializationsForSemester = (semester) => {
    switch (semester) {
        case 1: return 1;
        case 2: return 2;
        case 3:
        default: return 3;
    }
};

const ParallelSpecializationSelector = ({ 
    onSelectionUpdate,
    onNext, 
    hideNavigation = false,
    showProgressionInfo = true 
}) => {
    const [activeSpecializations, setActiveSpecializations] = useState([]);
    const [availableSpecializations, setAvailableSpecializations] = useState([]);
    const [selectedSpecializations, setSelectedSpecializations] = useState(new Set());
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    
    useEffect(() => {
        fetchSpecializationData();
    }, []);
    
    const fetchSpecializationData = async () => {
        try {
            setLoading(true);
            
            // Get comprehensive dashboard data
            const dashboard = await apiService.get('/parallel-specializations/dashboard');
            setDashboardData(dashboard);
            setActiveSpecializations(dashboard.active_specializations || []);
            
            // Get license metadata for proper titles
            const licenseMetadata = await apiService.get('/licenses/metadata');
            
            // Enrich available specializations with proper license metadata
            const enrichedAvailable = (dashboard.available_specializations || []).map(spec => {
                const levelMetadata = licenseMetadata.find(meta => 
                    meta.specialization_type === spec.specialization_type && meta.level_number === 1
                );
                return {
                    ...spec,
                    licenseMetadata: levelMetadata
                };
            });
            
            setAvailableSpecializations(enrichedAvailable);
            
            // Pre-select already active specializations
            const activeSet = new Set(
                dashboard.active_specializations?.map(spec => spec.specialization_type) || []
            );
            setSelectedSpecializations(activeSet);
            
        } catch (error) {
            console.error('Error fetching specialization data:', error);
            setError('Nem sikerült betölteni a specializációs adatokat');
        } finally {
            setLoading(false);
        }
    };
    
    const handleSpecializationToggle = async (specCode) => {
        if (saving) return;
        
        const newSelection = new Set(selectedSpecializations);
        const isCurrentlySelected = selectedSpecializations.has(specCode);
        const isAlreadyActive = activeSpecializations.some(spec => spec.specialization_type === specCode);
        
        if (isAlreadyActive) {
            // Cannot deselect already active specializations
            return;
        }
        
        if (isCurrentlySelected) {
            newSelection.delete(specCode);
        } else {
            // Check semester limits
            const currentSemester = dashboardData?.current_semester || 1;
            const maxAllowed = getMaxSpecializationsForSemester(currentSemester);
            const currentTotal = activeSpecializations.length + newSelection.size;
            
            if (currentTotal >= maxAllowed) {
                setError(`${currentSemester}. szemeszterben maximum ${maxAllowed} specializáció választható!`);
                return;
            }
            
            // For semester 1, only allow one selection at a time
            if (currentSemester === 1 && newSelection.size > 0) {
                newSelection.clear(); // Clear previous selection
            }
            
            // Validate addition
            try {
                const validation = await apiService.get(`/parallel-specializations/validate/${specCode}`);
                if (!validation.valid) {
                    setError(`${specCode}: ${validation.reason}`);
                    return;
                }
                newSelection.add(specCode);
            } catch (error) {
                setError(`Hiba a specializáció validálásakor: ${error.message}`);
                return;
            }
        }
        
        setSelectedSpecializations(newSelection);
        setError(null);
        
        // Update parent component
        if (onSelectionUpdate) {
            onSelectionUpdate(Array.from(newSelection));
        }
    };
    
    const handleStartNewSpecializations = async () => {
        setSaving(true);
        setError(null);
        
        const newSpecializations = Array.from(selectedSpecializations).filter(
            spec => !activeSpecializations.some(active => active.specialization_type === spec)
        );
        
        if (newSpecializations.length === 0) {
            setSaving(false);
            if (onNext) {
                onNext(); // Allow progression even if no new specializations selected
            }
            return;
        }
        
        // Final validation before starting
        const currentSemester = dashboardData?.current_semester || 1;
        const maxAllowed = getMaxSpecializationsForSemester(currentSemester);
        const totalAfterAddition = activeSpecializations.length + newSpecializations.length;
        
        if (totalAfterAddition > maxAllowed) {
            setError(`Túl sok specializáció! Maximum ${maxAllowed} engedélyezett a ${currentSemester}. szemeszterben.`);
            setSaving(false);
            return;
        }
        
        try {
            const results = [];
            for (const spec of newSpecializations) {
                const result = await apiService.post('/parallel-specializations/start', {
                    specialization: spec
                });
                results.push(result);
            }
            
            // Refresh data after successful additions
            await fetchSpecializationData();
            
            console.log('✅ Successfully started new specializations:', results);
            
            // Proceed to next step if callback is provided
            if (onNext) {
                onNext();
            }
            
        } catch (error) {
            console.error('Error starting specializations:', error);
            setError(`Hiba a specializációk indításakor: ${error.message}`);
        } finally {
            setSaving(false);
        }
    };
    
    const getSpecializationStatus = (specCode) => {
        const isActive = activeSpecializations.some(spec => spec.specialization_type === specCode);
        const isSelected = selectedSpecializations.has(specCode);
        const isAvailable = availableSpecializations.some(spec => 
            spec.specialization_type === specCode && spec.can_start
        );
        
        if (isActive) return 'active';
        if (isSelected) return 'selected';
        if (isAvailable) return 'available';
        return 'locked';
    };
    
    if (loading) {
        return (
            <div className="parallel-specialization-loading">
                <div className="loading-spinner"></div>
                <p>Specializációs adatok betöltése...</p>
            </div>
        );
    }
    
    if (error && !dashboardData) {
        return (
            <div className="parallel-specialization-error">
                <p>{error}</p>
                <button onClick={fetchSpecializationData} className="retry-button">
                    Újrapróbálás
                </button>
            </div>
        );
    }
    
    return (
        <div className="parallel-specialization-selector">
            <div className="specialization-header">
                <h2>🎓 Specializációs Választás</h2>
                <p className="specialization-intro">
                    {dashboardData && dashboardData.current_semester === 1 
                        ? 'Válaszd ki az első specializációdat! Ez lesz a kezdő lépésed a GānCuju™️©️ programban.'
                        : `${dashboardData.current_semester}. szemeszterben már ${getMaxSpecializationsForSemester(dashboardData.current_semester)} specializációt választhatsz párhuzamosan!`
                    }
                </p>
                
                {dashboardData && (
                    <div className="current-status">
                        <span className="semester-info">
                            📚 Jelenlegi szemeszter: {dashboardData.current_semester}
                        </span>
                        <span className="active-count">
                            🎯 Aktív specializációk: {dashboardData.parallel_progress.total_active}/{getMaxSpecializationsForSemester(dashboardData.current_semester)}
                        </span>
                    </div>
                )}
            </div>
            
            {error && (
                <div className="error-message">
                    <span>⚠️ {error}</span>
                </div>
            )}
            
            {/* Active Specializations */}
            {activeSpecializations.length > 0 && (
                <div className="active-specializations">
                    <h3>✅ Már aktív specializációid:</h3>
                    <div className="active-spec-list">
                        {activeSpecializations.map(spec => (
                            <div key={spec.specialization_type} className="active-spec-card">
                                <span className="spec-icon">
                                    {spec.current_level_metadata?.icon_emoji || '🎓'}
                                </span>
                                <div className="spec-info">
                                    <strong>{spec.current_level_metadata?.title || spec.specialization_type}</strong>
                                    <small>{spec.current_level_metadata?.subtitle || 'Folyamatban'}</small>
                                    <div className="spec-level-info">
                                        <span className="level-badge">
                                            {spec.current_level_metadata?.level_display || `Level ${spec.current_level}`}
                                        </span>
                                        {spec.current_level < spec.max_achieved_level && (
                                            <span className="next-level-hint">
                                                → Következő: Level {spec.current_level + 1}
                                            </span>
                                        )}
                                    </div>
                                    <div className="spec-progress">
                                        <div className="progress-timeline">
                                            <span className="progress-start">Kezdés: {new Date(spec.started_at).toLocaleDateString('hu-HU')}</span>
                                            {spec.last_advanced_at && (
                                                <span className="progress-advancement">
                                                    Utolsó előrelépés: {new Date(spec.last_advanced_at).toLocaleDateString('hu-HU')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
            
            {/* Available Specializations */}
            {availableSpecializations.length > 0 && (
                <div className="available-specializations">
                    <h3>
                        {dashboardData && dashboardData.current_semester === 1 
                            ? '🎯 Válaszd ki az első specializációdat:'
                            : '🆕 Új specializációk hozzáadása:'
                        }
                    </h3>
                    <div className="specialization-options-enhanced">
                        {availableSpecializations.map(spec => {
                            const status = getSpecializationStatus(spec.specialization_type);
                            const isDisabled = !spec.can_start || saving;
                            const trackType = spec.specialization_type;
                            const trackClass = `${trackType.toLowerCase()}-track`;
                            
                            return (
                                <div 
                                    key={spec.specialization_type}
                                    className={`enhanced-specialization-card ${trackClass} ${status} ${isDisabled ? 'disabled' : ''}`}
                                    onClick={() => !isDisabled && handleSpecializationToggle(spec.specialization_type)}
                                >
                                    {/* Card Header with Icon and Title */}
                                    <div className="enhanced-spec-header">
                                        <div className="enhanced-spec-icon">
                                            <span className="icon-emoji">
                                                {spec.specialization_type === 'PLAYER' ? '⚽' : 
                                                 spec.specialization_type === 'COACH' ? '👨‍🏫' : 
                                                 spec.specialization_type === 'INTERNSHIP' ? '💼' : '🎓'}
                                            </span>
                                        </div>
                                        <div className="enhanced-spec-title">
                                            <h4>{spec.licenseMetadata?.title || spec.specialization_type}</h4>
                                            <p className="enhanced-spec-subtitle">
                                                {spec.specialization_type === 'PLAYER' ? 'GānCuju™️©️ Játékos Specializáció' : 
                                                 spec.specialization_type === 'COACH' ? 'LFA Edzői Specializáció' : 
                                                 spec.specialization_type === 'INTERNSHIP' ? 'LFA Gyakornoki Program' : 
                                                 spec.licenseMetadata?.subtitle || spec.reason}
                                            </p>
                                        </div>
                                        
                                        {/* Selection Status Indicator */}
                                        <div className="enhanced-selection-status">
                                            {status === 'selected' && (
                                                <div className="status-badge selected">
                                                    <span>✅</span>
                                                    <span>Kiválasztva</span>
                                                </div>
                                            )}
                                            {status === 'active' && (
                                                <div className="status-badge active">
                                                    <span>🎯</span>
                                                    <span>Aktív</span>
                                                </div>
                                            )}
                                            {status === 'available' && spec.can_start && (
                                                <div className="status-badge available">
                                                    <span>🔓</span>
                                                    <span>Elérhető</span>
                                                </div>
                                            )}
                                            {status === 'locked' && (
                                                <div className="status-badge locked">
                                                    <span>🔒</span>
                                                    <span>Zárolt</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    
                                    {/* Enhanced Card Content */}
                                    <div className="enhanced-spec-content">
                                        
                                        {/* Track Highlights */}
                                        <div className="enhanced-track-highlights">
                                            <div className="track-highlight">
                                                <span className="highlight-icon">🎯</span>
                                                <span>8 szintes fejlődési rendszer</span>
                                            </div>
                                            <div className="track-highlight">
                                                <span className="highlight-icon">⭐</span>
                                                <span>Professzionális képzési program</span>
                                            </div>
                                        </div>
                                        
                                        {/* Track Information */}
                                        <div className="enhanced-track-info">
                                            <div className="track-detail">
                                                <span className="detail-label">Fejlődési út:</span>
                                                <span className="detail-value">8 szintes rendszer</span>
                                            </div>
                                            <div className="track-detail">
                                                <span className="detail-label">Kezdő szint:</span>
                                                <span className="detail-value">
                                                    {spec.licenseMetadata?.level_display || 'Level 1'}
                                                </span>
                                            </div>
                                        </div>
                                        
                                        {/* Requirements */}
                                        {(spec.age_requirement || spec.payment_requirement) && (
                                            <div className="enhanced-requirements">
                                                {spec.age_requirement && (
                                                    <div className={`requirement-item ${spec.age_requirement.meets_requirement ? 'met' : 'unmet'}`}>
                                                        <span className="req-icon">👤</span>
                                                        <span className="req-text">
                                                            Életkor: {spec.age_requirement.user_age || 'N/A'} / {spec.age_requirement.required_age} év
                                                        </span>
                                                        <span className="req-status">
                                                            {spec.age_requirement.meets_requirement ? '✅' : '❌'}
                                                        </span>
                                                    </div>
                                                )}
                                                {spec.payment_requirement && (
                                                    <div className={`requirement-item ${spec.payment_requirement.payment_verified ? 'met' : 'unmet'}`}>
                                                        <span className="req-icon">💳</span>
                                                        <span className="req-text">
                                                            Befizetés: {spec.payment_requirement.payment_status_display}
                                                        </span>
                                                        <span className="req-status">
                                                            {spec.payment_requirement.payment_verified ? '✅' : '❌'}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        
                                        {/* Action Area */}
                                        <div className="enhanced-card-action">
                                            {spec.can_start ? (
                                                <button 
                                                    className={`track-select-btn ${status} ${trackType.toLowerCase()}-btn`}
                                                    disabled={isDisabled}
                                                >
                                                    {status === 'selected' ? '✅ Kiválasztva' : 
                                                     status === 'active' ? '🎯 Aktív specializáció' : 
                                                     '🚀 Specializáció választása'}
                                                </button>
                                            ) : (
                                                <div className="track-locked-info">
                                                    <span className="locked-icon">🔒</span>
                                                    <span className="locked-text">{spec.reason}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
            
            
            {!hideNavigation && (
                <div className="specialization-actions">
                    <button 
                        onClick={handleStartNewSpecializations}
                        disabled={saving || (dashboardData?.current_semester === 1 && selectedSpecializations.size === 0)}
                        className="action-button primary forward-only"
                    >
                        {saving ? 'Mentés...' : (() => {
                            const newSpecCount = selectedSpecializations.size - activeSpecializations.length;
                            if (newSpecCount > 0) {
                                return `${newSpecCount} új specializáció indítása`;
                            } else if (activeSpecializations.length > 0) {
                                return 'Onboarding befejezése →';
                            } else {
                                return 'Válassz specializációt!';
                            }
                        })()}
                    </button>
                </div>
            )}
        </div>
    );
};

export default ParallelSpecializationSelector;