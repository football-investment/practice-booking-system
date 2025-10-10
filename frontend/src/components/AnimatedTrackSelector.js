import React, { useState, useEffect } from 'react';

const AnimatedTrackSelector = () => {
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [animationStage, setAnimationStage] = useState('enter');

  useEffect(() => {
    // Entrance animation sequence
    const timer = setTimeout(() => {
      setAnimationStage('ready');
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  const tracks = [
    {
      id: 'player',
      title: 'Player Track',
      subtitle: 'GānCuju™️©️ Játékos Specializáció',
      emoji: '⚽',
      animatedEmojis: ['⚽', '🥅', '🏆', '👕', '⭐'],
      color: '#4F46E5',
      gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
      description: 'Játékos fejlesztés és futball technikák',
      features: ['8 szintes fejlődési rendszer', 'Labdaérzék fejlesztés', 'Taktikai képzés']
    },
    {
      id: 'coach',
      title: 'Coach Track', 
      subtitle: 'LFA Edzői Specializáció',
      emoji: '👨‍🏫',
      animatedEmojis: ['👨‍🏫', '📋', '🎯', '📊', '🏅'],
      color: '#DC2626',
      gradient: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
      description: 'Edzői készségek és csapatvezetés',
      features: ['Taktikai elemzés', 'Csapatépítés', 'Kommunikáció']
    },
    {
      id: 'internship',
      title: 'Internship Track',
      subtitle: 'LFA Gyakornoki Program', 
      emoji: '💼',
      animatedEmojis: ['💼', '📈', '🤝', '🎓', '🌟'],
      color: '#059669',
      gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
      description: 'Gyakorlati tapasztalat és szakmai fejlődés',
      features: ['Mentorálás', 'Projekt munka', 'Networking']
    }
  ];

  const FloatingEmoji = ({ emoji, delay, duration = 3 }) => {
    const [position, setPosition] = useState({ x: 0, y: 0 });
    
    useEffect(() => {
      const interval = setInterval(() => {
        setPosition({
          x: Math.sin(Date.now() / 1000 + delay) * 20,
          y: Math.cos(Date.now() / 1500 + delay) * 15
        });
      }, 50);
      
      return () => clearInterval(interval);
    }, [delay]);

    return (
      <div 
        className="floating-emoji"
        style={{
          position: 'absolute',
          fontSize: '1.5rem',
          opacity: 0.7,
          pointerEvents: 'none',
          transform: `translate(${position.x}px, ${position.y}px)`,
          transition: 'transform 0.1s ease-out',
          animationDelay: `${delay}s`
        }}
      >
        {emoji}
      </div>
    );
  };

  const TrackCard = ({ track, index }) => {
    const [isHovered, setIsHovered] = useState(false);
    const [currentEmojiIndex, setCurrentEmojiIndex] = useState(0);
    const isSelected = selectedTrack === track.id;

    useEffect(() => {
      if (isHovered) {
        const interval = setInterval(() => {
          setCurrentEmojiIndex(prev => (prev + 1) % track.animatedEmojis.length);
        }, 400);
        return () => clearInterval(interval);
      }
    }, [isHovered, track.animatedEmojis.length]);

    return (
      <div
        className="track-card"
        style={{ 
          position: 'relative',
          overflow: 'hidden',
          borderRadius: '16px',
          cursor: 'pointer',
          transition: 'all 0.5s ease',
          transform: animationStage === 'enter' ? 'translateY(20px)' : 'translateY(0)',
          opacity: animationStage === 'enter' ? 0 : 1,
          background: track.gradient,
          minHeight: '420px',
          margin: '0 auto',
          width: '100%',
          maxWidth: '350px',
          boxShadow: isSelected ? '0 25px 50px rgba(0,0,0,0.25)' : '0 10px 25px rgba(0,0,0,0.15)',
          scale: isSelected ? '1.05' : (isHovered ? '1.02' : '1.0'),
          animationDelay: `${index * 150}ms`
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => setSelectedTrack(isSelected ? null : track.id)}
      >
        {/* Background Pattern */}
        <div style={{ position: 'absolute', inset: 0, opacity: 0.1 }}>
          <div style={{ position: 'absolute', top: '16px', right: '16px' }}>
            <FloatingEmoji emoji={track.animatedEmojis[1]} delay={0} />
          </div>
          <div style={{ position: 'absolute', bottom: '24px', left: '24px' }}>
            <FloatingEmoji emoji={track.animatedEmojis[2]} delay={1} />
          </div>
          <div style={{ position: 'absolute', top: '50%', right: '24px' }}>
            <FloatingEmoji emoji={track.animatedEmojis[3]} delay={2} />
          </div>
        </div>

        {/* Content */}
        <div style={{ position: 'relative', padding: '24px', height: '100%', display: 'flex', flexDirection: 'column', color: 'white' }}>
          {/* Main Emoji */}
          <div style={{ textAlign: 'center', marginBottom: '16px' }}>
            <div 
              style={{
                fontSize: '4rem',
                transition: 'all 0.3s ease',
                transform: `scale(${isHovered ? 1.25 : 1.0}) rotate(${isHovered ? 12 : 0}deg)`,
                display: 'inline-block',
                animation: isSelected ? 'bounce 1s infinite' : 'none'
              }}
            >
              {isHovered ? track.animatedEmojis[currentEmojiIndex] : track.emoji}
            </div>
          </div>

          {/* Title */}
          <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', textAlign: 'center', marginBottom: '8px' }}>
            {track.title}
          </h3>
          
          <p style={{ color: 'rgba(255,255,255,0.9)', textAlign: 'center', fontSize: '0.875rem', marginBottom: '16px', fontWeight: '500' }}>
            {track.subtitle}
          </p>

          {/* Description */}
          <div style={{ flex: 1, textAlign: 'center' }}>
            <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.875rem', lineHeight: '1.6', marginBottom: '16px' }}>
              {track.description}
            </p>

            {/* Features - Show on hover or selection */}
            <div style={{
              transition: 'all 0.3s ease',
              overflow: 'hidden',
              maxHeight: (isHovered || isSelected) ? '160px' : '0',
              opacity: (isHovered || isSelected) ? 1 : 0
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {track.features.map((feature, idx) => (
                  <div 
                    key={idx}
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center', 
                      color: 'rgba(255,255,255,0.9)', 
                      fontSize: '0.75rem',
                      animationDelay: `${idx * 100}ms`
                    }}
                  >
                    <span style={{ marginRight: '8px' }}>✨</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Selection Indicator */}
          {isSelected && (
            <div style={{ textAlign: 'center', marginTop: '16px' }}>
              <div style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                background: 'rgba(255,255,255,0.2)', 
                borderRadius: '20px', 
                padding: '8px 16px', 
                fontSize: '0.875rem', 
                fontWeight: '500' 
              }}>
                <span style={{ marginRight: '8px' }}>✅</span>
                Kiválasztva
              </div>
            </div>
          )}

          {/* Hover Indicator */}
          {isHovered && !isSelected && (
            <div style={{ textAlign: 'center', marginTop: '16px' }}>
              <div style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                background: 'rgba(255,255,255,0.1)', 
                borderRadius: '20px', 
                padding: '8px 16px', 
                fontSize: '0.875rem' 
              }}>
                <span style={{ marginRight: '8px' }}>👆</span>
                Kattints a kiválasztáshoz
              </div>
            </div>
          )}
        </div>

        {/* Selection Glow Effect */}
        {isSelected && (
          <div style={{ 
            position: 'absolute', 
            inset: 0, 
            border: '4px solid rgba(255,255,255,0.5)', 
            borderRadius: '16px', 
            animation: 'pulse 2s infinite' 
          }}></div>
        )}
      </div>
    );
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%)', 
      padding: '16px' 
    }}>
      {/* Header */}
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <div style={{ marginBottom: '16px' }}>
            <span style={{ fontSize: '4rem', animation: 'bounce 2s infinite', display: 'inline-block' }}>🏆</span>
          </div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '16px' }}>
            Üdvözölünk az LFA Képzési Rendszerben!
          </h1>
          <p style={{ color: '#64748b', fontSize: '1.125rem' }}>
            Válassz egy szakirányból és kezdd el a fejlődést 🚀
          </p>
        </div>

        {/* Track Selection Grid */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
          gap: '32px', 
          marginBottom: '48px',
          justifyItems: 'center'
        }}>
          {tracks.map((track, index) => (
            <TrackCard key={track.id} track={track} index={index} />
          ))}
        </div>

        {/* Action Button */}
        {selectedTrack && (
          <div style={{ textAlign: 'center' }}>
            <button 
              style={{
                background: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)',
                color: 'white',
                fontWeight: 'bold',
                padding: '16px 32px',
                borderRadius: '50px',
                transform: 'scale(1)',
                transition: 'all 0.3s ease',
                boxShadow: '0 10px 25px rgba(0,0,0,0.15)',
                border: 'none',
                cursor: 'pointer',
                fontSize: '1rem',
                animation: 'fadeIn 0.5s ease-out'
              }}
              onMouseEnter={(e) => e.target.style.transform = 'scale(1.05)'}
              onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
              onClick={() => alert(`${tracks.find(t => t.id === selectedTrack)?.title} kiválasztva! 🎉`)}
            >
              <span style={{ marginRight: '8px' }}>🚀</span>
              Folytatás a kiválasztott képzéssel
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
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}} />
    </div>
  );
};

export default AnimatedTrackSelector;