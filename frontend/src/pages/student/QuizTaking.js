import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { apiService } from '../../services/apiService';
import './QuizTaking.css';

const QuizTaking = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { theme, colorScheme } = useTheme();
  
  const [quiz, setQuiz] = useState(null);
  const [attempt, setAttempt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState({});
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [timeLeft, setTimeLeft] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [timeUpHandled, setTimeUpHandled] = useState(false);
  const [showTimeUpNotification, setShowTimeUpNotification] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [answerFeedback, setAnswerFeedback] = useState({});
  
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  useEffect(() => {
    loadQuiz();
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Theme is handled by ThemeContext, no need for manual theme management

  const loadQuiz = async () => {
    try {
      setLoading(true);
      
      // Validate quiz ID
      const quizId = parseInt(id);
      if (isNaN(quizId) || quizId <= 0) {
        setError('Invalid quiz ID');
        return;
      }
      
      // Get quiz details
      const quizResponse = await apiService.getQuizForTaking(quizId);
      setQuiz(quizResponse);
      
      // Start attempt
      const attemptResponse = await apiService.startQuizAttempt(quizId);
      if (!attemptResponse || !attemptResponse.id) {
        throw new Error('Failed to create quiz attempt');
      }
      setAttempt(attemptResponse);
      
      // Initialize timer
      const timeLimit = quizResponse.time_limit_minutes * 60; // Convert to seconds
      setTimeLeft(timeLimit);
      startTimeRef.current = Date.now();
      
      // Start countdown
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        const remaining = timeLimit - elapsed;
        
        if (remaining <= 0) {
          setTimeLeft(0);
          if (!timeUpHandled) {
            handleTimeUp();
          }
        } else {
          setTimeLeft(remaining);
        }
      }, 1000);
      
    } catch (err) {
      console.error('Failed to load quiz:', err);
      setError(err.message || 'Failed to load quiz');
    } finally {
      setLoading(false);
    }
  };

  const displayTimeUpNotification = () => {
    setShowTimeUpNotification(true);
    // Auto-hide after 3 seconds and submit
    setTimeout(async () => {
      setShowTimeUpNotification(false);
      await submitQuiz(true);
    }, 3000);
  };

  const handleTimeUp = async () => {
    // Set flag to prevent multiple calls
    setTimeUpHandled(true);
    
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    
    // Create animated time-up notification instead of alert
    displayTimeUpNotification();
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
    
    // Add visual feedback for answer selection
    setSelectedAnswer(questionId);
    setAnswerFeedback(prev => ({
      ...prev,
      [questionId]: { 
        selected: true, 
        timestamp: Date.now(),
        value: value
      }
    }));
    
    // Clear feedback after animation
    setTimeout(() => {
      setSelectedAnswer(null);
    }, 500);
  };

  const getCurrentQuestionData = () => {
    if (!quiz || !quiz.questions) return null;
    return quiz.questions[currentQuestion];
  };

  const nextQuestion = () => {
    if (currentQuestion < quiz.questions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    }
  };

  const previousQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(prev => prev - 1);
    }
  };

  const goToQuestion = (index) => {
    setCurrentQuestion(index);
  };

  const submitQuiz = async (forced = false) => {
    if (!forced && !showConfirmDialog) {
      setShowConfirmDialog(true);
      return;
    }

    try {
      setSubmitting(true);
      
      // Clear timer to prevent any further timeup events
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      
      // Check if attempt exists
      if (!attempt || !attempt.id) {
        console.error('No valid attempt found for quiz submission');
        setError('Quiz session expired. Please start the quiz again.');
        setSubmitting(false);
        // Navigate back to quiz selection
        navigate('/student/quiz');
        return;
      }
      
      // Format answers for submission
      const formattedAnswers = Object.entries(answers).map(([questionId, answer]) => {
        const questionData = quiz.questions.find(q => q.id.toString() === questionId);
        
        if (!questionData) return null;
        
        const submission = {
          question_id: parseInt(questionId)
        };
        
        if (questionData.question_type === 'multiple_choice' || questionData.question_type === 'true_false') {
          submission.selected_option_id = parseInt(answer);
        } else if (questionData.question_type === 'fill_in_blank') {
          submission.answer_text = answer;
        }
        
        return submission;
      }).filter(Boolean);
      
      const result = await apiService.submitQuizAttempt(attempt.id, formattedAnswers);
      
      // Navigate to results page
      navigate('/student/quiz/result', { 
        state: { result: result, quiz: quiz } 
      });
      
    } catch (err) {
      console.error('Failed to submit quiz:', err);
      setError(err.message || 'Failed to submit quiz');
      setSubmitting(false);
    }
  };

  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const getAnsweredCount = () => {
    return Object.keys(answers).length;
  };

  const isQuestionAnswered = (questionIndex) => {
    const question = quiz.questions[questionIndex];
    return question && answers[question.id] !== undefined;
  };

  if (loading) {
    return (
      <div className="quiz-taking">
        <div className="loading-state">
          <div className="loading-spinner-enhanced">
            <div className="spinner-ring"></div>
            <div className="spinner-emoji">🧠</div>
          </div>
          <div className="loading-text">
            <h3>🚀 Preparing Your Quiz Experience</h3>
            <p>Optimizing questions for maximum learning impact...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="quiz-taking">
        <div className="error-state-enhanced">
          <div className="error-icon-container">
            <span className="error-emoji">😰</span>
            <div className="error-pulse"></div>
          </div>
          <h2>⚠️ Oops! Something went wrong</h2>
          <div className="error-message">
            <p>{error}</p>
          </div>
          <div className="error-actions">
            <button onClick={() => navigate('/student/quiz')} className="back-btn-enhanced">
              <span>🏠</span> Return to Quiz Dashboard
            </button>
            <button onClick={loadQuiz} className="retry-btn-enhanced">
              <span>🔄</span> Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!quiz) {
    return (
      <div className="quiz-taking">
        <div className="error-state">
          <h2>Quiz Not Found</h2>
          <button onClick={() => navigate('/student/quiz')} className="back-btn">
            Back to Quiz List
          </button>
        </div>
      </div>
    );
  }

  const question = getCurrentQuestionData();

  return (
    <div className="quiz-taking">
      {/* Quiz Header */}
      <div className="quiz-header">
        <div className="quiz-info">
          <h1>
            <span className="quiz-emoji">🎯</span>
            {quiz.title}
            <span className="quiz-sparkle">✨</span>
          </h1>
          <div className="quiz-meta">
            <span className="progress-indicator">
              📝 Question {currentQuestion + 1} / {quiz.questions.length}
            </span>
            <span>•</span>
            <span className="answered-indicator">
              ✅ {getAnsweredCount()} / {quiz.questions.length} completed
            </span>
          </div>
        </div>
        
        <div className="quiz-timer">
          <div className={`timer ${timeLeft <= 120 ? 'warning' : ''} ${timeLeft <= 60 ? 'danger' : ''}`}>
            <span className="timer-icon">⏱️</span>
            <span className="timer-text">{formatTime(timeLeft)}</span>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-container">
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${((currentQuestion + 1) / quiz.questions.length) * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Question Navigation */}
      <div className="question-navigation">
        {quiz.questions.map((_, index) => (
          <button
            key={index}
            className={`question-nav-btn ${
              index === currentQuestion ? 'current' : ''
            } ${isQuestionAnswered(index) ? 'answered' : ''}`}
            onClick={() => goToQuestion(index)}
          >
            {index + 1}
          </button>
        ))}
      </div>

      {/* Current Question */}
      {question && (
        <div className="question-container">
          <div className="question-card">
            <div className="question-header">
              <h2>Question {currentQuestion + 1}</h2>
              <div className="question-points">{question.points} {question.points === 1 ? 'point' : 'points'}</div>
            </div>
            
            <div className="question-content">
              <p className="question-text">{question.question_text}</p>
              
              <div className="answer-options">
                {question.question_type === 'multiple_choice' && (
                  <div className="multiple-choice-options">
                    {question.answer_options.map(option => (
                      <label key={option.id} className="option-label">
                        <input
                          type="radio"
                          name={`question_${question.id}`}
                          value={option.id}
                          checked={answers[question.id] === option.id.toString()}
                          onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                        />
                        <div className="option-content">
                          <div className="option-radio"></div>
                          <span className="option-text">{option.option_text}</span>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
                
                {question.question_type === 'true_false' && (
                  <div className="true-false-options">
                    {question.answer_options.map(option => (
                      <button
                        key={option.id}
                        className={`tf-option ${answers[question.id] === option.id.toString() ? 'selected' : ''}`}
                        onClick={() => handleAnswerChange(question.id, option.id.toString())}
                      >
                        {(option.option_text === 'Igaz' || option.option_text === 'True' || (option.option_text.toLowerCase().includes('igen') && !option.option_text.toLowerCase().includes('nem'))) ? `✅ ${option.option_text}` : `❌ ${option.option_text}`}
                      </button>
                    ))}
                  </div>
                )}
                
                {question.question_type === 'fill_in_blank' && (
                  <div className="fill-blank-container">
                    <p className="instruction">Choose the most appropriate answer:</p>
                    <select
                      value={answers[question.id] || ''}
                      onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                      className="fill-blank-select"
                    >
                      <option value="">-- Select --</option>
                      {question.answer_options.map(option => (
                        <option key={option.id} value={option.option_text}>
                          {option.option_text}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Controls */}
      <div className="quiz-navigation">
        <button 
          onClick={previousQuestion} 
          disabled={currentQuestion === 0}
          className="nav-btn secondary"
        >
          ← Previous
        </button>
        
        <div className="nav-center">
          {currentQuestion === quiz.questions.length - 1 ? (
            <button 
              onClick={() => submitQuiz()} 
              className="submit-btn primary"
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : '🚀 Submit Quiz'}
            </button>
          ) : (
            <button 
              onClick={nextQuestion} 
              className="nav-btn primary"
            >
              Next →
            </button>
          )}
        </div>
        
        <button 
          onClick={() => setShowConfirmDialog(true)} 
          className="nav-btn secondary"
        >
          Finish
        </button>
      </div>

      {/* Confirm Dialog */}
      {showConfirmDialog && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Submit Quiz</h3>
            <p>
              Are you sure you want to submit the quiz? 
              {getAnsweredCount() < quiz.questions.length && (
                <span className="warning-text">
                  <br/>Warning: {quiz.questions.length - getAnsweredCount()} questions are still unanswered!
                </span>
              )}
            </p>
            <div className="modal-actions">
              <button 
                onClick={() => setShowConfirmDialog(false)} 
                className="modal-btn secondary"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  setShowConfirmDialog(false);
                  submitQuiz(true);
                }} 
                className="modal-btn primary"
                disabled={submitting}
              >
                {submitting ? 'Submitting...' : 'Yes, Submit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Time Up Notification */}
      {showTimeUpNotification && (
        <div className="time-up-notification">
          <div className="notification-content">
            <div className="notification-icon">
              <span className="timer-emoji">⏰</span>
              <div className="pulse-ring"></div>
            </div>
            <div className="notification-text">
              <h3>⏰ Time's Up!</h3>
              <p>Your quiz will be automatically submitted...</p>
            </div>
            <div className="countdown-circle">
              <div className="countdown-progress"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuizTaking;