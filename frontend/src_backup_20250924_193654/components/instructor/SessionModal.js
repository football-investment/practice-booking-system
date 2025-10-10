import React, { useState, useEffect } from 'react';
import './SessionModal.css';

const SessionModal = ({ 
  isOpen, 
  onClose, 
  onSave, 
  session = null,
  isLoading = false 
}) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    location: '',
    sport_type: 'Football',
    level: 'All Levels',
    capacity: 20,
    date_start: '',
    date_end: '',
    duration: 90
  });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (session) {
      // Edit mode - populate with existing data
      const startDate = new Date(session.date_start);
      const endDate = new Date(session.date_end);
      
      setFormData({
        title: session.title || '',
        description: session.description || '',
        location: session.location || '',
        sport_type: session.sport_type || 'Football',
        level: session.level || 'All Levels',
        capacity: session.capacity || 20,
        date_start: startDate.toISOString().slice(0, 16), // Format for datetime-local
        date_end: endDate.toISOString().slice(0, 16),
        duration: session.duration || 90
      });
    } else {
      // Create mode - reset form
      setFormData({
        title: '',
        description: '',
        location: '',
        sport_type: 'Football',
        level: 'All Levels',
        capacity: 20,
        date_start: '',
        date_end: '',
        duration: 90
      });
    }
    setErrors({});
  }, [session, isOpen]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }

    // Auto-calculate end time when start time or duration changes
    if (name === 'date_start' || name === 'duration') {
      const startTime = name === 'date_start' ? value : formData.date_start;
      const duration = name === 'duration' ? parseInt(value) : formData.duration;
      
      if (startTime && duration) {
        const start = new Date(startTime);
        const end = new Date(start.getTime() + duration * 60000);
        setFormData(prev => ({
          ...prev,
          date_end: end.toISOString().slice(0, 16)
        }));
      }
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    
    if (!formData.location.trim()) {
      newErrors.location = 'Location is required';
    }
    
    if (!formData.date_start) {
      newErrors.date_start = 'Start date and time is required';
    }
    
    if (!formData.date_end) {
      newErrors.date_end = 'End date and time is required';
    }
    
    if (formData.date_start && formData.date_end) {
      if (new Date(formData.date_start) >= new Date(formData.date_end)) {
        newErrors.date_end = 'End time must be after start time';
      }
    }
    
    if (formData.capacity < 1 || formData.capacity > 50) {
      newErrors.capacity = 'Capacity must be between 1 and 50';
    }
    
    if (formData.duration < 15 || formData.duration > 300) {
      newErrors.duration = 'Duration must be between 15 and 300 minutes';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    onSave({
      ...formData,
      capacity: parseInt(formData.capacity),
      duration: parseInt(formData.duration)
    });
  };

  const sportTypes = [
    'Football', 'Basketball', 'Tennis', 'Swimming', 
    'Running', 'Gym', 'Yoga', 'Boxing', 'General'
  ];

  const levels = [
    'All Levels', 'Beginner', 'Intermediate', 'Advanced', 'Expert'
  ];

  if (!isOpen) return null;

  return (
    <div className="session-modal-overlay" onClick={onClose}>
      <div className="session-modal" onClick={e => e.stopPropagation()}>
        <div className="session-modal-header">
          <h2>{session ? 'Edit Session' : 'Create New Session'}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit} className="session-modal-form">
          <div className="form-grid">
            <div className="form-group full-width">
              <label htmlFor="title">Session Title *</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                className={errors.title ? 'error' : ''}
                placeholder="e.g. Advanced Football Training"
              />
              {errors.title && <span className="error-text">{errors.title}</span>}
            </div>
            
            <div className="form-group full-width">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Session description and objectives..."
                rows="3"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="location">Location *</label>
              <input
                type="text"
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
                className={errors.location ? 'error' : ''}
                placeholder="e.g. Main Stadium, Gym A"
              />
              {errors.location && <span className="error-text">{errors.location}</span>}
            </div>
            
            <div className="form-group">
              <label htmlFor="sport_type">Sport Type</label>
              <select
                id="sport_type"
                name="sport_type"
                value={formData.sport_type}
                onChange={handleChange}
              >
                {sportTypes.map(sport => (
                  <option key={sport} value={sport}>{sport}</option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="level">Level</label>
              <select
                id="level"
                name="level"
                value={formData.level}
                onChange={handleChange}
              >
                {levels.map(level => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="capacity">Capacity *</label>
              <input
                type="number"
                id="capacity"
                name="capacity"
                value={formData.capacity}
                onChange={handleChange}
                min="1"
                max="50"
                className={errors.capacity ? 'error' : ''}
              />
              {errors.capacity && <span className="error-text">{errors.capacity}</span>}
            </div>
            
            <div className="form-group">
              <label htmlFor="date_start">Start Date & Time *</label>
              <input
                type="datetime-local"
                id="date_start"
                name="date_start"
                value={formData.date_start}
                onChange={handleChange}
                className={errors.date_start ? 'error' : ''}
              />
              {errors.date_start && <span className="error-text">{errors.date_start}</span>}
            </div>
            
            <div className="form-group">
              <label htmlFor="duration">Duration (minutes) *</label>
              <input
                type="number"
                id="duration"
                name="duration"
                value={formData.duration}
                onChange={handleChange}
                min="15"
                max="300"
                step="15"
                className={errors.duration ? 'error' : ''}
              />
              {errors.duration && <span className="error-text">{errors.duration}</span>}
            </div>
            
            <div className="form-group">
              <label htmlFor="date_end">End Date & Time (Auto)</label>
              <input
                type="datetime-local"
                id="date_end"
                name="date_end"
                value={formData.date_end}
                onChange={handleChange}
                className={errors.date_end ? 'error' : ''}
                readOnly
              />
              {errors.date_end && <span className="error-text">{errors.date_end}</span>}
            </div>
          </div>
          
          <div className="session-modal-actions">
            <button 
              type="button" 
              className="btn-cancel" 
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-save"
              disabled={isLoading}
            >
              {isLoading ? 'Saving...' : session ? 'Update Session' : 'Create Session'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SessionModal;