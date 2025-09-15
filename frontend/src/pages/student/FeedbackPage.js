import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './FeedbackPage.css';

const FeedbackPage = () => {
  const { logout } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [editingFeedback, setEditingFeedback] = useState(null);
  const [feedbackForm, setFeedbackForm] = useState({
    rating: 5,
    instructor_rating: 5,
    session_quality: 5,
    would_recommend: true,
    comment: ''
  });
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

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      console.log('Loading student feedback page data...');
      
      const [bookingsResponse, feedbackResponse] = await Promise.all([
        apiService.getMyBookings().catch(() => ({})),
        apiService.getMyFeedback().catch(() => ({}))
      ]);
      
      console.log('Student Bookings API response:', bookingsResponse);
      console.log('Student Feedback API response:', feedbackResponse);
      
      // Extract data arrays from API response objects
      const bookingsData = Array.isArray(bookingsResponse) ? bookingsResponse : 
                          (bookingsResponse?.bookings || bookingsResponse?.data || []);
      const feedbackData = Array.isArray(feedbackResponse) ? feedbackResponse :
                          (feedbackResponse?.feedbacks || feedbackResponse?.data || []);
      
      // Ensure we have arrays
      const finalBookingsData = Array.isArray(bookingsData) ? bookingsData : [];
      const finalFeedbackData = Array.isArray(feedbackData) ? feedbackData : [];
      
      setBookings(finalBookingsData);
      setFeedback(finalFeedbackData);
      
      console.log('Student feedback page loaded:', { 
        bookings: finalBookingsData, 
        feedback: finalFeedbackData 
      });
      
    } catch (err) {
      console.error('Failed to load feedback data:', err);
      setError('Failed to load feedback data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitFeedback = async (e) => {
    e.preventDefault();
    if (!selectedBooking && !editingFeedback) return;
    
    const feedbackId = editingFeedback?.id || selectedBooking?.id;
    setSubmitting(feedbackId);
    setError('');
    setSuccess('');
    
    try {
      const feedbackData = {
        session_id: editingFeedback?.session_id || selectedBooking.session?.id,
        rating: feedbackForm.rating,
        instructor_rating: feedbackForm.instructor_rating,
        session_quality: feedbackForm.session_quality,
        would_recommend: feedbackForm.would_recommend,
        comment: feedbackForm.comment,
        is_anonymous: false
      };
      
      if (editingFeedback) {
        await apiService.updateFeedback(editingFeedback.id, feedbackData);
        setSuccess('Feedback updated successfully!');
        setEditingFeedback(null);
      } else {
        await apiService.submitFeedback(feedbackData);
        setSuccess('Feedback submitted successfully!');
        setSelectedBooking(null);
      }
      setFeedbackForm({
        rating: 5,
        instructor_rating: 5,
        session_quality: 5,
        would_recommend: true,
        comment: ''
      });
      
      loadData(); // Refresh data
      
    } catch (err) {
      console.error('Feedback operation failed:', err);
      setError(`Failed to ${editingFeedback ? 'update' : 'submit'} feedback: ${err.message}`);
    } finally {
      setSubmitting(null);
    }
  };

  const handleEditFeedback = (feedbackItem) => {
    setEditingFeedback(feedbackItem);
    setFeedbackForm({
      rating: feedbackItem.rating || 5,
      instructor_rating: feedbackItem.instructor_rating || 5,
      session_quality: feedbackItem.session_quality || 5,
      would_recommend: feedbackItem.would_recommend !== null ? feedbackItem.would_recommend : true,
      comment: feedbackItem.comment || ''
    });
  };

  const completedBookingsWithoutFeedback = Array.isArray(bookings) ? bookings.filter(booking => {
    // Backend validation requirements alignment
    const hasConfirmedStatus = booking.status === 'CONFIRMED' || booking.status === 'confirmed';
    const hasAttended = booking.attended === true;
    const isPastSession = booking.session && new Date(booking.session.date_start) < new Date();
    const noExistingFeedback = !feedback.some(f => f.session_id === booking.session?.id);
    
    // Match backend validation requirements exactly
    return hasConfirmedStatus && hasAttended && isPastSession && noExistingFeedback;
  }) : [];


  const getEmojisForRating = (name, value) => {
    const emojiSets = {
      rating: ['😱', '😔', '😐', '😊', '🤩'], // Overall rating
      instructor_rating: ['👨‍💀', '😑', '👨‍🏫', '👨‍✨', '🧙‍♂️'], // Instructor rating  
      session_quality: ['💩', '📉', '📊', '📈', '💎'] // Session quality
    };
    return emojiSets[name] || ['⭐', '⭐', '⭐', '⭐', '⭐'];
  };

  const renderEmojiRating = (value, onChange, name) => (
    <div className="emoji-rating">
      {[1, 2, 3, 4, 5].map(rating => {
        const emojis = getEmojisForRating(name, rating);
        const emoji = emojis[rating - 1];
        return (
          <button
            key={rating}
            type="button"
            className={`emoji-star ${rating <= value ? 'filled' : ''}`}
            onClick={() => onChange({...feedbackForm, [name]: rating})}
            data-rating={rating}
          >
            <span className="emoji-icon">{emoji}</span>
          </button>
        );
      })}
      <div className="rating-text">
        <span className="rating-emoji">{getEmojisForRating(name)[value - 1]}</span>
        <span className="rating-value">({value}/5)</span>
      </div>
    </div>
  );

  if (loading) {
    return <div className="page-loading">Loading feedback...</div>;
  }

  return (
    <div className="feedback-page">
      {/* Navigation */}
      <div className="page-header">
        <div>
          <Link to="/student/dashboard" className="back-link">← Dashboard</Link>
          <h1>Session Feedback</h1>
        </div>
        <button onClick={() => logout()} className="logout-btn">Logout</button>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      <div className="feedback-content">
        {/* Pending Feedback Section */}
        <div className="feedback-section">
          <h2>Sessions Awaiting Feedback</h2>
          {completedBookingsWithoutFeedback.length === 0 ? (
            <div className="empty-state">
              <p>No sessions awaiting feedback</p>
              <Link to="/student/sessions" className="cta-button">Book More Sessions</Link>
            </div>
          ) : (
            <div className="pending-feedback-list">
              {completedBookingsWithoutFeedback.map(booking => (
                <div key={booking.id} className="feedback-item">
                  <div className="session-info">
                    <h3>{booking.session?.title || `Session ${booking.session?.id}`}</h3>
                    <p>📅 {new Date(booking.session?.date_start).toLocaleDateString()}</p>
                    <p>📍 {booking.session?.location}</p>
                  </div>
                  <button
                    onClick={() => setSelectedBooking(booking)}
                    className="feedback-btn"
                  >
                    <span className="btn-emoji">✨</span>
                    <span>Give Feedback</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Feedback Form Modal */}
        {(selectedBooking || editingFeedback) && (
          <div className="feedback-modal">
            <div className="modal-content">
              <div className="modal-header">
                <h3>{editingFeedback ? 'Edit' : 'Feedback for'} {editingFeedback?.session?.title || selectedBooking?.session?.title}</h3>
                <button 
                  onClick={() => {
                    setSelectedBooking(null);
                    setEditingFeedback(null);
                  }}
                  className="close-btn"
                >
                  ✕
                </button>
              </div>
              
              <form onSubmit={handleSubmitFeedback} className="feedback-form">
                <div className="form-group">
                  <label>🎯 Overall Rating</label>
                  <p className="rating-description">How was your overall experience?</p>
                  {renderEmojiRating(feedbackForm.rating, setFeedbackForm, 'rating')}
                </div>
                
                <div className="form-group">
                  <label>👨‍🏫 Instructor Rating</label>
                  <p className="rating-description">How would you rate the instructor?</p>
                  {renderEmojiRating(feedbackForm.instructor_rating, setFeedbackForm, 'instructor_rating')}
                </div>
                
                <div className="form-group">
                  <label>⚽ Session Quality</label>
                  <p className="rating-description">How was the session quality?</p>
                  {renderEmojiRating(feedbackForm.session_quality, setFeedbackForm, 'session_quality')}
                </div>
                
                <div className="form-group">
                  <label>💫 Would you recommend this session?</label>
                  <p className="rating-description">Help other students discover great sessions!</p>
                  <div className="recommendation-buttons">
                    <button
                      type="button"
                      className={`recommendation-btn ${feedbackForm.would_recommend === true ? 'active positive' : ''}`}
                      onClick={() => setFeedbackForm({...feedbackForm, would_recommend: true})}
                    >
                      <span className="rec-emoji">🚀</span>
                      <span className="rec-text">Absolutely!</span>
                      <span className="rec-subtitle">I'd recommend it</span>
                    </button>
                    <button
                      type="button"
                      className={`recommendation-btn ${feedbackForm.would_recommend === false ? 'active negative' : ''}`}
                      onClick={() => setFeedbackForm({...feedbackForm, would_recommend: false})}
                    >
                      <span className="rec-emoji">🤔</span>
                      <span className="rec-text">Not really</span>
                      <span className="rec-subtitle">Needs improvement</span>
                    </button>
                  </div>
                </div>
                
                <div className="form-group">
                  <label>💭 Additional Comments</label>
                  <p className="rating-description">Share your thoughts and suggestions!</p>
                  <textarea
                    value={feedbackForm.comment}
                    onChange={(e) => setFeedbackForm({...feedbackForm, comment: e.target.value})}
                    className="form-textarea"
                    rows="4"
                    placeholder="✍️ Share your experience, tips, or suggestions..."
                  />
                </div>
                
                <div className="form-actions">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedBooking(null);
                      setEditingFeedback(null);
                    }}
                    className="cancel-btn"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting === (editingFeedback?.id || selectedBooking?.id)}
                    className="submit-btn"
                  >
                    {submitting === (editingFeedback?.id || selectedBooking?.id) ? 
                      <><span className="btn-emoji spin">⏳</span>{editingFeedback ? 'Updating...' : 'Submitting...'}</> : 
                      <><span className="btn-emoji">{editingFeedback ? '🔄' : '🚀'}</span>{editingFeedback ? 'Update Feedback' : 'Submit Feedback'}</>
                    }
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Previous Feedback */}
        <div className="feedback-section">
          <h2>My Previous Feedback</h2>
          {!Array.isArray(feedback) || feedback.length === 0 ? (
            <div className="empty-state">
              <p>No feedback submitted yet</p>
            </div>
          ) : (
            <div className="feedback-history">
              {Array.isArray(feedback) && feedback.map(item => (
                <div key={item.id} className="feedback-history-item">
                  <div className="feedback-header">
                    <h4>{item.session?.title || `Session ${item.session?.id}`}</h4>
                    <div className="feedback-actions">
                      <div className="feedback-rating">
                        <span className="rating-emoji-display">{getEmojisForRating('rating')[item.rating - 1]}</span>
                        <span>{item.rating}/5</span>
                      </div>
                      <button
                        onClick={() => handleEditFeedback(item)}
                        className="edit-feedback-btn"
                        title="Edit this feedback"
                      >
                        <span className="edit-emoji">🖋️</span>
                        <span>Edit</span>
                      </button>
                    </div>
                  </div>
                  <div className="feedback-ratings">
                    <div className="rating-item overall">
                      <span className="rating-emoji">{getEmojisForRating('rating')[item.rating - 1]}</span>
                      <span>Overall: {item.rating}/5</span>
                    </div>
                    {item.instructor_rating && (
                      <div className="rating-item instructor">
                        <span className="rating-emoji">{getEmojisForRating('instructor_rating')[item.instructor_rating - 1]}</span>
                        <span>Instructor: {item.instructor_rating}/5</span>
                      </div>
                    )}
                    {item.session_quality && (
                      <div className="rating-item quality">
                        <span className="rating-emoji">{getEmojisForRating('session_quality')[item.session_quality - 1]}</span>
                        <span>Quality: {item.session_quality}/5</span>
                      </div>
                    )}
                    {item.would_recommend !== null && (
                      <div className="rating-item recommendation">
                        <span className="rating-emoji">{item.would_recommend ? '🚀' : '🤔'}</span>
                        <span>Recommends: {item.would_recommend ? 'Yes' : 'No'}</span>
                      </div>
                    )}
                  </div>
                  <p className="feedback-date">
                    📅 {new Date(item.created_at).toLocaleDateString()}
                  </p>
                  {item.comment && (
                    <p className="feedback-comment">"{item.comment}"</p>
                  )}
                  <div className="feedback-details">
                    <span>Submitted: {new Date(item.created_at).toLocaleDateString()}</span>
                    {item.updated_at && item.updated_at !== item.created_at && (
                      <span>Updated: {new Date(item.updated_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FeedbackPage;