import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
import './ParallelSpecializationSelector.css';

const ParallelSpecializationSelector = ({
    onNext,
    hideNavigation = false
}) => {
    const [activeSpecializations, setActiveSpecializations] = useState([]);
    const [availableSpecializations, setAvailableSpecializations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchSpecializationData();
    }, []);

    const fetchSpecializationData = async () => {
        try {
            setLoading(true);
            const dashboard = await apiService.get('/parallel-specializations/dashboard');
            setActiveSpecializations(dashboard.active_specializations || []);
            setAvailableSpecializations(dashboard.available_specializations || []);
            setError(null);
        } catch (err) {
            console.error('Failed to load specialization data:', err);
            setError('Failed to load specialization data. Please refresh the page.');
        } finally {
            setLoading(false);
        }
    };

    const handleStartSpecialization = async (specializationType) => {
        try {
            setSaving(true);
            setError(null);

            await apiService.post('/parallel-specializations/start', {
                specialization_type: specializationType
            });

            await fetchSpecializationData();

            if (onNext) {
                onNext();
            }
        } catch (err) {
            console.error('Failed to start specialization:', err);
            setError(err.response?.data?.detail || 'Failed to start specialization. Please try again.');
        } finally {
            setSaving(false);
        }
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

    const getSpecializationTitle = (type) => {
        const titles = {
            GANCUJU_PLAYER: 'GānCuju Player',
            LFA_FOOTBALL_PLAYER: 'LFA Football Player',
            LFA_COACH: 'LFA Coach',
            INTERNSHIP: 'Internship Program'
        };
        return titles[type] || type;
    };

    const getSpecializationDescription = (type) => {
        const descriptions = {
            GANCUJU_PLAYER: '8-Level Development System for advanced football training',
            LFA_FOOTBALL_PLAYER: 'Professional player development program with modern techniques',
            LFA_COACH: 'Professional coaching certification (UEFA standards)',
            INTERNSHIP: 'Practical experience in sports management and coaching'
        };
        return descriptions[type] || '';
    };

    if (loading) {
        return (
            <div className="specialization-selector-container">
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading specializations...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="specialization-selector-container">
            <div className="specialization-header">
                <h1>🎓 Specialization Selection</h1>
                <p className="subtitle">Choose your learning path</p>
            </div>

            {error && (
                <div className="error-banner">
                    <span className="error-icon">⚠️</span>
                    <span>{error}</span>
                </div>
            )}

            {activeSpecializations.length > 0 && (
                <div className="active-specializations-section">
                    <h2>Your Active Specializations</h2>
                    <div className="specializations-grid">
                        {activeSpecializations.map((spec) => (
                            <div key={spec.specialization_type} className="spec-card active">
                                <div className="spec-icon">{getSpecializationIcon(spec.specialization_type)}</div>
                                <h3>{getSpecializationTitle(spec.specialization_type)}</h3>
                                <div className="spec-status active-badge">Active</div>
                                <div className="spec-progress">
                                    <div className="progress-label">Level {spec.current_level || 1}</div>
                                    {spec.start_date && (
                                        <div className="date-info">
                                            Started: {new Date(spec.start_date).toLocaleDateString('en-US')}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {availableSpecializations.length > 0 && (
                <div className="available-specializations-section">
                    <h2>Available Specializations</h2>
                    <div className="specializations-grid">
                        {availableSpecializations.map((spec) => (
                            <div key={spec.specialization_type} className="spec-card available">
                                <div className="spec-icon">{getSpecializationIcon(spec.specialization_type)}</div>
                                <h3>{getSpecializationTitle(spec.specialization_type)}</h3>
                                <p className="spec-description">
                                    {getSpecializationDescription(spec.specialization_type)}
                                </p>
                                <div className="spec-requirements">
                                    {spec.age_requirement && (
                                        <div className="requirement">
                                            Age: {spec.age_requirement}+
                                        </div>
                                    )}
                                    {spec.payment_required && (
                                        <div className="requirement">
                                            Payment: Required
                                        </div>
                                    )}
                                </div>
                                <button
                                    className="start-button"
                                    onClick={() => handleStartSpecialization(spec.specialization_type)}
                                    disabled={saving}
                                >
                                    {saving ? 'Starting...' : 'Start Specialization'}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {availableSpecializations.length === 0 && activeSpecializations.length > 0 && (
                <div className="info-banner">
                    <p>You have reached the maximum number of active specializations.</p>
                </div>
            )}

            {!hideNavigation && activeSpecializations.length > 0 && (
                <div className="navigation-buttons">
                    <button
                        className="continue-button"
                        onClick={onNext}
                        disabled={saving}
                    >
                        Continue to Dashboard →
                    </button>
                </div>
            )}
        </div>
    );
};

export default ParallelSpecializationSelector;
