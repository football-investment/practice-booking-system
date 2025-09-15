import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import './InstructorProjectStudents.css';

const InstructorProjectStudents = () => {
  const { projectId } = useParams();
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState(null);
  const [allStudents, setAllStudents] = useState([]);
  const [enrolledStudents, setEnrolledStudents] = useState([]);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all'); // all, enrolled, available
  const [isProcessing, setIsProcessing] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [projectData, studentsData] = await Promise.all([
        apiService.getProjectDetails(projectId),
        apiService.getInstructorStudents()
      ]);
      
      setProject(projectData);
      setAllStudents(studentsData.students || []);
      
      // Filter students enrolled in this specific project
      const enrolled = (studentsData.students || []).filter(student => 
        student.enrollments?.some(enrollment => 
          enrollment.project_id === parseInt(projectId) && enrollment.status === 'active'
        )
      );
      setEnrolledStudents(enrolled);
      
      setError('');
    } catch (err) {
      console.error('Failed to load data:', err);
      setError(err.response?.data?.detail || 'Failed to load project students');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getFilteredStudents = () => {
    let filtered = allStudents;

    // Filter by enrollment status
    if (filterStatus === 'enrolled') {
      filtered = enrolledStudents;
    } else if (filterStatus === 'available') {
      filtered = allStudents.filter(student => 
        !student.enrollments?.some(enrollment => 
          enrollment.project_id === parseInt(projectId) && enrollment.status === 'active'
        )
      );
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(student =>
        student.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        student.email.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    return filtered;
  };

  const handleEnrollStudent = async (studentId) => {
    if (isProcessing) return;

    try {
      setIsProcessing(true);
      const result = await apiService.enrollStudentInProject(projectId, studentId);
      alert(result.message || 'Student enrolled successfully');
      await loadData(); // Reload data
    } catch (err) {
      console.error('Failed to enroll student:', err);
      alert(err.message || 'Failed to enroll student. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRemoveStudent = async (studentId) => {
    if (isProcessing) return;
    
    if (!window.confirm('Are you sure you want to remove this student from the project?')) {
      return;
    }

    try {
      setIsProcessing(true);
      const result = await apiService.removeStudentFromProject(projectId, studentId);
      alert(result.message || 'Student removed successfully');
      await loadData(); // Reload data
    } catch (err) {
      console.error('Failed to remove student:', err);
      alert(err.message || 'Failed to remove student. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const getStatusBadge = (student) => {
    const enrollment = student.enrollments?.find(e => 
      e.project_id === parseInt(projectId)
    );
    
    if (!enrollment) {
      return <span className="status-badge available">Available</span>;
    }
    
    switch (enrollment.status) {
      case 'active':
        return <span className="status-badge enrolled">Enrolled</span>;
      case 'withdrawn':
        return <span className="status-badge withdrawn">Withdrawn</span>;
      case 'completed':
        return <span className="status-badge completed">Completed</span>;
      default:
        return <span className="status-badge unknown">Unknown</span>;
    }
  };

  if (loading) {
    return (
      <div className="instructor-project-students">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading project students...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="instructor-project-students">
        <div className="page-header">
          <div>
            <Link to={`/instructor/projects/${projectId}`} className="back-btn">
              ← Back to Project
            </Link>
            <h1>👥 Project Students</h1>
          </div>
        </div>
        <div className="error-container">
          <div className="error-message">
            <h3>❌ Error Loading Data</h3>
            <p>{error}</p>
            <button className="btn-primary" onClick={loadData}>
              🔄 Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const filteredStudents = getFilteredStudents();
  const enrolledCount = enrolledStudents.length;
  const availableCount = allStudents.length - enrolledCount;

  return (
    <div className="instructor-project-students">
      <div className="page-header">
        <div>
          <Link to={`/instructor/projects/${projectId}`} className="back-btn">
            ← Back to Project
          </Link>
          <h1>👥 Project Students</h1>
          <p>Manage students for: {project?.title}</p>
        </div>
        <div className="header-actions">
          <Link 
            to={`/instructor/projects/${projectId}`}
            className="btn-secondary"
          >
            📊 Project Details
          </Link>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <div className="stat-number">{enrolledCount}</div>
            <div className="stat-label">Enrolled Students</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <div className="stat-number">{availableCount}</div>
            <div className="stat-label">Available Students</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-content">
            <div className="stat-number">{project?.max_participants || 0}</div>
            <div className="stat-label">Max Capacity</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <div className="stat-number">{Math.round((enrolledCount / (project?.max_participants || 1)) * 100)}%</div>
            <div className="stat-label">Capacity Used</div>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="controls-section">
        <div className="search-filter-container">
          <div className="search-box">
            <input
              type="text"
              placeholder="🔍 Search students..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>
          <div className="filter-tabs">
            <button 
              className={`filter-tab ${filterStatus === 'all' ? 'active' : ''}`}
              onClick={() => setFilterStatus('all')}
            >
              All ({allStudents.length})
            </button>
            <button 
              className={`filter-tab ${filterStatus === 'enrolled' ? 'active' : ''}`}
              onClick={() => setFilterStatus('enrolled')}
            >
              Enrolled ({enrolledCount})
            </button>
            <button 
              className={`filter-tab ${filterStatus === 'available' ? 'active' : ''}`}
              onClick={() => setFilterStatus('available')}
            >
              Available ({availableCount})
            </button>
          </div>
        </div>
      </div>

      {/* Students List */}
      <div className="students-container">
        {filteredStudents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">👥</div>
            <h3>No Students Found</h3>
            <p>
              {searchTerm 
                ? `No students match your search "${searchTerm}"`
                : `No ${filterStatus === 'all' ? '' : filterStatus + ' '}students found`
              }
            </p>
          </div>
        ) : (
          <div className="students-grid">
            {filteredStudents.map(student => {
              const enrollment = student.enrollments?.find(e => 
                e.project_id === parseInt(projectId)
              );
              const isEnrolled = enrollment?.status === 'active';

              return (
                <div key={student.id} className="student-card">
                  <div className="student-header">
                    <div className="student-info">
                      <div className="student-name">{student.name}</div>
                      <div className="student-email">{student.email}</div>
                    </div>
                    {getStatusBadge(student)}
                  </div>
                  
                  {enrollment && (
                    <div className="enrollment-details">
                      <div className="detail-item">
                        <span className="label">Enrolled:</span>
                        <span className="value">
                          {new Date(enrollment.enrolled_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="label">Progress:</span>
                        <span className="value">
                          {enrollment.project.completion_percentage}%
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="student-actions">
                    {isEnrolled ? (
                      <>
                        <Link 
                          to={`/instructor/students/${student.id}/progress?project=${projectId}`}
                          className="btn-action view"
                        >
                          📊 View Progress
                        </Link>
                        <button 
                          className="btn-action remove"
                          onClick={() => handleRemoveStudent(student.id)}
                          disabled={isProcessing}
                        >
                          ❌ Remove
                        </button>
                      </>
                    ) : (
                      <button 
                        className="btn-action enroll"
                        onClick={() => handleEnrollStudent(student.id)}
                        disabled={isProcessing || enrolledCount >= (project?.max_participants || 0)}
                      >
                        ➕ Enroll
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default InstructorProjectStudents;