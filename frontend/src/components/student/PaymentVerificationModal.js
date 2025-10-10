import React from 'react';
import './PaymentVerificationModal.css';

const PaymentVerificationModal = ({ 
  isOpen, 
  onClose, 
  onContactAdmin,
  action = 'enroll', // 'enroll', 'book', 'access'
  title = null
}) => {
  if (!isOpen) return null;

  const getActionText = () => {
    switch (action) {
      case 'enroll': return 'projektbe való jelentkezéshez';
      case 'book': return 'óra lefoglalásához';
      case 'access': return 'funkció eléréséhez';
      default: return 'folytatáshoz';
    }
  };

  const getActionIcon = () => {
    switch (action) {
      case 'enroll': return '📚';
      case 'book': return '📅';
      case 'access': return '🔐';
      default: return '💰';
    }
  };

  const handleContactAdmin = () => {
    if (onContactAdmin) {
      onContactAdmin();
    } else {
      // Default behavior - could navigate to contact page or show contact info
      window.location.href = '/admin/contact';
    }
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="payment-modal-overlay" onClick={handleBackdropClick}>
      <div className="payment-modal">
        <div className="payment-modal-header">
          <div className="modal-icon">{getActionIcon()}</div>
          <h2>{title || 'Díjfizetés szükséges'}</h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="payment-modal-content">
          <div className="alert-section">
            <div className="alert-icon">⚠️</div>
            <div className="alert-text">
              <p>
                A {getActionText()} szükséges a <strong>szemeszter díjfizetés igazolása</strong>.
              </p>
            </div>
          </div>

          <div className="payment-info">
            <h4>Mit kell tenned?</h4>
            <ol>
              <li>
                <span className="step-icon">📧</span>
                <strong>Vedd fel a kapcsolatot</strong> az adminisztrációval
              </li>
              <li>
                <span className="step-icon">💳</span>
                <strong>Igazold a díjfizetést</strong> (banki átutalás, készpénz stb.)
              </li>
              <li>
                <span className="step-icon">✅</span>
                <strong>Várd meg a jóváhagyást</strong> - utána minden funkció elérhető lesz
              </li>
            </ol>
          </div>

          <div className="contact-info">
            <h4>Kapcsolatfelvétel</h4>
            <div className="contact-methods">
              <div className="contact-method">
                <span className="contact-icon">📧</span>
                <span>admin@lfa.hu</span>
              </div>
              <div className="contact-method">
                <span className="contact-icon">📞</span>
                <span>+36 1 234 5678</span>
              </div>
              <div className="contact-method">
                <span className="contact-icon">🏢</span>
                <span>LFA Irodája, H-Cs 9:00-17:00</span>
              </div>
            </div>
          </div>

          <div className="payment-note">
            <p>
              <strong>Megjegyzés:</strong> A díjfizetés igazolása után azonnal hozzáférhetsz minden funkcióhoz.
              Az adminisztrátor általában 1-2 munkanapon belül feldolgozza a kéréseket.
            </p>
          </div>
        </div>

        <div className="payment-modal-actions">
          <button 
            className="btn-secondary" 
            onClick={onClose}
          >
            Később
          </button>
          <button 
            className="btn-primary" 
            onClick={handleContactAdmin}
          >
            📧 Kapcsolatfelvétel
          </button>
        </div>
      </div>
    </div>
  );
};

export default PaymentVerificationModal;