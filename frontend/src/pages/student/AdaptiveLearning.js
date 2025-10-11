import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { apiService } from '../../services/apiService';
import AdaptiveQuestionRenderer from '../../components/adaptive/AdaptiveQuestionRenderer';
import './AdaptiveLearning.css';
import './AdaptiveLearning-UX-Improvements.css';

const AdaptiveLearning = () => {
  const { user } = useAuth();
  const { theme, colorScheme } = useTheme();
  
  // Session state
  const [sessionId, setSessionId] = useState(null);
  const [sessionActive, setSessionActive] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [userAnswer, setUserAnswer] = useState(null);
  const [sessionStats, setSessionStats] = useState({
    questions_answered: 0,
    questions_correct: 0,
    xp_earned: 0,
    target_difficulty: 0.5,
    performance_trend: 0.0
  });

  // UI state
  const [loading, setLoading] = useState(false);
  const [questionLoading, setQuestionLoading] = useState(false);
  const [error, setError] = useState('');
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('general');
  const [sessionComplete, setSessionComplete] = useState(false);
  
  // ⚡ UX Enhancement states
  const [buttonDisabled, setButtonDisabled] = useState(false);
  const [successAnimation, setSuccessAnimation] = useState(false);
  const [leaderboard, setLeaderboard] = useState([]);
  const [showLeaderboard, setShowLeaderboard] = useState(false);

  // Question interaction state
  const [questionStartTime, setQuestionStartTime] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [submittedAnswer, setSubmittedAnswer] = useState(false);
  const [answerFeedback, setAnswerFeedback] = useState(null);

  // Timer state - Session-wide timer instead of per-question
  const [sessionTimeLeft, setSessionTimeLeft] = useState(0);
  const [sessionTimerActive, setSessionTimerActive] = useState(false);
  const [sessionDuration, setSessionDuration] = useState(180); // 3 minutes default
  const sessionTimerRef = useRef(null);
  
  // 🔍 DEBUG MODE - Add visual debugging state
  const [debugMode, setDebugMode] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);
  
  useEffect(() => {
    if (selectedCategory) {
      loadLeaderboard();
    }
  }, [selectedCategory]);

  const loadCategories = async () => {
    try {
      const response = await apiService.request('/adaptive-learning/categories');
      // Backend returns objects with value and name properties
      const categoryValues = response && Array.isArray(response) 
        ? response.map(cat => cat.value || cat) 
        : ['general', 'marketing', 'economics', 'informatics', 'sports_physiology', 'nutrition'];
      setCategories(categoryValues);
    } catch (error) {
      console.error('Failed to load categories:', error);
      setCategories(['general', 'marketing', 'economics', 'informatics', 'sports_physiology', 'nutrition']);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const queryParams = new URLSearchParams({
        category: selectedCategory,
        timeframe: 'week'
      });
      const response = await apiService.request(`/adaptive-learning/leaderboard?${queryParams}`);
      setLeaderboard(response.leaderboard || []);
    } catch (error) {
      console.error('Failed to load leaderboard:', error);
    }
  };

  const startSession = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await apiService.request('/adaptive-learning/start-session', {
        method: 'POST',
        body: JSON.stringify({
          category: selectedCategory
        })
      });
      
      setSessionId(response.session_id);
      setSessionActive(true);
      setSessionComplete(false);
      setQuestionStartTime(Date.now());
      
      // Start session-wide timer
      const duration = response.session_duration_seconds || sessionDuration;
      setSessionDuration(duration);
      startSessionTimer(duration);
      
      // Load first question
      await loadNextQuestion(response.session_id);
      
    } catch (error) {
      setError('Failed to start learning session. Please try again.');
      console.error('Start session error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadNextQuestion = async (sessionIdParam = sessionId) => {
    if (questionLoading) return; // Prevent duplicate calls
    
    try {
      setQuestionLoading(true);
      const response = await apiService.request(`/adaptive-learning/sessions/${sessionIdParam}/next-question`, {
        method: 'POST'
      });
      
      if (response.session_complete) {
        await endSession();
        return;
      }
      
      setCurrentQuestion(response);
      setUserAnswer(null);
      setShowFeedback(false);
      setSubmittedAnswer(false);
      setAnswerFeedback(null);
      setQuestionStartTime(Date.now());
      
      // Update session timer if backend provides remaining time
      if (response.session_time_remaining !== undefined) {
        setSessionTimeLeft(response.session_time_remaining);
      }
      
      // Session stats will be updated when answer is submitted
      
    } catch (error) {
      setError('Failed to load next question. Please try again.');
      console.error('Load question error:', error);
    } finally {
      setQuestionLoading(false);
    }
  };

  const submitAnswer = async (answer, metadata = {}) => {
    if (!sessionId || !currentQuestion || submittedAnswer || buttonDisabled) return;
    
    try {
      // ⚡ Immediate UI feedback
      setSubmittedAnswer(true);
      setButtonDisabled(true);
      setLoading(true);
      
      const timeSpent = questionStartTime ? (Date.now() - questionStartTime) / 1000 : 0;
      
      const response = await apiService.request(`/adaptive-learning/sessions/${sessionId}/answer`, {
        method: 'POST',
        body: JSON.stringify({
          question_id: currentQuestion.id,
          selected_option_id: parseInt(answer),
          time_spent_seconds: timeSpent
        })
      });
      
      // Store feedback data
      setAnswerFeedback({
        isCorrect: response.is_correct,
        explanation: response.explanation,
        xpEarned: response.xp_earned
      });
      setShowFeedback(true);
      setSessionStats(response.session_stats || sessionStats);
      
      // ⚡ Success animation for correct answers
      if (response.is_correct) {
        setSuccessAnimation(true);
        setTimeout(() => setSuccessAnimation(false), 600);
      }
      
      // Show feedback for 3 seconds, then load next question
      setTimeout(() => {
        if (!sessionActive) {
          console.log('🚫 Session not active, skipping next question load');
          return; // Prevent calls if session ended
        }
        console.log('⏰ 3 second feedback period complete, loading next question...');
        setShowFeedback(false);
        setAnswerFeedback(null);
        setSubmittedAnswer(false); // Reset for next question
        setButtonDisabled(false); // Re-enable interactions
        setLoading(false);
        
        // Prevent page jump by maintaining scroll position
        const currentScrollPosition = window.pageYOffset;
        loadNextQuestion();
        
        // Restore scroll position after question load
        setTimeout(() => {
          window.scrollTo(0, currentScrollPosition);
        }, 100);
      }, 3000);
      
    } catch (error) {
      setError('Failed to submit answer. Please try again.');
      console.error('Submit answer error:', error);
      setSubmittedAnswer(false);
      setButtonDisabled(false); // Re-enable on error
      setLoading(false);
    }
  };

  const endSession = async () => {
    if (!sessionId) return;
    
    try {
      const response = await apiService.request(`/adaptive-learning/sessions/${sessionId}/end`, {
        method: 'POST'
      });
      
      setSessionComplete(true);
      setSessionActive(false);
      setCurrentQuestion(null);
      setSessionStats(response.final_stats || sessionStats);
      
      // Stop session timer
      stopSessionTimer();
      
      // Refresh leaderboard
      await loadLeaderboard();
      
    } catch (error) {
      console.error('End session error:', error);
    }
  };

  const handleAnswerChange = useCallback((answer, metadata) => {
    setUserAnswer(answer);
  }, []);

  const handleQuestionSubmit = useCallback((answer, metadata) => {
    if (!submittedAnswer) {
      submitAnswer(answer, metadata);
    }
  }, [submitAnswer, submittedAnswer]);

  const resetSession = () => {
    setSessionId(null);
    setSessionActive(false);
    setCurrentQuestion(null);
    setUserAnswer(null);
    setSessionComplete(false);
    setSessionStats({
      questions_answered: 0,
      questions_correct: 0,
      xp_earned: 0,
      target_difficulty: 0.5,
      performance_trend: 0.0
    });
    setShowFeedback(false);
    setSubmittedAnswer(false);
    setAnswerFeedback(null);
    
    // Reset session timer
    stopSessionTimer();
    setSessionTimeLeft(0);
  };

  // Session Timer functions
  const startSessionTimer = (seconds) => {
    stopSessionTimer(); // Clear any existing timer
    setSessionTimeLeft(seconds);
    setSessionTimerActive(true);
    
    sessionTimerRef.current = setInterval(() => {
      setSessionTimeLeft(prev => {
        if (prev <= 1) {
          handleSessionTimeUp();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const stopSessionTimer = () => {
    if (sessionTimerRef.current) {
      clearInterval(sessionTimerRef.current);
      sessionTimerRef.current = null;
    }
    setSessionTimerActive(false);
  };

  const handleSessionTimeUp = () => {
    stopSessionTimer();
    if (sessionActive) {
      setError('Session time is up! Ending session...');
      setTimeout(() => {
        setError('');
        endSession();
      }, 2000);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      stopSessionTimer();
    };
  }, []);


  const getPerformanceTrendIcon = (trend) => {
    if (trend > 0.1) return '📈';
    if (trend < -0.1) return '📉';
    return '➡️';
  };

  return (
    <>
    <div className={`adaptive-learning ${theme} ${debugMode ? 'debug-mode' : ''}`} data-color-scheme={colorScheme}>
      <div className="adaptive-learning-container">
        
        {/* 🔍 DEBUG MODE TOGGLE */}
        <div style={{ position: 'fixed', top: '10px', right: '10px', zIndex: 9999 }}>
          <button
            onClick={() => setDebugMode(!debugMode)}
            style={{
              padding: '10px 15px',
              backgroundColor: debugMode ? '#ff0000' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            {debugMode ? '🔴 DEBUG OFF' : '🔍 DEBUG MODE'}
          </button>
          {debugMode && (
            <div style={{
              marginTop: '5px',
              padding: '10px',
              backgroundColor: 'rgba(0,0,0,0.9)',
              color: 'white',
              borderRadius: '5px',
              fontSize: '11px',
              width: '200px'
            }}>
              <strong>🔍 DEBUG AKTIVÁLVA</strong><br/>
              🔴 Piros: Stats bar container<br/>
              🔵 Kék: Stat cards<br/>
              🟢 Zöld: Featured timer<br/>
              🟠 Narancs: Timer circle<br/>
              🟣 Lila: Timer content<br/>
              🔵 Cián: Progress circles<br/>
              🟡 Sárga: Labels<br/>
              🌸 Rózsaszín: Values
            </div>
          )}
        </div>
        
        {/* 🎯 Refactored Clean Stats Layout - Timer Center, XP & Success on Sides */}
        {sessionActive && (
          <div className="clean-stats-container">
            <div className="stats-layout">
              {/* Left: XP Counter */}
              <div className="side-stat left-stat">
                <div className="stat-icon-large">
                  <span className="icon">⭐</span>
                </div>
                <div className="stat-info">
                  <div className="stat-value-large">{sessionStats.xp_earned}</div>
                  <div className="stat-label-clean">XP Earned</div>
                </div>
              </div>

              {/* Center: Main Timer */}
              {sessionTimerActive && (
                <div className="center-timer">
                  <div className="timer-circle-large">
                    <svg className="timer-svg-large" width="120" height="120" viewBox="0 0 120 120">
                      {/* Background circle */}
                      <circle
                        className="timer-bg-large"
                        cx="60"
                        cy="60"
                        r="50"
                        fill="none"
                        stroke="rgba(255,255,255,0.2)"
                        strokeWidth="6"
                      />
                      {/* Progress circle */}
                      {sessionTimerActive && sessionTimeLeft > 0 && (
                        <circle
                          className={`timer-progress-large ${
                            sessionTimeLeft <= 30 ? 'critical' : 
                            sessionTimeLeft <= 60 ? 'warning' : 'safe'
                          }`}
                          cx="60"
                          cy="60"
                          r="50"
                          fill="none"
                          strokeWidth="8"
                          strokeLinecap="round"
                          style={{
                            strokeDasharray: `${2 * Math.PI * 50}`,
                            strokeDashoffset: `${
                              2 * Math.PI * 50 * (1 - (sessionTimeLeft / sessionDuration))
                            }`,
                            transform: 'rotate(-90deg)',
                            transformOrigin: '60px 60px',
                            transition: 'stroke-dashoffset 1s ease-in-out, stroke 0.3s ease'
                          }}
                        />
                      )}
                    </svg>
                    <div className="timer-content-large">
                      <div className="timer-time-large">
                        {formatTime(sessionTimeLeft)}
                      </div>
                      <div className="timer-label-large">Time Left</div>
                    </div>
                    
                    {/* Pulse effect for critical time */}
                    {sessionTimeLeft <= 30 && (
                      <div className="pulse-effect"></div>
                    )}
                  </div>
                </div>
              )}

              {/* Right: Success Rate */}
              <div className="side-stat right-stat">
                <div className="circular-progress-large">
                  <svg width="60" height="60" viewBox="0 0 60 60">
                    <circle 
                      className="bg-circle-large" 
                      cx="30" 
                      cy="30" 
                      r="25"
                      fill="none"
                      stroke="rgba(255,255,255,0.2)"
                      strokeWidth="4"
                    />
                    <circle 
                      className="progress-circle-large success-rate" 
                      cx="30" 
                      cy="30" 
                      r="25"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="5"
                      strokeLinecap="round"
                      style={{
                        strokeDasharray: `${2 * Math.PI * 25}`,
                        strokeDashoffset: sessionStats.questions_answered > 0 
                          ? (2 * Math.PI * 25) * (1 - (sessionStats.questions_correct / sessionStats.questions_answered))
                          : (2 * Math.PI * 25),
                        transform: 'rotate(-90deg)',
                        transformOrigin: '30px 30px',
                        transition: 'stroke-dashoffset 0.5s ease'
                      }}
                    />
                  </svg>
                  <div className="center-value-large">
                    <div className="stat-value-large">
                      {sessionStats.questions_answered > 0 
                        ? Math.round((sessionStats.questions_correct / sessionStats.questions_answered) * 100)
                        : 0}%
                    </div>
                  </div>
                </div>
                <div className="stat-label-clean">Success Rate</div>
              </div>
            </div>
          </div>
        )}


        {/* Main Content Area */}
        <div className="main-content-area">

        {/* Category Selection */}
        {!sessionActive && (
          <div className="category-selection">
            <h3>Choose Learning Category</h3>
            <div className="category-grid">
              {categories.map(category => (
                <button
                  key={category}
                  className={`category-button ${selectedCategory === category ? 'selected' : ''}`}
                  onClick={() => setSelectedCategory(category)}
                >
                  <div className="category-icon">
                    {category === 'informatics' && '💻'}
                    {category === 'economics' && '📈'}
                    {category === 'sports_physiology' && '🏃'}
                    {category === 'nutrition' && '🥗'}
                    {category === 'marketing' && '📊'}
                    {category === 'general' && '🎯'}
                  </div>
                  <span className="category-name">
                    {category.replace('_', ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}


        {/* Current Question */}
        {sessionActive && currentQuestion && (
          <div className="question-section">
            <AdaptiveQuestionRenderer
              question={currentQuestion}
              userAnswer={userAnswer}
              onAnswerChange={handleAnswerChange}
              onSubmit={handleQuestionSubmit}
              isSubmitted={submittedAnswer}
              showFeedback={showFeedback}
              difficulty={sessionStats.target_difficulty}
              timeRemaining={null}
              loading={questionLoading}
            />
          </div>
        )}

        {/* Answer Feedback */}
        {showFeedback && answerFeedback && (
          <div className={`answer-feedback ${answerFeedback.isCorrect ? 'correct' : 'incorrect'}`}>
            <div className="feedback-header">
              <span className="feedback-icon">
                {answerFeedback.isCorrect ? '✅' : '❌'}
              </span>
              <span className="feedback-text">
                {answerFeedback.isCorrect ? 'Correct!' : 'Incorrect'}
              </span>
              {answerFeedback.xpEarned > 0 && (
                <span className="xp-earned">+{answerFeedback.xpEarned} XP</span>
              )}
            </div>
            {answerFeedback.explanation && (
              <div className="feedback-explanation">
                <strong>Explanation:</strong> {answerFeedback.explanation}
              </div>
            )}
          </div>
        )}

        {/* Session Controls */}
        {!sessionActive && !sessionComplete && (
          <div className="session-controls">
            <button
              className="btn btn-primary start-session-button"
              onClick={startSession}
              disabled={loading}
            >
              {loading ? 'Starting...' : 'Start Learning Session'}
            </button>
          </div>
        )}

        {sessionActive && (
          <div className="session-controls">
            <button
              className="btn btn-danger end-session-button"
              onClick={endSession}
              disabled={loading}
            >
              End Session
            </button>
          </div>
        )}

        {/* Session Complete */}
        {sessionComplete && (
          <div className="session-complete">
            <div className="completion-header">
              <h2>🎉 Session Complete!</h2>
              <p>Great job on your learning session!</p>
            </div>
            
            <div className="final-stats">
              <h3>Your Performance</h3>
              <div className="stats-summary">
                <div className="summary-item">
                  <span className="summary-label">Questions Answered:</span>
                  <span className="summary-value">{sessionStats.questions_answered}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Correct Answers:</span>
                  <span className="summary-value">{sessionStats.questions_correct}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">Accuracy:</span>
                  <span className="summary-value">
                    {sessionStats.questions_answered > 0 
                      ? Math.round((sessionStats.questions_correct / sessionStats.questions_answered) * 100)
                      : 0}%
                  </span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">XP Earned:</span>
                  <span className="summary-value xp">{sessionStats.xp_earned}</span>
                </div>
              </div>
            </div>

            <div className="completion-actions">
              <button
                className="btn btn-primary new-session-button"
                onClick={resetSession}
              >
                Start New Session
              </button>
              <button
                className="btn btn-success show-leaderboard-button"
                onClick={() => setShowLeaderboard(true)}
              >
                View Leaderboard
              </button>
            </div>
          </div>
        )}


        </div> {/* End of main-content-area */}

        {/* Overlay Elements - Outside main content area */}

        {/* Leaderboard Modal */}
        {showLeaderboard && (
          <div className="leaderboard-modal">
            <div className="modal-content">
              <div className="modal-header">
                <h3>🏆 Weekly Leaderboard - {selectedCategory}</h3>
                <button
                  className="close-modal"
                  onClick={() => setShowLeaderboard(false)}
                >
                  ×
                </button>
              </div>
              
              <div className="leaderboard-list">
                {leaderboard.map((entry, index) => (
                  <div 
                    key={entry.user_id || index}
                    className={`leaderboard-entry ${entry.user_id === user?.id ? 'current-user' : ''}`}
                  >
                    <div className="rank">#{index + 1}</div>
                    <div className="username">{entry.username || entry.name}</div>
                    <div className="score">{entry.total_xp} XP</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ⚡ Instant XP Display - Success Animation */}
        {successAnimation && answerFeedback && (
          <div className="instant-xp-popup success-animation">
            <div className="xp-celebration">
              <span className="success-icon">🎉</span>
              <span className="xp-text">+{answerFeedback.xpEarned} XP</span>
              <span className="celebration-text">Great job!</span>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
            <button 
              className="dismiss-error"
              onClick={() => setError('')}
            >
              ×
            </button>
          </div>
        )}

        {/* Loading Overlay - Only show for significant operations */}
        {loading && !currentQuestion && (
          <div className="loading-overlay">
            <div className="loading-spinner">
              <div className="spinner"></div>
              <p>Loading...</p>
            </div>
          </div>
        )}
      </div> {/* End of adaptive-learning-container */}
    </div> {/* End of adaptive-learning */}
    </>
  );
};

export default AdaptiveLearning;

// Clean Refactored CSS for Timer-Centric Layout
const additionalStyles = `
/* 🎯 Clean Stats Container - Timer Central Focus */
.clean-stats-container {
  width: 100%;
  padding: 1.5rem 1rem;
  background: linear-gradient(135deg, 
    rgba(59, 130, 246, 0.1) 0%, 
    rgba(147, 51, 234, 0.1) 50%, 
    rgba(239, 68, 68, 0.1) 100%);
  border-radius: 20px;
  margin-bottom: 2rem;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.stats-layout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 600px;
  margin: 0 auto;
  gap: 2rem;
}

/* 🌟 Side Stats (XP & Success) */
.side-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 120px;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  backdrop-filter: blur(5px);
}

.side-stat:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 25px rgba(0, 0, 0, 0.15);
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.15);
}

/* XP Icon */
.stat-icon-large {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.75rem;
  box-shadow: 0 4px 15px rgba(251, 191, 36, 0.3);
}

.stat-icon-large .icon {
  font-size: 1.75rem;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

/* Stat Values & Labels */
.stat-value-large {
  font-size: 1.75rem;
  font-weight: 800;
  color: #ffffff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  margin-bottom: 0.25rem;
}

.stat-label-clean {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-align: center;
}

/* ⏰ Central Timer - Hero Element */
.center-timer {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
}

.timer-circle-large {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.timer-svg-large {
  filter: drop-shadow(0 8px 20px rgba(0, 0, 0, 0.2));
}

.timer-content-large {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 3;
}

.timer-time-large {
  font-size: 2rem;
  font-weight: 900;
  color: #ffffff;
  text-shadow: 0 3px 10px rgba(0, 0, 0, 0.4);
  font-family: 'Courier New', monospace;
  letter-spacing: 2px;
}

.timer-label-large {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 0.25rem;
}

/* Timer Progress Colors */
.timer-progress-large.safe {
  stroke: #10b981;
  filter: drop-shadow(0 0 8px rgba(16, 185, 129, 0.6));
}

.timer-progress-large.warning {
  stroke: #f59e0b;
  filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.6));
}

.timer-progress-large.critical {
  stroke: #ef4444;
  filter: drop-shadow(0 0 12px rgba(239, 68, 68, 0.8));
  animation: criticalPulse 1s ease-in-out infinite;
}

@keyframes criticalPulse {
  0%, 100% { 
    opacity: 1; 
    stroke-width: 8;
  }
  50% { 
    opacity: 0.7; 
    stroke-width: 10;
  }
}

/* Critical Time Pulse Effect */
.pulse-effect {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 140px;
  height: 140px;
  border: 3px solid #ef4444;
  border-radius: 50%;
  animation: expandPulse 2s ease-out infinite;
  pointer-events: none;
  z-index: 1;
}

@keyframes expandPulse {
  0% {
    width: 120px;
    height: 120px;
    opacity: 1;
  }
  100% {
    width: 160px;
    height: 160px;
    opacity: 0;
  }
}

/* 📊 Success Rate Circle */
.circular-progress-large {
  position: relative;
  margin-bottom: 0.75rem;
}

.center-value-large {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

/* 📱 Mobile Responsive Design */
@media (max-width: 768px) {
  .clean-stats-container {
    padding: 1rem 0.75rem;
  }
  
  .stats-layout {
    gap: 1rem;
    max-width: 100%;
  }
  
  .side-stat {
    min-width: 90px;
    padding: 0.75rem;
  }
  
  .stat-icon-large {
    width: 40px;
    height: 40px;
  }
  
  .stat-icon-large .icon {
    font-size: 1.5rem;
  }
  
  .stat-value-large {
    font-size: 1.5rem;
  }
  
  .timer-svg-large {
    width: 100px;
    height: 100px;
  }
  
  .timer-time-large {
    font-size: 1.5rem;
  }
  
  .circular-progress-large svg {
    width: 50px;
    height: 50px;
  }
}

@media (max-width: 580px) {
  .stats-layout {
    flex-direction: column;
    gap: 1.5rem;
  }
  
  .center-timer {
    order: -1; /* Timer goes to top on mobile */
  }
  
  .side-stat {
    min-width: 140px;
  }
  
  .stats-layout {
    align-items: center;
  }
}

@media (max-width: 400px) {
  .side-stat {
    min-width: 120px;
    padding: 0.5rem;
  }
  
  .stat-value-large {
    font-size: 1.25rem;
  }
  
  .timer-svg-large {
    width: 90px;
    height: 90px;
  }
  
  .timer-time-large {
    font-size: 1.25rem;
  }
}
`;

// Inject the additional styles
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = additionalStyles;
  document.head.appendChild(styleSheet);
}