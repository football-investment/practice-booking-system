import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { apiService } from '../../services/apiService';
import './StudentOnboarding.css';

const StudentOnboarding = () => {
  const { user, updateUserProfile } = useAuth();
  const { theme, colorScheme } = useTheme();
  const navigate = useNavigate();
  
  // State management
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Form data for different steps
  const [formData, setFormData] = useState({
    selectedSemester: null,
    ndaAccepted: false,
    profileData: {
      nickname: '',
      phone: '',
      dateOfBirth: '',
      emergencyContact: '',
      emergencyPhone: '',
      medicalNotes: '',
      interests: []
    }
  });

  // Available semesters and other data
  const [semesters, setSemesters] = useState([]);
  const [nicknameError, setNicknameError] = useState('');
  const [nicknameChecking, setNicknameChecking] = useState(false);
  const [availableInterests] = useState([
    'Football', 'Basketball', 'Tennis', 'Swimming', 'Running',
    'Fitness', 'Yoga', 'Martial Arts', 'Dance', 'Cycling'
  ]);

  const totalSteps = 5;

  // Load initial data
  useEffect(() => {
    // iPad/Safari specific error handling
    const handleIPadErrors = () => {
      if (window.iosBrowserCompatibility && window.iosBrowserCompatibility.isIPadOrSafari()) {
        console.log('🔧 iPad/Safari detected - applying compatibility fixes...');
        
        // Add error recovery for script errors
        window.addEventListener('error', (event) => {
          if (event.message === 'Script error.' || event.filename === '') {
            console.warn('🔧 Script error detected on iPad - attempting recovery...');
            setError('Kapcsolódási probléma iPad-en. Újrapróbálkozás...');
            
            // Attempt to reload after a short delay
            setTimeout(() => {
              setError('');
            }, 3000);
          }
        });
      }
    };

    handleIPadErrors();
    loadSemesters();
  }, []);

  const loadSemesters = async () => {
    try {
      const response = await apiService.getSemesters();
      // Handle both direct array and wrapped response formats
      const semesterList = Array.isArray(response) ? response : response.semesters || [];
      setSemesters(semesterList.filter(sem => sem.is_active));
    } catch (err) {
      console.error('Failed to load semesters:', err);
    }
  };

  // Debounced nickname validation
  const checkNickname = async (nickname) => {
    if (!nickname || nickname.length < 3) {
      setNicknameError('');
      return;
    }

    try {
      setNicknameChecking(true);
      const response = await apiService.request(`/api/v1/users/check-nickname/${encodeURIComponent(nickname)}`);
      
      if (response.available) {
        setNicknameError('');
      } else {
        setNicknameError(response.message);
      }
    } catch (err) {
      console.error('Nickname check failed:', err);
      setNicknameError('Nem sikerült ellenőrizni a becenevet');
    } finally {
      setNicknameChecking(false);
    }
  };

  // Debounce nickname checking
  useEffect(() => {
    const timer = setTimeout(() => {
      if (formData.profileData.nickname) {
        checkNickname(formData.profileData.nickname);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [formData.profileData.nickname]);

  // Step navigation
  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Form handlers
  const handleInputChange = (field, value) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  const handleInterestToggle = (interest) => {
    const currentInterests = formData.profileData.interests;
    const newInterests = currentInterests.includes(interest)
      ? currentInterests.filter(i => i !== interest)
      : [...currentInterests, interest];
    
    handleInputChange('profileData.interests', newInterests);
  };

  // Step validation
  const canProceed = () => {
    switch (currentStep) {
      case 1: return true; // Welcome screen
      case 2: return formData.selectedSemester !== null;
      case 3: return formData.ndaAccepted;
      case 4: {
        // Check required fields
        if (!formData.profileData.nickname || !formData.profileData.phone || !formData.profileData.emergencyContact) {
          return false;
        }
        // Check nickname errors
        if (nicknameError || nicknameChecking) {
          return false;
        }
        // Check phone numbers are different
        if (formData.profileData.phone === formData.profileData.emergencyPhone && formData.profileData.emergencyPhone) {
          return false;
        }
        return true;
      }
      case 5: return true; // System overview
      default: return false;
    }
  };

  // Complete onboarding
  const completeOnboarding = async () => {
    setLoading(true);
    setError('');

    try {
      // 1. Update user profile
      const updatedUser = await apiService.updateProfile({
        nickname: formData.profileData.nickname,
        phone: formData.profileData.phone,
        date_of_birth: formData.profileData.dateOfBirth,
        emergency_contact: formData.profileData.emergencyContact,
        emergency_phone: formData.profileData.emergencyPhone,
        medical_notes: formData.profileData.medicalNotes,
        interests: JSON.stringify(formData.profileData.interests),
        onboarding_completed: true
      });

      // 2. Join selected semester (if any API exists for this)
      if (formData.selectedSemester) {
        // This would be a semester join API call
        // await apiService.joinSemester(formData.selectedSemester.id);
        console.log('Selected semester:', formData.selectedSemester);
      }

      // 3. Record NDA acceptance
      // await apiService.acceptNDA();

      // 4. Update local user data with complete response from server
      updateUserProfile(updatedUser);

      // 5. Navigate to dashboard
      navigate('/student/dashboard', { replace: true });

    } catch (err) {
      setError('Failed to complete onboarding: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Step content renderers
  const renderWelcomeStep = () => (
    <div className="onboarding-step welcome-step">
      <div className="step-icon">🎓</div>
      <h2>Üdvözlünk a rendszerben, {user?.name}!</h2>
      <p className="step-description">
        Örülünk, hogy csatlakozol hozzánk! Az alábbi lépéseken keresztül 
        segítünk beállítani a fiókodat és megismerkedni a rendszerrel.
      </p>
      
      <div className="welcome-features">
        <div className="feature-item">
          <span className="feature-icon">📅</span>
          <div className="feature-content">
            <h4>Edzések és események</h4>
            <p>Böngészd és jelentkezz edzésekre, eseményekre</p>
          </div>
        </div>
        
        <div className="feature-item">
          <span className="feature-icon">📚</span>
          <div className="feature-content">
            <h4>Projektek és quizek</h4>
            <p>Csatlakozz projektekhez és tesztelj tudásod</p>
          </div>
        </div>
        
        <div className="feature-item">
          <span className="feature-icon">🏆</span>
          <div className="feature-content">
            <h4>Gamification</h4>
            <p>Szerezz XP-t, érd el az achievementeket</p>
          </div>
        </div>
      </div>

      <p className="step-note">
        <strong>Ez a folyamat körülbelül 3-5 percet vesz igénybe.</strong>
      </p>
    </div>
  );

  const renderSemesterStep = () => (
    <div className="onboarding-step semester-step">
      <div className="step-icon">🎯</div>
      <h2>Válassz szemesztert</h2>
      <p className="step-description">
        Válaszd ki a jelenlegi aktív szemesztert, amelyben részt szeretnél venni.
      </p>

      <div className="semester-options">
        {semesters.length > 0 ? semesters.map(semester => (
          <div 
            key={semester.id} 
            className={`semester-card ${formData.selectedSemester?.id === semester.id ? 'selected' : ''}`}
            onClick={() => handleInputChange('selectedSemester', semester)}
          >
            <div className="semester-header">
              <h4>{semester.name}</h4>
              <span className="semester-status active">Aktív</span>
            </div>
            <div className="semester-dates">
              📅 {(() => {
                try {
                  const startDate = new Date(semester.start_date);
                  const endDate = new Date(semester.end_date);
                  
                  // Safari-safe date formatting
                  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                    return `${semester.start_date} - ${semester.end_date}`;
                  }
                  
                  return `${startDate.toLocaleDateString('hu-HU')} - ${endDate.toLocaleDateString('hu-HU')}`;
                } catch (error) {
                  console.warn('Date formatting error on iPad/Safari:', error);
                  return `${semester.start_date} - ${semester.end_date}`;
                }
              })()}
            </div>
            {semester.description && (
              <p className="semester-description">{semester.description}</p>
            )}
          </div>
        )) : (
          <div className="no-semesters">
            <p>⚠️ Jelenleg nincsenek aktív szemeszterek elérhető.</p>
            <p>Később is kiválaszthatod a szemesztert a beállításokban.</p>
          </div>
        )}
      </div>

      {formData.selectedSemester && (
        <div className="selection-confirmation">
          ✅ Kiválasztva: <strong>{formData.selectedSemester.name}</strong>
        </div>
      )}
    </div>
  );

  const renderNDAStep = () => (
    <div className="onboarding-step nda-step">
      <div className="step-icon">📜</div>
      <h2>Titoktartási nyilatkozat</h2>
      <p className="step-description">
        A folytatás előtt kérjük, olvasd el és fogadd el a titoktartási nyilatkozatot.
      </p>

      <div className="nda-content">
        <div className="nda-document">
          <h4>Titoktartási és Adatvédelmi Megállapodás</h4>
          
          <div className="nda-section">
            <h5>1. Alapelvek</h5>
            <p>
              A SportMax Practice Booking System használatával hozzáférhetsz 
              különböző edzési anyagokhoz, személyes adatokhoz és belső információkhoz.
            </p>
          </div>

          <div className="nda-section">
            <h5>2. Titoktartási kötelezettség</h5>
            <p>
              Kötelezed magad arra, hogy minden, a rendszer használata során megismert 
              információt bizalmasan kezelsz, és harmadik félnek nem adod át.
            </p>
          </div>

          <div className="nda-section">
            <h5>3. Adatvédelem</h5>
            <p>
              Személyes adataidat a GDPR előírásainak megfelelően kezeljük. 
              Adataid csak a szolgáltatás nyújtásához szükséges mértékben kerülnek felhasználásra.
            </p>
          </div>

          <div className="nda-section">
            <h5>4. Felelősség</h5>
            <p>
              A nyilatkozat megszegése esetén vállalos a károkat megtéríteni 
              és felelősséget vállalsz a jogsértésért.
            </p>
          </div>
        </div>

        <div className="nda-acceptance">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={formData.ndaAccepted}
              onChange={(e) => handleInputChange('ndaAccepted', e.target.checked)}
            />
            <span className="checkmark"></span>
            Elolvastam és elfogadom a titoktartási nyilatkozatot
          </label>
        </div>
      </div>
    </div>
  );

  const renderProfileStep = () => (
    <div className="onboarding-step profile-step">
      <div className="step-icon">👤</div>
      <h2>Profil kiegészítése</h2>
      <p className="step-description">
        Add meg az alábbi adatokat a teljes profil létrehozásához.
      </p>

      <div className="profile-form">
        <div className="form-section">
          <h4>Alapvető adatok</h4>
          
          <div className="form-row">
            <div className="form-group">
              <label>Becenév (nickname) *</label>
              <input
                type="text"
                value={formData.profileData.nickname}
                onChange={(e) => handleInputChange('profileData.nickname', e.target.value)}
                placeholder="Pl. SportsPro, FutballFan stb."
                required
                maxLength="30"
                className={nicknameError ? 'error' : ''}
              />
              {nicknameChecking && (
                <div className="field-hint">
                  <span>⏳</span> Ellenőrzés...
                </div>
              )}
              {!nicknameChecking && nicknameError && (
                <div className="field-error animated-error">
                  <span className="error-icon">⚠️</span>
                  <span className="error-text">{nicknameError}</span>
                </div>
              )}
              {!nicknameChecking && !nicknameError && formData.profileData.nickname.length >= 3 && (
                <div className="field-success">
                  <span>✅</span> Remek! Ez a becenév elérhető.
                </div>
              )}
              <div className="field-hint">
                <span>🔒</span> Ez jelenik meg mások számára a listákban az adatvédelem érdekében
              </div>
            </div>
            
            <div className="form-group">
              <label>Telefonszám *</label>
              <input
                type="tel"
                value={formData.profileData.phone}
                onChange={(e) => handleInputChange('profileData.phone', e.target.value)}
                placeholder="+36 XX XXX XXXX"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Születési dátum</label>
              <input
                type="date"
                value={formData.profileData.dateOfBirth}
                onChange={(e) => handleInputChange('profileData.dateOfBirth', e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <h4>Vészhelyzeti kontakt</h4>
          
          <div className="form-row">
            <div className="form-group">
              <label>Vészhelyzeti kapcsolattartó neve *</label>
              <input
                type="text"
                value={formData.profileData.emergencyContact}
                onChange={(e) => handleInputChange('profileData.emergencyContact', e.target.value)}
                placeholder="Pl. Kovács János (apa)"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Vészhelyzeti telefonszám</label>
              <input
                type="tel"
                value={formData.profileData.emergencyPhone}
                onChange={(e) => handleInputChange('profileData.emergencyPhone', e.target.value)}
                placeholder="+36 XX XXX XXXX"
                className={formData.profileData.phone === formData.profileData.emergencyPhone && formData.profileData.emergencyPhone ? 'error' : ''}
              />
              {formData.profileData.phone === formData.profileData.emergencyPhone && formData.profileData.emergencyPhone && (
                <div className="field-error animated-error">
                  <span className="error-icon">🚨</span>
                  <span className="error-text">
                    Hoppá! A vészhelyzeti telefonszám nem lehet ugyanaz, mint a sajátod
                  </span>
                  <span className="error-emoji">🤔</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="form-section">
          <h4>További információk</h4>
          
          <div className="form-group">
            <label>Egészségügyi megjegyzések</label>
            <textarea
              value={formData.profileData.medicalNotes}
              onChange={(e) => handleInputChange('profileData.medicalNotes', e.target.value)}
              placeholder="Allergiák, gyógyszerek, korlátok stb. (opcionális)"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label>Érdeklődési területek</label>
            <div className="interests-grid">
              {availableInterests.map(interest => (
                <button
                  key={interest}
                  type="button"
                  className={`interest-tag ${formData.profileData.interests.includes(interest) ? 'selected' : ''}`}
                  onClick={() => handleInterestToggle(interest)}
                >
                  {interest}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderSystemOverviewStep = () => (
    <div className="onboarding-step overview-step">
      <div className="step-icon">🚀</div>
      <h2>Rendszer áttekintése</h2>
      <p className="step-description">
        Ismerkedj meg a rendszer főbb funkcióival és lehetőségeivel!
      </p>

      <div className="system-features">
        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📅</span>
            <h4>Edzések és foglalások</h4>
          </div>
          <ul>
            <li>Böngészd az elérhető edzéseket</li>
            <li>Foglalj időpontot egyszerűen</li>
            <li>Követheted a foglalásaidat</li>
            <li>Check-in funkció az edzéseken</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📚</span>
            <h4>Projektek és tanulás</h4>
          </div>
          <ul>
            <li>Csatlakozz szemeszter projektekhez</li>
            <li>Töltsd ki a kvízeket és szerezz XP-t</li>
            <li>Kövesd a haladásodat</li>
            <li>Kommunikálj az oktatókkal</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">🏆</span>
            <h4>Gamification és fejlődés</h4>
          </div>
          <ul>
            <li>Szerezz XP pontokat aktivitásaidért</li>
            <li>Oldj meg achievementeket</li>
            <li>Lépj szinteket és gyűjts badge-eket</li>
            <li>Versenyezz társaiddal</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">💬</span>
            <h4>Kommunikáció és visszajelzés</h4>
          </div>
          <ul>
            <li>Üzenetek az oktatókkal</li>
            <li>Értékeld az edzéseket</li>
            <li>Adj visszajelzést</li>
            <li>Kapj értesítéseket</li>
          </ul>
        </div>
      </div>

      <div className="getting-started">
        <h4>🎯 Következő lépések:</h4>
        <ol>
          <li>Böngészd meg a dashboard-ot</li>
          <li>Nézd meg az elérhető edzéseket</li>
          <li>Csatlakozz egy projekthez</li>
          <li>Töltsd ki az első kvízt</li>
        </ol>
      </div>

      <div className="completion-note">
        <p>
          🎉 <strong>Gratulálunk!</strong> Sikeresen beállítottad a fiókodat. 
          Most már készen állsz a SportMax rendszer teljes funkcionalitásának felfedezésére!
        </p>
      </div>
    </div>
  );

  // Main render
  return (
    <div className={`student-onboarding theme-${theme} color-${colorScheme}`}>
      <div className="onboarding-container">
        {/* Progress bar */}
        <div className="progress-header">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${(currentStep / totalSteps) * 100}%` }}
            ></div>
          </div>
          <div className="progress-text">
            {currentStep} / {totalSteps} lépés
          </div>
        </div>

        {/* Step indicators */}
        <div className="step-indicators">
          {[1, 2, 3, 4, 5].map(step => (
            <div key={step} className={`step-indicator ${currentStep >= step ? 'active' : ''} ${currentStep === step ? 'current' : ''}`}>
              <div className="step-number">{step}</div>
              <div className="step-label">
                {step === 1 && 'Üdvözlés'}
                {step === 2 && 'Szemeszter'}
                {step === 3 && 'NDA'}
                {step === 4 && 'Profil'}
                {step === 5 && 'Áttekintés'}
              </div>
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="step-content">
          {currentStep === 1 && renderWelcomeStep()}
          {currentStep === 2 && renderSemesterStep()}
          {currentStep === 3 && renderNDAStep()}
          {currentStep === 4 && renderProfileStep()}
          {currentStep === 5 && renderSystemOverviewStep()}
        </div>

        {/* Error display */}
        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {/* Navigation */}
        <div className="step-navigation">
          {currentStep > 1 && (
            <button
              type="button"
              onClick={prevStep}
              className="btn-secondary"
              disabled={loading}
            >
              ← Előző
            </button>
          )}
          
          <div className="nav-spacer"></div>
          
          {currentStep < totalSteps ? (
            <button
              type="button"
              onClick={nextStep}
              className={`btn-primary ${!canProceed() ? 'disabled' : ''}`}
              disabled={!canProceed() || loading}
            >
              Következő →
            </button>
          ) : (
            <button
              type="button"
              onClick={completeOnboarding}
              className="btn-primary complete-btn"
              disabled={loading}
            >
              {loading ? '⏳ Befejezés...' : '🎯 Befejezés és indulás!'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentOnboarding;