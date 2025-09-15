import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const SemesterManagement = () => {
  const { logout } = useAuth();
  const [semesters, setSemesters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSemester, setEditingSemester] = useState(null);
  const [deletingSemester, setDeletingSemester] = useState(null);
  const [semesterForm, setSemesterForm] = useState({
    code: '',
    name: '',
    start_date: '',
    end_date: '',
    is_active: true,
    description: ''
  });

  useEffect(() => {
    loadSemesters();
  }, []);

  const loadSemesters = async () => {
    setLoading(true);
    try {
      const response = await apiService.getSemesters();
      console.log('Raw semesters API response:', response);
      
      // Extract semesters array from API response object
      const semestersData = response?.semesters || response || [];
      
      setSemesters(semestersData);
      console.log('Semesters loaded:', semestersData.length, 'Total:', response?.total || 0);
    } catch (err) {
      console.error('Failed to load semesters:', err);
      setError('Failed to load semesters: ' + (err.message || 'Unknown error'));
      setSemesters([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSemester = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    // Enhanced validation
    const validationErrors = [];
    
    if (!semesterForm.code?.trim()) {
      validationErrors.push('Semester code is required');
    }
    
    if (!semesterForm.name?.trim()) {
      validationErrors.push('Semester name is required');
    }
    
    if (!semesterForm.start_date) {
      validationErrors.push('Start date is required');
    }
    
    if (!semesterForm.end_date) {
      validationErrors.push('End date is required');
    }
    
    if (semesterForm.start_date && semesterForm.end_date) {
      if (new Date(semesterForm.start_date) >= new Date(semesterForm.end_date)) {
        validationErrors.push('End date must be after start date');
      }
    }
    
    if (validationErrors.length > 0) {
      setError('Validation failed: ' + validationErrors.join(', '));
      return;
    }
    
    try {
      console.log('Semester creation payload:', semesterForm);
      
      const payload = {
        code: semesterForm.code.trim().toUpperCase(),
        name: semesterForm.name.trim(),
        start_date: semesterForm.start_date,
        end_date: semesterForm.end_date,
        is_active: semesterForm.is_active,
        description: semesterForm.description?.trim() || ''
      };
      
      console.log('Calling createSemester API with payload:', payload);
      const result = await apiService.createSemester(payload);
      console.log('Semester creation result:', result);
      
      setSuccess('Semester created successfully!');
      setShowCreateModal(false);
      resetForm();
      loadSemesters();
    } catch (err) {
      console.error('Semester creation failed:', err);
      setError('Semester creation failed: ' + (err.message || 'Unknown error'));
    }
  };

  const handleUpdateSemester = async (e) => {
    e.preventDefault();
    if (!editingSemester) return;
    
    setError('');
    setSuccess('');
    
    if (new Date(semesterForm.start_date) >= new Date(semesterForm.end_date)) {
      setError('End date must be after start date');
      return;
    }
    
    try {
      await apiService.updateSemester(editingSemester.id, semesterForm);
      setSuccess('Semester updated successfully!');
      setEditingSemester(null);
      resetForm();
      loadSemesters();
    } catch (err) {
      console.error('Semester update failed:', err);
      setError(`Failed to update semester: ${err.message}`);
    }
  };

  const handleDeleteSemester = async (semesterId) => {
    if (!window.confirm('Are you sure you want to delete this semester? This action cannot be undone.')) {
      return;
    }
    
    setDeletingSemester(semesterId);
    try {
      await apiService.deleteSemester(semesterId);
      setSuccess('Semester deleted successfully');
      loadSemesters();
    } catch (err) {
      console.error('Semester deletion failed:', err);
      setError(`Failed to delete semester: ${err.message}`);
    } finally {
      setDeletingSemester(null);
    }
  };

  const resetForm = () => {
    setSemesterForm({
      code: '',
      name: '',
      start_date: '',
      end_date: '',
      is_active: true,
      description: ''
    });
  };

  const openEditModal = (semester) => {
    setEditingSemester(semester);
    setSemesterForm({
      code: semester.code || '',
      name: semester.name || '',
      start_date: semester.start_date ? new Date(semester.start_date).toISOString().slice(0, 10) : '',
      end_date: semester.end_date ? new Date(semester.end_date).toISOString().slice(0, 10) : '',
      is_active: semester.is_active !== false,
      description: semester.description || ''
    });
  };

  const closeModal = () => {
    setShowCreateModal(false);
    setEditingSemester(null);
    resetForm();
    setError('');
  };

  const isCurrentSemester = (semester) => {
    const now = new Date();
    const start = new Date(semester.start_date);
    const end = new Date(semester.end_date);
    return start <= now && now <= end;
  };

  return (
    <div className="semester-management">
      {/* Navigation */}
      <div className="admin-page-header">
        <div>
          <Link to="/admin/dashboard" className="back-link">← Admin Dashboard</Link>
          <h1>Semester Management</h1>
        </div>
        <div className="header-actions">
          <button 
            onClick={() => setShowCreateModal(true)}
            className="create-btn primary"
          >
            ➕ Create Semester
          </button>
          <button onClick={() => logout()} className="logout-btn">Logout</button>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Semester Stats */}
      <div className="semester-stats">
        <div className="stat-card">
          <h3>Total Semesters</h3>
          <div className="stat-number">{semesters.length}</div>
        </div>
        <div className="stat-card">
          <h3>Active Semesters</h3>
          <div className="stat-number">{semesters.filter(s => s.is_active).length}</div>
        </div>
        <div className="stat-card">
          <h3>Current Semester</h3>
          <div className="stat-number">{semesters.filter(s => isCurrentSemester(s)).length}</div>
        </div>
      </div>

      {/* Semesters List */}
      <div className="semesters-container">
        {loading ? (
          <div className="loading-state">Loading semesters...</div>
        ) : semesters.length === 0 ? (
          <div className="empty-state">
            <h3>No semesters found</h3>
            <p>Create your first academic semester to get started</p>
            <button onClick={() => setShowCreateModal(true)} className="cta-button">
              Create Semester
            </button>
          </div>
        ) : (
          <div className="semesters-grid">
            {semesters.map(semester => (
              <div key={semester.id} className={`semester-card ${isCurrentSemester(semester) ? 'current' : ''}`}>
                <div className="semester-header">
                  <h3>{semester.name}</h3>
                  <div className="semester-badges">
                    {isCurrentSemester(semester) && (
                      <span className="badge current">CURRENT</span>
                    )}
                    <span className={`badge ${semester.is_active ? 'active' : 'inactive'}`}>
                      {semester.is_active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </div>
                </div>

                <div className="semester-details">
                  <p className="semester-dates">
                    📅 {new Date(semester.start_date).toLocaleDateString()} - 
                    {new Date(semester.end_date).toLocaleDateString()}
                  </p>
                  <p className="semester-duration">
                    📊 {Math.ceil((new Date(semester.end_date) - new Date(semester.start_date)) / (1000 * 60 * 60 * 24))} days
                  </p>
                  {semester.description && (
                    <p className="semester-description">{semester.description}</p>
                  )}
                </div>

                <div className="semester-actions">
                  <button
                    onClick={() => openEditModal(semester)}
                    className="edit-btn"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={() => handleDeleteSemester(semester.id)}
                    disabled={deletingSemester === semester.id}
                    className="delete-btn"
                  >
                    {deletingSemester === semester.id ? '⏳' : '🗑️'} Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingSemester) && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingSemester ? 'Edit Semester' : 'Create New Semester'}</h3>
              <button onClick={closeModal} className="close-btn">✕</button>
            </div>
            
            <form onSubmit={editingSemester ? handleUpdateSemester : handleCreateSemester}>
              <div className="form-group">
                <label>Semester Code *</label>
                <input
                  type="text"
                  value={semesterForm.code}
                  onChange={(e) => setSemesterForm({...semesterForm, code: e.target.value})}
                  className="form-input"
                  placeholder="e.g. FALL2025, SPRING2026"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Semester Name *</label>
                <input
                  type="text"
                  value={semesterForm.name}
                  onChange={(e) => setSemesterForm({...semesterForm, name: e.target.value})}
                  className="form-input"
                  placeholder="e.g. Fall 2024, Spring 2025"
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Start Date *</label>
                  <input
                    type="date"
                    value={semesterForm.start_date}
                    onChange={(e) => setSemesterForm({...semesterForm, start_date: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>End Date *</label>
                  <input
                    type="date"
                    value={semesterForm.end_date}
                    onChange={(e) => setSemesterForm({...semesterForm, end_date: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={semesterForm.description}
                  onChange={(e) => setSemesterForm({...semesterForm, description: e.target.value})}
                  className="form-textarea"
                  rows="3"
                  placeholder="Optional description for this semester"
                />
              </div>

              <div className="form-group checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={semesterForm.is_active}
                    onChange={(e) => setSemesterForm({...semesterForm, is_active: e.target.checked})}
                  />
                  Active Semester
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" onClick={closeModal} className="cancel-btn">
                  Cancel
                </button>
                <button type="submit" className="save-btn">
                  {editingSemester ? 'Update Semester' : 'Create Semester'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default SemesterManagement;