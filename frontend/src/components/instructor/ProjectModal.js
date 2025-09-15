import React, { useState, useEffect } from 'react';
import './ProjectModal.css';
import { apiService } from '../../services/apiService';

const ProjectModal = ({ 
  isOpen, 
  onClose, 
  onSave, 
  project = null,
  isLoading = false 
}) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    requirements: '',
    objectives: '',
    max_participants: 30,
    required_sessions: 8,
    xp_reward: 200,
    difficulty_level: 'Intermediate',
    estimated_duration: 120, // hours
    skills_gained: '',
    resources_provided: '',
    deadline: '',
    status: 'draft',
    semester_id: '' // Will be set when semesters are loaded
  });
  const [errors, setErrors] = useState({});
  const [semesters, setSemesters] = useState([]);

  useEffect(() => {
    if (project) {
      // Edit mode - populate with existing data
      const deadline = project.deadline ? new Date(project.deadline).toISOString().slice(0, 10) : '';
      
      setFormData({
        title: project.title || '',
        description: project.description || '',
        requirements: project.requirements || '',
        objectives: project.objectives || '',
        max_participants: project.max_participants || 30,
        required_sessions: project.required_sessions || 8,
        xp_reward: project.xp_reward || 200,
        difficulty_level: project.difficulty_level || 'Intermediate',
        estimated_duration: project.estimated_duration || 120,
        skills_gained: project.skills_gained || '',
        resources_provided: project.resources_provided || '',
        deadline: deadline,
        status: project.status || 'draft',
        semester_id: project.semester_id || 20
      });
    } else {
      // Create mode - reset form
      setFormData({
        title: '',
        description: '',
        requirements: '',
        objectives: '',
        max_participants: 30,
        required_sessions: 8,
        xp_reward: 200,
        difficulty_level: 'Intermediate',
        estimated_duration: 120,
        skills_gained: '',
        resources_provided: '',
        deadline: '',
        status: 'draft',
        semester_id: '' // Will be set when semesters are loaded
      });
    }
    setErrors({});
  }, [project, isOpen]);

  // Fetch semesters when modal opens
  useEffect(() => {
    if (isOpen) {
      const fetchSemesters = async () => {
        try {
          const response = await apiService.getSemesters();
          console.log('Semesters API response:', response);
          
          // Handle API response structure - backend returns {semesters: [...], total: number}
          let semesterData = [];
          if (response && Array.isArray(response.semesters)) {
            semesterData = response.semesters;
          } else if (Array.isArray(response)) {
            semesterData = response;
          } else {
            console.warn('Unexpected semesters API response structure:', response);
            semesterData = [];
          }
          
          setSemesters(semesterData);
          
          // Set default semester for new projects
          if (!project && semesterData && semesterData.length > 0) {
            setFormData(prev => ({
              ...prev,
              semester_id: semesterData[0].id
            }));
          }
        } catch (error) {
          console.error('Failed to fetch semesters:', error);
          setSemesters([]);
        }
      };
      fetchSemesters();
    }
  }, [isOpen, project]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'max_participants' || name === 'estimated_duration' || name === 'required_sessions' || name === 'xp_reward' || name === 'semester_id' ? parseInt(value) || 0 : value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.title.trim()) {
      newErrors.title = 'Project title is required';
    }
    
    if (!formData.description.trim()) {
      newErrors.description = 'Project description is required';
    }
    
    if (!formData.objectives.trim()) {
      newErrors.objectives = 'Project objectives are required';
    }
    
    if (formData.max_participants < 1 || formData.max_participants > 100) {
      newErrors.max_participants = 'Max participants must be between 1 and 100';
    }
    
    if (formData.required_sessions < 1 || formData.required_sessions > 50) {
      newErrors.required_sessions = 'Required sessions must be between 1 and 50';
    }
    
    if (formData.xp_reward < 1 || formData.xp_reward > 1000) {
      newErrors.xp_reward = 'XP reward must be between 1 and 1000';
    }
    
    if (!formData.semester_id) {
      newErrors.semester_id = 'Semester selection is required';
    }
    
    if (formData.estimated_duration < 1 || formData.estimated_duration > 1000) {
      newErrors.estimated_duration = 'Estimated duration must be between 1 and 1000 hours';
    }

    if (formData.deadline) {
      const deadlineDate = new Date(formData.deadline);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      if (deadlineDate < today) {
        newErrors.deadline = 'Deadline must be in the future';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    // Transform form data to match backend schema
    const projectData = {
      title: formData.title,
      description: formData.description,
      max_participants: parseInt(formData.max_participants, 10),
      required_sessions: parseInt(formData.required_sessions, 10),
      xp_reward: parseInt(formData.xp_reward, 10),
      deadline: formData.deadline || null,
      semester_id: parseInt(formData.semester_id, 10),
      // Don't send status during creation - backend will set default
      // Don't send instructor_id - backend will set it automatically for instructors
      // Only send backend-supported fields
    };
    
    onSave(projectData);
  };

  const difficultyLevels = [
    'Beginner', 'Intermediate', 'Advanced', 'Expert'
  ];

  const statusOptions = [
    { value: 'draft', label: 'Draft' },
    { value: 'active', label: 'Active' },
    { value: 'archived', label: 'Archived' }
  ];

  if (!isOpen) return null;

  return (
    <div className="project-modal-overlay" onClick={onClose}>
      <div className="project-modal" onClick={e => e.stopPropagation()}>
        <div className="project-modal-header">
          <h2>{project ? 'Edit Project' : 'Create New Project'}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit} className="project-modal-form">
          <div className="form-grid">
            <div className="form-group full-width">
              <label htmlFor="title">Project Title *</label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                className={errors.title ? 'error' : ''}
                placeholder="e.g. Advanced Web Development Bootcamp"
              />
              {errors.title && <span className="error-text">{errors.title}</span>}
            </div>
            
            <div className="form-group full-width">
              <label htmlFor="description">Project Description *</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                className={errors.description ? 'error' : ''}
                placeholder="Comprehensive overview of the project..."
                rows="4"
              />
              {errors.description && <span className="error-text">{errors.description}</span>}
            </div>

            <div className="form-group full-width">
              <label htmlFor="objectives">Learning Objectives *</label>
              <textarea
                id="objectives"
                name="objectives"
                value={formData.objectives}
                onChange={handleChange}
                className={errors.objectives ? 'error' : ''}
                placeholder="What will students learn and achieve..."
                rows="3"
              />
              {errors.objectives && <span className="error-text">{errors.objectives}</span>}
            </div>

            <div className="form-group full-width">
              <label htmlFor="requirements">Prerequisites & Requirements</label>
              <textarea
                id="requirements"
                name="requirements"
                value={formData.requirements}
                onChange={handleChange}
                placeholder="Required skills, knowledge, or equipment..."
                rows="2"
              />
            </div>

            <div className="form-group">
              <label htmlFor="max_participants">Max Participants *</label>
              <input
                type="number"
                id="max_participants"
                name="max_participants"
                value={formData.max_participants}
                onChange={handleChange}
                min="1"
                max="100"
                className={errors.max_participants ? 'error' : ''}
              />
              {errors.max_participants && <span className="error-text">{errors.max_participants}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="required_sessions">Required Sessions *</label>
              <input
                type="number"
                id="required_sessions"
                name="required_sessions"
                value={formData.required_sessions}
                onChange={handleChange}
                min="1"
                max="50"
                className={errors.required_sessions ? 'error' : ''}
              />
              {errors.required_sessions && <span className="error-text">{errors.required_sessions}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="xp_reward">XP Reward *</label>
              <input
                type="number"
                id="xp_reward"
                name="xp_reward"
                value={formData.xp_reward}
                onChange={handleChange}
                min="1"
                max="1000"
                className={errors.xp_reward ? 'error' : ''}
              />
              {errors.xp_reward && <span className="error-text">{errors.xp_reward}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="semester_id">Semester *</label>
              <select
                id="semester_id"
                name="semester_id"
                value={formData.semester_id}
                onChange={handleChange}
                className={errors.semester_id ? 'error' : ''}
              >
                <option value="">Select a semester</option>
                {Array.isArray(semesters) && semesters.map(semester => (
                  <option key={semester.id} value={semester.id}>
                    {semester.name}
                  </option>
                ))}
              </select>
              {errors.semester_id && <span className="error-text">{errors.semester_id}</span>}
            </div>
            
            <div className="form-group">
              <label htmlFor="difficulty_level">Difficulty Level</label>
              <select
                id="difficulty_level"
                name="difficulty_level"
                value={formData.difficulty_level}
                onChange={handleChange}
              >
                {difficultyLevels.map(level => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="estimated_duration">Duration (hours) *</label>
              <input
                type="number"
                id="estimated_duration"
                name="estimated_duration"
                value={formData.estimated_duration}
                onChange={handleChange}
                min="1"
                max="1000"
                className={errors.estimated_duration ? 'error' : ''}
              />
              {errors.estimated_duration && <span className="error-text">{errors.estimated_duration}</span>}
            </div>
            
            <div className="form-group">
              <label htmlFor="deadline">Project Deadline</label>
              <input
                type="date"
                id="deadline"
                name="deadline"
                value={formData.deadline}
                onChange={handleChange}
                className={errors.deadline ? 'error' : ''}
              />
              {errors.deadline && <span className="error-text">{errors.deadline}</span>}
            </div>

            <div className="form-group">
              <label htmlFor="status">Project Status</label>
              <select
                id="status"
                name="status"
                value={formData.status}
                onChange={handleChange}
              >
                {statusOptions.map(status => (
                  <option key={status.value} value={status.value}>{status.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group full-width">
              <label htmlFor="skills_gained">Skills Students Will Gain</label>
              <textarea
                id="skills_gained"
                name="skills_gained"
                value={formData.skills_gained}
                onChange={handleChange}
                placeholder="Technical skills, soft skills, certifications..."
                rows="2"
              />
            </div>

            <div className="form-group full-width">
              <label htmlFor="resources_provided">Resources Provided</label>
              <textarea
                id="resources_provided"
                name="resources_provided"
                value={formData.resources_provided}
                onChange={handleChange}
                placeholder="Materials, tools, access, mentorship..."
                rows="2"
              />
            </div>
          </div>
          
          <div className="project-modal-actions">
            <button 
              type="button" 
              className="btn-cancel" 
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-save"
              disabled={isLoading}
            >
              {isLoading ? 'Saving...' : project ? 'Update Project' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProjectModal;