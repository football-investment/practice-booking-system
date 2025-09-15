import React from 'react';
import './SessionCard.css';

const SessionCard = ({ session, onViewDetails, onBook, isBooking = false }) => {
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  };

  const calculateDuration = (startStr, endStr) => {
    const start = new Date(startStr);
    const end = new Date(endStr);
    const duration = Math.round((end - start) / (1000 * 60));
    return duration;
  };

  const getAvailabilityColor = (current, capacity) => {
    const ratio = current / capacity;
    if (ratio >= 0.9) return '#ff6b6b'; // Red - almost full
    if (ratio >= 0.7) return '#ffa726'; // Orange - filling up
    return '#4caf50'; // Green - available
  };

  // Sport category colors (admin configurable base colors)
  const getSportColors = (sport) => {
    const sportColorMap = {
      'football': { base: '#28a745', light: '#34ce57', dark: '#1e7e34' },
      'basketball': { base: '#ff6b35', light: '#ff8c69', dark: '#d55529' },
      'tennis': { base: '#ffd700', light: '#ffed4e', dark: '#ccac00' },
      'swimming': { base: '#17a2b8', light: '#46b8da', dark: '#117a8b' },
      'boxing': { base: '#dc3545', light: '#e76370', dark: '#a71e2a' },
      'programming': { base: '#6f42c1', light: '#8a63d2', dark: '#5a2d91' },
      'volleyball': { base: '#fd7e14', light: '#ff922b', dark: '#ca5d11' },
      'yoga': { base: '#6f9654', light: '#83a869', dark: '#557a41' }
    };
    return sportColorMap[sport?.toLowerCase()] || { base: '#6c757d', light: '#8fa8b2', dark: '#495057' };
  };

  // Level intensity mapping (lighter = easier, darker = harder)
  const getLevelIntensity = (level, baseColors) => {
    const levelMap = {
      'all levels': baseColors.light,
      'beginner': baseColors.light,
      'intermediate': baseColors.base,
      'advanced': baseColors.dark,
      'expert': baseColors.dark
    };
    return levelMap[level?.toLowerCase()] || baseColors.base;
  };

  const getSportIcon = (sport) => {
    switch(sport?.toLowerCase()) {
      case 'football': return '⚽';
      case 'basketball': return '🏀';
      case 'tennis': return '🎾';
      case 'swimming': return '🏊';
      case 'boxing': return '🥊';
      case 'programming': return '💻';
      default: return '🏃';
    }
  };

  // Ensure we have all required data with defaults
  const safeSession = {
    ...session,
    title: session.title || `Session ${session.id}`,
    instructor_name: session.instructor_name || (typeof session.instructor === 'object' ? session.instructor?.name : session.instructor) || "TBD",
    location: session.location || "TBD", 
    sport_type: session.sport_type || "General",
    level: session.level || "All Levels",
    description: session.description || "Training session",
    capacity: session.capacity || 20,
    current_bookings: session.current_bookings || 0,
    is_full: session.is_full || false
  };

  const duration = calculateDuration(safeSession.date_start, safeSession.date_end);
  const availabilityRatio = safeSession.current_bookings / safeSession.capacity;
  
  // Get dynamic colors for this session
  const sportColors = getSportColors(safeSession.sport_type);
  const levelColor = getLevelIntensity(safeSession.level, sportColors);
  
  return (
    <div className="session-card-improved" data-testid="session-card">
      {/* Header with sport type and level */}
      <div 
        className="session-header"
        style={{ 
          background: `linear-gradient(135deg, ${sportColors.base} 0%, ${sportColors.dark} 100%)` 
        }}
      >
        <div className="sport-badge">
          {getSportIcon(safeSession.sport_type)} {safeSession.sport_type}
        </div>
        <div 
          className="level-badge"
          style={{ backgroundColor: levelColor }}
        >
          {safeSession.level}
        </div>
      </div>

      {/* Main content */}
      <div className="session-main">
        <h3 className="session-title">{safeSession.title}</h3>
        <p className="session-description">{safeSession.description}</p>
        
        {/* Key info grid */}
        <div className="session-info-grid">
          <div className="info-item">
            <span className="info-icon">📅</span>
            <span>{formatDate(safeSession.date_start)}</span>
          </div>
          
          <div className="info-item">
            <span className="info-icon">🕐</span>
            <span>{formatTime(safeSession.date_start)} ({duration}min)</span>
          </div>
          
          <div className="info-item">
            <span className="info-icon">📍</span>
            <span>{safeSession.location}</span>
          </div>
          
          <div className="info-item">
            <span className="info-icon">👤</span>
            <span>{safeSession.instructor_name}</span>
          </div>
        </div>

        {/* Availability indicator */}
        <div className="availability-section">
          <div className="availability-bar">
            <div 
              className="availability-fill"
              style={{ 
                width: `${availabilityRatio * 100}%`,
                backgroundColor: getAvailabilityColor(safeSession.current_bookings, safeSession.capacity)
              }}
            ></div>
          </div>
          <div className="availability-text">
            <span className="info-icon">👥</span>
            <span>{safeSession.current_bookings}/{safeSession.capacity} booked</span>
            {safeSession.is_full && <span className="full-badge">FULL</span>}
          </div>
        </div>
      </div>

      {/* Action button */}
      <div className="session-footer">
        <button 
          className="view-details-btn-improved"
          data-testid="book-button"
          onClick={() => {
            if (safeSession.is_full || new Date(safeSession.date_start) <= new Date()) {
              onViewDetails(safeSession);
            } else {
              onBook(safeSession);
            }
          }}
          disabled={isBooking}
        >
          {isBooking ? 'Booking...' :
           new Date(safeSession.date_start) <= new Date() ? 'Session Ended' :
           safeSession.is_full ? 'Full - View Details' : 'Book Now'}
        </button>
      </div>
    </div>
  );
};

export default SessionCard;