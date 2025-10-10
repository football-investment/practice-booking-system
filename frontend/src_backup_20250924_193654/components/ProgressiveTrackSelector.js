import React, { useState, useEffect } from 'react';
import progressionService from '../services/progressionService';

// Enhanced track data with rotating emojis and detailed descriptions
const TRACK_ENHANCEMENTS = {
  internship: {
    emojis: ['💼', '🎯', '📈', '🚀'],
    description: `A gyakorlati tapasztalatok megszerzésének helye. 
    Itt fejlődhet a futballal kapcsolatos tudásod, 
    miközben valós projekteken dolgozol tapasztalt 
    mentorok irányítása alatt.`
  },
  coach: {
    emojis: ['👨‍🏫', '⚽', '🏆', '📋'],
    description: `Teljes körű edzői képzés alapoktól a profi szintig. 
    Specializációs lehetőségekkel: kapusedző, erőnléti 
    edző és rehabilitációs szakember területeken. 
    Hivatalos LFA minősítéssel.`
  },
  gancuju: {
    emojis: ['⚽', '🐲', '🌙', '🎋'],
    description: `8 szintű hagyományos kínai futball művészet. 
    A Bambusz Tanítványtól a Sárkány Bölcsességig. 
    Egyedülálló fejlesztési rendszer a test-lélek 
    harmóniájának megteremtésére.`
  }
};

