import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './InstructorFeedback.css';

const InstructorFeedback = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState([]);
  const [filteredFeedback, setFilteredFeedback] = useState([]);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    search: '',
    rating: 'all',
    session: 'all',
    dateRange: 'all'
  });
  const [stats, setStats] = useState({
    totalFeedback: 0,
    averageRating: 0,
    recentFeedback: 0,
    highRatings: 0
  });

  useEffect(() => {
    loadFeedback();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [feedback, filters]);

  const loadFeedback = async () => {
    try {
      setLoading(true);
      const response = await apiService.getInstructorFeedback();
      const feedbackData = Array.isArray(response) ? response : (response?.feedback || []);
      
      setFeedback(feedbackData);
      calculateStats(feedbackData);
      
      console.log('Instructor feedback loaded:', feedbackData.length);
    } catch (err) {
      console.error('Failed to load feedback:', err);
      setError('Failed to load feedback: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (feedbackData) => {
    const stats = {
      totalFeedback: feedbackData.length,
      averageRating: 0,
      recentFeedback: 0,
      highRatings: 0
    };

    if (feedbackData.length > 0) {
      // Calculate average rating
      const totalRating = feedbackData.reduce((sum, fb) => sum + (fb.rating || 0), 0);
      stats.averageRating = Math.round((totalRating / feedbackData.length) * 10) / 10;

      // Count high ratings (4+ stars)
      stats.highRatings = feedbackData.filter(fb => fb.rating >= 4).length;

      // Count recent feedback (last 30 days)
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      
      stats.recentFeedback = feedbackData.filter(fb => 
        new Date(fb.created_at) >= thirtyDaysAgo
      ).length;
    }

    setStats(stats);
  };

  const applyFilters = () => {
    let filtered = [...feedback];

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(fb =>
        fb.session?.title?.toLowerCase().includes(filters.search.toLowerCase()) ||
        fb.comment?.toLowerCase().includes(filters.search.toLowerCase()) ||
        fb.user?.name?.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Rating filter
    if (filters.rating !== 'all') {
      const ratingValue = parseInt(filters.rating);
      filtered = filtered.filter(fb => Math.floor(fb.rating) === ratingValue);
    }

    // Date range filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      let dateThreshold;
      
      switch (filters.dateRange) {
        case 'week':
          dateThreshold = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case 'month':
          dateThreshold = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          break;
        case 'quarter':
          dateThreshold = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
          break;
        default:
          dateThreshold = null;
      }
      
      if (dateThreshold) {
        filtered = filtered.filter(fb => new Date(fb.created_at) >= dateThreshold);
      }
    }

    setFilteredFeedback(filtered);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const getRatingStars = (rating) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 !== 0;
    
    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push('⭐');
      } else if (i === fullStars && hasHalfStar) {
        stars.push('⭐');
      } else {
        stars.push('☆');
      }
    }
    
    return stars.join('');
  };

  const getRatingColor = (rating) => {
    if (rating >= 4.5) return '#10b981'; // green
    if (rating >= 3.5) return '#f59e0b'; // amber
    if (rating >= 2.5) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getUniqueSessions = () => {
    const sessions = new Set();
    feedback.forEach(fb => {
      if (fb.session) {
        sessions.add(JSON.stringify({
          id: fb.session_id,
          title: fb.session.title
        }));
      }
    });
    return Array.from(sessions).map(s => JSON.parse(s));
  };

  if (loading) {
    return (
      <div className="instructor-feedback">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading feedback...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-feedback">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>💬 Feedback Overview</h1>
          <p>Monitor and analyze student feedback on your sessions</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-item">
          <span className="stat-number">{stats.totalFeedback}</span>
          <span className="stat-label">Total Feedback</span>
        </div>
        <div className="stat-item">
          <span className="stat-number" style={{ color: getRatingColor(stats.averageRating) }}>
            {stats.averageRating.toFixed(1)}
          </span>
          <span className="stat-label">Average Rating</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.recentFeedback}</span>
          <span className="stat-label">Recent (30 days)</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.highRatings}</span>
          <span className="stat-label">High Ratings (4+)</span>
        </div>
      </div>

      {/* Rating Distribution */}
      {feedback.length > 0 && (
        <div className="rating-distribution">
          <h3>Rating Distribution</h3>
          <div className="rating-bars">
            {[5, 4, 3, 2, 1].map(rating => {
              const count = feedback.filter(fb => Math.floor(fb.rating) === rating).length;
              const percentage = (count / feedback.length) * 100;
              
              return (
                <div key={rating} className="rating-bar-item">
                  <span className="rating-label">{rating}⭐</span>
                  <div className="rating-bar-container">
                    <div 
                      className="rating-bar-fill" 
                      style={{ 
                        width: `${percentage}%`,
                        backgroundColor: getRatingColor(rating)
                      }}
                    ></div>
                  </div>
                  <span className="rating-count">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filters-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Search feedback..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filter-controls">
          <select
            value={filters.rating}
            onChange={(e) => handleFilterChange('rating', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Ratings</option>
            <option value="5">5 Stars</option>
            <option value="4">4 Stars</option>
            <option value="3">3 Stars</option>
            <option value="2">2 Stars</option>
            <option value="1">1 Star</option>
          </select>

          <select
            value={filters.dateRange}
            onChange={(e) => handleFilterChange('dateRange', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Time</option>
            <option value="week">Last Week</option>
            <option value="month">Last Month</option>
            <option value="quarter">Last 3 Months</option>
          </select>

          <select
            value={filters.session}
            onChange={(e) => handleFilterChange('session', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Sessions</option>
            {getUniqueSessions().map(session => (
              <option key={session.id} value={session.id}>{session.title}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Feedback List */}
      <div className="feedback-section">
        <div className="section-header">
          <h2>Student Feedback</h2>
          <span className="results-count">{filteredFeedback.length} feedback entries</span>
        </div>

        {filteredFeedback.length === 0 ? (
          <div className="empty-state">
            {filters.search || filters.rating !== 'all' || filters.dateRange !== 'all' ? (
              <p>🔍 No feedback matches your filters.</p>
            ) : (
              <p>💬 No feedback received yet.</p>
            )}
          </div>
        ) : (
          <div className="feedback-grid">
            {filteredFeedback.map(feedbackItem => (
              <div key={feedbackItem.id} className="feedback-card">
                <div className="feedback-header">
                  <div className="feedback-rating">
                    <span className="stars">{getRatingStars(feedbackItem.rating)}</span>
                    <span className="rating-value">({feedbackItem.rating}/5)</span>
                  </div>
                  <span className="feedback-date">
                    {formatDate(feedbackItem.created_at)}
                  </span>
                </div>

                <div className="feedback-session">
                  <h4>{feedbackItem.session?.title || 'Unknown Session'}</h4>
                  <p className="session-date">
                    📅 {feedbackItem.session?.date_start ? 
                      new Date(feedbackItem.session.date_start).toLocaleDateString() : 
                      'Date unavailable'}
                  </p>
                </div>

                <div className="feedback-student">
                  <span>👤 {feedbackItem.user?.name || 'Anonymous'}</span>
                </div>

                {feedbackItem.comment && (
                  <div className="feedback-comment">
                    <p>"{feedbackItem.comment}"</p>
                  </div>
                )}

                <div className="feedback-actions">
                  <button className="btn-secondary">
                    📧 Reply
                  </button>
                  <button className="btn-tertiary">
                    🔍 View Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <div className="action-card">
            <div className="action-icon">📊</div>
            <h3>Feedback Analytics</h3>
            <p>Generate detailed feedback reports and trends</p>
            <button className="action-btn">View Analytics</button>
          </div>
          <div className="action-card">
            <div className="action-icon">📧</div>
            <h3>Follow Up</h3>
            <p>Respond to student feedback and concerns</p>
            <button className="action-btn">Manage Responses</button>
          </div>
          <div className="action-card">
            <div className="action-icon">📈</div>
            <h3>Improvement Plan</h3>
            <p>Create action plans based on feedback insights</p>
            <button className="action-btn">Create Plan</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InstructorFeedback;