import React, { useState } from 'react';
import { apiService } from '../../services/apiService';

const CheckinModal = ({ onClose, bookings, onCheckin }) => {
  const [checkinMethod, setCheckinMethod] = useState('qr'); // 'qr' or 'code'
  const [sessionCode, setSessionCode] = useState('');
  const [selectedBooking, setSelectedBooking] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [qrActive, setQrActive] = useState(false);

  const handleQRScan = () => {
    setQrActive(true);
    setError(null);
    
    // Simulate QR scanning
    setTimeout(() => {
      if (bookings.length > 0) {
        setSelectedBooking(bookings[0].id);
        onCheckin('Check-in successful via QR code!');
      } else {
        setError('No confirmed bookings found for check-in');
        setQrActive(false);
      }
    }, 3000);
  };

  const handleCodeCheckin = async () => {
    if (!sessionCode || sessionCode.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // For demo, we'll use the first confirmed booking
      if (bookings.length > 0) {
        await apiService.checkinToSession(bookings[0].id);
        onCheckin('Check-in successful!');
      } else {
        setError('No confirmed bookings found');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Check-in failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay show" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3 className="modal-title">📱 Session Check-in</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <div style={{ textAlign: 'center' }}>
            {error && (
              <div className="error-message" style={{ position: 'relative', marginBottom: '20px' }}>{error}</div>
            )}
            
            <h4>Choose Check-in Method:</h4>
            <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', margin: '20px 0' }}>
              <button 
                className={`btn ${checkinMethod === 'qr' ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => setCheckinMethod('qr')}
              >
                📷 Scan QR Code
              </button>
              <button 
                className={`btn ${checkinMethod === 'code' ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => setCheckinMethod('code')}
              >
                🔢 Enter Code
              </button>
            </div>
            
            {checkinMethod === 'qr' && (
              <div>
                <div className={`qr-simulator ${qrActive ? 'active' : ''}`}>
                  {qrActive ? (
                    <div style={{ textAlign: 'center', color: 'var(--primary)' }}>
                      📷 Camera Active<br />
                      <span className="loading-spinner"></span><br />
                      Scanning for QR code...
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--gray-500)' }}>
                      📷<br />
                      Click "Start Scanning" to activate camera
                    </div>
                  )}
                </div>
                <button 
                  className="btn btn-primary" 
                  onClick={handleQRScan}
                  disabled={qrActive}
                >
                  {qrActive ? 'Scanning...' : 'Start Scanning'}
                </button>
              </div>
            )}
            
            {checkinMethod === 'code' && (
              <div style={{ margin: '20px 0' }}>
                <div className="form-group">
                  <label className="form-label">Session Code</label>
                  <input 
                    type="text" 
                    className="form-input"
                    placeholder="Enter 6-digit code"
                    maxLength="6"
                    value={sessionCode}
                    onChange={(e) => setSessionCode(e.target.value)}
                    style={{ textAlign: 'center', fontSize: '18px', letterSpacing: '2px' }}
                  />
                </div>
                <button 
                  className="btn btn-success" 
                  onClick={handleCodeCheckin}
                  disabled={loading || sessionCode.length !== 6}
                >
                  {loading ? <span className="loading-spinner"></span> : 'Check In'}
                </button>
              </div>
            )}
            
            {bookings.length === 0 && (
              <div style={{ marginTop: '20px', padding: '20px', background: 'var(--gray-50)', borderRadius: '8px' }}>
                <p style={{ color: 'var(--gray-500)' }}>
                  No confirmed bookings available for check-in.
                </p>
              </div>
            )}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default CheckinModal;