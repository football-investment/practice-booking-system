import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/apiService';
import './InstructorStudents.css';

const InstructorStudents = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [students, setStudents] = useState([]);
  const [filteredStudents, setFilteredStudents] = useState([]);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    search: '',
    project: 'all',
    session: 'all',
    status: 'all'
  });
  const [stats, setStats] = useState({
    totalStudents: 0,
    activeEnrollments: 0,
    completedProjects: 0,
    averageProgress: 0
  });
  
  // Contact modal state
  const [showContactModal, setShowContactModal] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [contactMessage, setContactMessage] = useState({
    subject: '',
    message: '',
    priority: 'normal'
  });
  const [sending, setSending] = useState(false);

  useEffect(() => {
    loadStudents();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [students, filters]);

  const loadStudents = async () => {
    try {
      setLoading(true);
      const response = await apiService.getInstructorStudents();
      const studentsData = Array.isArray(response) ? response : (response?.students || []);
      
      setStudents(studentsData);
      calculateStats(studentsData);
      
      console.log('Instructor students loaded:', studentsData.length);
    } catch (err) {
      console.error('Failed to load students:', err);
      setError('Failed to load students: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (studentsData) => {
    const stats = {
      totalStudents: studentsData.length,
      activeEnrollments: 0,
      completedProjects: 0,
      averageProgress: 0
    };

    let totalProgress = 0;

    studentsData.forEach(student => {
      // Count active enrollments
      if (student.enrollments) {
        const activeEnrollments = student.enrollments.filter(e => e.status === 'active');
        stats.activeEnrollments += activeEnrollments.length;
        
        const completedProjects = student.enrollments.filter(e => e.status === 'completed');
        stats.completedProjects += completedProjects.length;
        
        // Calculate average progress
        const projectProgress = student.enrollments
          .filter(e => e.project && e.project.completion_percentage)
          .reduce((sum, e) => sum + e.project.completion_percentage, 0);
        
        totalProgress += projectProgress / (student.enrollments.length || 1);
      }
    });

    stats.averageProgress = Math.round(totalProgress / (studentsData.length || 1));
    setStats(stats);
  };

  const applyFilters = () => {
    let filtered = [...students];

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(student =>
        student.name?.toLowerCase().includes(filters.search.toLowerCase()) ||
        student.email?.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Project filter
    if (filters.project !== 'all') {
      filtered = filtered.filter(student =>
        student.enrollments?.some(e => 
          e.project_id?.toString() === filters.project
        )
      );
    }

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(student => {
        if (filters.status === 'active') {
          return student.enrollments?.some(e => e.status === 'active');
        } else if (filters.status === 'completed') {
          return student.enrollments?.some(e => e.status === 'completed');
        }
        return true;
      });
    }

    setFilteredStudents(filtered);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const getStudentStatus = (student) => {
    if (!student.enrollments || student.enrollments.length === 0) {
      return { label: 'No Enrollments', class: 'inactive', icon: '⚪' };
    }

    const activeCount = student.enrollments.filter(e => e.status === 'active').length;
    const completedCount = student.enrollments.filter(e => e.status === 'completed').length;

    if (activeCount > 0) {
      return { label: 'Active', class: 'active', icon: '🟢' };
    } else if (completedCount > 0) {
      return { label: 'Completed', class: 'completed', icon: '✅' };
    } else {
      return { label: 'Enrolled', class: 'enrolled', icon: '🔵' };
    }
  };

  const getProgressColor = (percentage) => {
    if (percentage >= 80) return '#10b981'; // green
    if (percentage >= 60) return '#f59e0b'; // amber
    if (percentage >= 40) return '#ef4444'; // red
    return '#6b7280'; // gray
  };

  const getUniqueProjects = () => {
    const projects = new Set();
    students.forEach(student => {
      student.enrollments?.forEach(enrollment => {
        if (enrollment.project) {
          projects.add(JSON.stringify({
            id: enrollment.project_id,
            title: enrollment.project.title
          }));
        }
      });
    });
    return Array.from(projects).map(p => JSON.parse(p));
  };

  // Contact functionality
  const handleContactStudent = (student) => {
    setSelectedStudent(student);
    setContactMessage({
      subject: `Message from ${user?.name || 'Instructor'}`,
      message: '',
      priority: 'normal'
    });
    setShowContactModal(true);
  };

  const handleSendMessage = async () => {
    if (!selectedStudent || !contactMessage.message.trim()) {
      alert('Please enter a message');
      return;
    }

    setSending(true);
    try {
      // Save message to localStorage for now (until backend is ready)
      const newMessage = {
        id: Date.now(),
        to: { name: selectedStudent.name, email: selectedStudent.email },
        subject: contactMessage.subject,
        message: contactMessage.message,
        priority: contactMessage.priority,
        timestamp: new Date().toISOString()
      };
      
      // Get existing sent messages from localStorage
      const existingSentMessages = JSON.parse(localStorage.getItem('sentMessages') || '[]');
      existingSentMessages.unshift(newMessage); // Add to beginning of array
      localStorage.setItem('sentMessages', JSON.stringify(existingSentMessages));
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      alert(`Message sent successfully to ${selectedStudent.name}!`);
      setShowContactModal(false);
      setContactMessage({ subject: '', message: '', priority: 'normal' });
    } catch (err) {
      console.error('Failed to send message:', err);
      alert('Failed to send message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const handleCloseContactModal = () => {
    setShowContactModal(false);
    setSelectedStudent(null);
    setContactMessage({ subject: '', message: '', priority: 'normal' });
  };

  if (loading) {
    return (
      <div className="instructor-students">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading your students...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="instructor-students">
      {/* Header */}
      <div className="page-header">
        <div>
          <button onClick={() => navigate('/instructor/dashboard')} className="back-btn">
            ← Dashboard
          </button>
          <h1>👥 My Students</h1>
          <p>Monitor and manage your enrolled students</p>
        </div>
      </div>

      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-item">
          <span className="stat-number">{stats.totalStudents}</span>
          <span className="stat-label">Total Students</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.activeEnrollments}</span>
          <span className="stat-label">Active Enrollments</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.completedProjects}</span>
          <span className="stat-label">Completed Projects</span>
        </div>
        <div className="stat-item">
          <span className="stat-number">{stats.averageProgress}%</span>
          <span className="stat-label">Average Progress</span>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Search students..."
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
            <option value="completed">Completed</option>
          </select>

          <select
            value={filters.project}
            onChange={(e) => handleFilterChange('project', e.target.value)}
            className="filter-select"
          >
            <option value="all">All Projects</option>
            {getUniqueProjects().map(project => (
              <option key={project.id} value={project.id}>{project.title}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Students List */}
      <div className="students-section">
        <div className="section-header">
          <h2>Students</h2>
          <span className="results-count">{filteredStudents.length} students</span>
        </div>

        {filteredStudents.length === 0 ? (
          <div className="empty-state">
            {filters.search || filters.project !== 'all' || filters.status !== 'all' ? (
              <p>🔍 No students match your filters.</p>
            ) : (
              <p>👥 No students found.</p>
            )}
          </div>
        ) : (
          <div className="students-grid">
            {filteredStudents.map(student => {
              const statusInfo = getStudentStatus(student);
              const enrollments = student.enrollments || [];
              
              return (
                <div key={student.id} className={`student-card ${statusInfo.class}`}>
                  <div className="student-header">
                    <div className="student-title-row">
                      <h3>{student.name}</h3>
                      <span className={`status-badge ${statusInfo.class}`}>
                        {statusInfo.icon} {statusInfo.label}
                      </span>
                    </div>
                    <div className="student-meta">
                      <span>📧 {student.email}</span>
                      <span>📚 {enrollments.length} enrollments</span>
                    </div>
                  </div>

                  {/* Student Enrollments */}
                  <div className="enrollments-section">
                    <h4>Project Enrollments</h4>
                    {enrollments.length === 0 ? (
                      <p className="no-enrollments">No active enrollments</p>
                    ) : (
                      <div className="enrollments-list">
                        {enrollments.slice(0, 3).map(enrollment => (
                          <div key={enrollment.id} className="enrollment-item">
                            <div className="enrollment-info">
                              <span className="project-title">
                                {enrollment.project?.title || 'Unknown Project'}
                              </span>
                              <span className={`enrollment-status ${enrollment.status}`}>
                                {enrollment.status}
                              </span>
                            </div>
                            {enrollment.project?.completion_percentage && (
                              <div className="progress-bar">
                                <div 
                                  className="progress-fill" 
                                  style={{ 
                                    width: `${enrollment.project.completion_percentage}%`,
                                    backgroundColor: getProgressColor(enrollment.project.completion_percentage)
                                  }}
                                ></div>
                              </div>
                            )}
                          </div>
                        ))}
                        {enrollments.length > 3 && (
                          <p className="more-enrollments">
                            +{enrollments.length - 3} more enrollments
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Student Actions */}
                  <div className="student-actions">
                    <Link 
                      to={`/instructor/students/${student.id}`} 
                      className="btn-primary"
                    >
                      📋 View Details
                    </Link>
                    <Link 
                      to={`/instructor/students/${student.id}/progress`} 
                      className="btn-secondary"
                    >
                      📊 Progress
                    </Link>
                    <button 
                      className="btn-tertiary"
                      onClick={() => handleContactStudent(student)}
                    >
                      💬 Contact
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2>Quick Actions</h2>
        <div className="quick-actions-grid">
          <div className="action-card">
            <div className="action-icon">📊</div>
            <h3>Student Analytics</h3>
            <p>View detailed student performance analytics</p>
            <button className="action-btn">View Analytics</button>
          </div>
          <div className="action-card">
            <div className="action-icon">📧</div>
            <h3>Send Message</h3>
            <p>Send announcements or messages to students</p>
            <button className="action-btn">Send Message</button>
          </div>
          <div className="action-card">
            <div className="action-icon">📈</div>
            <h3>Progress Report</h3>
            <p>Generate progress reports for all students</p>
            <button className="action-btn">Generate Report</button>
          </div>
        </div>
      </div>

      {/* Contact Modal */}
      {showContactModal && selectedStudent && (
        <div className="contact-modal-overlay" onClick={handleCloseContactModal}>
          <div className="contact-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>💬 Contact {selectedStudent.name}</h3>
              <button className="close-btn" onClick={handleCloseContactModal}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="student-info">
                <div className="student-avatar">👤</div>
                <div>
                  <h4>{selectedStudent.name}</h4>
                  <p>{selectedStudent.email}</p>
                </div>
              </div>

              <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}>
                <div className="form-group">
                  <label>Subject</label>
                  <input
                    type="text"
                    value={contactMessage.subject}
                    onChange={(e) => setContactMessage(prev => ({
                      ...prev,
                      subject: e.target.value
                    }))}
                    placeholder="Enter message subject"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Priority</label>
                  <select
                    value={contactMessage.priority}
                    onChange={(e) => setContactMessage(prev => ({
                      ...prev,
                      priority: e.target.value
                    }))}
                  >
                    <option value="low">🟢 Low Priority</option>
                    <option value="normal">🟡 Normal Priority</option>
                    <option value="high">🔴 High Priority</option>
                    <option value="urgent">⚡ Urgent</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Message</label>
                  <textarea
                    value={contactMessage.message}
                    onChange={(e) => setContactMessage(prev => ({
                      ...prev,
                      message: e.target.value
                    }))}
                    placeholder="Write your message to the student..."
                    rows={6}
                    required
                  />
                </div>

                <div className="modal-actions">
                  <button 
                    type="button" 
                    className="btn-secondary"
                    onClick={handleCloseContactModal}
                    disabled={sending}
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    className="btn-primary"
                    disabled={sending || !contactMessage.message.trim()}
                  >
                    {sending ? '📤 Sending...' : '📤 Send Message'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InstructorStudents;