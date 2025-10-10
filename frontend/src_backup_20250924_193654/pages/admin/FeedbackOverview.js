import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const FeedbackOverview = () => {
  const { logout } = useAuth();
  const [feedback, setFeedback] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [sessionFilter, setSessionFilter] = useState('all');
  const [ratingFilter, setRatingFilter] = useState('all');
  const [deletingFeedback, setDeletingFeedback] = useState(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      console.log('Loading feedback overview data...');
      
      const [feedbackResponse, sessionsResponse, usersResponse] = await Promise.all([
        apiService.getAllFeedback().catch(() => ({})),
        apiService.getSessions().catch(() => ({})),
        apiService.getUsers().catch(() => ({}))
      ]);
      
      console.log('Feedback API response:', feedbackResponse);
      console.log('Sessions API response:', sessionsResponse);
      console.log('Users API response:', usersResponse);
      
      // Extract data arrays from API response objects
      const feedbackData = feedbackResponse?.feedbacks || feedbackResponse?.data || feedbackResponse || [];
      const sessionsData = sessionsResponse?.sessions || sessionsResponse || [];
      const usersData = usersResponse?.users || usersResponse || [];
      
      setFeedback(feedbackData);
      setSessions(sessionsData);
      setUsers(usersData);
      
      console.log('Feedback data loaded:', {
        feedback: feedbackData.length,
        sessions: sessionsData.length,
        users: usersData.length
      });
      
    } catch (err) {
      console.error('Failed to load feedback data:', err);
      setError('Failed to load feedback data');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFeedback = async (feedbackId) => {
    if (!window.confirm('Are you sure you want to delete this feedback?')) {
      return;
    }
    
    setDeletingFeedback(feedbackId);
    try {
      await apiService.deleteFeedback(feedbackId);
      setSuccess('Feedback deleted successfully');
      loadAllData();
    } catch (err) {
      console.error('Feedback deletion failed:', err);
      setError(`Failed to delete feedback: ${err.message}`);
    } finally {
      setDeletingFeedback(null);
    }
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user?.full_name || user?.email || `User ${userId}`;
  };

  const getSessionName = (sessionId) => {
    const session = sessions.find(s => s.id === sessionId);
    return session?.title || `Session ${sessionId}`;
  };

  const filteredFeedback = feedback.filter(item => {
    const matchesSession = sessionFilter === 'all' || item.session_id === parseInt(sessionFilter);
    
    let matchesRating = true;
    if (ratingFilter !== 'all') {
      const rating = item.rating;
      switch (ratingFilter) {
        case 'excellent':
          matchesRating = rating >= 4;
          break;
        case 'good':
          matchesRating = rating === 3;
          break;
        case 'poor':
          matchesRating = rating <= 2;
          break;
      }
    }
    
    return matchesSession && matchesRating;
  });

  const feedbackStats = {
    total: feedback.length,
    averageRating: feedback.length > 0 ? 
      (feedback.reduce((sum, f) => sum + f.rating, 0) / feedback.length).toFixed(1) : 0,
    averageSessionQuality: feedback.length > 0 ? 
      (feedback.reduce((sum, f) => sum + (f.session_quality || 0), 0) / feedback.length).toFixed(1) : 0,
    averageInstructorRating: feedback.length > 0 ? 
      (feedback.reduce((sum, f) => sum + (f.instructor_rating || 0), 0) / feedback.length).toFixed(1) : 0,
    recommendationRate: feedback.length > 0 ? 
      Math.round((feedback.filter(f => f.would_recommend).length / feedback.length) * 100) : 0
  };

  const exportFeedbackCSV = () => {
    const csvData = filteredFeedback.map(item => {
      const session = sessions.find(s => s.id === item.session_id);
      const user = users.find(u => u.id === item.user_id);
      
      return {
        'User Name': user?.full_name || user?.email,
        'User Email': user?.email,
        'Session Title': session?.title,
        'Session Date': session?.date_start ? new Date(session.date_start).toLocaleDateString() : '',
        'Overall Rating': item.rating,
        'Session Quality': item.session_quality || '',
        'Instructor Rating': item.instructor_rating || '',
        'Would Recommend': item.would_recommend ? 'Yes' : 'No',
        'Comment': item.comment || '',
        'Submitted Date': new Date(item.created_at).toLocaleDateString()
      };
    });

    const csvContent = [
      Object.keys(csvData[0] || {}).join(','),
      ...csvData.map(row => Object.values(row).map(val => `"${val}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback_report_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    
    setSuccess('Feedback report exported successfully!');
  };

  return (
    <div className="feedback-overview">
      {/* Navigation */}
      <div className="admin-page-header">
        <div>
          <Link to="/admin/dashboard" className="back-link">← Admin Dashboard</Link>
          <h1>Feedback Overview</h1>
        </div>
        <div className="header-actions">
          <button 
            onClick={exportFeedbackCSV}
            className="export-btn primary"
            disabled={filteredFeedback.length === 0}
          >
            📊 Export CSV
          </button>
          <button onClick={() => logout()} className="logout-btn">Logout</button>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Feedback Stats */}
      <div className="feedback-stats">
        <div className="stat-card">
          <h3>Total Feedback</h3>
          <div className="stat-number">{feedbackStats.total}</div>
        </div>
        <div className="stat-card">
          <h3>Average Rating</h3>
          <div className="stat-number">⭐ {feedbackStats.averageRating}/5</div>
        </div>
        <div className="stat-card">
          <h3>Session Quality</h3>
          <div className="stat-number">⭐ {feedbackStats.averageSessionQuality}/5</div>
        </div>
        <div className="stat-card">
          <h3>Instructor Rating</h3>
          <div className="stat-number">⭐ {feedbackStats.averageInstructorRating}/5</div>
        </div>
        <div className="stat-card">
          <h3>Recommendation Rate</h3>
          <div className="stat-number">{feedbackStats.recommendationRate}%</div>
        </div>
      </div>

      {/* Filters */}
      <div className="feedback-filters">
        <div className="filter-section">
          <select
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="session-filter"
          >
            <option value="all">All Sessions</option>
            {sessions.map(session => (
              <option key={session.id} value={session.id}>
                {session.title || `Session ${session.id}`}
              </option>
            ))}
          </select>
          
          <select
            value={ratingFilter}
            onChange={(e) => setRatingFilter(e.target.value)}
            className="rating-filter"
          >
            <option value="all">All Ratings</option>
            <option value="excellent">Excellent (4-5 stars)</option>
            <option value="good">Good (3 stars)</option>
            <option value="poor">Poor (1-2 stars)</option>
          </select>
        </div>
      </div>

      {/* Feedback List */}
      <div className="feedback-container">
        {loading ? (
          <div className="loading-state">Loading feedback...</div>
        ) : filteredFeedback.length === 0 ? (
          <div className="empty-state">
            <h3>No feedback found</h3>
            <p>Try adjusting your filters</p>
          </div>
        ) : (
          <div className="feedback-list">
            {filteredFeedback.map(item => {
              const user = users.find(u => u.id === item.user_id);
              const session = sessions.find(s => s.id === item.session_id);
              
              return (
                <div key={item.id} className="feedback-card">
                  <div className="feedback-header">
                    <div className="feedback-user">
                      <div className="user-avatar">🎓</div>
                      <div>
                        <div className="user-name">{user?.full_name || user?.email}</div>
                        <div className="feedback-date">
                          {new Date(item.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                    <div className="feedback-session">
                      <div className="session-name">{session?.title || `Session ${item.session_id}`}</div>
                      <div className="session-date">
                        {session?.date_start ? new Date(session.date_start).toLocaleDateString() : ''}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteFeedback(item.id)}
                      disabled={deletingFeedback === item.id}
                      className="delete-feedback-btn"
                      title="Delete Feedback"
                    >
                      {deletingFeedback === item.id ? '⏳' : '🗑️'}
                    </button>
                  </div>

                  <div className="feedback-ratings">
                    <div className="rating-item">
                      <span className="rating-label">Overall:</span>
                      <span className="rating-stars">
                        {'⭐'.repeat(item.rating)} ({item.rating}/5)
                      </span>
                    </div>
                    {item.session_quality && (
                      <div className="rating-item">
                        <span className="rating-label">Session Quality:</span>
                        <span className="rating-stars">
                          {'⭐'.repeat(item.session_quality)} ({item.session_quality}/5)
                        </span>
                      </div>
                    )}
                    {item.instructor_rating && (
                      <div className="rating-item">
                        <span className="rating-label">Instructor:</span>
                        <span className="rating-stars">
                          {'⭐'.repeat(item.instructor_rating)} ({item.instructor_rating}/5)
                        </span>
                      </div>
                    )}
                    <div className="rating-item">
                      <span className="rating-label">Recommendation:</span>
                      <span className={`recommendation ${item.would_recommend ? 'positive' : 'negative'}`}>
                        {item.would_recommend ? '👍 Yes' : '👎 No'}
                      </span>
                    </div>
                  </div>

                  {item.comment && (
                    <div className="feedback-comment">
                      <h4>Comment:</h4>
                      <p>"{item.comment}"</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default FeedbackOverview;