import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './PaymentStatusBanner.css';

const PaymentStatusBanner = ({ 
  showOnlyIfUnverified = false, 
  compact = false,
  onStatusUpdate = null 
}) => {
  const { user } = useAuth();
  const [paymentStatus, setPaymentStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPaymentStatus();
  }, [user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Prevent auto-scroll when component updates
  useEffect(() => {
    // Store current scroll position
    const scrollY = window.scrollY;
    
    // Restore scroll position after any DOM changes
    const restoreScroll = () => {
      if (window.scrollY !== scrollY) {
        window.scrollTo(0, scrollY);
      }
    };
    
    // Use a small delay to ensure DOM has updated
    const timeoutId = setTimeout(restoreScroll, 10);
    
    return () => clearTimeout(timeoutId);
  }, [paymentStatus, loading]);

  const loadPaymentStatus = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError('');
    
    try {
      // Get user's current payment verification status
      const response = await apiService.getCurrentUser();
      const isVerified = response.payment_verified || false;
      
      setPaymentStatus({
        verified: isVerified,
        verifiedAt: response.payment_verified_at,
        verifiedBy: response.payment_verified_by
      });
      
      // Notify parent component of status
      if (onStatusUpdate) {
        onStatusUpdate(isVerified);
      }
      
    } catch (err) {
      console.warn('Failed to load payment status:', err);
      setError('Unable to check payment status');
    } finally {
      setLoading(false);
    }
  };

  // Don't render if loading or if we should only show unverified and user is verified
  if (loading) {
    return compact ? null : (
      <div className="payment-status-banner loading">
        <div className="banner-loading">Checking payment status...</div>
      </div>
    );
  }

  if (showOnlyIfUnverified && paymentStatus?.verified) {
    return null;
  }

  if (error) {
    return (
      <div className="payment-status-banner error">
        <div className="banner-content">
          <span className="banner-icon">⚠️</span>
          <span className="banner-text">{error}</span>
        </div>
      </div>
    );
  }

  const isVerified = paymentStatus?.verified;
  const bannerClass = `payment-status-banner ${isVerified ? 'verified' : 'unverified'} ${compact ? 'compact' : ''}`;

  return (
    <div className={bannerClass}>
      <div className="banner-content">
        <span className="banner-icon">
          {isVerified ? '✅' : '❌'}
        </span>
        
        <div className="banner-info">
          <div className="banner-title">
            {isVerified ? 'Díjfizetés rendben' : 'Díjfizetés nincs igazolva'}
          </div>
          
          {!compact && (
            <div className="banner-description">
              {isVerified ? (
                <>
                  Szemeszter díjad be van fizetve és igazolva.
                  {paymentStatus.verifiedAt && (
                    <span className="verification-date">
                      {' '}Igazolva: {new Date(paymentStatus.verifiedAt).toLocaleDateString('hu-HU')}
                    </span>
                  )}
                </>
              ) : (
                <>
                  A szemeszter díjfizetésed még nincs igazolva. 
                  <strong> Vedd fel a kapcsolatot az adminisztrációval</strong> a díjfizetés megerősítéséhez.
                  Addig nem tudsz projektekre jelentkezni vagy órákat lefoglalni.
                </>
              )}
            </div>
          )}
        </div>

        {!isVerified && !compact && (
          <div className="banner-actions">
            <button 
              onClick={loadPaymentStatus}
              className="refresh-btn"
              title="Státusz frissítése"
            >
              🔄
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PaymentStatusBanner;