import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './SpecializationSelector.css';

const SpecializationSelector = ({ 
    onSelect, 
    selectedSpecialization, 
    onNext, 
    onBack, 
    hideNavigation = false,
    currentUserSpecialization = null,
    semesterCount = 1,
    showProgressionInfo = true
}) => {
    const [availableSpecializations, setAvailableSpecializations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    
    useEffect(() => {
        fetchSpecializations();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    
    const fetchSpecializations = async () => {
        try {
            setLoading(true);
            const response = await apiService.get('/api/v1/specializations/');
            
            if (response && Array.isArray(response)) {
                // Filter available specializations based on progression rules
                const available = filterAvailableSpecializations(response);
                setAvailableSpecializations(available);
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            console.error('Error fetching specializations:', error);
            setError('Nem sikerült betölteni a szakirányokat');
        } finally {
            setLoading(false);
        }
    };

    const filterAvailableSpecializations = (allSpecs) => {
        return allSpecs.filter(spec => {
            // Internship is always available
            if (spec.code === 'INTERNSHIP') {
                return true;
            }
            
            // First semester - only Player
            if (semesterCount === 1) {
                return spec.code === 'PLAYER';
            }
            
            // Second semester+ - Player always available, Coach only if had Player
            if (semesterCount >= 2) {
                if (spec.code === 'PLAYER') {
                    return true;
                }
                if (spec.code === 'COACH') {
                    return currentUserSpecialization === 'PLAYER' || currentUserSpecialization === null;
                }
            }
            
            return false;
        });
    };
    
    const handleSpecializationSelect = async (specCode) => {
        try {
            setSaving(true);
            setError(null);
            
            // Update local state immediately
            onSelect(specCode);
            
            // Save to backend
            const response = await apiService.post('/api/v1/specializations/me', {
                specialization: specCode
            });
            
            if (response && response.message) {
                console.log(`✅ Specialization saved: ${response.user.specialization.name}`);
            } else {
                throw new Error('Failed to save specialization');
            }
            
        } catch (error) {
            console.error('Error saving specialization:', error);
            setError(`Hiba történt a szakirány mentésekor: ${error.message}`);
            // Reset selection on error
            onSelect(null);
        } finally {
            setSaving(false);
        }
    };
    
    if (loading) {
        return (
            <div className="specialization-loading">
                <div className="loading-spinner"></div>
                <p>Szakirányok betöltése...</p>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className="specialization-error">
                <p>{error}</p>
                <button onClick={fetchSpecializations} className="retry-button">
                    Újrapróbálás
                </button>
            </div>
        );
    }
    
    return (
        <div className="specialization-selector">
            <div className="specialization-header">
                <h2>🎓 Válassz szakirányt</h2>
                <p className="specialization-intro">
                    A szakirány választása segít személyre szabni a tananyagot, gyakorlatokat és projekteket az Ön céljaihoz.
                </p>
            </div>
            
            <div className="specialization-options">
                {availableSpecializations.map(spec => {
                    const isDisabled = saving;
                    
                    return (
                        <div 
                            key={spec.code}
                            className={`specialization-card ${selectedSpecialization === spec.code ? 'selected' : ''} ${saving ? 'saving' : ''}`}
                            onClick={() => !isDisabled && handleSpecializationSelect(spec.code)}
                        >
                        <div className="spec-icon">
                            <span className="icon-emoji">{spec.icon}</span>
                        </div>
                        
                        <div className="spec-content">
                            <h3>{spec.name}</h3>
                            <p className="spec-description">{spec.description}</p>
                            
                            <div className="spec-features">
                                <h4>Főbb területek:</h4>
                                <ul>
                                    {spec.features.map((feature, index) => (
                                        <li key={index}>{feature}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                        
                        <div className="spec-selection">
                            {selectedSpecialization === spec.code && (
                                <div className="selected-indicator">
                                    ✅ Kiválasztva
                                </div>
                            )}
                        </div>
                    </div>
                    );
                })}
            </div>
            
            {showProgressionInfo && (
                <div className="progression-info">
                    <h3>📈 Szakirány fejlődési útvonal</h3>
                    <div className="progression-path">
                        <div className={`progression-step ${semesterCount >= 1 ? 'available' : 'future'}`}>
                            <span className="step-number">1</span>
                            <span className="step-content">
                                <strong>⚽ Player</strong>
                                <small>1. szemeszter - Alapképzés</small>
                            </span>
                        </div>
                        
                        <div className="progression-arrow">→</div>
                        
                        <div className={`progression-step ${semesterCount >= 2 && (currentUserSpecialization === 'PLAYER' || currentUserSpecialization === null) ? 'available' : semesterCount >= 2 ? 'locked' : 'future'}`}>
                            <span className="step-number">2</span>
                            <span className="step-content">
                                <strong>👨‍🏫 Coach</strong>
                                <small>2. szemeszter+ - Player után</small>
                            </span>
                        </div>
                        
                        <div className="progression-arrow">→</div>
                        
                        <div className="progression-step available">
                            <span className="step-number">🎓</span>
                            <span className="step-content">
                                <strong>Internship</strong>
                                <small>Bármikor elérhető</small>
                            </span>
                        </div>
                    </div>
                    
                    <div className="current-status">
                        <strong>Jelenlegi helyzet:</strong> 
                        {semesterCount === 1 
                            ? " Első szemeszter - Player szakirány választható" 
                            : semesterCount >= 2 
                            ? ` ${semesterCount}. szemeszter - Player és Coach (Player után) elérhető`
                            : " Új felhasználó"
                        }
                        {currentUserSpecialization && (
                            <span className="user-spec"> | Jelenlegi: {currentUserSpecialization}</span>
                        )}
                    </div>
                </div>
            )}
            
            <div className="specialization-note">
                💡 <strong>Tudta?</strong> A szakirány később is módosítható a profil beállításokban.
            </div>
            
            {!hideNavigation && (
                <div className="specialization-actions">
                    <button 
                        onClick={onBack} 
                        className="action-button secondary"
                        disabled={saving}
                    >
                        ← Vissza
                    </button>
                    
                    <button 
                        onClick={onNext}
                        disabled={!selectedSpecialization || saving}
                        className="action-button primary"
                    >
                        {saving ? 'Mentés...' : 'Tovább →'}
                    </button>
                </div>
            )}
        </div>
    );
};

export default SpecializationSelector;