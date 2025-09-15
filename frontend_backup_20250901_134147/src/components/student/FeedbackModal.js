import React, { useState } from 'react';
import { apiService } from '../../services/apiService';

const FeedbackModal = ({ onClose, sessions, onSubmit }) => {
  const [formData, setFormData] = useState({
    session_id: '',
    rating: 0,
    comment: '',
    is_anonymous: false
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRatingClick = (rating) => {
    setFormData({...formData, rating});
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.session_id || !formData.rating) {
      setError('Please select a session and rating!');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await apiService.createFeedback(formData);
      onSubmit('Feedback submitted successfully!');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to submit feedback');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay show" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3 className="modal-title">⭐ Give Feedback</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          {error && (
            <div className="error-message" style={{ position: 'relative', marginBottom: '20px' }}>{error}</div>
          )}
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Select Session</label>
              <select 
                className="form-select"
                value={formData.session_id}
                onChange={(e) => setFormData({...formData, session_id: e.target.value})}
                required
              >
                <option value="">Choose a completed session...</option>
                {sessions.map(session => (
                  <option key={session.id} value={session.id}>
                    {session.title} - {session.date_start ? new Date(session.date_start).toLocaleDateString() : 'TBD'}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Rating</label>
              <div className="rating-stars">
                {[1,2,3,4,5].map(star => (
                  <span 
                    key={star}
                    className="star"
                    onClick={() => handleRatingClick(star)}
                    style={{
                      color: formData.rating >= star ? '#fbbf24' : 'var(--gray-300)',
                    }}
                  >
                    ★
                  </span>
                ))}
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Comments</label>
              <textarea 
                className="form-textarea"
                placeholder="Share your thoughts about the session..."
                value={formData.comment}
                onChange={(e) => setFormData({...formData, comment: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input 
                  type="checkbox" 
                  checked={formData.is_anonymous}
                  onChange={(e) => setFormData({...formData, is_anonymous: e.target.checked})}
                />
                Submit anonymously
              </label>
            </div>
          </form>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? <span className="loading-spinner"></span> : 'Submit Feedback'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackModal;