import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const UserManagement = () => {
  const { logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [deletingUser, setDeletingUser] = useState(null);
  const [userForm, setUserForm] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'student',
    phone: '',
    student_id: '',
    is_active: true
  });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await apiService.getUsers();
      const usersData = Array.isArray(response.users) ? response.users : [];
      setUsers(usersData);
      console.log('Users loaded:', usersData.length);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError('Failed to load users');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    try {
      await apiService.createUser(userForm);
      setSuccess('User created successfully!');
      setShowCreateModal(false);
      resetForm();
      loadUsers();
    } catch (err) {
      console.error('User creation failed:', err);
      setError(`Failed to create user: ${err.message}`);
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    if (!editingUser) return;
    
    setError('');
    setSuccess('');
    
    try {
      const updateData = { ...userForm };
      if (!updateData.password) delete updateData.password; // Don't update password if empty
      
      await apiService.updateUser(editingUser.id, updateData);
      setSuccess('User updated successfully!');
      setEditingUser(null);
      resetForm();
      loadUsers();
    } catch (err) {
      console.error('User update failed:', err);
      setError(`Failed to update user: ${err.message}`);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return;
    }
    
    setDeletingUser(userId);
    try {
      await apiService.deleteUser(userId);
      setSuccess('User deleted successfully');
      loadUsers();
    } catch (err) {
      console.error('User deletion failed:', err);
      setError(`Failed to delete user: ${err.message}`);
    } finally {
      setDeletingUser(null);
    }
  };

  const resetForm = () => {
    setUserForm({
      email: '',
      full_name: '',
      password: '',
      role: 'student',
      phone: '',
      student_id: '',
      is_active: true
    });
  };

  const openEditModal = (user) => {
    setEditingUser(user);
    setUserForm({
      email: user.email || '',
      full_name: user.full_name || '',
      password: '', // Don't pre-fill password
      role: user.role || 'student',
      phone: user.phone || '',
      student_id: user.student_id || '',
      is_active: user.is_active !== false
    });
  };

  const closeModal = () => {
    setShowCreateModal(false);
    setEditingUser(null);
    resetForm();
    setError('');
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = 
      user.email?.toLowerCase().includes(search.toLowerCase()) ||
      user.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      user.student_id?.toLowerCase().includes(search.toLowerCase());
    
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    
    return matchesSearch && matchesRole;
  });

  return (
    <div className="user-management">
      {/* Navigation */}
      <div className="admin-page-header">
        <div>
          <Link to="/admin/dashboard" className="back-link">← Admin Dashboard</Link>
          <h1>User Management</h1>
        </div>
        <div className="header-actions">
          <button 
            onClick={() => setShowCreateModal(true)}
            className="create-btn primary"
          >
            ➕ Create User
          </button>
          <button onClick={() => logout()} className="logout-btn">Logout</button>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Filters */}
      <div className="user-filters">
        <div className="search-section">
          <input
            type="text"
            placeholder="Search users by name, email, or student ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="filter-section">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="role-filter"
          >
            <option value="all">All Roles ({users.length})</option>
            <option value="student">Students ({users.filter(u => u.role === 'student').length})</option>
            <option value="admin">Admins ({users.filter(u => u.role === 'admin').length})</option>
            <option value="instructor">Instructors ({users.filter(u => u.role === 'instructor').length})</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="users-table-container">
        {loading ? (
          <div className="table-loading">Loading users...</div>
        ) : filteredUsers.length === 0 ? (
          <div className="table-empty">
            <h3>No users found</h3>
            <p>Try adjusting your search or filters</p>
          </div>
        ) : (
          <table className="users-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Student ID</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map(user => (
                <tr key={user.id}>
                  <td className="user-info">
                    <div className="user-avatar">
                      {user.role === 'admin' ? '👨‍💼' : 
                       user.role === 'instructor' ? '👨‍🏫' : '🎓'}
                    </div>
                    <div>
                      <div className="user-name">{user.full_name || user.email}</div>
                      <div className="user-email">{user.email}</div>
                    </div>
                  </td>
                  <td>
                    <span className={`role-badge ${user.role}`}>
                      {user.role?.charAt(0).toUpperCase() + user.role?.slice(1)}
                    </span>
                  </td>
                  <td>{user.student_id || '-'}</td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  <td className="table-actions">
                    <button
                      onClick={() => openEditModal(user)}
                      className="edit-btn"
                      title="Edit User"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => handleDeleteUser(user.id)}
                      disabled={deletingUser === user.id}
                      className="delete-btn"
                      title="Delete User"
                    >
                      {deletingUser === user.id ? '⏳' : '🗑️'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create/Edit User Modal */}
      {(showCreateModal || editingUser) && (
        <div className="modal-overlay">
          <div className="modal-content large">
            <div className="modal-header">
              <h3>{editingUser ? 'Edit User' : 'Create New User'}</h3>
              <button onClick={closeModal} className="close-btn">✕</button>
            </div>
            
            <form onSubmit={editingUser ? handleUpdateUser : handleCreateUser}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Email Address *</label>
                  <input
                    type="email"
                    value={userForm.email}
                    onChange={(e) => setUserForm({...userForm, email: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    value={userForm.full_name}
                    onChange={(e) => setUserForm({...userForm, full_name: e.target.value})}
                    className="form-input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Role *</label>
                  <select
                    value={userForm.role}
                    onChange={(e) => setUserForm({...userForm, role: e.target.value})}
                    className="form-select"
                    required
                  >
                    <option value="student">Student</option>
                    <option value="admin">Admin</option>
                    <option value="instructor">Instructor</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Password {editingUser ? '(leave blank to keep current)' : '*'}</label>
                  <input
                    type="password"
                    value={userForm.password}
                    onChange={(e) => setUserForm({...userForm, password: e.target.value})}
                    className="form-input"
                    required={!editingUser}
                    minLength="6"
                  />
                </div>

                <div className="form-group">
                  <label>Phone Number</label>
                  <input
                    type="tel"
                    value={userForm.phone}
                    onChange={(e) => setUserForm({...userForm, phone: e.target.value})}
                    className="form-input"
                  />
                </div>

                <div className="form-group">
                  <label>Student ID</label>
                  <input
                    type="text"
                    value={userForm.student_id}
                    onChange={(e) => setUserForm({...userForm, student_id: e.target.value})}
                    className="form-input"
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={userForm.is_active}
                      onChange={(e) => setUserForm({...userForm, is_active: e.target.checked})}
                    />
                    Active User
                  </label>
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" onClick={closeModal} className="cancel-btn">
                  Cancel
                </button>
                <button type="submit" className="save-btn">
                  {editingUser ? 'Update User' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;