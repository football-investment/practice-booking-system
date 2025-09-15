import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';

const BookingModal = ({ session, onClose, onBookingComplete }) => {
  const [isBooking, setIsBooking] = useState(false);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState(null);

  // PAST SESSION PROTECTION
  useEffect(() => {
    if (session) {
      const now = new Date();
      const sessionStart = new Date(session.date_start);
      const sessionEnd = new Date(session.date_end);
      
      // Check if session is in the past or ongoing
      if (now >= sessionEnd) {
        setError('This session has already ended');
        return;
      }
      
      if (now >= sessionStart && now < sessionEnd) {
        setError('This session is currently ongoing and cannot be booked');
        return;
      }
      
      // Clear error if session is bookable
      setError(null);
    }
  }, [session]);

  const handleBooking = async () => {
    if (isBooking) return;
    
    // 24h deadline check
    const now = new Date();
    const sessionStart = new Date(session.date_start);
    const timeDiff = sessionStart - now;
    const hoursUntilSession = timeDiff / (1000 * 60 * 60);
    
    if (hoursUntilSession < 24) {
      setError('Cannot book within 24 hours of session start');
      return;
    }
    
    try {
      setIsBooking(true);
      setError(null);
      
      await apiService.createBooking({
        session_id: session.id,
        notes: notes.trim() || null,
        booking_type: 'online'
      });
      
      onBookingComplete?.();
      onClose();
    } catch (err) {
      console.error('Booking failed:', err);
      setError(err.response?.data?.message || err.enhancedMessage || err.message || 'Booking failed');
    } finally {
      setIsBooking(false);
    }
  };

  const formatDateTime = (dateString) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  if (!session) return null;

  return (
    <div className="modal-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }} onClick={onClose}>
      <div className="modal-content" style={{
        backgroundColor: 'white',
        padding: '30px',
        borderRadius: '8px',
        maxWidth: '500px',
        width: '90%',
        maxHeight: '80vh',
        overflow: 'auto',
        boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
      }} onClick={(e) => e.stopPropagation()}>
        
        <div className="modal-header" style={{marginBottom: '20px'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
            <div>
              <h3 style={{margin: '0 0 10px 0', color: '#495057'}}>📚 Book Session</h3>
              <h4 style={{margin: 0, color: '#007bff'}}>{session.title}</h4>
            </div>
            <button 
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '24px',
                cursor: 'pointer',
                color: '#aaa',
                padding: 0,
                lineHeight: 1
              }}
            >
              ×
            </button>
          </div>
        </div>
        
        <div className="session-details" style={{
          backgroundColor: '#f8f9fa',
          padding: '20px',
          borderRadius: '6px',
          marginBottom: '20px',
          border: '1px solid #e9ecef'
        }}>
          <div style={{display: 'grid', gap: '8px'}}>
            <p style={{margin: 0, display: 'flex', alignItems: 'center'}}>
              <span style={{minWidth: '100px', fontWeight: 'bold'}}>📅 Date:</span>
              <span>{formatDateTime(session.date_start)}</span>
            </p>
            <p style={{margin: 0, display: 'flex', alignItems: 'center'}}>
              <span style={{minWidth: '100px', fontWeight: 'bold'}}>⏱️ Duration:</span>
              <span>{session.duration || 'TBD'} minutes</span>
            </p>
            <p style={{margin: 0, display: 'flex', alignItems: 'center'}}>
              <span style={{minWidth: '100px', fontWeight: 'bold'}}>👨‍🏫 Instructor:</span>
              <span>{session.instructor?.name || 'TBD'}</span>
            </p>
            <p style={{margin: 0, display: 'flex', alignItems: 'center'}}>
              <span style={{minWidth: '100px', fontWeight: 'bold'}}>👥 Capacity:</span>
              <span>{session.current_bookings || 0}/{session.capacity || 0}</span>
            </p>
            {session.location && (
              <p style={{margin: 0, display: 'flex', alignItems: 'center'}}>
                <span style={{minWidth: '100px', fontWeight: 'bold'}}>📍 Location:</span>
                <span>{session.location}</span>
              </p>
            )}
            {session.mode && (
              <p style={{margin: 0, display: 'flex', alignItems: 'center'}}>
                <span style={{minWidth: '100px', fontWeight: 'bold'}}>💻 Mode:</span>
                <span style={{
                  textTransform: 'capitalize',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '12px',
                  backgroundColor: session.mode === 'online' ? '#d4edda' : '#fff3cd',
                  color: session.mode === 'online' ? '#155724' : '#856404'
                }}>
                  {session.mode}
                </span>
              </p>
            )}
            {session.description && (
              <div style={{marginTop: '10px'}}>
                <p style={{margin: '0 0 5px 0', fontWeight: 'bold'}}>📝 Description:</p>
                <p style={{margin: 0, color: '#6c757d', fontSize: '14px', lineHeight: '1.4'}}>
                  {session.description}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* DEADLINE WARNING */}
        {(() => {
          const now = new Date();
          const sessionStart = new Date(session.date_start);
          const timeDiff = sessionStart - now;
          const hoursUntilSession = timeDiff / (1000 * 60 * 60);
          
          if (hoursUntilSession < 24) {
            return (
              <div style={{
                backgroundColor: '#fff3cd',
                border: '1px solid #ffc107',
                borderRadius: '6px',
                padding: '12px',
                marginBottom: '15px',
                color: '#856404'
              }}>
                ⚠️ This session starts in {Math.round(hoursUntilSession)} hours. 
                Booking is only allowed 24+ hours before session start.
              </div>
            );
          }
          return null;
        })()}

        {error && (
          <div style={{
            backgroundColor: '#f8d7da',
            border: '1px solid #f5c6cb',
            padding: '10px',
            borderRadius: '4px',
            marginBottom: '15px',
            color: '#721c24'
          }}>
            <strong>⚠️ Error:</strong> {error}
          </div>
        )}

        <div style={{marginBottom: '20px'}}>
          <label style={{display: 'block', marginBottom: '8px', fontWeight: 'bold', color: '#495057'}}>
            📝 Notes (optional):
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any special notes, questions, or requirements for this session..."
            rows="3"
            style={{
              width: '100%',
              padding: '10px',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              resize: 'vertical',
              fontFamily: 'inherit',
              fontSize: '14px',
              boxSizing: 'border-box'
            }}
          />
          <small style={{color: '#6c757d', fontSize: '12px'}}>
            This information will be visible to your instructor.
          </small>
        </div>
        
        <div style={{display: 'flex', gap: '10px', justifyContent: 'flex-end'}}>
          <button
            onClick={onClose}
            disabled={isBooking}
            style={{
              padding: '12px 24px',
              border: '1px solid #6c757d',
              borderRadius: '4px',
              backgroundColor: 'white',
              color: '#6c757d',
              cursor: isBooking ? 'not-allowed' : 'pointer',
              opacity: isBooking ? 0.6 : 1,
              fontWeight: '500',
              transition: 'all 0.2s'
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleBooking}
            disabled={isBooking}
            style={{
              padding: '12px 24px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: '#007bff',
              color: 'white',
              cursor: isBooking ? 'not-allowed' : 'pointer',
              opacity: isBooking ? 0.6 : 1,
              fontWeight: '500',
              transition: 'all 0.2s',
              boxShadow: isBooking ? 'none' : '0 2px 4px rgba(0,123,255,0.2)'
            }}
          >
            {isBooking ? '⏳ Booking...' : '✅ Confirm Booking'}
          </button>
        </div>
        
        {/* Booking Progress Indicator */}
        {isBooking && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(255,255,255,0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '8px'
          }}>
            <div style={{
              textAlign: 'center'
            }}>
              <div style={{
                border: '4px solid #f3f3f3',
                borderTop: '4px solid #007bff',
                borderRadius: '50%',
                width: '40px',
                height: '40px',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 10px'
              }}></div>
              <p style={{margin: 0, color: '#495057'}}>Creating your booking...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BookingModal;