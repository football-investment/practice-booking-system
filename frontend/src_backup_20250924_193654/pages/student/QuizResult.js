import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './QuizResult.css';

const QuizResult = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [theme, setTheme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme, setColorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    // Apply theme and color scheme to document
    const root = document.documentElement;
    
    if (theme === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const applyAutoTheme = () => {
        root.setAttribute('data-theme', mediaQuery.matches ? 'dark' : 'light');
        root.setAttribute('data-color', colorScheme);
      };
      
      applyAutoTheme();
      mediaQuery.addListener(applyAutoTheme);
      
      return () => mediaQuery.removeListener(applyAutoTheme);
    } else {
      root.setAttribute('data-theme', theme);
      root.setAttribute('data-color', colorScheme);
    }
  }, [theme, colorScheme]);

  // Get result data from navigation state
  const result = location.state?.result;
  const quiz = location.state?.quiz;

  useEffect(() => {
    // If no result data, redirect to quiz dashboard
    if (!result || !quiz) {
      navigate('/student/quiz');
    }
  }, [result, quiz, navigate]);

  if (!result || !quiz) {
    return (
      <div className="quiz-result">
        <div className="loading-state">
          <p>Redirecting...</p>
        </div>
      </div>
    );
  }

  const getCategoryIcon = (category) => {
    const icons = {
      marketing: '📢',
      economics: '💰',
      informatics: '💻',
      sports_physiology: '🏃‍♂️',
      nutrition: '🥗'
    };
    return icons[category] || '📚';
  };

  const getCategoryName = (category) => {
    const names = {
      marketing: 'Marketing',
      economics: 'Economics',
      informatics: 'Informatika',
      sports_physiology: 'Sports Physiology',
      nutrition: 'Nutrition'
    };
    return names[category] || category;
  };

  const getGradeIcon = () => {
    if (result.passed) {
      if (result.score >= 90) return '🏆';
      if (result.score >= 80) return '🥇';
      return '✅';
    }
    return '❌';
  };

  const getGradeColor = () => {
    if (result.passed) {
      if (result.score >= 90) return '#ffd700'; // Gold
      if (result.score >= 80) return '#10b981'; // Green
      return '#059669'; // Dark green
    }
    return '#ef4444'; // Red
  };

  const getPerformanceMessage = () => {
    if (!result.passed) {
      return "You did not reach the minimum score. Please try again later!";
    }
    
    if (result.score >= 95) {
      return "Excellent performance! Congratulations!";
    } else if (result.score >= 85) {
      return "Very good result! Great job!";
    } else if (result.score >= 75) {
      return "Good performance! You successfully completed the test.";
    } else {
      return "Acceptable result. You managed to complete the test.";
    }
  };

  return (
    <div className="quiz-result">
      {/* Header */}
      <div className="result-header">
        <div className="quiz-info">
          <div className="category-badge">
            <span className="category-icon">{getCategoryIcon(quiz.category)}</span>
            <span className="category-name">{getCategoryName(quiz.category)}</span>
          </div>
          <h1>{quiz.title}</h1>
        </div>
        
        <div className="completion-time">
          <span>Completed: {
            result.completed_at && result.completed_at !== null 
              ? new Date(result.completed_at).toLocaleString('en-US')
              : 'Incomplete'
          }</span>
        </div>
      </div>

      {/* Main Result Card */}
      <div className="main-result-card">
        <div className="result-icon-section">
          <div 
            className="result-icon"
            style={{ backgroundColor: getGradeColor() }}
          >
            {getGradeIcon()}
          </div>
          <h2 className={`result-title ${result.passed ? 'passed' : 'failed'}`}>
            {result.passed ? 'Passed!' : 'Failed'}
          </h2>
        </div>
        
        <div className="score-section">
          <div className="score-circle">
            <div className="score-value">{result.score?.toFixed(1) || 0}%</div>
            <div className="score-label">Score</div>
          </div>
          
          <div className="score-details">
            <div className="detail-item">
              <span className="detail-label">Correct Answers:</span>
              <span className="detail-value">{result.correct_answers} / {result.total_questions}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Minimum Score:</span>
              <span className="detail-value">{quiz.passing_score}%</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Time Spent:</span>
              <span className="detail-value">
                {(() => {
                  // time_spent_minutes now contains seconds
                  const totalSeconds = Math.max(0, result.time_spent_minutes || 0);
                  const minutes = Math.floor(totalSeconds / 60);
                  const seconds = totalSeconds % 60;
                  
                  if (minutes === 0) {
                    return `${seconds} seconds`;
                  } else if (seconds === 0) {
                    return `${minutes} minutes`;
                  } else {
                    return `${minutes} minutes ${seconds} seconds`;
                  }
                })()}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">XP Earned:</span>
              <span className="detail-value xp-value">+{result.xp_awarded} XP</span>
            </div>
          </div>
        </div>
        
        <div className="performance-message">
          <p>{getPerformanceMessage()}</p>
        </div>
      </div>

      {/* Statistics Card */}
      <div className="statistics-card">
        <h3>📊 Detailed Statistics</h3>
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-icon">⏱️</div>
            <div className="stat-content">
              <div className="stat-value">
                {(() => {
                  // time_spent_minutes now contains seconds, convert to minutes for display
                  const totalSeconds = Math.max(0, result.time_spent_minutes || 0);
                  const usedMinutes = Math.floor(totalSeconds / 60);
                  const remainingSeconds = totalSeconds % 60;
                  
                  if (remainingSeconds === 0) {
                    return `${usedMinutes} / ${quiz.time_limit_minutes}`;
                  } else {
                    return `${usedMinutes}:${remainingSeconds.toString().padStart(2, '0')} / ${quiz.time_limit_minutes}`;
                  }
                })()}
              </div>
              <div className="stat-label">Minutes (used/available)</div>
            </div>
          </div>
          
          <div className="stat-item">
            <div className="stat-icon">🎯</div>
            <div className="stat-content">
              <div className="stat-value">{((result.correct_answers / result.total_questions) * 100).toFixed(1)}%</div>
              <div className="stat-label">Accuracy</div>
            </div>
          </div>
          
          <div className="stat-item">
            <div className="stat-icon">🏃‍♂️</div>
            <div className="stat-content">
              <div className="stat-value">
                {(() => {
                  // time_spent_minutes now contains seconds, convert to seconds per question
                  const totalSeconds = Math.max(0, result.time_spent_minutes || 0);
                  const secondsPerQuestion = (totalSeconds / result.total_questions);
                  
                  if (secondsPerQuestion >= 60) {
                    const minutes = Math.floor(secondsPerQuestion / 60);
                    const seconds = Math.round(secondsPerQuestion % 60);
                    return seconds > 0 ? `${minutes}:${seconds.toString().padStart(2, '0')}` : `${minutes}:00`;
                  } else {
                    return `${Math.round(secondsPerQuestion)}s`;
                  }
                })()}
              </div>
              <div className="stat-label">Time/question</div>
            </div>
          </div>
          
          <div className="stat-item">
            <div className="stat-icon">⭐</div>
            <div className="stat-content">
              <div className="stat-value">{result.xp_awarded}</div>
              <div className="stat-label">XP Earned</div>
            </div>
          </div>
        </div>
      </div>

      {/* XP Reward Animation */}
      {result.xp_awarded > 0 && (
        <div className="xp-reward-section">
          <div className="xp-animation">
            <div className="xp-icon">⭐</div>
            <div className="xp-text">+{result.xp_awarded} XP earned!</div>
          </div>
          <p>XP has been automatically added to your profile.</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="action-buttons">
        <Link to="/student/quiz" className="btn secondary">
          ← Back to Tests
        </Link>
        
        <Link to="/student/dashboard" className="btn primary">
          🏠 Home
        </Link>
        
        <Link to="/student/gamification" className="btn accent">
          🏆 Gamification Profile
        </Link>
      </div>

      {/* Encouragement Section */}
      <div className="encouragement-section">
        {result.passed ? (
          <div className="success-encouragement">
            <h3>🎉 Congratulations!</h3>
            <p>You have successfully completed the {quiz.title} test. Continue learning in other areas as well!</p>
          </div>
        ) : (
          <div className="retry-encouragement">
            <h3>💪 Don't give up!</h3>
            <p>Learning is a process. Review the topic and try again later. Practice makes perfect!</p>
            <div className="tips">
              <h4>💡 Tips for next time:</h4>
              <ul>
                <li>Read the questions carefully</li>
                <li>Use the available time wisely</li>
                <li>Don't rush, think through your answers</li>
                <li>You can try again later</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuizResult;