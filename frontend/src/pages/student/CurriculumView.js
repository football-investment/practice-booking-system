import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiService from '../../services/apiService';
import './CurriculumView.css';

const CurriculumView = () => {
  const { specializationId } = useParams();
  const navigate = useNavigate();

  const [curriculum, setCurriculum] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [userProgress, setUserProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCurriculum();
  }, [specializationId]);

  const fetchCurriculum = async () => {
    try {
      setLoading(true);

      // Fetch curriculum track
      const curriculumResponse = await apiService.get(`/curriculum/track/${specializationId}`);
      setCurriculum(curriculumResponse.data);

      // Fetch lessons
      const lessonsResponse = await apiService.get(`/curriculum/track/${specializationId}/lessons`);
      setLessons(lessonsResponse.data);

      // Fetch user progress
      const progressResponse = await apiService.get(`/curriculum/progress/${specializationId}`);
      setUserProgress(progressResponse.data);

      setLoading(false);
    } catch (err) {
      console.error('Error fetching curriculum:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  const getLessonStatus = (lessonId) => {
    const progress = userProgress[lessonId];
    if (!progress) return 'LOCKED';
    return progress.status;
  };

  const getLessonProgress = (lessonId) => {
    const progress = userProgress[lessonId];
    if (!progress) return 0;
    return progress.completion_percentage || 0;
  };

  const handleLessonClick = (lesson) => {
    const status = getLessonStatus(lesson.id);
    if (status === 'LOCKED') {
      alert('Ez a lecke még nem elérhető. Teljesítsd az előző leckét!');
      return;
    }
    navigate(`/student/curriculum/${specializationId}/lesson/${lesson.id}`);
  };

  if (loading) {
    return (
      <div className="curriculum-view">
        <div className="loading-spinner">Betöltés...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="curriculum-view">
        <div className="error-message">Hiba: {error}</div>
      </div>
    );
  }

  return (
    <div className="curriculum-view">
      {/* Header */}
      <div className="curriculum-header">
        <button className="back-button" onClick={() => navigate('/student/dashboard')}>
          ← Vissza
        </button>
        <h1>{curriculum?.name}</h1>
        <div className="curriculum-stats">
          <div className="stat">
            <span className="stat-value">{lessons.length}</span>
            <span className="stat-label">Leckék</span>
          </div>
          <div className="stat">
            <span className="stat-value">{curriculum?.total_hours || 0}</span>
            <span className="stat-label">Órák</span>
          </div>
          <div className="stat">
            <span className="stat-value">
              {Object.values(userProgress).filter(p => p.status === 'COMPLETED').length}
            </span>
            <span className="stat-label">Teljesítve</span>
          </div>
        </div>
      </div>

      {/* Lesson List */}
      <div className="lessons-container">
        <h2>Tananyag</h2>
        <div className="lessons-list">
          {lessons.map((lesson, index) => {
            const status = getLessonStatus(lesson.id);
            const progress = getLessonProgress(lesson.id);
            const isLocked = status === 'LOCKED';

            return (
              <div
                key={lesson.id}
                className={`lesson-card ${status.toLowerCase()} ${isLocked ? 'locked' : 'clickable'}`}
                onClick={() => !isLocked && handleLessonClick(lesson)}
              >
                <div className="lesson-number">Lecke {index + 1}</div>

                <div className="lesson-content">
                  <h3>{lesson.title}</h3>
                  <p className="lesson-description">{lesson.description}</p>

                  <div className="lesson-meta">
                    <span className="lesson-duration">
                      ⏱️ {lesson.estimated_hours} óra
                    </span>
                    <span className="lesson-xp">
                      ⭐ {lesson.xp_reward} XP
                    </span>
                  </div>

                  {/* Progress bar */}
                  {!isLocked && (
                    <div className="lesson-progress-bar">
                      <div
                        className="lesson-progress-fill"
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                  )}
                </div>

                {/* Status Badge */}
                <div className={`lesson-status-badge ${status.toLowerCase()}`}>
                  {isLocked && '🔒'}
                  {status === 'UNLOCKED' && '🆕'}
                  {status === 'IN_PROGRESS' && '📖'}
                  {status === 'COMPLETED' && '✅'}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CurriculumView;
