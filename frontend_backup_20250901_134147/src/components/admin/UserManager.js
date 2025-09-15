import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './UserManager.css';

function UserManager() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'student'
  });

  const canManageUsers = user?.role === 'admin';

  useEffect(() => {
    if (canManageUsers) {
      loadUsers();
    }
  }, [canManageUsers]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getUsers();
      
      if (data && typeof data === 'object' && data.users) {
        setUsers(Array.isArray(data.users) ? data.users : []);
      } else if (Array.isArray(data)) {
        setUsers(data);
      } else {
        setUsers([]);
      }
    } catch (error) {
      console.error('Failed to load users:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to load users: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      password: '',
      role: 'student'
    });
    setShowModal(false);
    setEditingUser(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name || !formData.email) {
      setError('Name and email are required');
      return;
    }

    if (!editingUser && !formData.password) {
      setError('Password is required for new users');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      if (editingUser) {
        await apiService.updateUser(editingUser.id, formData);
      } else {
        await apiService.createUser(formData);
      }
      
      await loadUsers();
      resetForm();
    } catch (error) {
      console.error('Failed to save user:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to save user: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (userToEdit) => {
    setFormData({
      name: userToEdit.name,
      email: userToEdit.email,
      password: '',
      role: userToEdit.role
    });
    setEditingUser(userToEdit);
    setShowModal(true);
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiService.deleteUser(userId);
      await loadUsers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to delete user: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (userId) => {
    if (!window.confirm('Are you sure you want to reset this user\'s password?')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiService.resetUserPassword(userId);
      alert('Password reset successfully. User will receive email with new password.');
    } catch (error) {
      console.error('Failed to reset password:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to reset password: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Filter users based on search and role
  const filteredUsers = users.filter(user => {
    const matchesSearch = !searchTerm || 
      user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesRole = !roleFilter || user.role === roleFilter;
    
    return matchesSearch && matchesRole;
  });

  if (!canManageUsers) {
    return (
      <div className="user-manager">
        <div className="access-denied">
          <h2>Access Denied</h2>
          <p>You do not have permission to manage users.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="user-manager">
      <div className="user-header">
        <h2>User Management</h2>
        <button
          onClick={() => setShowModal(true)}
          className="btn btn-primary"
          disabled={loading}
        >
          + Create User
        </button>
      </div>

      <div className="user-filters">
        <div className="filter-group">
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="role-filter"
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="instructor">Instructor</option>
            <option value="student">Student</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="error-close">×</button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="user-modal">
            <div className="modal-header">
              <h3>{editingUser ? 'Edit User' : 'Create New User'}</h3>
              <button onClick={resetForm} className="modal-close">×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="user-form">
              <div className="form-group">
                <label htmlFor="name">Full Name:</label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({...prev, name: e.target.value}))}
                  disabled={loading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="email">Email:</label>
                <input
                  type="email"
                  id="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({...prev, email: e.target.value}))}
                  disabled={loading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">
                  Password {editingUser ? '(leave empty to keep current)' : ''}:
                </label>
                <input
                  type="password"
                  id="password"
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({...prev, password: e.target.value}))}
                  disabled={loading}
                  required={!editingUser}
                />
              </div>

              <div className="form-group">
                <label htmlFor="role">Role:</label>
                <select
                  id="role"
                  value={formData.role}
                  onChange={(e) => setFormData(prev => ({...prev, role: e.target.value}))}
                  disabled={loading}
                >
                  <option value="student">Student</option>
                  <option value="instructor">Instructor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Saving...' : (editingUser ? 'Update' : 'Create')}
                </button>
                <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="user-list">
        <h3>Users ({filteredUsers.length})</h3>
        {filteredUsers.length === 0 ? (
          <p className="no-data">No users found.</p>
        ) : (
          <div className="user-table">
            <div className="user-row user-header-row">
              <div className="user-cell">Name</div>
              <div className="user-cell">Email</div>
              <div className="user-cell">Role</div>
              <div className="user-cell">Created</div>
              <div className="user-cell">Actions</div>
            </div>
            
            {filteredUsers.map(user => (
              <div key={user.id} className="user-row">
                <div className="user-cell">
                  <strong>{user.name}</strong>
                </div>
                <div className="user-cell">
                  {user.email}
                </div>
                <div className="user-cell">
                  <span className={`role-badge role-${user.role}`}>
                    {user.role}
                  </span>
                </div>
                <div className="user-cell">
                  {user.created_at ? new Date(user.created_at).toLocaleDateString('hu-HU') : 'N/A'}
                </div>
                <div className="user-cell actions">
                  <button 
                    onClick={() => handleEdit(user)}
                    className="btn btn-small btn-primary"
                    disabled={loading}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => handleResetPassword(user.id)}
                    className="btn btn-small btn-warning"
                    disabled={loading}
                  >
                    Reset Pass
                  </button>
                  <button 
                    onClick={() => handleDelete(user.id)}
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

export default UserManager;