import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './InstructorProfile.css';

const InstructorProfile = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    bio: '',
    specialization: '',
    experience_years: '',
    certifications: '',
    phone: '',
    office_hours: ''
  });
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [profileImageFile, setProfileImageFile] = useState(null);
  const [profileImagePreview, setProfileImagePreview] = useState(null);
  const [stats, setStats] = useState({
    totalSessions: 0,
    totalStudents: 0,
    averageRating: 0,
    yearsExperience: 0
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const response = await apiService.getCurrentUser();
      
      setProfile(response);
      setFormData({
        name: response.name || '',
        email: response.email || '',
        bio: response.bio || '',
        specialization: response.specialization || '',
        experience_years: response.experience_years || '',
        certifications: response.certifications || '',
        phone: response.phone || '',
        office_hours: response.office_hours || ''
      });

      // Load instructor stats
      await loadInstructorStats();
      
    } catch (err) {
      console.error('Failed to load profile:', err);
      setError('Failed to load profile: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const loadInstructorStats = async () => {
    try {
      // Load sessions and calculate stats
      const sessionsResponse = await apiService.getInstructorSessions();
      const sessions = Array.isArray(sessionsResponse) ? sessionsResponse : (sessionsResponse?.sessions || []);
      
      // Load students
      const studentsResponse = await apiService.getInstructorStudents();
      const students = Array.isArray(studentsResponse) ? studentsResponse : (studentsResponse?.students || []);

      // Load feedback to calculate average rating
      const feedbackResponse = await apiService.getInstructorFeedback();
      const feedback = Array.isArray(feedbackResponse) ? feedbackResponse : (feedbackResponse?.feedback || []);

      const newStats = {
        totalSessions: sessions.length,
        totalStudents: students.length,
        averageRating: 0,
        yearsExperience: profile?.experience_years || 0
      };

      // Calculate average rating
      if (feedback.length > 0) {
        const totalRating = feedback.reduce((sum, fb) => sum + (fb.rating || 0), 0);
        newStats.averageRating = Math.round((totalRating / feedback.length) * 10) / 10;
      }

      setStats(newStats);
    } catch (error) {
      console.error('Failed to load instructor stats:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleProfileImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setProfileImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfileImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      setSuccess('');
      
      // Upload profile image if selected
      if (profileImageFile) {
        await apiService.uploadProfilePicture(profileImageFile);
      }
      
      await apiService.updateProfile(formData);
      
      setSuccess('Profile updated successfully!');
      setIsEditing(false);
      setProfileImageFile(null);
      setProfileImagePreview(null);
      loadProfile(); // Reload profile data
    } catch (err) {
      console.error('Failed to update profile:', err);
      setError('Failed to update profile: ' + (err.message || 'Unknown error'));
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      setSuccess('');
      
      if (passwordData.newPassword !== passwordData.confirmPassword) {
        setError('New passwords do not match');
        return;
      }

      if (passwordData.newPassword.length < 6) {
        setError('New password must be at least 6 characters long');
        return;
      }

      await apiService.changePassword({
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      });
      
      setSuccess('Password changed successfully!');
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
      setShowPasswordChange(false);
    } catch (err) {
      console.error('Failed to change password:', err);
      setError('Failed to change password: ' + (err.message || 'Unknown error'));
    }
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setFormData({
      name: profile?.name || '',
      email: profile?.email || '',
      bio: profile?.bio || '',
      specialization: profile?.specialization || '',
      experience_years: profile?.experience_years || '',
      certifications: profile?.certifications || '',
      phone: profile?.phone || '',
      office_hours: profile?.office_hours || ''
    });
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

  if (loading) {
    return (
      <div className="instructor-profile">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-profile">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>👤 My Profile</h1>
          <p>Manage your instructor profile and account settings</p>
        </div>
        <div className="header-actions">
          {!isEditing ? (
            <button onClick={() => setIsEditing(true)} className="btn-primary">
              ✏️ Edit Profile
            </button>
          ) : (
            <div className="edit-actions">
              <button onClick={cancelEdit} className="btn-secondary">
                Cancel
              </button>
              <button form="profile-form" type="submit" className="btn-primary">
                💾 Save Changes
              </button>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {success && (
        <div className="success-banner">✅ {success}</div>
      )}

      <div className="profile-content">
        {/* Profile Stats */}
        <div className="stats-section">
          <h2>Profile Statistics</h2>
          <div className="stats-row">
            <div className="stat-item">
              <span className="stat-number">{stats.totalSessions}</span>
              <span className="stat-label">Total Sessions</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{stats.totalStudents}</span>
              <span className="stat-label">Students Taught</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">
                {stats.averageRating > 0 ? stats.averageRating.toFixed(1) : 'N/A'}
              </span>
              <span className="stat-label">Average Rating</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{stats.yearsExperience}</span>
              <span className="stat-label">Years Experience</span>
            </div>
          </div>
        </div>

        <div className="profile-main">
          {/* Profile Information */}
          <div className="profile-info-section">
            <div className="section-header">
              <h2>Profile Information</h2>
              {stats.averageRating > 0 && (
                <div className="rating-display">
                  <span className="rating-stars">{getRatingStars(stats.averageRating)}</span>
                  <span className="rating-text">({stats.averageRating}/5)</span>
                </div>
              )}
            </div>

            <form id="profile-form" onSubmit={handleSubmit}>
              {/* Profile Picture Section */}
              {isEditing && (
                <div className="profile-picture-section">
                  <h3>Profile Picture</h3>
                  <div className="profile-picture-container">
                    <div className="current-picture">
                      <img 
                        src={profileImagePreview || profile?.avatar_url || '/default-avatar.png'} 
                        alt="Profile"
                        className="profile-avatar"
                      />
                    </div>
                    <div className="picture-upload">
                      <input
                        type="file"
                        id="profile-image"
                        accept="image/jpeg,image/png,image/gif"
                        onChange={handleProfileImageChange}
                        className="file-input"
                      />
                      <label htmlFor="profile-image" className="upload-btn">
                        📷 Choose New Picture
                      </label>
                      <p className="file-hint">JPG, PNG or GIF (max 5MB)</p>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="name">Full Name *</label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email">Email Address *</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="phone">Phone Number</label>
                  <input
                    type="tel"
                    id="phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="specialization">Specialization</label>
                  <input
                    type="text"
                    id="specialization"
                    name="specialization"
                    value={formData.specialization}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    placeholder="e.g., Football, Basketball, Swimming"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="experience_years">Years of Experience</label>
                  <input
                    type="number"
                    id="experience_years"
                    name="experience_years"
                    value={formData.experience_years}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    min="0"
                    max="50"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="office_hours">Office Hours</label>
                  <input
                    type="text"
                    id="office_hours"
                    name="office_hours"
                    value={formData.office_hours}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    placeholder="e.g., Mon-Fri 9AM-5PM"
                  />
                </div>

                <div className="form-group full-width">
                  <label htmlFor="bio">Bio</label>
                  <textarea
                    id="bio"
                    name="bio"
                    value={formData.bio}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    rows="4"
                    placeholder="Tell students about yourself, your background, and teaching philosophy..."
                  />
                </div>

                <div className="form-group full-width">
                  <label htmlFor="certifications">Certifications</label>
                  <textarea
                    id="certifications"
                    name="certifications"
                    value={formData.certifications}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    rows="3"
                    placeholder="List your professional certifications, licenses, and qualifications..."
                  />
                </div>
              </div>
            </form>
          </div>

          {/* Account Security */}
          <div className="security-section">
            <div className="section-header">
              <h2>Account Security</h2>
              <button 
                onClick={() => setShowPasswordChange(!showPasswordChange)}
                className="btn-secondary"
              >
                🔒 Change Password
              </button>
            </div>

            {showPasswordChange && (
              <form onSubmit={handlePasswordSubmit} className="password-form">
                <div className="form-group">
                  <label htmlFor="currentPassword">Current Password</label>
                  <input
                    type="password"
                    id="currentPassword"
                    name="currentPassword"
                    value={passwordData.currentPassword}
                    onChange={handlePasswordChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="newPassword">New Password</label>
                  <input
                    type="password"
                    id="newPassword"
                    name="newPassword"
                    value={passwordData.newPassword}
                    onChange={handlePasswordChange}
                    required
                    minLength="6"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="confirmPassword">Confirm New Password</label>
                  <input
                    type="password"
                    id="confirmPassword"
                    name="confirmPassword"
                    value={passwordData.confirmPassword}
                    onChange={handlePasswordChange}
                    required
                    minLength="6"
                  />
                </div>

                <div className="password-actions">
                  <button 
                    type="button" 
                    onClick={() => setShowPasswordChange(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary">
                    Update Password
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <div className="action-card">
            <div className="action-icon">📊</div>
            <h3>Performance Dashboard</h3>
            <p>View detailed analytics and performance metrics</p>
            <button className="action-btn" onClick={() => navigate('/instructor/dashboard')}>
              View Dashboard
            </button>
          </div>
          <div className="action-card">
            <div className="action-icon">📧</div>
            <h3>Communication Settings</h3>
            <p>Manage notification preferences and communication</p>
            <button className="action-btn">
              Configure Settings
            </button>
          </div>
          <div className="action-card">
            <div className="action-icon">📄</div>
            <h3>Export Profile</h3>
            <p>Download your profile data and teaching history</p>
            <button className="action-btn">
              Export Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InstructorProfile;