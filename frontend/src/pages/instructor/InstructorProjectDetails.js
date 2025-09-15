import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import ProjectModal from '../../components/instructor/ProjectModal';
import './InstructorProjectDetails.css';

const InstructorProjectDetails = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState(null);
  const [error, setError] = useState('');
  const [showEditModal, setShowEditModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'draft': return '📋';
      case 'active': return '🚀';
      case 'archived': return '📁';
      default: return '📁';
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'draft': return '#f59e0b';
      case 'active': return '#10b981';
      case 'archived': return '#6b7280';
      default: return '#6b7280';
    }
  };

  const loadProject = useCallback(async () => {
    try {
      setLoading(true);
      const projectData = await apiService.getProject(projectId);
      setProject(projectData);
      setError('');
    } catch (err) {
      console.error('Failed to load project:', err);
      setError(err.response?.data?.detail || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  const handleEdit = () => {
    setShowEditModal(true);
  };

  const handleSaveProject = async (projectData) => {
    try {
      await apiService.updateProject(projectId, projectData);
      await loadProject(); // Reload project data
      setShowEditModal(false);
      return true;
    } catch (err) {
      console.error('Failed to update project:', err);
      throw err;
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      return;
    }

    try {
      setIsDeleting(true);
      await apiService.deleteProject(projectId);
      navigate('/instructor/projects');
    } catch (err) {
      console.error('Failed to delete project:', err);
      alert('Failed to delete project. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="instructor-project-details">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading project details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="instructor-project-details">
        <div className="page-header">
          <div>
            <Link to="/instructor/projects" className="back-btn">
              ← Back to Projects
            </Link>
            <h1>📋 Project Details</h1>
          </div>
        </div>
        <div className="error-container">
          <div className="error-message">
            <h3>❌ Error Loading Project</h3>
            <p>{error}</p>
            <button className="btn-primary" onClick={loadProject}>
              🔄 Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="instructor-project-details">
        <div className="page-header">
          <div>
            <Link to="/instructor/projects" className="back-btn">
              ← Back to Projects
            </Link>
            <h1>📋 Project Details</h1>
          </div>
        </div>
        <div className="error-container">
          <div className="error-message">
            <h3>❌ Project Not Found</h3>
            <p>The requested project could not be found.</p>
            <Link to="/instructor/projects" className="btn-primary">
              ← Back to Projects
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-project-details">
      <div className="page-header">
        <div>
          <Link to="/instructor/projects" className="back-btn">
            ← Back to Projects
          </Link>
          <h1>📋 Project Details</h1>
          <p>Manage project: {project.title}</p>
        </div>
        <div className="header-actions">
          <button 
            className="btn-primary" 
            onClick={handleEdit}
          >
            ✏️ Edit Project
          </button>
          <Link 
            to={`/instructor/projects/${projectId}/students`}
            className="btn-secondary"
          >
            👥 Manage Students
          </Link>
          <button 
            className="btn-danger" 
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? '⏳ Deleting...' : '🗑️ Delete'}
          </button>
        </div>
      </div>

      <div className="project-content">
        {/* Project Overview */}
        <div className="project-overview-card">
          <div className="card-header">
            <h2>📊 Project Overview</h2>
            <div className="status-badge" style={{ backgroundColor: getStatusColor(project.status) }}>
              {getStatusIcon(project.status)} {project.status?.toUpperCase()}
            </div>
          </div>
          <div className="card-content">
            <div className="project-info-grid">
              <div className="info-item">
                <span className="label">Title:</span>
                <span className="value">{project.title}</span>
              </div>
              <div className="info-item">
                <span className="label">Description:</span>
                <span className="value">{project.description}</span>
              </div>
              <div className="info-item">
                <span className="label">Max Participants:</span>
                <span className="value">{project.max_participants}</span>
              </div>
              <div className="info-item">
                <span className="label">Enrolled Students:</span>
                <span className="value">{project.enrolled_count || 0}</span>
              </div>
              <div className="info-item">
                <span className="label">Available Spots:</span>
                <span className="value">{project.available_spots || (project.max_participants - (project.enrolled_count || 0))}</span>
              </div>
              <div className="info-item">
                <span className="label">Required Sessions:</span>
                <span className="value">{project.required_sessions}</span>
              </div>
              <div className="info-item">
                <span className="label">XP Reward:</span>
                <span className="value">{project.xp_reward} XP</span>
              </div>
              <div className="info-item">
                <span className="label">Deadline:</span>
                <span className="value">
                  {project.deadline ? new Date(project.deadline).toLocaleDateString() : 'No deadline set'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Project Statistics */}
        <div className="project-stats-grid">
          <div className="stat-card">
            <div className="stat-icon">👥</div>
            <div className="stat-content">
              <div className="stat-number">{project.enrolled_count || 0}</div>
              <div className="stat-label">Enrolled Students</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-content">
              <div className="stat-number">{project.completion_percentage || 0}%</div>
              <div className="stat-label">Completion Rate</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🎯</div>
            <div className="stat-content">
              <div className="stat-number">{project.required_sessions}</div>
              <div className="stat-label">Required Sessions</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">⭐</div>
            <div className="stat-content">
              <div className="stat-number">{project.xp_reward}</div>
              <div className="stat-label">XP Reward</div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="quick-actions-card">
          <div className="card-header">
            <h2>🚀 Quick Actions</h2>
          </div>
          <div className="card-content">
            <div className="action-buttons">
              <Link 
                to={`/instructor/projects/${projectId}/students`} 
                className="action-btn"
              >
                <div className="action-icon">👥</div>
                <div className="action-content">
                  <div className="action-title">Manage Students</div>
                  <div className="action-desc">View and manage enrolled students</div>
                </div>
              </Link>
              
              <button className="action-btn" onClick={handleEdit}>
                <div className="action-icon">✏️</div>
                <div className="action-content">
                  <div className="action-title">Edit Project</div>
                  <div className="action-desc">Update project details and settings</div>
                </div>
              </button>

              <Link 
                to={`/instructor/sessions?project=${projectId}`} 
                className="action-btn"
              >
                <div className="action-icon">📅</div>
                <div className="action-content">
                  <div className="action-title">View Sessions</div>
                  <div className="action-desc">Manage project-related sessions</div>
                </div>
              </Link>
            </div>
          </div>
        </div>

        {/* Project Milestones & Tracking */}
        <div className="project-milestones-card">
          <div className="card-header">
            <h2>🎯 Project Milestones & Progress Tracking</h2>
            <p>Track project progress through defined milestones</p>
          </div>
          <div className="card-content">
            {project.milestones && project.milestones.length > 0 ? (
              <div className="milestones-list">
                {project.milestones.map((milestone, index) => (
                  <div key={milestone.id} className="milestone-item">
                    <div className="milestone-header">
                      <div className="milestone-number">{index + 1}</div>
                      <div className="milestone-info">
                        <h3>{milestone.title}</h3>
                        <p>{milestone.description}</p>
                      </div>
                    </div>
                    <div className="milestone-details">
                      <div className="milestone-requirements">
                        <div className="requirement-item">
                          <span className="requirement-icon">📚</span>
                          <span className="requirement-text">
                            {milestone.required_sessions} sessions required
                          </span>
                        </div>
                        <div className="requirement-item">
                          <span className="requirement-icon">⭐</span>
                          <span className="requirement-text">
                            {milestone.xp_reward} XP reward
                          </span>
                        </div>
                        {milestone.deadline && (
                          <div className="requirement-item">
                            <span className="requirement-icon">📅</span>
                            <span className="requirement-text">
                              Due: {new Date(milestone.deadline).toLocaleDateString()}
                            </span>
                          </div>
                        )}
                        {milestone.is_required && (
                          <div className="requirement-item">
                            <span className="requirement-icon">⚠️</span>
                            <span className="requirement-text">Required</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-milestones">
                <div className="no-milestones-content">
                  <div className="no-milestones-icon">📋</div>
                  <h3>No Milestones Defined</h3>
                  <p>Add milestones to track student progress effectively</p>
                  <button 
                    className="btn-primary" 
                    onClick={handleEdit}
                  >
                    ➕ Add Milestones
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Session & Hours Tracking */}
        <div className="session-tracking-card">
          <div className="card-header">
            <h2>📊 Session & Hours Tracking</h2>
            <p>Track required sessions and time allocation for project completion</p>
          </div>
          <div className="card-content">
            <div className="tracking-info-grid">
              <div className="tracking-item">
                <div className="tracking-icon">📚</div>
                <div className="tracking-details">
                  <h4>Required Sessions</h4>
                  <div className="tracking-value">{project.required_sessions}</div>
                  <p>Total sessions needed to complete the project</p>
                </div>
              </div>
              
              <div className="tracking-item">
                <div className="tracking-icon">⏱️</div>
                <div className="tracking-details">
                  <h4>Estimated Hours</h4>
                  <div className="tracking-value">{project.required_sessions * 2}</div>
                  <p>Approximate time investment (2h per session)</p>
                </div>
              </div>

              <div className="tracking-item">
                <div className="tracking-icon">👥</div>
                <div className="tracking-details">
                  <h4>Active Students</h4>
                  <div className="tracking-value">{project.enrolled_count || 0}</div>
                  <p>Students currently working on this project</p>
                </div>
              </div>

              <div className="tracking-item">
                <div className="tracking-icon">🎯</div>
                <div className="tracking-details">
                  <h4>XP Reward</h4>
                  <div className="tracking-value">{project.xp_reward}</div>
                  <p>Experience points earned upon completion</p>
                </div>
              </div>
            </div>

            <div className="tracking-note">
              <h4>📝 Tracking Notes:</h4>
              <ul>
                <li><strong>Sessions are tracked individually</strong> - Each session completion is recorded</li>
                <li><strong>Hours are calculated automatically</strong> - Based on session attendance (approx. 2h per session)</li>
                <li><strong>Milestone progress is monitored</strong> - Students advance through defined milestones</li>
                <li><strong>Completion requires all milestones</strong> - All required milestones must be completed</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Project Modal */}
      {showEditModal && (
        <ProjectModal
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          onSave={handleSaveProject}
          project={project}
          isEditing={true}
        />
      )}
    </div>
  );
};

export default InstructorProjectDetails;