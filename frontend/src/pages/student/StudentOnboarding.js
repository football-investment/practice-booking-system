import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { apiService } from '../../services/apiService';
import ParallelSpecializationSelector from '../../components/onboarding/ParallelSpecializationSelector';
import CurrentSpecializationStatus from '../../components/onboarding/CurrentSpecializationStatus';
import './StudentOnboarding.css';

const StudentOnboarding = () => {
  const { user, updateUserProfile } = useAuth();
  const { theme, colorScheme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  
  // State management
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Form data for different steps
  const [formData, setFormData] = useState({
    selectedSpecialization: null,
    ndaAccepted: false,
    paymentVerified: false,
    profileData: {
      nickname: '',
      phone: '',
      emergencyContact: '',
      emergencyPhone: '',
      medicalNotes: '',
      interests: []
    }
  });

  // Other data
  const [nicknameError, setNicknameError] = useState('');
  const [nicknameChecking, setNicknameChecking] = useState(false);
  const [availableInterests] = useState([
    'Football', 'Basketball', 'Tennis', 'Swimming', 'Running',
    'Fitness', 'Yoga', 'Martial Arts', 'Dance', 'Cycling'
  ]);

  const totalSteps = 7;

  // iOS/Safari detection utility
  const isIOSSafari = useCallback(() => {
    const ua = navigator.userAgent;
    const isIOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
    const isSafari = /Safari/.test(ua) && !/Chrome|Chromium|Edge/.test(ua);
    return isIOS || isSafari;
  }, []);

  // iPhone Chrome detection utility
  const isIPhoneChrome = useCallback(() => {
    const ua = navigator.userAgent.toLowerCase();
    const isIPhone = /iphone/.test(ua);
    const isChrome = ua.includes('chrome') && !ua.includes('edg');
    return isIPhone && isChrome;
  }, []);


  // Load initial data
  useEffect(() => {
    const initializeOnboarding = async () => {
      try {
        // iOS/Safari specific optimizations
        if (isIOSSafari()) {
          console.log('🔧 iOS/Safari detected - applying onboarding optimizations...');
          
          // Set iOS-specific attributes for better error handling
          document.body.setAttribute('data-ios-onboarding', 'true');
          
          // Add viewport optimization for iOS
          const viewport = document.querySelector('meta[name="viewport"]');
          if (viewport && !viewport.content.includes('user-scalable=no')) {
            viewport.content = viewport.content + ', user-scalable=no';
          }
        }
        
        // iPhone Chrome specific optimizations
        if (isIPhoneChrome()) {
          console.log('📱 iPhone Chrome detected - applying iPhone-specific optimizations...');
          
          // Set iPhone Chrome-specific attributes
          document.body.setAttribute('data-ios-onboarding', 'true');
          document.body.classList.add('iphone-chrome-onboarding');
          
          // iPhone Chrome viewport optimization
          const viewport = document.querySelector('meta[name="viewport"]');
          if (viewport) {
            // Enhanced viewport for iPhone Chrome scrolling
            viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
          }
          
          // Enable smooth scrolling for iPhone Chrome
          document.documentElement.style.scrollBehavior = 'smooth';
          document.body.style.webkitOverflowScrolling = 'touch';
          
          // Prevent viewport shifts on input focus
          window.addEventListener('resize', () => {
            if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') {
              window.scrollTo(0, 0);
              document.body.scrollTop = 0;
            }
          });
        }
        
      } catch (error) {
        console.error('Onboarding initialization error:', error);
        setError('Betöltésben hiba történt. Kérlek, próbáld újra.');
        
        // Note: No semester loading needed in onboarding anymore
      }
    };

    initializeOnboarding();

    // Cleanup function
    return () => {
      if (isIOSSafari() || isIPhoneChrome()) {
        document.body.removeAttribute('data-ios-onboarding');
        document.body.classList.remove('iphone-chrome-onboarding');
      }
    };
  }, [isIOSSafari, isIPhoneChrome]);

  // Enhanced nickname validation with iOS/Safari optimization
  const checkNickname = useCallback(async (nickname) => {
    if (!nickname || nickname.length < 3) {
      setNicknameError('');
      return;
    }

    try {
      setNicknameChecking(true);
      
      // iOS/Safari optimization: shorter timeout
      const timeoutDuration = isIOSSafari() ? 5000 : 10000;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);
      
      const response = await apiService.request(
        `/api/v1/users/check-nickname/${encodeURIComponent(nickname)}`,
        { signal: controller.signal }
      );
      
      clearTimeout(timeoutId);
      
      if (response.available) {
        setNicknameError('');
      } else {
        setNicknameError(response.message);
      }
      
    } catch (err) {
      console.error('Nickname check failed:', err);
      
      if (err.name === 'AbortError') {
        setNicknameError('Becenév ellenőrzés időtúllépés');
      } else if (isIOSSafari() && err.message.includes('fetch')) {
        setNicknameError('Hálózati hiba iOS/Safari-ban');
      } else {
        setNicknameError('Nem sikerült ellenőrizni a becenevet');
      }
    } finally {
      setNicknameChecking(false);
    }
  }, [isIOSSafari]);

  // Debounce nickname checking with iOS/Safari optimization
  useEffect(() => {
    // Longer debounce for iOS/Safari to reduce API calls
    const debounceTime = isIOSSafari() ? 1000 : 500;
    
    const timer = setTimeout(() => {
      if (formData.profileData.nickname) {
        checkNickname(formData.profileData.nickname);
      }
    }, debounceTime);

    return () => clearTimeout(timer);
  }, [formData.profileData.nickname, checkNickname, isIOSSafari]);

  // iPhone Chrome scroll helper - DISABLED to fix scroll bug
  // eslint-disable-next-line no-unused-vars
  const scrollToTop = useCallback(() => {
    // ✅ DISABLED: Preventing automatic scroll that was causing UX issues
    console.log('scrollToTop called but disabled to prevent scroll interference');
    return; // Early return - do nothing
  }, []);

  // ===== SCROLL BUG FIX =====
  // These functions were causing automatic scroll-to-top behavior
  // that made the dashboard unusable. setTimeout calls removed.
  // ===========================
  
  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
      // ✅ FIXED: Removed automatic scroll-to-top
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
      // ✅ FIXED: Removed automatic scroll-to-top
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
    const result = (() => {
      switch (currentStep) {
        case 1: return true; // Welcome screen
        case 2: return true; // Current Status - always allow proceed
        case 3: return formData.selectedSpecialization !== null; // Specialization
        case 4: return formData.ndaAccepted; // NDA
        case 5: {
          // Profile - Check required fields
          if (!formData.profileData.nickname || !formData.profileData.phone || !formData.profileData.emergencyContact) {
            console.log('❌ Profile validation failed - missing fields:', {
              nickname: formData.profileData.nickname,
              phone: formData.profileData.phone,
              emergencyContact: formData.profileData.emergencyContact
            });
            return false;
          }
          // Check nickname errors
          if (nicknameError || nicknameChecking) {
            console.log('❌ Profile validation failed - nickname issue:', { nicknameError, nicknameChecking });
            return false;
          }
          // Check phone numbers are different
          if (formData.profileData.phone === formData.profileData.emergencyPhone && formData.profileData.emergencyPhone) {
            console.log('❌ Profile validation failed - phone numbers must be different');
            return false;
          }
          console.log('✅ Profile validation passed');
          return true;
        }
        case 6: return formData.paymentVerified; // Payment verification
        case 7: return true; // System overview
        default: return false;
      }
    })();

    console.log(`🔍 canProceed (step ${currentStep}):`, result);
    return result;
  };

  // Complete onboarding
  const completeOnboarding = async () => {
    setLoading(true);
    setError('');

    try {
      // 1. Update user profile with all onboarding data
      const updatedUser = await apiService.updateProfile({
        nickname: formData.profileData.nickname,
        phone: formData.profileData.phone,
        emergency_contact: formData.profileData.emergencyContact,
        emergency_phone: formData.profileData.emergencyPhone,
        medical_notes: formData.profileData.medicalNotes,
        interests: JSON.stringify(formData.profileData.interests),
        specialization: formData.selectedSpecialization,
        payment_verified: formData.paymentVerified,
        onboarding_completed: true
      });

      console.log('✅ Onboarding completed:', {
        specialization: formData.selectedSpecialization,
        paymentVerified: formData.paymentVerified,
        ndaAccepted: formData.ndaAccepted
      });

      // 2. Update local user data with complete response from server
      updateUserProfile(updatedUser);

      // 3. Navigate to dashboard
      navigate('/student/dashboard', {
        replace: true,
        state: { fromOnboarding: true }
      });

    } catch (err) {
      setError('Failed to complete onboarding: ' + err.message);
      console.error('❌ Onboarding error:', err);
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

  const renderCurrentStatusStep = () => (
    <div className="onboarding-step current-status-step">
      <div className="step-icon">📊</div>
      <h2>Az Ön jelenlegi állapota</h2>
      <p className="step-description">
        Az alábbi összeállítás megmutatja az Ön jelenlegi specializációit,
        licencszintjeit és eddig elvégzett szemesztereit.
      </p>

      <CurrentSpecializationStatus
        onNext={nextStep}
        hideNavigation={false}
      />
    </div>
  );

  const renderSpecializationStep = () => (
    <div className="onboarding-step specialization-step">
      <ParallelSpecializationSelector
        onSelectionUpdate={(selectedSpecs) => {
          // Handle multiple specializations - for now use first one for compatibility
          const primarySpec = selectedSpecs[0] || null;
          handleInputChange('selectedSpecialization', primarySpec);
        }}
        onNext={nextStep}
        hideNavigation={false}
        showProgressionInfo={true}
      />
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
          <label 
            className="checkbox-label"
            onClick={(e) => {
              // Manual checkbox toggle for iOS compatibility
              if (e.target.tagName !== 'INPUT') {
                console.log('📋 NDA label clicked, toggling checkbox');
                handleInputChange('ndaAccepted', !formData.ndaAccepted);
                e.preventDefault();
              }
            }}
          >
            <input
              type="checkbox"
              checked={formData.ndaAccepted}
              onChange={(e) => {
                console.log('📋 NDA checkbox changed:', e.target.checked);
                handleInputChange('ndaAccepted', e.target.checked);
              }}
              id="nda-checkbox"
            />
            Elolvastam és elfogadom a titoktartási nyilatkozatot
          </label>
          {/* Debug info */}
          <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.7 }}>
            Debug: ndaAccepted = {JSON.stringify(formData.ndaAccepted)}
          </div>
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

  const renderPaymentVerificationStep = () => (
    <div className="onboarding-step payment-step">
      <div className="step-icon">💳</div>
      <h2>Fizetés megerősítése</h2>
      <p className="step-description">
        Az LFA Academy programban való teljes körű részvételhez regisztrációs díj szükséges.
      </p>

      <div className="payment-info">
        <div className="pricing-card">
          <div className="price-header">
            <h3>Szemeszter díj</h3>
            <div className="price-amount">
              <span className="currency">HUF</span>
              <span className="amount">150,000</span>
              <span className="period">/ szemeszter</span>
            </div>
          </div>

          <div className="price-features">
            <h4>Mit tartalmaz:</h4>
            <ul>
              <li>✅ Korlátlan hozzáférés az edzésekhez</li>
              <li>✅ Specializációs képzés (PLAYER/COACH/INTERNSHIP)</li>
              <li>✅ Adaptive Learning kvíz rendszer</li>
              <li>✅ Competency assessment és fejlesztés</li>
              <li>✅ Module-based progression tracking</li>
              <li>✅ Gamification és achievement system</li>
              <li>✅ Személyre szabott ajánlások</li>
              <li>✅ Tanácsadás szakmai coachchal</li>
            </ul>
          </div>
        </div>

        <div className="payment-methods">
          <h4>Fizetési módok:</h4>
          <div className="method-list">
            <div className="payment-method">
              <span className="method-icon">🏦</span>
              <span className="method-name">Banki átutalás</span>
            </div>
            <div className="payment-method">
              <span className="method-icon">💳</span>
              <span className="method-name">Bankkártya (Stripe)</span>
            </div>
            <div className="payment-method">
              <span className="method-icon">📱</span>
              <span className="method-name">Online fizetés (SimplePay)</span>
            </div>
          </div>
        </div>

        <div className="payment-confirmation">
          <div className="confirmation-box">
            <p className="info-text">
              <strong>Demo célokra:</strong> Jelenleg demo módban vagy. Valós fizetés nem szükséges.
              Kattints az alábbi gombra a fizetés szimulálásához.
            </p>

            {!formData.paymentVerified ? (
              <button
                className="verify-payment-btn"
                onClick={() => handleInputChange('paymentVerified', true)}
              >
                ✅ Fizetés megerősítése (DEMO)
              </button>
            ) : (
              <div className="verified-status">
                <span className="verified-icon">✅</span>
                <span className="verified-text">Fizetés megerősítve!</span>
              </div>
            )}
          </div>

          <p className="help-text">
            Kérdésed van a fizetéssel kapcsolatban? Írj nekünk: <a href="mailto:billing@lfa.com">billing@lfa.com</a>
          </p>
        </div>
      </div>
    </div>
  );

  const renderSystemOverviewStep = () => (
    <div className="onboarding-step overview-step">
      <div className="step-icon">🚀</div>
      <h2>Rendszer áttekintése</h2>
      <p className="step-description">
        Ismerkedj meg az LFA Academy főbb funkcióival és lehetőségeivel!
      </p>

      <div className="system-features">
        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📅</span>
            <h4>Sessions (Edzések) és Bookings (Foglalások)</h4>
          </div>
          <ul>
            <li><strong>Böngészd az edzéseket:</strong> Specializáció szerint szűrt sessions</li>
            <li><strong>Foglalj időpontot:</strong> Egyszerű booking rendszer</li>
            <li><strong>Követés:</strong> Upcoming, past és cancelled bookings</li>
            <li><strong>Check-in:</strong> QR kóddal vagy manuális jelenlét rögzítés</li>
            <li><strong>Instructor értékelés:</strong> Feedback a coachoknak</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">🧠</span>
            <h4>Adaptive Learning (Intelligens kvíz rendszer)</h4>
          </div>
          <ul>
            <li><strong>Személyre szabott kvízek:</strong> Nehézség a tudásszintedhez igazodik</li>
            <li><strong>Difficulty scaling:</strong> EASY → MEDIUM → HARD → EXPERT</li>
            <li><strong>Real-time feedback:</strong> Azonnali magyarázat minden válaszhoz</li>
            <li><strong>XP és rewards:</strong> Pontszerzés helyes válaszokért</li>
            <li><strong>Leaderboard:</strong> Versenyezz társaiddal</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📊</span>
            <h4>Competency Framework (Kompetencia értékelés)</h4>
          </div>
          <ul>
            <li><strong>Skill assessment:</strong> 15+ kompetencia mérése specializációnként</li>
            <li><strong>Radar chart:</strong> Vizuális feedback a fejlődésedről</li>
            <li><strong>Progress tracking:</strong> Milestone-ok és level-up rendszer</li>
            <li><strong>Recommendations:</strong> Személyre szabott fejlesztési javaslatok</li>
            <li><strong>Hook integration:</strong> Automatikus skill frissítés quiz/booking után</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📚</span>
            <h4>Module System (Moduláris tanulás)</h4>
          </div>
          <ul>
            <li><strong>Structured progression:</strong> Modul → Téma → Lecke struktúra</li>
            <li><strong>Prerequisites:</strong> Előfeltételek modul megnyitáshoz</li>
            <li><strong>Completion tracking:</strong> Haladás követés modulonként</li>
            <li><strong>Specialization-specific:</strong> PLAYER, COACH, INTERNSHIP modulok</li>
            <li><strong>Certificates:</strong> Elismerés a befejezett modulokért</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">🏆</span>
            <h4>Gamification és Achievement System</h4>
          </div>
          <ul>
            <li><strong>XP points:</strong> Szerezz pontokat minden aktivitásért</li>
            <li><strong>Levels:</strong> Lépj szinteket és unlock special features</li>
            <li><strong>Achievements:</strong> 50+ achievement kategória (quiz, session, skill)</li>
            <li><strong>Badges:</strong> Gyűjts digitális badge-eket</li>
            <li><strong>Streaks:</strong> Napi bejelentkezési és aktivitási sorozatok</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">💬</span>
            <h4>Kommunikáció és Feedback</h4>
          </div>
          <ul>
            <li><strong>Üzenetek:</strong> Chat az oktatókkal és coachokkal</li>
            <li><strong>Session értékelés:</strong> 5 csillagos rating + szöveges feedback</li>
            <li><strong>Notifikációk:</strong> Email és push értesítések</li>
            <li><strong>Progress reports:</strong> Havi összefoglaló jelentések</li>
          </ul>
        </div>
      </div>

      <div className="getting-started">
        <h4>🎯 Következő lépések az onboarding után:</h4>
        <ol>
          <li><strong>Dashboard:</strong> Tekintsd meg a főoldalt és a statisztikáidat</li>
          <li><strong>Sessions:</strong> Foglalj le az első edzésedet</li>
          <li><strong>Adaptive Quiz:</strong> Teszteld a tudásodat egy kvízben</li>
          <li><strong>Competency:</strong> Végezz el egy kompetencia felmérést</li>
          <li><strong>Modules:</strong> Kezdj el egy tanulási modult</li>
        </ol>
      </div>

      <div className="completion-note">
        <p>
          🎉 <strong>Gratulálunk!</strong> Sikeresen beállítottad a fiókodat.
          Most már készen állsz az LFA Academy rendszer teljes funkcionalitásának felfedezésére!
        </p>
        <p className="tech-note">
          💡 <strong>Technikai infó:</strong> A rendszer FastAPI backend-del és React frontend-del működik,
          PostgreSQL adatbázissal, JWT autentikációval és real-time WebSocket supporttal.
        </p>
      </div>
    </div>
  );

  // Main render
  return (
    <div
      className={`student-onboarding theme-${theme} color-${colorScheme} chrome-ios-optimized`}
      data-theme={theme}
    >
        <div className="onboarding-container">
        {/* Header with theme toggle */}
        <div className="onboarding-header">
          <div className="header-left">
            <span className="logo-icon">⚽</span>
            <span className="logo-text">LFA Onboarding</span>
          </div>
          <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>

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
          {[1, 2, 3, 4, 5, 6, 7].map(step => (
            <div key={step} className={`step-indicator ${currentStep >= step ? 'active' : ''} ${currentStep === step ? 'current' : ''}`}>
              <div className="step-number">{step}</div>
              <div className="step-label">
                {step === 1 && 'Üdvözlés'}
                {step === 2 && 'Státusz'}
                {step === 3 && 'Szakirány'}
                {step === 4 && 'NDA'}
                {step === 5 && 'Profil'}
                {step === 6 && 'Fizetés'}
                {step === 7 && 'Áttekintés'}
              </div>
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="step-content">
          {currentStep === 1 && renderWelcomeStep()}
          {currentStep === 2 && renderCurrentStatusStep()}
          {currentStep === 3 && renderSpecializationStep()}
          {currentStep === 4 && renderNDAStep()}
          {currentStep === 5 && renderProfileStep()}
          {currentStep === 6 && renderPaymentVerificationStep()}
          {currentStep === 7 && renderSystemOverviewStep()}
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
          
          {/* Skip button - always visible */}
          <button
            type="button"
            onClick={() => navigate('/student/dashboard')}
            className="btn-skip"
            disabled={loading}
            title="Onboarding kihagyása és dashboard-ra ugrás"
          >
            ⏭️ Kihagyás
          </button>
          
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