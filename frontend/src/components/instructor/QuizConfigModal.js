import React, { useState, useEffect } from 'react';
import './QuizConfigModal.css';

const QuizConfigModal = ({ isOpen, onClose, project, onSave }) => {
  const [quizzes, setQuizzes] = useState([]);
  const [projectQuizzes, setProjectQuizzes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedQuiz, setSelectedQuiz] = useState('');
  const [quizType, setQuizType] = useState('enrollment');
  const [selectedMilestone, setSelectedMilestone] = useState('');
  const [minimumScore, setMinimumScore] = useState(75);
  const [isRequired, setIsRequired] = useState(true);

  useEffect(() => {
    if (isOpen && project) {
      fetchQuizzes();
      fetchProjectQuizzes();
    }
  }, [isOpen, project]);

  const fetchQuizzes = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/v1/quizzes', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setQuizzes(data);
      }
    } catch (error) {
      console.error('Error fetching quizzes:', error);
    }
  };

  const fetchProjectQuizzes = async () => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/v1/projects/${project.id}/quizzes`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setProjectQuizzes(data);
      }
    } catch (error) {
      console.error('Error fetching project quizzes:', error);
    }
  };

  const handleAddQuiz = async () => {
    if (!selectedQuiz) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const payload = {
        quiz_id: parseInt(selectedQuiz),
        quiz_type: quizType,
        milestone_id: selectedMilestone ? parseInt(selectedMilestone) : null,
        minimum_score: minimumScore,
        is_required: isRequired
      };

      const response = await fetch(`/api/v1/projects/${project.id}/quizzes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        await fetchProjectQuizzes();
        setSelectedQuiz('');
        setQuizType('enrollment');
        setSelectedMilestone('');
        setMinimumScore(75);
        setIsRequired(true);
      }
    } catch (error) {
      console.error('Error adding quiz:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveQuiz = async (projectQuizId) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/v1/projects/${project.id}/quizzes/${projectQuizId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        await fetchProjectQuizzes();
      }
    } catch (error) {
      console.error('Error removing quiz:', error);
    } finally {
      setLoading(false);
    }
  };

  const getQuizById = (quizId) => {
    return quizzes.find(q => q.id === quizId);
  };

  const getMilestoneById = (milestoneId) => {
    return project?.milestones?.find(m => m.id === milestoneId);
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'enrollment': return '🎯';
      case 'milestone': return '🏆';
      default: return '❓';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="quiz-config-modal">
        <div className="modal-header">
          <h2>🧠 Quiz Configuration - {project?.title}</h2>
          <button onClick={onClose} className="close-btn">✕</button>
        </div>

        <div className="modal-content">
          {/* Current Project Quizzes */}
          <div className="section">
            <h3>📋 Configured Quizzes</h3>
            {projectQuizzes.length === 0 ? (
              <p className="empty-state">No quizzes configured yet.</p>
            ) : (
              <div className="quiz-list">
                {projectQuizzes.map((pq) => {
                  const quiz = getQuizById(pq.quiz_id);
                  const milestone = getMilestoneById(pq.milestone_id);
                  
                  return (
                    <div key={pq.id} className="quiz-item">
                      <div className="quiz-info">
                        <div className="quiz-title">
                          {getTypeIcon(pq.quiz_type)} {quiz?.title || 'Unknown Quiz'}
                        </div>
                        <div className="quiz-details">
                          <span className="quiz-type">{pq.quiz_type}</span>
                          {milestone && <span className="milestone">→ {milestone.title}</span>}
                          <span className="min-score">Min: {pq.minimum_score}%</span>
                          {pq.is_required && <span className="required">Required</span>}
                        </div>
                      </div>
                      <button 
                        onClick={() => handleRemoveQuiz(pq.id)}
                        className="remove-btn"
                        disabled={loading}
                      >
                        🗑️
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Add New Quiz */}
          <div className="section">
            <h3>➕ Add Quiz</h3>
            <div className="add-quiz-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Quiz:</label>
                  <select 
                    value={selectedQuiz} 
                    onChange={(e) => setSelectedQuiz(e.target.value)}
                  >
                    <option value="">Select a quiz...</option>
                    {quizzes.map((quiz) => (
                      <option key={quiz.id} value={quiz.id}>
                        {quiz.title} ({quiz.category})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Type:</label>
                  <select 
                    value={quizType} 
                    onChange={(e) => setQuizType(e.target.value)}
                  >
                    <option value="enrollment">Enrollment Quiz</option>
                    <option value="milestone">Milestone Quiz</option>
                  </select>
                </div>
              </div>

              {quizType === 'milestone' && (
                <div className="form-row">
                  <div className="form-group">
                    <label>Milestone:</label>
                    <select 
                      value={selectedMilestone} 
                      onChange={(e) => setSelectedMilestone(e.target.value)}
                    >
                      <option value="">Select milestone...</option>
                      {project?.milestones?.map((milestone) => (
                        <option key={milestone.id} value={milestone.id}>
                          {milestone.title}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              <div className="form-row">
                <div className="form-group">
                  <label>Minimum Score (%):</label>
                  <input 
                    type="number" 
                    min="0" 
                    max="100" 
                    value={minimumScore}
                    onChange={(e) => setMinimumScore(parseInt(e.target.value))}
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label>
                    <input 
                      type="checkbox"
                      checked={isRequired}
                      onChange={(e) => setIsRequired(e.target.checked)}
                    />
                    Required Quiz
                  </label>
                </div>
              </div>

              <button 
                onClick={handleAddQuiz}
                disabled={!selectedQuiz || loading}
                className="add-btn"
              >
                {loading ? 'Adding...' : '➕ Add Quiz'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuizConfigModal;