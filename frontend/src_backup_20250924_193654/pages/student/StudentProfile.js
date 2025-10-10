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
    name: '',
    phone: '',
    emergency_contact: '',
    emergency_phone: '',
    position: '',
    specialization: '',
    date_of_birth: ''
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
        name: profileResponse.name || user?.name || '',
        phone: profileResponse.phone || user?.phone || '',
        emergency_contact: profileResponse.emergency_contact || user?.emergency_contact || '',
        emergency_phone: profileResponse.emergency_phone || user?.emergency_phone || '',
        position: profileResponse.position || user?.position || '',
        specialization: profileResponse.specialization || user?.specialization || '',
        date_of_birth: profileResponse.date_of_birth ? profileResponse.date_of_birth.split('T')[0] : ''
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
        name: user?.name || '',
        phone: user?.phone || '',
        emergency_contact: user?.emergency_contact || '',
        emergency_phone: user?.emergency_phone || '',
        position: user?.position || '',
        specialization: user?.specialization || ''
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
      updateUser({
        ...profile
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
        {/* Main Profile Card */}
        <div className="profile-section main-profile">
          <h2>👤 Personal Information</h2>
          <form onSubmit={handleProfileSubmit} className="profile-form">
            <div className="form-row">
              <div className="form-group">
                <label>📧 Email Address</label>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({...profile, email: e.target.value})}
                  className="form-input"
                  required
                />
              </div>
              <div className="form-group">
                <label>👤 Full Name</label>
                <input
                  type="text"
                  value={profile.name}
                  onChange={(e) => setProfile({...profile, name: e.target.value})}
                  className="form-input"
                  required
                  placeholder="e.g. Cristiano Ronaldo"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>📱 Phone Number</label>
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile({...profile, phone: e.target.value})}
                  className="form-input"
                  placeholder="+36 30 123 4567"
                />
              </div>
              <div className="form-group">
                <label>⚽ Playing Position</label>
                <select
                  value={profile.position}
                  onChange={(e) => setProfile({...profile, position: e.target.value})}
                  className="form-select"
                >
                  <option value="">Select Position</option>
                  <option value="goalkeeper">🥅 Goalkeeper</option>
                  <option value="defender">🛡️ Defender</option>
                  <option value="midfielder">⚡ Midfielder</option>
                  <option value="forward">🔥 Forward</option>
                  <option value="coach">📋 Coach</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>🎯 Specialization</label>
                <select
                  value={profile.specialization}
                  onChange={(e) => setProfile({...profile, specialization: e.target.value})}
                  className="form-select"
                >
                  <option value="">Select Specialization</option>
                  <option value="player">⚽ Player Track</option>
                  <option value="coach">📋 Coach Track</option>
                  <option value="internship">🏢 Internship Track</option>
                </select>
              </div>
              <div className="form-group">
                <label>🆘 Emergency Contact Name</label>
                <input
                  type="text"
                  value={profile.emergency_contact}
                  onChange={(e) => setProfile({...profile, emergency_contact: e.target.value})}
                  className="form-input"
                  placeholder="e.g. Parent/Guardian Name"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>🎂 Date of Birth</label>
                <input
                  type="date"
                  value={profile.date_of_birth}
                  onChange={(e) => setProfile({...profile, date_of_birth: e.target.value})}
                  className="form-input"
                  max={new Date().toISOString().split('T')[0]}
                />
                <small className="form-help">
                  Required for age-based specialization access (Player: 5+, Coach: 14+, Internship: 18+)
                </small>
              </div>
              <div className="form-group">
                <label>📞 Emergency Phone Number</label>
                <input
                  type="tel"
                  value={profile.emergency_phone}
                  onChange={(e) => setProfile({...profile, emergency_phone: e.target.value})}
                  className="form-input"
                  placeholder="+36 30 987 6543"
                />
                <small className="form-help">
                  Contact for emergencies during training sessions
                </small>
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

        {/* Secondary Sections Row */}
        <div className="profile-row">
          {/* Password Change */}
          <div className="profile-section half-width">
            <h2>🔒 Change Password</h2>
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

          {/* Account Statistics */}
          <div className="profile-section half-width">
            <h2>📊 Account Statistics</h2>
            <div className="stats-overview compact">
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

      </div>
    </div>
  );
};

export default StudentProfile;