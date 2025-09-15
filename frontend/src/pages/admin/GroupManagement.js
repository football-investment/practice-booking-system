import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';

const GroupManagement = () => {
  const { logout } = useAuth();
  const [groups, setGroups] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [deletingGroup, setDeletingGroup] = useState(null);
  const [groupForm, setGroupForm] = useState({
    name: '',
    description: '',
    capacity: 20,
    is_active: true
  });

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      console.log('Loading group management data...');
      
      const [groupsResponse, usersResponse] = await Promise.all([
        apiService.getGroups().catch(() => ({})),
        apiService.getUsers().catch(() => ({}))
      ]);
      
      console.log('Groups API response:', groupsResponse);
      console.log('Users API response:', usersResponse);
      
      // Extract data arrays from API response objects
      const groupsData = groupsResponse?.groups || groupsResponse || [];
      const usersData = usersResponse?.users || usersResponse || [];
      
      setGroups(groupsData);
      setUsers(usersData);
      
      console.log('Group management data loaded:', {
        groups: groupsData.length,
        users: usersData.length
      });
      
    } catch (err) {
      console.error('Failed to load group data:', err);
      setError('Failed to load group data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    try {
      await apiService.createGroup(groupForm);
      setSuccess('Group created successfully!');
      setShowCreateModal(false);
      resetForm();
      loadAllData();
    } catch (err) {
      console.error('Group creation failed:', err);
      setError(`Failed to create group: ${err.message}`);
    }
  };

  const handleUpdateGroup = async (e) => {
    e.preventDefault();
    if (!editingGroup) return;
    
    setError('');
    setSuccess('');
    
    try {
      await apiService.updateGroup(editingGroup.id, groupForm);
      setSuccess('Group updated successfully!');
      setEditingGroup(null);
      resetForm();
      loadAllData();
    } catch (err) {
      console.error('Group update failed:', err);
      setError(`Failed to update group: ${err.message}`);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (!window.confirm('Are you sure you want to delete this group?')) {
      return;
    }
    
    setDeletingGroup(groupId);
    try {
      await apiService.deleteGroup(groupId);
      setSuccess('Group deleted successfully');
      loadAllData();
    } catch (err) {
      console.error('Group deletion failed:', err);
      setError(`Failed to delete group: ${err.message}`);
    } finally {
      setDeletingGroup(null);
    }
  };

  const resetForm = () => {
    setGroupForm({
      name: '',
      description: '',
      capacity: 20,
      is_active: true
    });
  };

  const openEditModal = (group) => {
    setEditingGroup(group);
    setGroupForm({
      name: group.name || '',
      description: group.description || '',
      capacity: group.capacity || 20,
      is_active: group.is_active !== false
    });
  };

  const closeModal = () => {
    setShowCreateModal(false);
    setEditingGroup(null);
    resetForm();
    setError('');
  };

  return (
    <div className="group-management">
      {/* Navigation */}
      <div className="admin-page-header">
        <div>
          <Link to="/admin/dashboard" className="back-link">← Admin Dashboard</Link>
          <h1>Group Management</h1>
        </div>
        <div className="header-actions">
          <button 
            onClick={() => setShowCreateModal(true)}
            className="create-btn primary"
          >
            ➕ Create Group
          </button>
          <button onClick={() => logout()} className="logout-btn">Logout</button>
        </div>
      </div>

      {/* Notifications */}
      {error && <div className="error-banner">⚠️ {error}</div>}
      {success && <div className="success-banner">✅ {success}</div>}

      {/* Groups Overview */}
      <div className="groups-container">
        {loading ? (
          <div className="loading-state">Loading groups...</div>
        ) : groups.length === 0 ? (
          <div className="empty-state">
            <h3>No groups found</h3>
            <p>Create your first group to organize students</p>
            <button onClick={() => setShowCreateModal(true)} className="cta-button">
              Create Group
            </button>
          </div>
        ) : (
          <div className="groups-grid">
            {groups.map(group => (
              <div key={group.id} className="group-card">
                <div className="group-header">
                  <h3>{group.name}</h3>
                  <div className="group-badges">
                    <span className={`badge ${group.is_active ? 'active' : 'inactive'}`}>
                      {group.is_active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </div>
                </div>

                <div className="group-details">
                  <p className="group-capacity">
                    👥 {group.member_count || 0}/{group.capacity} members
                  </p>
                  {group.description && (
                    <p className="group-description">{group.description}</p>
                  )}
                  <p className="group-created">
                    📅 Created: {new Date(group.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="group-actions">
                  <button
                    onClick={() => openEditModal(group)}
                    className="edit-btn"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={() => handleDeleteGroup(group.id)}
                    disabled={deletingGroup === group.id}
                    className="delete-btn"
                  >
                    {deletingGroup === group.id ? '⏳' : '🗑️'} Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingGroup) && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingGroup ? 'Edit Group' : 'Create New Group'}</h3>
              <button onClick={closeModal} className="close-btn">✕</button>
            </div>
            
            <form onSubmit={editingGroup ? handleUpdateGroup : handleCreateGroup}>
              <div className="form-group">
                <label>Group Name *</label>
                <input
                  type="text"
                  value={groupForm.name}
                  onChange={(e) => setGroupForm({...groupForm, name: e.target.value})}
                  className="form-input"
                  placeholder="e.g. Beginner Group A, Advanced Team"
                  required
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={groupForm.description}
                  onChange={(e) => setGroupForm({...groupForm, description: e.target.value})}
                  className="form-textarea"
                  rows="3"
                  placeholder="Describe this group's purpose or skill level"
                />
              </div>

              <div className="form-group">
                <label>Capacity *</label>
                <input
                  type="number"
                  value={groupForm.capacity}
                  onChange={(e) => setGroupForm({...groupForm, capacity: parseInt(e.target.value)})}
                  className="form-input"
                  min="1"
                  max="100"
                  required
                />
              </div>

              <div className="form-group checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={groupForm.is_active}
                    onChange={(e) => setGroupForm({...groupForm, is_active: e.target.checked})}
                  />
                  Active Group
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" onClick={closeModal} className="cancel-btn">
                  Cancel
                </button>
                <button type="submit" className="save-btn">
                  {editingGroup ? 'Update Group' : 'Create Group'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default GroupManagement;