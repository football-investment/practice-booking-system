import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import './InstructorAnalytics.css';

const InstructorAnalytics = () => {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState({
    projects: [],
    totalProjects: 0,
    totalStudents: 0,
    completedProjects: 0,
    averageCompletion: 0,
    projectsByStatus: {},
    studentEngagement: [],
    recentActivity: []
  });
  const [error, setError] = useState('');

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      
      // Load instructor projects
      const projectsResponse = await apiService.getInstructorProjects();
      const projects = Array.isArray(projectsResponse) ? projectsResponse : (projectsResponse?.projects || []);
      
      // Load instructor students
      const studentsResponse = await apiService.getInstructorStudents();
      const students = studentsResponse?.students || [];
      
      // Calculate analytics
      const totalProjects = projects.length;
      const totalStudents = students.length;
      const completedProjects = projects.filter(p => p.status === 'completed').length;
      
      // Calculate average completion percentage
      const averageCompletion = projects.length > 0 
        ? projects.reduce((sum, p) => sum + (p.completion_percentage || 0), 0) / projects.length
        : 0;

      // Group projects by status
      const projectsByStatus = projects.reduce((acc, project) => {
        const status = project.status || 'unknown';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      }, {});

      // Student engagement metrics
      const studentEngagement = students.map(student => ({
        id: student.id,
        name: student.name,
        email: student.email,
        enrollments: student.enrollments?.length || 0,
        activeProjects: student.enrollments?.filter(e => e.status === 'active').length || 0
      })).sort((a, b) => b.enrollments - a.enrollments);

      setAnalytics({
        projects,
        totalProjects,
        totalStudents,
        completedProjects,
        averageCompletion,
        projectsByStatus,
        studentEngagement: studentEngagement.slice(0, 10), // Top 10
        recentActivity: projects.slice(0, 5) // Latest 5 projects
      });

    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError(err.message || 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
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
      <div className="instructor-analytics">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="instructor-analytics">
        <div className="page-header">
          <div>
            <Link to="/instructor/projects" className="back-btn">
              ← Back to Projects
            </Link>
            <h1>📊 Project Analytics</h1>
          </div>
        </div>
        <div className="error-container">
          <div className="error-message">
            <h3>❌ Error Loading Analytics</h3>
            <p>{error}</p>
            <button className="btn-primary" onClick={loadAnalytics}>
              🔄 Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-analytics">
      <div className="page-header">
        <div>
          <Link to="/instructor/projects" className="back-btn">
            ← Back to Projects
          </Link>
          <h1>📊 Project Analytics</h1>
          <p>Overall project performance and statistics</p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={loadAnalytics}>
            🔄 Refresh Data
          </button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="stats-overview">
        <div className="stat-card">
          <div className="stat-icon">📁</div>
          <div className="stat-content">
            <div className="stat-number">{analytics.totalProjects}</div>
            <div className="stat-label">Total Projects</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <div className="stat-number">{analytics.totalStudents}</div>
            <div className="stat-label">Total Students</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <div className="stat-number">{analytics.completedProjects}</div>
            <div className="stat-label">Completed Projects</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <div className="stat-number">{Math.round(analytics.averageCompletion)}%</div>
            <div className="stat-label">Average Completion</div>
          </div>
        </div>
      </div>

      {/* Projects by Status */}
      <div className="analytics-section">
        <div className="section-header">
          <h2>Projects by Status</h2>
        </div>
        <div className="status-chart">
          {Object.entries(analytics.projectsByStatus).map(([status, count]) => (
            <div key={status} className="status-item">
              <div 
                className="status-bar"
                style={{ 
                  backgroundColor: getStatusColor(status),
                  width: `${(count / analytics.totalProjects) * 100}%`
                }}
              ></div>
              <div className="status-info">
                <span className="status-name">{status.charAt(0).toUpperCase() + status.slice(1)}</span>
                <span className="status-count">{count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Students */}
      <div className="analytics-section">
        <div className="section-header">
          <h2>Most Active Students</h2>
          <p>Students with the most project enrollments</p>
        </div>
        <div className="students-table">
          <div className="table-header">
            <div>Student</div>
            <div>Total Enrollments</div>
            <div>Active Projects</div>
          </div>
          {analytics.studentEngagement.map((student, index) => (
            <div key={student.id} className="table-row">
              <div className="student-info">
                <span className="rank">#{index + 1}</span>
                <div>
                  <div className="student-name">{student.name}</div>
                  <div className="student-email">{student.email}</div>
                </div>
              </div>
              <div className="enrollment-count">{student.enrollments}</div>
              <div className="active-count">{student.activeProjects}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="analytics-section">
        <div className="section-header">
          <h2>Recent Projects</h2>
          <p>Latest projects created</p>
        </div>
        <div className="recent-projects">
          {analytics.recentActivity.map(project => (
            <Link 
              key={project.id} 
              to={`/instructor/projects/${project.id}`}
              className="project-item"
            >
              <div className="project-info">
                <div className="project-title">{project.title}</div>
                <div className="project-meta">
                  <span className="project-students">{project.enrolled_count || 0} students</span>
                  <span className="project-status" style={{ color: getStatusColor(project.status) }}>
                    {project.status}
                  </span>
                </div>
              </div>
              <div className="project-completion">
                {Math.round(project.completion_percentage || 0)}%
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default InstructorAnalytics;