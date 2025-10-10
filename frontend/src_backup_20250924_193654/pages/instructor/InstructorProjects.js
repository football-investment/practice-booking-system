import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import InstructorProjectCard from '../../components/instructor/InstructorProjectCard';
import ProjectModal from '../../components/instructor/ProjectModal';
import QuizConfigModal from '../../components/instructor/QuizConfigModal';
import './InstructorProjects.css';

const InstructorProjects = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState([]);
  const [filteredProjects, setFilteredProjects] = useState([]);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    status: 'all', // all, active, completed, planning
    search: '',
    semester: 'all'
  });
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    completed: 0,
    planning: 0,
    totalStudents: 0
  });
  const [showModal, setShowModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [isModalLoading, setIsModalLoading] = useState(false);
  const [showQuizModal, setShowQuizModal] = useState(false);
  const [quizConfigProject, setQuizConfigProject] = useState(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [projects, filters]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await apiService.getInstructorProjects();
      const projectsData = Array.isArray(response) ? response : (response?.projects || []);
      
      setProjects(projectsData);
      calculateStats(projectsData);
      
      console.log('Instructor projects loaded:', projectsData.length);
    } catch (err) {
      console.error('Failed to load projects:', err);
      setError('Failed to load projects: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (projectsData) => {
    const stats = {
      total: projectsData.length,
      active: 0,
      completed: 0,
      planning: 0,
      totalStudents: 0
    };

    projectsData.forEach(project => {
      // Count by status
      switch (project.status) {
        case 'active':
          stats.active++;
          break;
        case 'completed':
          stats.completed++;
          break;
        case 'planning':
          stats.planning++;
          break;
      }
      
      // Sum enrolled students
      stats.totalStudents += project.enrolled_count || 0;
    });

    setStats(stats);
  };

  const applyFilters = () => {
    let filtered = [...projects];

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(project => project.status === filters.status);
    }

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(project =>
        project.title.toLowerCase().includes(filters.search.toLowerCase()) ||
        project.description?.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Semester filter
    if (filters.semester !== 'all') {
      filtered = filtered.filter(project => project.semester_id.toString() === filters.semester);
    }

    setFilteredProjects(filtered);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const getProjectStatusInfo = (status) => {
    switch (status) {
      case 'active':
        return { label: 'Active', class: 'active', icon: '🚀' };
      case 'completed':
        return { label: 'Completed', class: 'completed', icon: '✅' };
      case 'planning':
        return { label: 'Planning', class: 'planning', icon: '📋' };
      default:
        return { label: 'Unknown', class: 'unknown', icon: '❓' };
    }
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return '#10b981'; // green
    if (percentage >= 60) return '#f59e0b'; // amber
    if (percentage >= 40) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const getSemesters = () => {
    const semesters = [...new Set(projects.map(p => p.semester_id).filter(Boolean))];
    return semesters.sort((a, b) => b - a); // Latest first
  };

  // CRUD Operations
  const handleCreateProject = () => {
    setSelectedProject(null);
    setShowModal(true);
  };

  const handleEditProject = (project) => {
    setSelectedProject(project);
    setShowModal(true);
  };

  const handleDeleteProject = async (projectId) => {
    if (!window.confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      return;
    }

    try {
      await apiService.deleteProject(projectId);
      await loadProjects(); // Refresh the list
      console.log('Project deleted successfully');
    } catch (err) {
      console.error('Failed to delete project:', err);
      alert('Failed to delete project: ' + (err.message || 'Unknown error'));
    }
  };

  const handleSaveProject = async (projectData) => {
    try {
      setIsModalLoading(true);
      
      if (selectedProject) {
        // Update existing project
        await apiService.updateProject(selectedProject.id, projectData);
        console.log('Project updated successfully');
      } else {
        // Create new project
        await apiService.createProject(projectData);
        console.log('Project created successfully');
      }
      
      setShowModal(false);
      setSelectedProject(null);
      await loadProjects(); // Refresh the list
      
    } catch (err) {
      console.error('Failed to save project:', err);
      alert('Failed to save project: ' + (err.message || 'Unknown error'));
    } finally {
      setIsModalLoading(false);
    }
  };

  const handleCloseModal = () => {
    if (!isModalLoading) {
      setShowModal(false);
      setSelectedProject(null);
    }
  };

  const handleViewDetails = (project) => {
    navigate(`/instructor/projects/${project.id}`);
  };

  const handleManageStudents = (project) => {
    navigate(`/instructor/projects/${project.id}/students`);
  };

  const handleConfigureQuizzes = (project) => {
    setQuizConfigProject(project);
    setShowQuizModal(true);
  };

  const handleCloseQuizModal = () => {
    setShowQuizModal(false);
    setQuizConfigProject(null);
  };

  const handleSaveQuizConfig = () => {
    // Quiz configuration changes are handled in the modal itself
    // No additional action needed here
  };

  if (loading) {
    return (
      <div className="instructor-projects">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading your projects...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-projects">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>📁 My Projects</h1>
          <p>Manage and track your student projects</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-item">
          <span className="stat-number">{stats.total}</span>
          <span className="stat-label">Total Projects</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.active}</span>
          <span className="stat-label">Active</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.completed}</span>
          <span className="stat-label">Completed</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.totalStudents}</span>
          <span className="stat-label">Total Students</span>
        </div>
      </div>

      {/* Actions & Filters */}
      <div className="filters-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Search projects..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filter-controls">
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="planning">Planning</option>
            <option value="completed">Completed</option>
          </select>

          <select
            value={filters.semester}
            onChange={(e) => handleFilterChange('semester', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Semesters</option>
            {getSemesters().map(semesterId => (
              <option key={semesterId} value={semesterId}>Semester {semesterId}</option>
            ))}
          </select>

          <button 
            onClick={handleCreateProject}
            className="create-project-btn"
          >
            ➕ New Project
          </button>
        </div>
      </div>

      {/* Projects List */}
      <div className="projects-section">
        <div className="section-header">
          <h2>Projects</h2>
          <span className="results-count">{filteredProjects.length} projects</span>
        </div>

        {filteredProjects.length === 0 ? (
          <div className="empty-state">
            {filters.search || filters.status !== 'all' || filters.semester !== 'all' ? (
              <p>🔍 No projects match your filters.</p>
            ) : (
              <p>📁 No projects found.</p>
            )}
          </div>
        ) : (
          <div className="projects-grid">
            {filteredProjects.map(project => (
              <InstructorProjectCard
                key={project.id}
                project={project}
                onViewDetails={handleViewDetails}
                onEdit={handleEditProject}
                onDelete={handleDeleteProject}
                onManageStudents={handleManageStudents}
                onConfigureQuizzes={handleConfigureQuizzes}
              />
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <div className="action-card">
            <div className="action-icon">📊</div>
            <h3>Project Analytics</h3>
            <p>View overall project performance and statistics</p>
            <Link to="/instructor/analytics" className="action-btn">View Analytics</Link>
          </div>
          <div className="action-card">
            <div className="action-icon">📋</div>
            <h3>Create Project</h3>
            <p>Set up a new project for your students</p>
            <button className="action-btn" onClick={handleCreateProject}>Create Project</button>
          </div>
          <div className="action-card">
            <div className="action-icon">📈</div>
            <h3>Progress Report</h3>
            <p>Generate progress reports for all projects</p>
            <Link to="/instructor/reports" className="action-btn">Generate Report</Link>
          </div>
        </div>
      </div>

      {/* Project Modal */}
      <ProjectModal
        isOpen={showModal}
        onClose={handleCloseModal}
        onSave={handleSaveProject}
        project={selectedProject}
        isLoading={isModalLoading}
      />

      {/* Quiz Config Modal */}
      <QuizConfigModal
        isOpen={showQuizModal}
        onClose={handleCloseQuizModal}
        project={quizConfigProject}
        onSave={handleSaveQuizConfig}
      />
    </div>
  );
};

export default InstructorProjects;