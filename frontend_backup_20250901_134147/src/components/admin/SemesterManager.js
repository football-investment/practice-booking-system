import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './SemesterManager.css';

function SemesterManager() {
  const { user } = useAuth();
  const [semesters, setSemesters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingSemester, setEditingSemester] = useState(null);

  const [formData, setFormData] = useState({
    code: '',
    name: '',
    start_date: '',
    end_date: '',
    is_active: true
  });

  // Permissions check
  const canManageSemesters = user?.role === 'admin';

  useEffect(() => {
    if (canManageSemesters) {
      loadSemesters();
    }
  }, [canManageSemesters]);

  const loadSemesters = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getSemesters();

      // FIXED: Proper response handling
      if (data && typeof data === 'object' && data.semesters) {
        // Backend returns {semesters: [], total: x} format
        setSemesters(Array.isArray(data.semesters) ? data.semesters : []);
      } else if (Array.isArray(data)) {
        // Fallback: Direct array response
        setSemesters(data);
      } else {
        setSemesters([]);
      }
    } catch (error) {
      console.error('Failed to load semesters:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to load semesters: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      code: '',
      name: '',
      start_date: '',
      end_date: '',
      is_active: true
    });
    setShowCreateForm(false);
    setEditingSemester(null);
  };

  const generateUniqueCode = () => {
    const now = new Date();
    const year = now.getFullYear();
    const semester = now.getMonth() < 6 ? 1 : 2; // 1: Spring, 2: Fall
    const timestamp = now.getTime().toString().slice(-4);
    return `${year}/${semester}-${timestamp}`;
  };

  const showSuccess = (message) => {
    // You can implement toast notifications or temporary success state
    console.log('Success:', message);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    if (!formData.code || !formData.name || !formData.start_date || !formData.end_date) {
      setError('All fields are required');
      return;
    }

    if (new Date(formData.start_date) >= new Date(formData.end_date)) {
      setError('End date must be after start date');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      if (editingSemester) {
        await apiService.updateSemester(editingSemester.id, formData);
        showSuccess('Semester updated successfully');
      } else {
        await apiService.createSemester(formData);
        showSuccess('Semester created successfully');
      }
      
      await loadSemesters();
      resetForm();
    } catch (error) {
      console.error('Failed to save semester:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to save semester: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (semester) => {
    setFormData({
      code: semester.code,
      name: semester.name,
      start_date: semester.start_date.split('T')[0], // Format for date input
      end_date: semester.end_date.split('T')[0],
      is_active: semester.is_active
    });
    setEditingSemester(semester);
    setShowCreateForm(true);
  };

  const handleDelete = async (semesterId) => {
    if (!window.confirm('Are you sure you want to delete this semester?')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiService.deleteSemester(semesterId);
      showSuccess('Semester deleted successfully');
      await loadSemesters();
    } catch (error) {
      console.error('Failed to delete semester:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to delete semester: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const toggleActive = async (semester) => {
    try {
      setLoading(true);
      setError(null);
      await apiService.updateSemester(semester.id, {
        ...semester,
        is_active: !semester.is_active
      });
      await loadSemesters();
    } catch (error) {
      console.error('Failed to update semester:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to update semester: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!canManageSemesters) {
    return (
      <div className="semester-manager">
        <div className="access-denied">
          <h2>Access Denied</h2>
          <p>You do not have permission to manage semesters.</p>
        </div>
      </div>
    );
  }

  if (loading && semesters.length === 0) {
    return (
      <div className="semester-manager">
        <div className="loading">Loading semesters...</div>
      </div>
    );
  }

  return (
    <div className="semester-manager">
      <div className="semester-header">
        <h2>Semester Management</h2>
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn btn-primary"
          disabled={loading}
        >
          + Create Semester
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="error-close">×</button>
        </div>
      )}

      {showCreateForm && (
        <div className="semester-form">
          <h3>{editingSemester ? 'Edit Semester' : 'Create New Semester'}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="code">Semester Code:</label>
              <input
                type="text"
                id="code"
                value={formData.code}
                onChange={(e) => setFormData(prev => ({...prev, code: e.target.value}))}
                placeholder="e.g., 2024/1 or click Generate"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setFormData(prev => ({...prev, code: generateUniqueCode()}))}
                className="btn btn-secondary btn-small"
                style={{ marginTop: '8px' }}
                disabled={loading}
              >
                Generate Unique Code
              </button>
            </div>

            <div className="form-group">
              <label htmlFor="name">Semester Name:</label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({...prev, name: e.target.value}))}
                placeholder="e.g., Spring 2024"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="start_date">Start Date:</label>
              <input
                type="date"
                id="start_date"
                value={formData.start_date}
                onChange={(e) => setFormData(prev => ({...prev, start_date: e.target.value}))}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="end_date">End Date:</label>
              <input
                type="date"
                id="end_date"
                value={formData.end_date}
                onChange={(e) => setFormData(prev => ({...prev, end_date: e.target.value}))}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData(prev => ({...prev, is_active: e.target.checked}))}
                  disabled={loading}
                />
                Active Semester
              </label>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Saving...' : (editingSemester ? 'Update' : 'Create')}
              </button>
              <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="semester-list">
        <h3>Existing Semesters</h3>
        {semesters.length === 0 ? (
          <p className="no-data">No semesters found. Create your first semester above.</p>
        ) : (
          <div className="semester-table">
            <div className="semester-row semester-header-row">
              <div className="semester-cell">Code</div>
              <div className="semester-cell">Name</div>
              <div className="semester-cell">Period</div>
              <div className="semester-cell">Status</div>
              <div className="semester-cell">Stats</div>
              <div className="semester-cell">Actions</div>
            </div>
            {semesters.map(semester => (
              <div key={semester.id} className="semester-row">
                <div className="semester-cell">
                  <strong>{semester.code}</strong>
                </div>
                <div className="semester-cell">
                  {semester.name}
                </div>
                <div className="semester-cell">
                  {new Date(semester.start_date).toLocaleDateString('hu-HU')} - {new Date(semester.end_date).toLocaleDateString('hu-HU')}
                </div>
                <div className="semester-cell">
                  <span className={`status ${semester.is_active ? 'active' : 'inactive'}`}>
                    {semester.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="semester-cell">
                  <small>
                    {semester.total_groups || 0} groups, {semester.total_sessions || 0} sessions
                  </small>
                </div>
                <div className="semester-cell actions">
                  <button 
                    onClick={() => handleEdit(semester)}
                    className="btn btn-small btn-primary"
                    disabled={loading}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => toggleActive(semester)}
                    className="btn btn-small btn-warning"
                    disabled={loading}
                  >
                    {semester.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  <button 
                    onClick={() => handleDelete(semester.id)}
                    className="btn btn-small btn-danger"
                    disabled={loading}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default SemesterManager;