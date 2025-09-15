import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import './InstructorProgressReport.css';

const InstructorProgressReport = () => {
  const [loading, setLoading] = useState(true);
  const [reportData, setReportData] = useState({
    projects: [],
    students: [],
    summary: {
      totalProjects: 0,
      totalStudents: 0,
      overallProgress: 0,
      onTrackProjects: 0,
      behindProjects: 0
    }
  });
  const [error, setError] = useState('');
  const [reportType, setReportType] = useState('overview'); // overview, detailed, export
  const [selectedProject, setSelectedProject] = useState('all');

  useEffect(() => {
    loadReportData();
  }, []);

  const loadReportData = async () => {
    try {
      setLoading(true);
      
      // Load instructor projects
      const projectsResponse = await apiService.getInstructorProjects();
      const projects = Array.isArray(projectsResponse) ? projectsResponse : (projectsResponse?.projects || []);
      
      // Load instructor students
      const studentsResponse = await apiService.getInstructorStudents();
      const students = studentsResponse?.students || [];
      
      // Calculate summary statistics
      const totalProjects = projects.length;
      const totalStudents = students.length;
      const overallProgress = projects.length > 0 
        ? Math.round(projects.reduce((sum, p) => sum + (p.completion_percentage || 0), 0) / projects.length)
        : 0;
      
      const onTrackProjects = projects.filter(p => (p.completion_percentage || 0) >= 50).length;
      const behindProjects = projects.filter(p => (p.completion_percentage || 0) < 50).length;

      setReportData({
        projects,
        students,
        summary: {
          totalProjects,
          totalStudents,
          overallProgress,
          onTrackProjects,
          behindProjects
        }
      });

    } catch (err) {
      console.error('Failed to load report data:', err);
      setError(err.message || 'Failed to load report data');
    } finally {
      setLoading(false);
    }
  };

  const exportReport = () => {
    // Create CSV content
    const csvContent = generateCSVReport();
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `progress-report-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const generateCSVReport = () => {
    let csv = 'Project Title,Status,Enrolled Students,Completion %,XP Reward,Deadline\n';
    
    const projectsToExport = selectedProject === 'all' 
      ? reportData.projects 
      : reportData.projects.filter(p => p.id === parseInt(selectedProject));

    projectsToExport.forEach(project => {
      csv += `"${project.title}","${project.status}",${project.enrolled_count || 0},${project.completion_percentage || 0}%,${project.xp_reward},"${project.deadline || 'No deadline'}"\n`;
    });

    return csv;
  };

  const getProjectsByStatus = () => {
    const statusGroups = reportData.projects.reduce((acc, project) => {
      const status = project.status || 'unknown';
      if (!acc[status]) acc[status] = [];
      acc[status].push(project);
      return acc;
    }, {});

    return statusGroups;
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return '#10b981';
    if (percentage >= 60) return '#f59e0b';
    if (percentage >= 30) return '#f97316';
    return '#ef4444';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#10b981';
      case 'completed': return '#6b7280';
      case 'planning': return '#f59e0b';
      case 'archived': return '#ef4444';
      default: return '#6b7280';
    }
  };

  if (loading) {
    return (
      <div className="instructor-progress-report">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading progress report...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="instructor-progress-report">
        <div className="page-header">
          <div>
            <Link to="/instructor/projects" className="back-btn">
              ← Back to Projects
            </Link>
            <h1>📈 Progress Report</h1>
          </div>
        </div>
        <div className="error-container">
          <div className="error-message">
            <h3>❌ Error Loading Report</h3>
            <p>{error}</p>
            <button className="btn-primary" onClick={loadReportData}>
              🔄 Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const projectsByStatus = getProjectsByStatus();

  return (
    <div className="instructor-progress-report">
      <div className="page-header">
        <div>
          <Link to="/instructor/projects" className="back-btn">
            ← Back to Projects
          </Link>
          <h1>📈 Progress Report</h1>
          <p>Comprehensive progress tracking for all projects</p>
        </div>
        <div className="header-actions">
          <select 
            className="project-filter"
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
          >
            <option value="all">All Projects</option>
            {reportData.projects.map(project => (
              <option key={project.id} value={project.id}>
                {project.title}
              </option>
            ))}
          </select>
          <button className="btn-secondary" onClick={exportReport}>
            📁 Export CSV
          </button>
          <button className="btn-primary" onClick={loadReportData}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Summary Dashboard */}
      <div className="summary-dashboard">
        <div className="summary-card">
          <div className="summary-icon">📊</div>
          <div className="summary-content">
            <div className="summary-number">{reportData.summary.totalProjects}</div>
            <div className="summary-label">Total Projects</div>
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-icon">👥</div>
          <div className="summary-content">
            <div className="summary-number">{reportData.summary.totalStudents}</div>
            <div className="summary-label">Total Students</div>
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-icon">📈</div>
          <div className="summary-content">
            <div className="summary-number">{reportData.summary.overallProgress}%</div>
            <div className="summary-label">Overall Progress</div>
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-icon">✅</div>
          <div className="summary-content">
            <div className="summary-number">{reportData.summary.onTrackProjects}</div>
            <div className="summary-label">On Track</div>
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-icon">⚠️</div>
          <div className="summary-content">
            <div className="summary-number">{reportData.summary.behindProjects}</div>
            <div className="summary-label">Behind Schedule</div>
          </div>
        </div>
      </div>

      {/* Report Type Tabs */}
      <div className="report-tabs">
        <button 
          className={`tab-btn ${reportType === 'overview' ? 'active' : ''}`}
          onClick={() => setReportType('overview')}
        >
          📊 Overview
        </button>
        <button 
          className={`tab-btn ${reportType === 'detailed' ? 'active' : ''}`}
          onClick={() => setReportType('detailed')}
        >
          📋 Detailed
        </button>
      </div>

      {/* Report Content */}
      {reportType === 'overview' && (
        <div className="report-content">
          {/* Projects by Status */}
          <div className="report-section">
            <div className="section-header">
              <h3>Projects by Status</h3>
            </div>
            <div className="status-groups">
              {Object.entries(projectsByStatus).map(([status, projects]) => (
                <div key={status} className="status-group">
                  <div className="status-header">
                    <span 
                      className="status-indicator"
                      style={{ backgroundColor: getStatusColor(status) }}
                    ></span>
                    <span className="status-title">
                      {status.charAt(0).toUpperCase() + status.slice(1)} ({projects.length})
                    </span>
                  </div>
                  <div className="project-list">
                    {projects.map(project => (
                      <Link 
                        key={project.id}
                        to={`/instructor/projects/${project.id}`}
                        className="project-summary"
                      >
                        <div className="project-info">
                          <div className="project-title">{project.title}</div>
                          <div className="project-meta">
                            {project.enrolled_count || 0} students • {project.completion_percentage || 0}% complete
                          </div>
                        </div>
                        <div 
                          className="progress-indicator"
                          style={{ color: getProgressColor(project.completion_percentage || 0) }}
                        >
                          {project.completion_percentage || 0}%
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {reportType === 'detailed' && (
        <div className="report-content">
          {/* Detailed Project Table */}
          <div className="report-section">
            <div className="section-header">
              <h3>Project Details</h3>
            </div>
            <div className="detailed-table">
              <div className="table-header">
                <div>Project</div>
                <div>Status</div>
                <div>Students</div>
                <div>Progress</div>
                <div>XP Reward</div>
                <div>Deadline</div>
              </div>
              {reportData.projects
                .filter(project => selectedProject === 'all' || project.id === parseInt(selectedProject))
                .map(project => (
                <div key={project.id} className="table-row">
                  <div className="project-cell">
                    <Link to={`/instructor/projects/${project.id}`} className="project-link">
                      <div className="project-title">{project.title}</div>
                      <div className="project-desc">{project.description?.substring(0, 60)}...</div>
                    </Link>
                  </div>
                  <div className="status-cell">
                    <span 
                      className="status-badge"
                      style={{ backgroundColor: getStatusColor(project.status) }}
                    >
                      {project.status}
                    </span>
                  </div>
                  <div className="students-cell">
                    {project.enrolled_count || 0}/{project.max_participants}
                  </div>
                  <div className="progress-cell">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ 
                          width: `${project.completion_percentage || 0}%`,
                          backgroundColor: getProgressColor(project.completion_percentage || 0)
                        }}
                      ></div>
                    </div>
                    <span className="progress-text">{project.completion_percentage || 0}%</span>
                  </div>
                  <div className="xp-cell">
                    {project.xp_reward} XP
                  </div>
                  <div className="deadline-cell">
                    {project.deadline ? new Date(project.deadline).toLocaleDateString() : 'No deadline'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InstructorProgressReport;