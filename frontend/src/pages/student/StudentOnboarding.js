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
        setError('Failed to load. Please try again.');
        
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
        setNicknameError('Nickname verification timeout');
      } else if (isIOSSafari() && err.message.includes('fetch')) {
        setNicknameError('Network error on iOS/Safari');
      } else {
        setNicknameError('Failed to verify nickname');
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
      <h2>Welcome to the system, {user?.name}!</h2>
      <p className="step-description">
        We're glad you're joining us! Through the following steps, we'll help you set up your account and get familiar with the system.
      </p>
      
      <div className="welcome-features">
        <div className="feature-item">
          <span className="feature-icon">📅</span>
          <div className="feature-content">
            <h4>Sessions and Events</h4>
            <p>Browse and sign up for sessions and events</p>
          </div>
        </div>
        
        <div className="feature-item">
          <span className="feature-icon">📚</span>
          <div className="feature-content">
            <h4>Projects and Quizzes</h4>
            <p>Join projects and test your knowledge</p>
          </div>
        </div>
        
        <div className="feature-item">
          <span className="feature-icon">🏆</span>
          <div className="feature-content">
            <h4>Gamification</h4>
            <p>Earn XP, unlock achievements</p>
          </div>
        </div>
      </div>

      <p className="step-note">
        <strong>This process takes approximately 3-5 minutes.</strong>
      </p>
    </div>
  );

  const renderCurrentStatusStep = () => (
    <div className="onboarding-step current-status-step">
      <div className="step-icon">📊</div>
      <h2>Your Current Status</h2>
      <p className="step-description">
        The following overview shows your current specializations, license levels and completed semesters.
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
      <h2>Non-Disclosure Agreement</h2>
      <p className="step-description">
        Before continuing, please read and accept the non-disclosure agreement.
      </p>

      <div className="nda-content">
        <div className="nda-document">
          <h4>Non-Disclosure and Data Protection Agreement</h4>
          
          <div className="nda-section">
            <h5>1. Principles</h5>
            <p>
              By using the SportMax Practice Booking System, you gain access to various training materials, personal data, and internal information.
            </p>
          </div>

          <div className="nda-section">
            <h5>2. Confidentiality Obligation</h5>
            <p>
              You commit to handling all information learned while using the system confidentially and not disclosing it to third parties.
            </p>
          </div>

          <div className="nda-section">
            <h5>3. Data Protection</h5>
            <p>
              Your personal data is processed in accordance with GDPR regulations. Your data is only used to the extent necessary to provide the service.
            </p>
          </div>

          <div className="nda-section">
            <h5>4. Liability</h5>
            <p>
              In case of violation of this agreement, you agree to compensate damages and accept liability for the infringement.
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
            I have read and accept the non-disclosure agreement
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
      <h2>Complete Your Profile</h2>
      <p className="step-description">
        Provide the following information to create your complete profile.
      </p>

      <div className="profile-form">
        <div className="form-section">
          <h4>Basic Information</h4>
          
          <div className="form-row">
            <div className="form-group">
              <label>Nickname *</label>
              <input
                type="text"
                value={formData.profileData.nickname}
                onChange={(e) => handleInputChange('profileData.nickname', e.target.value)}
                placeholder="E.g. SportsPro, FootballFan, etc."
                required
                maxLength="30"
                className={nicknameError ? 'error' : ''}
              />
              {nicknameChecking && (
                <div className="field-hint">
                  <span>⏳</span> Verifying...
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
                  <span>✅</span> Great! This nickname is available.
                </div>
              )}
              <div className="field-hint">
                <span>🔒</span> This will be displayed to others in lists for privacy purposes
              </div>
            </div>
            
            <div className="form-group">
              <label>Phone Number *</label>
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
          <h4>Emergency Contact</h4>
          
          <div className="form-row">
            <div className="form-group">
              <label>Emergency Contact Name *</label>
              <input
                type="text"
                value={formData.profileData.emergencyContact}
                onChange={(e) => handleInputChange('profileData.emergencyContact', e.target.value)}
                placeholder="E.g. John Smith (father)"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Emergency Phone Number</label>
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
                    Oops! The emergency phone number cannot be the same as yours
                  </span>
                  <span className="error-emoji">🤔</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="form-section">
          <h4>Additional Information</h4>
          
          <div className="form-group">
            <label>Medical Notes</label>
            <textarea
              value={formData.profileData.medicalNotes}
              onChange={(e) => handleInputChange('profileData.medicalNotes', e.target.value)}
              placeholder="Allergies, medications, limitations, etc. (optional)"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label>Areas of Interest</label>
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
      <h2>Payment Verification</h2>
      <p className="step-description">
        Full participation in the LFA Academy program requires a registration fee.
      </p>

      <div className="payment-info">
        <div className="pricing-card">
          <div className="price-header">
            <h3>Semester Fee</h3>
            <div className="price-amount">
              <span className="currency">HUF</span>
              <span className="amount">150,000</span>
              <span className="period">/ semester</span>
            </div>
          </div>

          <div className="price-features">
            <h4>What's Included:</h4>
            <ul>
              <li>✅ Unlimited access to sessions</li>
              <li>✅ Specialization training (PLAYER/COACH/INTERNSHIP)</li>
              <li>✅ Adaptive Learning quiz system</li>
              <li>✅ Competency assessment and development</li>
              <li>✅ Module-based progression tracking</li>
              <li>✅ Gamification and achievement system</li>
              <li>✅ Personalized recommendations</li>
              <li>✅ Consulting with professional coach</li>
            </ul>
          </div>
        </div>

        <div className="payment-methods">
          <h4>Payment Methods:</h4>
          <div className="method-list">
            <div className="payment-method">
              <span className="method-icon">🏦</span>
              <span className="method-name">Bank Transfer</span>
            </div>
            <div className="payment-method">
              <span className="method-icon">💳</span>
              <span className="method-name">Credit Card (Stripe)</span>
            </div>
            <div className="payment-method">
              <span className="method-icon">📱</span>
              <span className="method-name">Online Payment (SimplePay)</span>
            </div>
          </div>
        </div>

        <div className="payment-confirmation">
          <div className="confirmation-box">
            <p className="info-text">
              <strong>For Demo Purposes:</strong> You are currently in demo mode. No actual payment required. Click the button below to simulate payment.
            </p>

            {!formData.paymentVerified ? (
              <button
                className="verify-payment-btn"
                onClick={() => handleInputChange('paymentVerified', true)}
              >
                ✅ Payment Verification (DEMO)
              </button>
            ) : (
              <div className="verified-status">
                <span className="verified-icon">✅</span>
                <span className="verified-text">Payment Verified!</span>
              </div>
            )}
          </div>

          <p className="help-text">
            Questions about payment? Write to us: <a href="mailto:billing@lfa.com">billing@lfa.com</a>
          </p>
        </div>
      </div>
    </div>
  );

  const renderSystemOverviewStep = () => (
    <div className="onboarding-step overview-step">
      <div className="step-icon">🚀</div>
      <h2>System Overview</h2>
      <p className="step-description">
        Get familiar with the main features and capabilities of LFA Academy!
      </p>

      <div className="system-features">
        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📅</span>
            <h4>Sessions and Bookings</h4>
          </div>
          <ul>
            <li><strong>Browse Sessions:</strong> Sessions filtered by specialization</li>
            <li><strong>Book a Session:</strong> Simple booking system</li>
            <li><strong>Tracking:</strong> Upcoming, past and cancelled bookings</li>
            <li><strong>Check-in:</strong> QR code or manual attendance recording</li>
            <li><strong>Instructor Rating:</strong> Feedback for coaches</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">🧠</span>
            <h4>Adaptive Learning (Intelligent Quiz System)</h4>
          </div>
          <ul>
            <li><strong>Personalized Quizzes:</strong> Difficulty adjusts to your knowledge level</li>
            <li><strong>Difficulty scaling:</strong> EASY → MEDIUM → HARD → EXPERT</li>
            <li><strong>Real-time feedback:</strong> Instant explanation for every answer</li>
            <li><strong>XP and rewards:</strong> Points for correct answers</li>
            <li><strong>Leaderboard:</strong> Compete with peers</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📊</span>
            <h4>Competency Framework (Competency Assessment)</h4>
          </div>
          <ul>
            <li><strong>Skill Assessment:</strong> 15+ competencies measured per specialization</li>
            <li><strong>Radar Chart:</strong> Visual feedback on your progress</li>
            <li><strong>Progress Tracking:</strong> Milestones and level-up system</li>
            <li><strong>Recommendations:</strong> Personalized development suggestions</li>
            <li><strong>Hook Integration:</strong> Automatic skill update after quiz/booking</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">📚</span>
            <h4>Module System (Modular Learning)</h4>
          </div>
          <ul>
            <li><strong>Structured Progression:</strong> Module → Topic → Lesson structure</li>
            <li><strong>Prerequisites:</strong> Prerequisites for module access</li>
            <li><strong>Completion Tracking:</strong> Progress tracking per module</li>
            <li><strong>Specialization-Specific:</strong> PLAYER, COACH, INTERNSHIP modulok</li>
            <li><strong>Certificates:</strong> Recognition for completed modules</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">🏆</span>
            <h4>Gamification and Achievement System</h4>
          </div>
          <ul>
            <li><strong>XP Points:</strong> Earn points for every activity</li>
            <li><strong>Levels:</strong> Level up and unlock special features</li>
            <li><strong>Achievements:</strong> 50+ achievement categories (quiz, session, skill)</li>
            <li><strong>Badges:</strong> Collect digital badges</li>
            <li><strong>Streaks:</strong> Daily login and activity streaks</li>
          </ul>
        </div>

        <div className="feature-section">
          <div className="feature-header">
            <span className="feature-icon">💬</span>
            <h4>Communication and Feedback</h4>
          </div>
          <ul>
            <li><strong>Messages:</strong> Chat with instructors and coaches</li>
            <li><strong>Session Rating:</strong> 5-star rating + text feedback</li>
            <li><strong>Notifications:</strong> Email and push notifications</li>
            <li><strong>Progress Reports:</strong> Monthly summary reports</li>
          </ul>
        </div>
      </div>

      <div className="getting-started">
        <h4>🎯 Next Steps After Onboarding:</h4>
        <ol>
          <li><strong>Dashboard:</strong> View the main page and your statistics</li>
          <li><strong>Sessions:</strong> Book your first session</li>
          <li><strong>Adaptive Quiz:</strong> Test your knowledge in a quiz</li>
          <li><strong>Competency:</strong> Complete a competency assessment</li>
          <li><strong>Modules:</strong> Start a learning module</li>
        </ol>
      </div>

      <div className="completion-note">
        <p>
          🎉 <strong>Congratulations!</strong> You've successfully set up your account.
          You're now ready to explore the full functionality of the LFA Academy system!
        </p>
        <p className="tech-note">
          💡 <strong>Technical Info:</strong> The system runs with FastAPI backend and React frontend, PostgreSQL database, JWT authentication, and real-time WebSocket support.
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
            {currentStep} / {totalSteps} steps
          </div>
        </div>

        {/* Step indicators */}
        <div className="step-indicators">
          {[1, 2, 3, 4, 5, 6, 7].map(step => (
            <div key={step} className={`step-indicator ${currentStep >= step ? 'active' : ''} ${currentStep === step ? 'current' : ''}`}>
              <div className="step-number">{step}</div>
              <div className="step-label">
                {step === 1 && 'Welcome'}
                {step === 2 && 'Status'}
                {step === 3 && 'Specialization'}
                {step === 4 && 'NDA'}
                {step === 5 && 'Profile'}
                {step === 6 && 'Payment'}
                {step === 7 && 'Overview'}
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
              ← Previous
            </button>
          )}
          
          {/* Skip button - always visible */}
          <button
            type="button"
            onClick={() => navigate('/student/dashboard')}
            className="btn-skip"
            disabled={loading}
            title="Skip onboarding and go to dashboard"
          >
            ⏭️ Skip
          </button>
          
          <div className="nav-spacer"></div>
          
          {currentStep < totalSteps ? (
            <button
              type="button"
              onClick={nextStep}
              className={`btn-primary ${!canProceed() ? 'disabled' : ''}`}
              disabled={!canProceed() || loading}
            >
              Next →
            </button>
          ) : (
            <button
              type="button"
              onClick={completeOnboarding}
              className="btn-primary complete-btn"
              disabled={loading}
            >
              {loading ? '⏳ Completing...' : '🎯 Complete and Start!'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentOnboarding;