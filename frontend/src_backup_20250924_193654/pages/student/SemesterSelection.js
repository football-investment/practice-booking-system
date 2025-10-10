import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import PaymentStatusBanner from '../../components/student/PaymentStatusBanner';
import './SemesterSelection.css';

const SemesterSelection = () => {
  const { user, updateUserProfile } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [semesters, setSemesters] = useState([]);
  const [selectedSemester, setSelectedSemester] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [paymentVerified, setPaymentVerified] = useState(false);

  // Check if user came from onboarding
  const fromOnboarding = location.state?.fromOnboarding || false;

  useEffect(() => {
    loadSemesters();
  }, []);

  const loadSemesters = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await apiService.getSemesters();
      const semesterList = Array.isArray(response) ? response : response.semesters || [];
      const activeSemesters = semesterList.filter(sem => sem.is_active);
      
      setSemesters(activeSemesters);
    } catch (err) {
      console.error('Failed to load semesters:', err);
      setError('Nem sikerült betölteni a szemesztereket. Próbáld újra.');
    } finally {
      setLoading(false);
    }
  };

  const handleSemesterSelect = (semester) => {
    setSelectedSemester(semester);
  };

  const handleSubmit = async () => {
    if (!selectedSemester) return;
    
    // Check payment verification
    if (!paymentVerified) {
      setError('A szemeszter-választáshoz szükséges a díjfizetés igazolása. Vedd fel a kapcsolatot az adminisztrációval.');
      return;
    }
    
    setSubmitting(true);
    setError('');
    
    try {
      // Here you would call an API to associate user with semester
      // await apiService.joinSemester(selectedSemester.id);
      
      console.log('Selected semester:', selectedSemester);
      
      // Navigate to dashboard after successful selection
      navigate('/student/dashboard', { 
        replace: true,
        state: { semesterSelected: true }
      });
      
    } catch (err) {
      console.error('Failed to join semester:', err);
      setError('Nem sikerült csatlakozni a szemeszterhez: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkip = () => {
    // Allow skipping for now, but redirect to dashboard
    navigate('/student/dashboard', { replace: true });
  };

  if (loading) {
    return (
      <div className="semester-selection-loading">
        <div className="loading-spinner"></div>
        <p>Szemeszterek betöltése...</p>
      </div>
    );
  }

  return (
    <div className="semester-selection">
      <div className="semester-selection-container">
        {/* Header */}
        <div className="semester-header">
          <div className="step-icon">🎯</div>
          <h1>Szemeszter választás</h1>
          <p className="step-description">
            {fromOnboarding ? (
              'Gratulálunk! Az onboarding befejezése után válaszd ki az aktív szemesztert.'
            ) : (
              'Válassz szemesztert, amelyben részt szeretnél venni.'
            )}
          </p>
        </div>

        {/* Payment Status Banner */}
        <PaymentStatusBanner 
          onStatusUpdate={setPaymentVerified}
          showOnlyIfUnverified={false}
        />

        {/* Error Message */}
        {error && (
          <div className="error-banner">
            ⚠️ {error}
          </div>
        )}

        {/* Semester Options */}
        <div className="semester-content">
          {semesters.length > 0 ? (
            <div className="semester-grid">
              {semesters.map(semester => (
                <div 
                  key={semester.id} 
                  className={`semester-card ${selectedSemester?.id === semester.id ? 'selected' : ''} ${!paymentVerified ? 'disabled' : ''}`}
                  onClick={() => paymentVerified && handleSemesterSelect(semester)}
                >
                  <div className="semester-header">
                    <h3>{semester.name}</h3>
                    <span className="semester-status active">Aktív</span>
                  </div>
                  
                  <div className="semester-dates">
                    📅 {(() => {
                      try {
                        const startDate = new Date(semester.start_date);
                        const endDate = new Date(semester.end_date);
                        
                        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                          return `${semester.start_date} - ${semester.end_date}`;
                        }
                        
                        return `${startDate.toLocaleDateString('hu-HU')} - ${endDate.toLocaleDateString('hu-HU')}`;
                      } catch (error) {
                        return `${semester.start_date} - ${semester.end_date}`;
                      }
                    })()}
                  </div>
                  
                  {semester.description && (
                    <p className="semester-description">{semester.description}</p>
                  )}
                  
                  {selectedSemester?.id === semester.id && (
                    <div className="selected-indicator">✓ Kiválasztva</div>
                  )}
                  
                  {!paymentVerified && (
                    <div className="payment-required-overlay">
                      <span>💰 Díjfizetés szükséges</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="no-semesters">
              <div className="no-semesters-icon">📚</div>
              <h3>Nincsenek aktív szemeszterek</h3>
              <p>Jelenleg nincsenek elérhető aktív szemeszterek. Később is kiválaszthatod a szemesztert.</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="semester-actions">
          <button 
            onClick={handleSkip}
            className="skip-btn"
          >
            Későbbi kiválasztás
          </button>
          
          {selectedSemester && paymentVerified && (
            <button 
              onClick={handleSubmit}
              disabled={submitting}
              className="submit-btn primary"
            >
              {submitting ? '⏳ Csatlakozás...' : `Csatlakozás: ${selectedSemester.name}`}
            </button>
          )}
          
          {selectedSemester && !paymentVerified && (
            <button disabled className="submit-btn disabled">
              💰 Díjfizetés igazolása szükséges
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SemesterSelection;