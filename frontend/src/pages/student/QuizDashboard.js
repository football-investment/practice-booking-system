import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './QuizDashboard.css';

const QuizDashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [overview, setOverview] = useState(null);
  const [availableQuizzes, setAvailableQuizzes] = useState([]);
  const [recentAttempts, setRecentAttempts] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [theme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadQuizDashboard();
  }, []);

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

  const loadQuizDashboard = async () => {
    try {
      setLoading(true);
      
      const [overviewResponse, quizzesResponse, attemptsResponse, statsResponse] = await Promise.all([
        apiService.getQuizDashboardOverview(),
        apiService.getAvailableQuizzes(),
        apiService.getMyQuizAttempts(),
        apiService.getMyQuizStatistics()
      ]);
      
      setOverview(overviewResponse);
      setAvailableQuizzes(quizzesResponse);
      setRecentAttempts(attemptsResponse.slice(0, 5));
      setStatistics(statsResponse);
      
    } catch (err) {
      console.error('Failed to load quiz dashboard:', err);
      setError(err.message || 'Failed to load quiz dashboard');
    } finally {
      setLoading(false);
    }
  };

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
      informatics: 'Computer Science',
      sports_physiology: 'Sports Physiology',
      nutrition: 'Sports Nutrition'
    };
    return names[category] || category;
  };

  const getDifficultyColor = (difficulty) => {
    const colors = {
      easy: '#10b981',    // green
      medium: '#f59e0b',  // amber
      hard: '#ef4444'     // red
    };
    return colors[difficulty] || colors.medium;
  };

  const getDifficultyName = (difficulty) => {
    const names = {
      easy: 'Easy',
      medium: 'Medium',
      hard: 'Hard'
    };
    return names[difficulty] || difficulty;
  };

  if (loading) {
    return (
      <div className="quiz-dashboard">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="quiz-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1>🧠 Quiz Center</h1>
          <p>Welcome, {user?.full_name || user?.name}! Test your knowledge in various subjects.</p>
        </div>
        <div className="header-actions">
          <button onClick={loadQuizDashboard} disabled={loading} className="refresh-btn">
            🔄 Refresh
          </button>
          <Link to="/student/dashboard" className="back-btn">
            ← Back
          </Link>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Statistics Overview */}
      {overview && (
        <div className="stats-overview">
          <div className="stat-card">
            <div className="stat-icon">📚</div>
            <div className="stat-content">
              <div className="stat-value">{overview.available_quizzes}</div>
              <div className="stat-label">Available Quizzes</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <div className="stat-value">{overview.completed_quizzes}</div>
              <div className="stat-label">Completed Tests</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon">⭐</div>
            <div className="stat-content">
              <div className="stat-value">{overview.total_xp_from_quizzes}</div>
              <div className="stat-label">XP Earned</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon">🏆</div>
            <div className="stat-content">
              <div className="stat-value">
                {overview.best_category ? getCategoryIcon(overview.best_category) : '—'}
              </div>
              <div className="stat-label">
                {overview.best_category ? getCategoryName(overview.best_category) : 'No data'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Available Quizzes */}
      <div className="quizzes-section">
        <h2>🎯 Available Tests</h2>
        
        {availableQuizzes.length === 0 ? (
          <div className="empty-state">
            <p>🎉 Congratulations! You have completed all available tests!</p>
            <Link to="/student/dashboard" className="cta-button">
              Back to Dashboard
            </Link>
          </div>
        ) : (
          <div className="quizzes-grid">
            {availableQuizzes.map(quiz => (
              <div key={quiz.id} className="quiz-card">
                <div className="quiz-header">
                  <div className="quiz-category">
                    <span className="category-icon">{getCategoryIcon(quiz.category)}</span>
                    <span className="category-name">{getCategoryName(quiz.category)}</span>
                  </div>
                  <div 
                    className="difficulty-badge"
                    style={{ backgroundColor: getDifficultyColor(quiz.difficulty) }}
                  >
                    {getDifficultyName(quiz.difficulty)}
                  </div>
                </div>
                
                <div className="quiz-content">
                  <h3>{quiz.title}</h3>
                  {quiz.description && <p className="quiz-description">{quiz.description}</p>}
                  
                  <div className="quiz-meta">
                    <div className="meta-item">
                      <span className="meta-icon">❓</span>
                      <span>{quiz.question_count} questions</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-icon">⏱️</span>
                      <span>{quiz.time_limit_minutes} minutes</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-icon">⭐</span>
                      <span>{quiz.xp_reward} XP</span>
                    </div>
                  </div>
                </div>
                
                <div className="quiz-actions">
                  <Link 
                    to={`/student/quiz/${quiz.id}/take`}
                    className="start-quiz-btn"
                  >
                    🚀 Start Quiz
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Attempts */}
      {recentAttempts.length > 0 && (
        <div className="recent-attempts-section">
          <h2>📊 Recent Results</h2>
          <div className="attempts-list">
            {recentAttempts.map(attempt => (
              <div key={attempt.id} className="attempt-card">
                <div className="attempt-header">
                  <div className="attempt-title">
                    <span className="category-icon">{getCategoryIcon(attempt.quiz_category)}</span>
                    <span>{attempt.quiz_title}</span>
                  </div>
                  <div className={`attempt-status ${attempt.passed ? 'passed' : 'failed'}`}>
                    {attempt.passed ? '✅ Passed' : '❌ Failed'}
                  </div>
                </div>
                
                <div className="attempt-details">
                  <div className="detail-item">
                    <span>Score:</span>
                    <span>{attempt.score?.toFixed(1) || 0}%</span>
                  </div>
                  <div className="detail-item">
                    <span>XP:</span>
                    <span>{attempt.xp_awarded}</span>
                  </div>
                  <div className="detail-item">
                    <span>Duration:</span>
                    <span>
                      {(() => {
                        // time_spent_minutes now contains seconds
                        const totalSeconds = Math.max(0, attempt.time_spent_minutes || 0);
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
                    <span>Date:</span>
                    <span>
                      {attempt.completed_at && attempt.completed_at !== null 
                        ? new Date(attempt.completed_at).toLocaleDateString('en-US')
                        : 'Incomplete'
                      }
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="view-all">
            <Link to="/student/quiz/history" className="view-all-btn">
              View all results →
            </Link>
          </div>
        </div>
      )}

      {/* Statistics Summary */}
      {statistics && (
        <div className="statistics-section">
          <h2>📈 Statistics</h2>
          <div className="stats-grid">
            <div className="detailed-stat-card">
              <h3>Performance</h3>
              <div className="stat-rows">
                <div className="stat-row">
                  <span>Completed Tests:</span>
                  <span>{statistics.total_quizzes_completed}</span>
                </div>
                <div className="stat-row">
                  <span>Passed Tests:</span>
                  <span>{statistics.total_quizzes_passed}</span>
                </div>
                <div className="stat-row">
                  <span>Average Score:</span>
                  <span>{statistics.average_score?.toFixed(1) || 0}%</span>
                </div>
                <div className="stat-row">
                  <span>Pass Rate:</span>
                  <span>{statistics.pass_rate?.toFixed(1) || 0}%</span>
                </div>
              </div>
            </div>
            
            <div className="detailed-stat-card">
              <h3>Progress</h3>
              <div className="stat-rows">
                <div className="stat-row">
                  <span>Total Attempted:</span>
                  <span>{statistics.total_quizzes_attempted}</span>
                </div>
                <div className="stat-row">
                  <span>Completion Rate:</span>
                  <span>{statistics.completion_rate?.toFixed(1) || 0}%</span>
                </div>
                <div className="stat-row">
                  <span>Total XP:</span>
                  <span>{statistics.total_xp_earned}</span>
                </div>
                <div className="stat-row">
                  <span>Favorite Category:</span>
                  <span>
                    {statistics.favorite_category ? 
                      getCategoryName(statistics.favorite_category) : 
                      'No data'
                    }
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuizDashboard;