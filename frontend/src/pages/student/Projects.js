import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import ProjectCard from '../../components/student/ProjectCard';
import './Projects.css';

const Projects = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState([]);
  const [enrolledProjects, setEnrolledProjects] = useState(new Map());
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    available_only: false,
    search: ''
  });
  const [theme] = useState(() => 
    localStorage.getItem('theme') || 'auto'
  );
  const [colorScheme] = useState(() =>
    localStorage.getItem('colorScheme') || 'purple'
  );

  useEffect(() => {
    loadProjects();
    loadMyEnrollments();
  }, [filters.available_only, filters.search]);

  useEffect(() => {
    // Apply theme and color scheme to document
    const root = document.documentElement;
    
    if (theme === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const applyAutoTheme = () => {
        root.setAttribute('data-theme', mediaQuery.matches ? 'dark' : 'light');
        root.setAttribute('data-color', colorScheme);
      };
      
      applyAutoTheme();
      mediaQuery.addListener(applyAutoTheme);
      
      return () => mediaQuery.removeListener(applyAutoTheme);
    } else {
      root.setAttribute('data-theme', theme);
      root.setAttribute('data-color', colorScheme);
    }
  }, [theme, colorScheme]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const params = {
        status: 'active',
        ...filters
      };
      
      const response = await apiService.getProjects(params);
      setProjects(response.projects || []);
    } catch (err) {
      console.error('Failed to load projects:', err);
      setError(err.message || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const loadMyEnrollments = async () => {
    try {
      const summary = await apiService.getMyProjectSummary();
      const enrolled = new Map(); // Changed from Set to Map to store status
      
      // Add current project if exists (backward compatibility)
      if (summary.current_project) {
        enrolled.set(summary.current_project.project_id, summary.current_project.status);
      }
      
      // Add all enrolled projects from new field
      if (summary.enrolled_projects && Array.isArray(summary.enrolled_projects)) {
        summary.enrolled_projects.forEach(project => {
          enrolled.set(project.project_id, project.status);
        });
      }
      
      setEnrolledProjects(enrolled);
    } catch (err) {
      console.error('Failed to load enrollments:', err);
      // Set empty Map in case of error to ensure consistency
      setEnrolledProjects(new Map());
    }
  };

  const handleEnroll = async (project) => {
    try {
      // Check if already enrolled to prevent double enrollment
      if (enrolledProjects instanceof Map && enrolledProjects.has(project.id)) {
        const status = enrolledProjects.get(project.id);
        if (status === 'active') {
          alert('You are already enrolled in this project!');
          return;
        } else if (status === 'not_eligible') {
          alert('You are not eligible for this project. Please check the enrollment requirements.');
          return;
        }
      }
      
      await apiService.enrollInProject(project.id);
      
      // Refresh both project data and enrollments to update UI
      await Promise.all([
        loadProjects(),
        loadMyEnrollments()
      ]);
      
      // Show success message
      alert(`Successfully enrolled in "${project.title}" project!`);
    } catch (err) {
      console.error('Enrollment error:', err);
      if (err.message.includes('409') || err.message.includes('already enrolled')) {
        alert('You are already enrolled in this project!');
      } else {
        alert(`Error during enrollment: ${err.message}`);
      }
    }
  };

  const handleWithdraw = async (project) => {
    try {
      await apiService.withdrawFromProject(project.id);
      
      // Refresh both project data and enrollments to update UI
      await Promise.all([
        loadProjects(),
        loadMyEnrollments()
      ]);
      
      alert(`Successfully withdrew from "${project.title}" project.`);
    } catch (err) {
      alert(`Error during withdrawal: ${err.message}`);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const filteredProjects = projects.filter(project => {
    if (filters.search && !project.title.toLowerCase().includes(filters.search.toLowerCase())) {
      return false;
    }
    return true;
  });

  const availableProjects = filteredProjects.filter(project => 
    enrolledProjects instanceof Map ? !enrolledProjects.has(project.id) : true
  );
  const myProjects = filteredProjects.filter(project => 
    enrolledProjects instanceof Map ? enrolledProjects.has(project.id) : false
  );

  if (loading) {
    return (
      <div className="projects-page">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading projects...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="projects-page">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/student/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>📁 Projects</h1>
          <p>Welcome, {user?.name}! Choose a project for the semester.</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Filters */}
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
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={filters.available_only}
              onChange={(e) => handleFilterChange('available_only', e.target.checked)}
            />
            <span>Only available spots</span>
          </label>
        </div>
      </div>

      {/* My Projects Section */}
      {myProjects.length > 0 && (
        <section className="projects-section">
          <h2>🎯 My Projects</h2>
          <div className="projects-grid">
            {myProjects.map(project => (
              <ProjectCard
                key={project.id}
                project={project}
                isEnrolled={true}
                onWithdraw={handleWithdraw}
              />
            ))}
          </div>
        </section>
      )}

      {/* Available Projects Section */}
      <section className="projects-section">
        <h2>💡 Available Projects</h2>
        
        {availableProjects.length === 0 ? (
          <div className="empty-state">
            {filters.search ? (
              <p>🔍 No projects found matching your search criteria.</p>
            ) : (
              <p>🎉 No available projects at the moment, or you've already enrolled in all of them!</p>
            )}
          </div>
        ) : (
          <div className="projects-grid">
            {availableProjects.map(project => (
              <ProjectCard
                key={project.id}
                project={project}
                isEnrolled={enrolledProjects instanceof Map ? enrolledProjects.has(project.id) : false}
                enrollmentStatus={enrolledProjects instanceof Map ? enrolledProjects.get(project.id) : undefined}
                onEnroll={handleEnroll}
              />
            ))}
          </div>
        )}
      </section>

      {/* Statistics */}
      <div className="projects-stats">
        <div className="stat-item">
          <span className="stat-number">{filteredProjects.length}</span>
          <span className="stat-label">Total Projects</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{availableProjects.length}</span>
          <span className="stat-label">Available</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{myProjects.length}</span>
          <span className="stat-label">My Projects</span>
        </div>
      </div>
    </div>
  );
};

export default Projects;