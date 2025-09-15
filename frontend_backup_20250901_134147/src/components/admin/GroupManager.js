import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './GroupManager.css';

function GroupManager() {
  const { user } = useAuth();
  const [groups, setGroups] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showMembersModal, setShowMembersModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [semesterFilter, setSemesterFilter] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    semester_id: ''
  });

  const canManageGroups = user?.role === 'admin';

  useEffect(() => {
    if (canManageGroups) {
      loadInitialData();
    }
  }, [canManageGroups]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load semesters, groups, and users concurrently
      const [semestersData, groupsData, usersData] = await Promise.all([
        apiService.getSemesters(),
        apiService.getGroups(semesterFilter || null),
        apiService.getUsers()
      ]);

      // Handle semesters response
      if (semestersData && typeof semestersData === 'object' && semestersData.semesters) {
        setSemesters(Array.isArray(semestersData.semesters) ? semestersData.semesters : []);
      } else if (Array.isArray(semestersData)) {
        setSemesters(semestersData);
      }

      // Handle groups response
      if (groupsData && typeof groupsData === 'object' && groupsData.groups) {
        setGroups(Array.isArray(groupsData.groups) ? groupsData.groups : []);
      } else if (Array.isArray(groupsData)) {
        setGroups(groupsData);
      }

      // Handle users response
      if (usersData && typeof usersData === 'object' && usersData.users) {
        setUsers(Array.isArray(usersData.users) ? usersData.users : []);
      } else if (Array.isArray(usersData)) {
        setUsers(usersData);
      }

    } catch (error) {
      console.error('Failed to load data:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to load data: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getGroups(semesterFilter || null);
      
      if (data && typeof data === 'object' && data.groups) {
        setGroups(Array.isArray(data.groups) ? data.groups : []);
      } else if (Array.isArray(data)) {
        setGroups(data);
      } else {
        setGroups([]);
      }
    } catch (error) {
      console.error('Failed to load groups:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to load groups: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      semester_id: ''
    });
    setShowModal(false);
    setEditingGroup(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name || !formData.semester_id) {
      setError('Name and semester are required');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      if (editingGroup) {
        await apiService.updateGroup(editingGroup.id, formData);
      } else {
        await apiService.createGroup(formData);
      }
      
      await loadGroups();
      resetForm();
    } catch (error) {
      console.error('Failed to save group:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to save group: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (group) => {
    setFormData({
      name: group.name,
      description: group.description || '',
      semester_id: group.semester_id.toString()
    });
    setEditingGroup(group);
    setShowModal(true);
  };

  const handleDelete = async (groupId) => {
    if (!window.confirm('Are you sure you want to delete this group? This will remove all user assignments.')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiService.deleteGroup(groupId);
      await loadGroups();
    } catch (error) {
      console.error('Failed to delete group:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to delete group: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleManageMembers = async (group) => {
    try {
      setLoading(true);
      const groupDetails = await apiService.getGroupById(group.id);
      setSelectedGroup(groupDetails);
      setShowMembersModal(true);
    } catch (error) {
      console.error('Failed to load group members:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to load group members: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleAddUserToGroup = async (userId) => {
    if (!selectedGroup) return;

    try {
      setLoading(true);
      setError(null);
      await apiService.addUserToGroup(selectedGroup.id, userId);
      
      // Refresh group details
      const updatedGroup = await apiService.getGroupById(selectedGroup.id);
      setSelectedGroup(updatedGroup);
      await loadGroups();
    } catch (error) {
      console.error('Failed to add user to group:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to add user to group: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveUserFromGroup = async (userId) => {
    if (!selectedGroup) return;

    try {
      setLoading(true);
      setError(null);
      await apiService.removeUserFromGroup(selectedGroup.id, userId);
      
      // Refresh group details
      const updatedGroup = await apiService.getGroupById(selectedGroup.id);
      setSelectedGroup(updatedGroup);
      await loadGroups();
    } catch (error) {
      console.error('Failed to remove user from group:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message;
      setError('Failed to remove user from group: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Filter groups based on search and semester
  const filteredGroups = groups.filter(group => {
    const matchesSearch = !searchTerm || 
      group.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (group.description && group.description.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesSemester = !semesterFilter || group.semester_id.toString() === semesterFilter;
    
    return matchesSearch && matchesSemester;
  });

  // Get available users not in current group (for adding)
  const availableUsers = selectedGroup ? 
    users.filter(user => !selectedGroup.users?.some(groupUser => groupUser.id === user.id)) : 
    [];

  if (!canManageGroups) {
    return (
      <div className="group-manager">
        <div className="access-denied">
          <h2>Access Denied</h2>
          <p>You do not have permission to manage groups.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="group-manager">
      <div className="group-header">
        <h2>Group Management</h2>
        <button
          onClick={() => setShowModal(true)}
          className="btn btn-primary"
          disabled={loading}
        >
          + Create Group
        </button>
      </div>

      <div className="group-filters">
        <div className="filter-group">
          <input
            type="text"
            placeholder="Search groups..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <select
            value={semesterFilter}
            onChange={(e) => {
              setSemesterFilter(e.target.value);
              // Reload groups when semester filter changes
              if (e.target.value !== semesterFilter) {
                setTimeout(loadGroups, 100);
              }
            }}
            className="semester-filter"
          >
            <option value="">All Semesters</option>
            {semesters.map(semester => (
              <option key={semester.id} value={semester.id}>
                {semester.code} - {semester.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="error-close">×</button>
        </div>
      )}

      {/* Create/Edit Group Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="group-modal">
            <div className="modal-header">
              <h3>{editingGroup ? 'Edit Group' : 'Create New Group'}</h3>
              <button onClick={resetForm} className="modal-close">×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="group-form">
              <div className="form-group">
                <label htmlFor="name">Group Name:</label>
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
                <label htmlFor="description">Description:</label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({...prev, description: e.target.value}))}
                  disabled={loading}
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label htmlFor="semester">Semester:</label>
                <select
                  id="semester"
                  value={formData.semester_id}
                  onChange={(e) => setFormData(prev => ({...prev, semester_id: e.target.value}))}
                  disabled={loading}
                  required
                >
                  <option value="">Select Semester</option>
                  {semesters.map(semester => (
                    <option key={semester.id} value={semester.id}>
                      {semester.code} - {semester.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Saving...' : (editingGroup ? 'Update' : 'Create')}
                </button>
                <button type="button" onClick={resetForm} className="btn btn-secondary" disabled={loading}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Members Management Modal */}
      {showMembersModal && selectedGroup && (
        <div className="modal-overlay">
          <div className="members-modal">
            <div className="modal-header">
              <h3>Manage Members - {selectedGroup.name}</h3>
              <button onClick={() => setShowMembersModal(false)} className="modal-close">×</button>
            </div>
            
            <div className="members-content">
              <div className="current-members">
                <h4>Current Members ({selectedGroup.users?.length || 0})</h4>
                {selectedGroup.users && selectedGroup.users.length > 0 ? (
                  <div className="members-list">
                    {selectedGroup.users.map(user => (
                      <div key={user.id} className="member-item">
                        <div className="member-info">
                          <strong>{user.name}</strong>
                          <span className="member-email">{user.email}</span>
                          <span className={`role-badge role-${user.role}`}>{user.role}</span>
                        </div>
                        <button 
                          onClick={() => handleRemoveUserFromGroup(user.id)}
                          className="btn btn-small btn-danger"
                          disabled={loading}
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-members">No members in this group</p>
                )}
              </div>

              <div className="available-users">
                <h4>Add Members</h4>
                {availableUsers.length > 0 ? (
                  <div className="users-list">
                    {availableUsers.map(user => (
                      <div key={user.id} className="user-item">
                        <div className="user-info">
                          <strong>{user.name}</strong>
                          <span className="user-email">{user.email}</span>
                          <span className={`role-badge role-${user.role}`}>{user.role}</span>
                        </div>
                        <button 
                          onClick={() => handleAddUserToGroup(user.id)}
                          className="btn btn-small btn-primary"
                          disabled={loading}
                        >
                          Add
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-users">All users are already in this group</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="group-list">
        <h3>Groups ({filteredGroups.length})</h3>
        {filteredGroups.length === 0 ? (
          <p className="no-data">No groups found.</p>
        ) : (
          <div className="group-table">
            <div className="group-row group-header-row">
              <div className="group-cell">Name</div>
              <div className="group-cell">Semester</div>
              <div className="group-cell">Description</div>
              <div className="group-cell">Members</div>
              <div className="group-cell">Sessions</div>
              <div className="group-cell">Actions</div>
            </div>
            
            {filteredGroups.map(group => (
              <div key={group.id} className="group-row">
                <div className="group-cell">
                  <strong>{group.name}</strong>
                </div>
                <div className="group-cell">
                  {group.semester ? `${group.semester.code} - ${group.semester.name}` : 'N/A'}
                </div>
                <div className="group-cell">
                  <span className="group-description">
                    {group.description || 'No description'}
                  </span>
                </div>
                <div className="group-cell">
                  <span className="member-count">{group.user_count || 0} members</span>
                </div>
                <div className="group-cell">
                  <span className="session-count">{group.session_count || 0} sessions</span>
                </div>
                <div className="group-cell actions">
                  <button 
                    onClick={() => handleEdit(group)}
                    className="btn btn-small btn-primary"
                    disabled={loading}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => handleManageMembers(group)}
                    className="btn btn-small btn-secondary"
                    disabled={loading}
                  >
                    Members
                  </button>
                  <button 
                    onClick={() => handleDelete(group.id)}
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

export default GroupManager;