const ProgressiveTrackSelector = () => {
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [progressionSystems, setProgressionSystems] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [emojiIndex, setEmojiIndex] = useState(0);

  // Load user progress and systems on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        console.log('Starting API calls...');
        
        // Call both endpoints
        let userProgress, systemsResponse;
        
        try {
          console.log('Calling getProgressionSystems...');
          systemsResponse = await progressionService.getProgressionSystems();
          console.log('getProgressionSystems success:', systemsResponse);
        } catch (err) {
          console.error('getProgressionSystems failed:', err);
          systemsResponse = null;
        }
        
        try {
          console.log('Calling getUserProgress...');
          userProgress = await progressionService.getUserProgress();
          console.log('getUserProgress success:', userProgress);
        } catch (err) {
          console.error('getUserProgress failed:', err);
          // Fallback to mock user progress
          userProgress = {
            internship_level: 'junior',
            coach_foundation_level: 'pre_assistant', 
            coach_specializations: [],
            gancuju_level: 'bamboo',
            completed_semesters: { internship: 1, coach: 1, gancuju: 1 }
          };
        }
        
        console.log('Raw user progress:', userProgress);
        console.log('Raw systems response:', systemsResponse);
        console.log('Type of systems response:', typeof systemsResponse);
        
        setCurrentUser(userProgress);
        // Handle different API response structures
        console.log('Systems response:', systemsResponse);
        const systems = systemsResponse?.systems || systemsResponse?.data?.systems || systemsResponse;
        
        // Validate that we have the expected structure
        if (!systems || typeof systems !== 'object') {
          throw new Error('Invalid systems response structure');
        }
        
        // Check if we have the expected tracks
        if (!systems.internship || !systems.coach || !systems.gancuju) {
          console.warn('Missing expected tracks, falling back to mock data');
          setProgressionSystems(getMockSystems());
        } else {
          setProgressionSystems(systems);
        }
        setError(null);
      } catch (err) {
        console.error('Error loading progression data:', err);
        setError('Failed to load progression data');
        
        // Fallback to mock data
        setCurrentUser({
          internship_level: 'junior',
          coach_foundation_level: 'pre_assistant',
          coach_specializations: [],
          gancuju_level: 'bamboo',
          completed_semesters: { internship: 1, coach: 1, gancuju: 1 }
        });
        setProgressionSystems(getMockSystems());
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // Emoji rotation animation
  useEffect(() => {
    const interval = setInterval(() => {
      setEmojiIndex(prev => (prev + 1) % 4); // Cycle through 4 emojis
    }, 2000); // Change every 2 seconds

    return () => clearInterval(interval);
  }, []);

  // Mock systems for fallback
  const getMockSystems = () => ({
    internship: {
      id: 'internship',
      title: 'Internship Track',
      subtitle: 'LFA Gyakornoki Program',
      emoji: '💼',
      color: '#059669',
      gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
      levels: ['junior', 'medior', 'senior'],
      prerequisites: { medior: 'junior', senior: 'medior' }
    },
    coach: {
      id: 'coach',
      title: 'Coach Track',
      subtitle: 'LFA Edzői Specializáció',
      emoji: '👨‍🏫',
      color: '#DC2626',
      gradient: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
      foundation_levels: ['pre_assistant', 'pre_lead', 'youth_assistant', 'youth_lead', 'amateur_assistant', 'amateur_lead', 'pro_assistant', 'pro_lead'],
      specializations: ['goalkeeper', 'fitness', 'rehabilitation'],
      prerequisites: { pre_lead: 'pre_assistant', youth_assistant: 'pre_lead' },
      specialization_prerequisite: 'pre_lead'
    },
    gancuju: {
      id: 'gancuju',
      title: 'GānCuju™️©️ Track',
      subtitle: '8 Szintű Játékos Fejlesztési Rendszer',
      emoji: '⚽',
      color: '#4F46E5',
      gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
      levels: ['bamboo', 'dawn', 'reed', 'river', 'root', 'moon', 'guardian', 'dragon'],
      prerequisites: { dawn: 'bamboo', reed: 'dawn', river: 'reed', root: 'river', moon: 'root', guardian: 'moon', dragon: 'guardian' }
    }
  });

  // Loading state
  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'var(--bg-gradient-primary, linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%))',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '4rem', marginBottom: '16px' }}>⏳</div>
          <h2 style={{ color: 'var(--text-primary, #1e293b)' }}>Progresszió betöltése...</h2>
          <p style={{ color: 'var(--text-secondary, #64748b)' }}>Kérjük, várjon amíg betöltjük az aktuális állapotot.</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'var(--bg-gradient-primary, linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%))',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '4rem', marginBottom: '16px' }}>⚠️</div>
          <h2 style={{ color: 'var(--text-error, #dc2626)' }}>Hiba történt</h2>
          <p style={{ color: 'var(--text-secondary, #64748b)', marginBottom: '16px' }}>{error}</p>
          <button 
            onClick={() => window.location.reload()}
            style={{
              background: '#3b82f6',
              color: 'white',
              padding: '12px 24px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            Újratöltés
          </button>
        </div>
      </div>
    );
  }

  if (!currentUser || !progressionSystems || Object.keys(progressionSystems).length === 0) {
    return null;
  }

  const ProgressBar = ({ current, total, color, showNumbers = true }) => (
    <div style={{ width: '100%', marginBottom: '8px' }}>
      <div style={{
        width: '100%',
        height: '8px',
        backgroundColor: 'rgba(255,255,255,0.3)',
        borderRadius: '4px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${(current / total) * 100}%`,
          height: '100%',
          backgroundColor: color,
          transition: 'width 0.5s ease',
          borderRadius: '4px'
        }} />
      </div>
      {showNumbers && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'rgba(255,255,255,0.8)', marginTop: '4px' }}>
          <span>{current} / {total} szemeszter</span>
          <span>{Math.round((current / total) * 100)}%</span>
        </div>
      )}
    </div>
  );

  const LevelIndicator = ({ level, isActive, isCompleted, isLocked, onClick }) => {
    const getStatusColor = () => {
      if (isCompleted) return '#10b981';
      if (isActive) return '#3b82f6';
      if (isLocked) return '#6b7280';
      return '#94a3b8';
    };

    const getStatusEmoji = () => {
      if (isCompleted) return '✅';
      if (isActive) return '🎯';
      if (isLocked) return '🔒';
      return '⭕';
    };

    return (
      <div
        onClick={!isLocked ? onClick : undefined}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '8px 12px',
          margin: '4px 0',
          backgroundColor: isActive ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255,255,255,0.05)',
          border: `2px solid ${getStatusColor()}`,
          borderRadius: '8px',
          cursor: isLocked ? 'not-allowed' : 'pointer',
          opacity: isLocked ? 0.5 : 1,
          transition: 'all 0.3s ease'
        }}
      >
        <span style={{ marginRight: '8px', fontSize: '1.2rem' }}>{getStatusEmoji()}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 'bold', fontSize: '0.9rem', color: 'var(--text-primary, #ffffff)' }}>
            {level.title}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary, rgba(255,255,255,0.7))' }}>
            {level.semesters} szemeszter • {level.description}
          </div>
        </div>
      </div>
    );
  };

  const TrackDetailView = ({ track }) => {
    const getCurrentLevel = () => {
      if (track.id === 'internship') {
        return track.levels?.indexOf(currentUser.internship_level) || 0;
      } else if (track.id === 'coach') {
        return track.foundation_levels?.indexOf(currentUser.coach_foundation_level) || 0;
      } else if (track.id === 'gancuju') {
        return track.levels?.indexOf(currentUser.gancuju_level) || 0;
      }
      return 0;
    };

    const getTotalSemesters = () => {
      // This would come from the backend's semester_counts
      if (track.id === 'internship') {
        return 3; // junior(1) + medior(1) + senior(1)
      } else if (track.id === 'coach') {
        return 32; // Foundation levels total + potential specializations
      } else if (track.id === 'gancuju') {
        return 8; // 8 levels, 1 semester each
      }
      return 0;
    };

    const currentLevelIndex = getCurrentLevel();
    const totalSemesters = getTotalSemesters();
    const completedSemesters = currentUser.completed_semesters?.[track.id] || 0;

    return (
      <div style={{
        backgroundColor: 'var(--card-background, rgba(255,255,255,0.95))',
        borderRadius: '16px',
        padding: '24px',
        margin: '16px 0',
        boxShadow: 'var(--shadow-large, 0 10px 25px rgba(0,0,0,0.1))'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
          <span style={{ fontSize: '3rem', marginRight: '16px' }}>{track.emoji}</span>
          <div>
            <h3 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)', marginBottom: '4px' }}>
              {track.title}
            </h3>
            <p style={{ color: 'var(--text-secondary, #64748b)', fontSize: '1rem' }}>{track.subtitle}</p>
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)', marginBottom: '12px' }}>
            Általános Haladás
          </h4>
          <ProgressBar 
            current={completedSemesters} 
            total={totalSemesters} 
            color={track.color}
          />
        </div>

        {/* Track-specific content */}
        {track.id === 'internship' && (
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)', marginBottom: '12px' }}>
              Gyakornoki Szintek
            </h4>
            {track.levels?.map((levelId, index) => {
              const levelNames = { junior: 'Junior', medior: 'Medior', senior: 'Senior' };
              const levelDescriptions = { 
                junior: 'Alapozó gyakornoki szint', 
                medior: 'Közepes szintű gyakorlat', 
                senior: 'Haladó gyakornoki pozíció' 
              };
              
              return (
                <LevelIndicator
                  key={levelId}
                  level={{ 
                    id: levelId, 
                    title: levelNames[levelId] || levelId,
                    description: levelDescriptions[levelId] || '',
                    semesters: 1
                  }}
                  isActive={index === currentLevelIndex}
                  isCompleted={index < currentLevelIndex}
                  isLocked={index > currentLevelIndex + 1}
                />
              );
            })}
          </div>
        )}

        {track.id === 'coach' && (
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)', marginBottom: '12px' }}>
              Alapképzési Szintek
            </h4>
            {track.foundation_levels?.map((levelId, index) => {
              const levelNames = {
                pre_assistant: 'LFA Pre Football Asszisztens Edző',
                pre_lead: 'LFA Pre Football Vezetőedző',
                youth_assistant: 'LFA Youth Football Asszisztens Edző',
                youth_lead: 'LFA Youth Football Vezetőedző',
                amateur_assistant: 'LFA Amateur Football Asszisztens Edző',
                amateur_lead: 'LFA Amateur Football Vezetőedző',
                pro_assistant: 'LFA PRO Football Asszisztens Edző',
                pro_lead: 'LFA PRO Football Vezetőedző'
              };
              
              return (
                <LevelIndicator
                  key={levelId}
                  level={{ 
                    id: levelId, 
                    title: levelNames[levelId] || levelId,
                    description: 'Edzői képzés',
                    semesters: index < 2 ? index + 1 : index + 2
                  }}
                  isActive={index === currentLevelIndex}
                  isCompleted={index < currentLevelIndex}
                  isLocked={index > currentLevelIndex + 1}
                />
              );
            })}

            {currentUser.coach_foundation_level && 
             track.foundation_levels?.indexOf(currentUser.coach_foundation_level) >= 1 && (
              <div style={{ marginTop: '24px' }}>
                <h4 style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)', marginBottom: '12px' }}>
                  Specializációs Modulok <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary, #64748b)' }}>(Pre Football Vezetőedző után elérhető)</span>
                </h4>
                {track.specializations?.map((specId) => {
                  const specNames = {
                    goalkeeper: 'LFA Kapusedző',
                    fitness: 'LFA Erőnléti edző',
                    rehabilitation: 'LFA Rehabilitációs szakember'
                  };
                  
                  return (
                    <LevelIndicator
                      key={specId}
                      level={{
                        id: specId,
                        title: specNames[specId] || specId,
                        description: 'Szakirányú képzés',
                        semesters: 2
                      }}
                      isActive={false}
                      isCompleted={currentUser.coach_specializations?.includes(specId)}
                      isLocked={false}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}

        {track.id === 'gancuju' && (
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)', marginBottom: '12px' }}>
              8 Szintű Fejlődési Rendszer
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
              {track.levels?.map((levelId, index) => {
                const levelData = {
                  bamboo: { title: 'Bambusz Tanítvány', color: '#f8fafc' },
                  dawn: { title: 'Hajnali Harmat', color: '#fbbf24' },
                  reed: { title: 'Rugalmas Nád', color: '#10b981' },
                  river: { title: 'Égi Folyó', color: '#3b82f6' },
                  root: { title: 'Erős Gyökér', color: '#92400e' },
                  moon: { title: 'Téli Hold', color: '#6b7280' },
                  guardian: { title: 'Éjfél Őrzője', color: '#1f2937' },
                  dragon: { title: 'Sárkány Bölcsesség', color: '#dc2626' }
                };
                
                const level = levelData[levelId] || { title: levelId, color: '#e5e7eb' };
                
                return (
                  <div key={levelId} style={{
                    padding: '8px',
                    borderRadius: '8px',
                    border: `2px solid ${index === currentLevelIndex ? '#3b82f6' : (index < currentLevelIndex ? '#10b981' : '#e2e8f0')}`,
                    backgroundColor: index <= currentLevelIndex ? 'rgba(59, 130, 246, 0.1)' : 'rgba(0,0,0,0.02)',
                    textAlign: 'center'
                  }}>
                    <div style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      backgroundColor: level.color,
                      border: level.color === '#f8fafc' ? '2px solid #e2e8f0' : 'none',
                      margin: '0 auto 4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: level.color === '#1f2937' || level.color === '#dc2626' ? 'white' : 'black',
                      fontSize: '0.75rem'
                    }}>
                      {index < currentLevelIndex ? '✓' : (index === currentLevelIndex ? '🎯' : '')}
                    </div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)' }}>
                      {level.title}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #64748b)' }}>
                      1 szem.
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-gradient-primary, linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%))',
      padding: '16px'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ marginBottom: '16px' }}>
            <span style={{ fontSize: '4rem', animation: 'bounce 2s infinite', display: 'inline-block' }}>🏆</span>
          </div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-primary, #1e293b)', marginBottom: '16px' }}>
            LFA Progresszív Képzési Rendszer
          </h1>
          <p style={{ color: 'var(--text-secondary, #64748b)', fontSize: '1.125rem' }}>
            Kövesd nyomon a fejlődésedet és válassz a szakirányok közül! 🚀
          </p>
        </div>

        {/* Quick Stats */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '16px',
          marginBottom: '32px'
        }}>
          {Object.values(progressionSystems).map((track) => {
            const completedSemesters = currentUser.completed_semesters?.[track.id] || 0;
            const totalSemesters = track.id === 'coach' ? 32 : (track.id === 'internship' ? 3 : 8);
            const enhancement = TRACK_ENHANCEMENTS[track.id];
            const currentEmoji = enhancement?.emojis[emojiIndex] || track.emoji;

            return (
              <div
                key={track.id}
                onClick={() => setSelectedTrack(selectedTrack === track.id ? null : track.id)}
                style={{
                  background: track.gradient,
                  borderRadius: '16px',
                  padding: '24px',
                  color: 'white',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  transform: selectedTrack === track.id ? 'scale(1.02)' : 'scale(1)',
                  boxShadow: selectedTrack === track.id ? '0 15px 35px rgba(0,0,0,0.25)' : '0 8px 20px rgba(0,0,0,0.15)',
                  position: 'relative',
                  overflow: 'hidden'
                }}
              >
                {/* Animated background pattern */}
                <div style={{
                  position: 'absolute',
                  top: '-50%',
                  right: '-50%',
                  width: '200%',
                  height: '200%',
                  background: 'radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px)',
                  backgroundSize: '20px 20px',
                  animation: 'float 20s linear infinite',
                  zIndex: 0
                }} />
                
                <div style={{ position: 'relative', zIndex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: '16px' }}>
                    <div style={{ 
                      fontSize: '3rem', 
                      marginRight: '16px',
                      transition: 'transform 0.5s ease',
                      animation: 'emojiPulse 2s ease-in-out infinite'
                    }}>
                      {currentEmoji}
                    </div>
                    <div style={{ flex: 1 }}>
                      <h3 style={{ 
                        fontSize: '1.3rem', 
                        fontWeight: 'bold', 
                        marginBottom: '6px',
                        textShadow: '0 2px 4px rgba(0,0,0,0.3)'
                      }}>
                        {track.title}
                      </h3>
                      <p style={{ 
                        fontSize: '0.9rem', 
                        opacity: 0.95,
                        marginBottom: '12px',
                        textShadow: '0 1px 2px rgba(0,0,0,0.2)'
                      }}>
                        {track.subtitle}
                      </p>
                    </div>
                  </div>

                  {/* Enhanced description */}
                  <div style={{
                    fontSize: '0.85rem',
                    lineHeight: '1.4',
                    opacity: 0.9,
                    marginBottom: '16px',
                    padding: '12px',
                    backgroundColor: 'rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.2)',
                    textShadow: '0 1px 2px rgba(0,0,0,0.1)'
                  }}>
                    {enhancement?.description || 'Fejleszd magad ezen a területen!'}
                  </div>

                  <ProgressBar 
                    current={completedSemesters} 
                    total={totalSemesters} 
                    color="rgba(255,255,255,0.9)"
                    showNumbers={false}
                  />
                  <div style={{ 
                    fontSize: '0.8rem', 
                    opacity: 0.9, 
                    textAlign: 'center',
                    fontWeight: '600',
                    textShadow: '0 1px 2px rgba(0,0,0,0.2)'
                  }}>
                    {completedSemesters} / {totalSemesters} szemeszter teljesítve
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detailed Track View */}
        {selectedTrack && (
          <TrackDetailView track={progressionSystems[selectedTrack]} />
        )}

        {/* Continue Button */}
        {selectedTrack && (
          <div style={{ textAlign: 'center', marginTop: '32px' }}>
            <button 
              style={{
                background: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)',
                color: 'white',
                fontWeight: 'bold',
                padding: '16px 32px',
                borderRadius: '50px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '1rem',
                transition: 'all 0.3s ease',
                boxShadow: '0 10px 25px rgba(0,0,0,0.15)'
              }}
              onClick={() => alert(`${progressionSystems[selectedTrack].title} folytatása! 🎉`)}
            >
              <span style={{ marginRight: '8px' }}>🚀</span>
              Folytatás: {progressionSystems[selectedTrack].title}
              <span style={{ marginLeft: '8px' }}>✨</span>
            </button>
          </div>
        )}
      </div>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes bounce {
          0%, 20%, 53%, 80%, 100% { transform: translateY(0); }
          40%, 43% { transform: translateY(-30px); }
          70% { transform: translateY(-15px); }
          90% { transform: translateY(-4px); }
        }
        
        @keyframes emojiPulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
        
        @keyframes float {
          0% { transform: translate(-50%, -50%) rotate(0deg); }
          100% { transform: translate(-50%, -50%) rotate(360deg); }
        }
        
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        /* CSS Variables for Dark/Light Mode Support */
        :root {
          --text-primary: #1e293b;
          --text-secondary: #64748b;
          --text-error: #dc2626;
          --bg-gradient-primary: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
          --card-background: rgba(255,255,255,0.95);
          --shadow-large: 0 10px 25px rgba(0,0,0,0.1);
        }
        
        [data-theme="dark"], 
        .dark-mode,
        body.dark {
          --text-primary: #f1f5f9;
          --text-secondary: #94a3b8;
          --text-error: #f87171;
          --bg-gradient-primary: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          --card-background: rgba(30, 41, 59, 0.95);
          --shadow-large: 0 10px 25px rgba(0,0,0,0.3);
        }
        
        @media (prefers-color-scheme: dark) {
          :root:not([data-theme="light"]) {
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-error: #f87171;
            --bg-gradient-primary: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            --card-background: rgba(30, 41, 59, 0.95);
            --shadow-large: 0 10px 25px rgba(0,0,0,0.3);
          }
        }
      `}} />
    </div>
  );
};

export default ProgressiveTrackSelector;