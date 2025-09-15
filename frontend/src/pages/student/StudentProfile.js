import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { apiService } from '../../services/apiService';
import './StudentProfile.css';

const StudentProfile = () => {
  const { user, logout, updateUser } = useAuth();
  const { theme, colorScheme, setTheme, setColorScheme } = useTheme();
  const [profile, setProfile] = useState({
    email: '',
    full_name: '',
    phone: '',
    student_id: '',
    year_of_study: '',
    major: ''
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [bookings, setBookings] = useState([]);

  useEffect(() => {
    if (user) {
      loadProfile();
    }
  }, [user]);


  const loadProfile = async () => {
    setLoading(true);
    try {
      const [profileResponse, bookingsResponse] = await Promise.all([
        apiService.getCurrentUser().catch(() => ({})),
        apiService.getMyBookings().catch(() => [])
      ]);
      
      setProfile({
        email: profileResponse.email || user?.email || '',
        full_name: profileResponse.full_name || user?.full_name || '',
        phone: profileResponse.phone || user?.phone || '',
        student_id: profileResponse.student_id || user?.student_id || '',
        year_of_study: profileResponse.year_of_study || user?.year_of_study || '',
        major: profileResponse.major || user?.major || ''
      });
      
      // Extract bookings array from API response object
      const bookingsData = bookingsResponse?.bookings || bookingsResponse?.data || bookingsResponse || [];
      setBookings(bookingsData);
      
    } catch (err) {
      console.error('Failed to load profile:', err);
      setError('Failed to load profile data');
      setProfile(prev => ({
        ...prev,
        email: user?.email || '',
        full_name: user?.full_name || user?.name || '',
        phone: user?.phone || '',
        student_id: user?.student_id || '',
        year_of_study: user?.year_of_study || '',
        major: user?.major || ''
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    
    try {
      await apiService.updateProfile(profile);
      setSuccess('Profile updated successfully!');
      
      // Update AuthContext with new profile data
      // Also update the 'name' field for consistency with header display
      updateUser({
        ...profile,
        name: profile.full_name
      });
      
    } catch (err) {
      console.error('Profile update failed:', err);
      setError(`Failed to update profile: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setChangingPassword(true);
    setError('');
    setSuccess('');
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setError('New passwords do not match');
      setChangingPassword(false);
      return;
    }
    
    if (passwordForm.new_password.length < 6) {
      setError('New password must be at least 6 characters');
      setChangingPassword(false);
      return;
    }
    
    try {
      await apiService.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password
      });
      
      setSuccess('Password changed successfully!');
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
      
    } catch (err) {
      console.error('Password change failed:', err);
      setError(`Failed to change password: ${err.message}`);
    } finally {
      setChangingPassword(false);
    }
  };


  if (loading) {
    return <div className="page-loading">Loading profile...</div>;
  }

  return (
    <div className="student-profile">
      {/* Navigation */}
      <div className="page-header">
        <div>
          <Link to="/student/dashboard" className="back-link">← Dashboard</Link>
          <h1>My Profile</h1>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      <div className="profile-content">
        {/* Profile Information */}
        <div className="profile-section">
          <h2>Personal Information</h2>
          <form onSubmit={handleProfileSubmit} className="profile-form">
            <div className="form-row">
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({...profile, email: e.target.value})}
                  className="form-input"
                  required
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={profile.full_name}
                  onChange={(e) => setProfile({...profile, full_name: e.target.value})}
                  className="form-input"
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Phone Number</label>
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile({...profile, phone: e.target.value})}
                  className="form-input"
                />
              </div>
              <div className="form-group">
                <label>Student ID</label>
                <input
                  type="text"
                  value={profile.student_id}
                  onChange={(e) => setProfile({...profile, student_id: e.target.value})}
                  className="form-input"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Year of Study</label>
                <select
                  value={profile.year_of_study}
                  onChange={(e) => setProfile({...profile, year_of_study: e.target.value})}
                  className="form-select"
                >
                  <option value="">Select Year</option>
                  <option value="1">1st Year</option>
                  <option value="2">2nd Year</option>
                  <option value="3">3rd Year</option>
                  <option value="4">4th Year</option>
                  <option value="graduate">Graduate</option>
                </select>
              </div>
              <div className="form-group">
                <label>Major</label>
                <input
                  type="text"
                  value={profile.major}
                  onChange={(e) => setProfile({...profile, major: e.target.value})}
                  className="form-input"
                  placeholder="e.g. Computer Science"
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={saving}
              className="save-btn"
            >
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </form>
        </div>

        {/* Password Change */}
        <div className="profile-section">
          <h2>Change Password</h2>
          <form onSubmit={handlePasswordSubmit} className="password-form">
            <div className="form-group">
              <label>Current Password</label>
              <input
                type="password"
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm({...passwordForm, current_password: e.target.value})}
                className="form-input"
                required
              />
            </div>
            <div className="form-group">
              <label>New Password</label>
              <input
                type="password"
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm({...passwordForm, new_password: e.target.value})}
                className="form-input"
                required
                minLength="6"
              />
            </div>
            <div className="form-group">
              <label>Confirm New Password</label>
              <input
                type="password"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm({...passwordForm, confirm_password: e.target.value})}
                className="form-input"
                required
                minLength="6"
              />
            </div>
            <button 
              type="submit" 
              disabled={changingPassword}
              className="change-password-btn"
            >
              {changingPassword ? 'Changing...' : 'Change Password'}
            </button>
          </form>
        </div>

        {/* Theme Preferences */}
        <div className="profile-section">
          <h2>🎨 Theme Preferences</h2>
          <div className="theme-preferences">
            <div className="preference-group">
              <h3>🌈 Color Scheme</h3>
              <p className="preference-description">Choose your favorite color theme</p>
              <div className="color-scheme-grid">
                <button 
                  className={`color-scheme-card ${colorScheme === 'purple' ? 'active' : ''}`}
                  onClick={() => setColorScheme('purple')}
                >
                  <div className="color-preview purple">💜</div>
                  <span>Purple</span>
                </button>
                <button 
                  className={`color-scheme-card ${colorScheme === 'blue' ? 'active' : ''}`}
                  onClick={() => setColorScheme('blue')}
                >
                  <div className="color-preview blue">💙</div>
                  <span>Blue</span>
                </button>
                <button 
                  className={`color-scheme-card ${colorScheme === 'green' ? 'active' : ''}`}
                  onClick={() => setColorScheme('green')}
                >
                  <div className="color-preview green">💚</div>
                  <span>Green</span>
                </button>
                <button 
                  className={`color-scheme-card ${colorScheme === 'red' ? 'active' : ''}`}
                  onClick={() => setColorScheme('red')}
                >
                  <div className="color-preview red">❤️</div>
                  <span>Red</span>
                </button>
                <button 
                  className={`color-scheme-card ${colorScheme === 'orange' ? 'active' : ''}`}
                  onClick={() => setColorScheme('orange')}
                >
                  <div className="color-preview orange">🧡</div>
                  <span>Orange</span>
                </button>
              </div>
            </div>

            <div className="preference-group">
              <h3>🌙☀️ Theme Mode</h3>
              <p className="preference-description">Choose between light, dark, or auto mode</p>
              <div className="theme-mode-buttons">
                <button 
                  className={`theme-mode-btn ${theme === 'light' ? 'active' : ''}`}
                  onClick={() => setTheme('light')}
                >
                  <span className="theme-icon">☀️</span>
                  <div className="theme-info">
                    <span className="theme-name">Light Mode</span>
                    <span className="theme-desc">Always use light theme</span>
                  </div>
                </button>
                <button 
                  className={`theme-mode-btn ${theme === 'dark' ? 'active' : ''}`}
                  onClick={() => setTheme('dark')}
                >
                  <span className="theme-icon">🌙</span>
                  <div className="theme-info">
                    <span className="theme-name">Dark Mode</span>
                    <span className="theme-desc">Always use dark theme</span>
                  </div>
                </button>
                <button 
                  className={`theme-mode-btn ${theme === 'auto' ? 'active' : ''}`}
                  onClick={() => setTheme('auto')}
                >
                  <span className="theme-icon">🌗</span>
                  <div className="theme-info">
                    <span className="theme-name">Auto Mode</span>
                    <span className="theme-desc">Follow system preference</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Account Statistics */}
        <div className="profile-section">
          <h2>📊 Account Statistics</h2>
          <div className="stats-overview">
            <div className="stat-item">
              <span className="stat-label">Total Bookings:</span>
              <span className="stat-value">{bookings.length}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Sessions Attended:</span>
              <span className="stat-value">{bookings.filter(b => b.attended).length}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Attendance Rate:</span>
              <span className="stat-value">
                {bookings.length > 0 ? 
                  Math.round((bookings.filter(b => b.attended).length / bookings.length) * 100) + '%' : 
                  'N/A'
                }
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentProfile;