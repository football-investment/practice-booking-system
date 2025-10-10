import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiService from '../../services/apiService';
import './LessonView.css';

const LessonView = () => {
  const { specializationId, lessonId } = useParams();
  const navigate = useNavigate();

  const [lesson, setLesson] = useState(null);
  const [modules, setModules] = useState([]);
  const [quizzes, setQuizzes] = useState([]);
  const [exercises, setExercises] = useState([]);
  const [progress, setProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedModule, setExpandedModule] = useState(null);

  useEffect(() => {
    fetchLessonData();
  }, [lessonId]);

  const fetchLessonData = async () => {
    try {
      setLoading(true);

      // Fetch lesson details
      const lessonResponse = await apiService.get(`/curriculum/lesson/${lessonId}`);
      setLesson(lessonResponse.data);

      // Fetch modules
      const modulesResponse = await apiService.get(`/curriculum/lesson/${lessonId}/modules`);
      setModules(modulesResponse.data);

      // Fetch quizzes
      const quizzesResponse = await apiService.get(`/curriculum/lesson/${lessonId}/quizzes`);
      setQuizzes(quizzesResponse.data);

      // Fetch exercises
      const exercisesResponse = await apiService.get(`/curriculum/lesson/${lessonId}/exercises`);
      setExercises(exercisesResponse.data);

      // Fetch user progress
      const progressResponse = await apiService.get(`/curriculum/lesson/${lessonId}/progress`);
      setProgress(progressResponse.data);

      setLoading(false);
    } catch (err) {
      console.error('Error fetching lesson:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  const getModuleIcon = (moduleType) => {
    const icons = {
      THEORY: '📚',
      PRACTICE: '🎯',
      VIDEO: '🎥',
      EXERCISE: '✍️',
      QUIZ: '❓',
      INTERACTIVE: '🎮'
    };
    return icons[moduleType] || '📄';
  };

  const getModuleStatus = (moduleId) => {
    return progress.modules?.[moduleId]?.status || 'LOCKED';
  };

  const handleModuleClick = (module) => {
    const status = getModuleStatus(module.id);
    if (status === 'LOCKED') {
      alert('Teljesítsd az előző modult először!');
      return;
    }

    if (expandedModule === module.id) {
      setExpandedModule(null);
    } else {
      setExpandedModule(module.id);
      // Mark as viewed
      markModuleAsViewed(module.id);
    }
  };

  const markModuleAsViewed = async (moduleId) => {
    try {
      await apiService.post(`/curriculum/module/${moduleId}/view`);
      fetchLessonData(); // Refresh progress
    } catch (err) {
      console.error('Error marking module as viewed:', err);
    }
  };

  const handleQuizStart = (quiz) => {
    navigate(`/student/quiz/${quiz.id}`);
  };

  const handleExerciseClick = (exercise) => {
    navigate(`/student/curriculum/${specializationId}/lesson/${lessonId}/exercise/${exercise.id}`);
  };

  if (loading) {
    return (
      <div className="lesson-view">
        <div className="loading-spinner">Betöltés...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="lesson-view">
        <div className="error-message">Hiba: {error}</div>
      </div>
    );
  }

  const completionPercentage = progress.completion_percentage || 0;

  return (
    <div className="lesson-view">
      {/* Lesson Header */}
      <div className="lesson-header">
        <button
          className="back-button"
          onClick={() => navigate(`/student/curriculum/${specializationId}`)}
        >
          ← Vissza a tananyaghoz
        </button>

        <h1>{lesson?.title}</h1>
        <p className="lesson-description">{lesson?.description}</p>

        <div className="lesson-info">
          <span className="info-item">⏱️ {lesson?.estimated_hours} óra</span>
          <span className="info-item">⭐ {lesson?.xp_reward} XP</span>
          <span className="info-item">
            📊 {completionPercentage}% teljesítve
          </span>
        </div>

        {/* Overall Progress Bar */}
        <div className="overall-progress-bar">
          <div
            className="overall-progress-fill"
            style={{ width: `${completionPercentage}%` }}
          ></div>
        </div>
      </div>

      {/* Modules Section */}
      <div className="lesson-section">
        <h2>📚 Modulok ({modules.length})</h2>
        <div className="modules-list">
          {modules.map((module, index) => {
            const status = getModuleStatus(module.id);
            const isExpanded = expandedModule === module.id;
            const isLocked = status === 'LOCKED';

            return (
              <div
                key={module.id}
                className={`module-item ${status.toLowerCase()} ${isLocked ? 'locked' : ''}`}
              >
                <div
                  className="module-header"
                  onClick={() => !isLocked && handleModuleClick(module)}
                >
                  <span className="module-icon">{getModuleIcon(module.module_type)}</span>
                  <span className="module-title">{module.title}</span>
                  <span className="module-duration">{module.duration_minutes} perc</span>
                  <span className="module-status-icon">
                    {isLocked && '🔒'}
                    {status === 'COMPLETED' && '✅'}
                    {!isLocked && !isExpanded && '▶️'}
                    {!isLocked && isExpanded && '▼'}
                  </span>
                </div>

                {isExpanded && (
                  <div className="module-content">
                    <div dangerouslySetInnerHTML={{ __html: module.content }} />

                    {module.content_data?.video_url && (
                      <div className="module-video">
                        <iframe
                          src={module.content_data.video_url}
                          title={module.title}
                          frameBorder="0"
                          allowFullScreen
                        ></iframe>
                      </div>
                    )}

                    <button
                      className="complete-module-btn"
                      onClick={() => markModuleAsViewed(module.id)}
                    >
                      Modul teljesítve
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Quizzes Section */}
      {quizzes.length > 0 && (
        <div className="lesson-section">
          <h2>❓ Kvízek ({quizzes.length})</h2>
          <div className="quizzes-list">
            {quizzes.map((quiz) => (
              <div key={quiz.id} className="quiz-item">
                <div className="quiz-info">
                  <h3>{quiz.title}</h3>
                  <p>{quiz.description}</p>
                  <div className="quiz-meta">
                    <span>⏱️ {quiz.time_limit_minutes} perc</span>
                    <span>⭐ {quiz.xp_reward} XP</span>
                    <span>📊 Min. {quiz.passing_score}%</span>
                  </div>
                </div>
                <button
                  className="start-quiz-btn"
                  onClick={() => handleQuizStart(quiz)}
                >
                  Kvíz indítása
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Exercises Section */}
      {exercises.length > 0 && (
        <div className="lesson-section">
          <h2>✍️ Gyakorlatok ({exercises.length})</h2>
          <div className="exercises-list">
            {exercises.map((exercise) => {
              const submission = progress.exercises?.[exercise.id];
              const hasSubmission = !!submission;
              const submissionStatus = submission?.status || 'NOT_STARTED';

              return (
                <div
                  key={exercise.id}
                  className={`exercise-item ${submissionStatus.toLowerCase()}`}
                  onClick={() => handleExerciseClick(exercise)}
                >
                  <div className="exercise-icon">{getModuleIcon(exercise.exercise_type)}</div>
                  <div className="exercise-info">
                    <h3>{exercise.title}</h3>
                    <p>{exercise.description}</p>
                    <div className="exercise-meta">
                      <span>⏱️ {exercise.estimated_time_minutes} perc</span>
                      <span>⭐ {exercise.xp_reward} XP</span>
                      {exercise.deadline_days && (
                        <span>📅 {exercise.deadline_days} nap határidő</span>
                      )}
                    </div>
                  </div>
                  <div className="exercise-status">
                    {!hasSubmission && (
                      <span className="status-badge not-started">Nincs leadva</span>
                    )}
                    {submissionStatus === 'DRAFT' && (
                      <span className="status-badge draft">Vázlat</span>
                    )}
                    {submissionStatus === 'SUBMITTED' && (
                      <span className="status-badge submitted">Leadva</span>
                    )}
                    {submissionStatus === 'UNDER_REVIEW' && (
                      <span className="status-badge review">Értékelés alatt</span>
                    )}
                    {submissionStatus === 'APPROVED' && (
                      <span className="status-badge approved">Elfogadva ✅</span>
                    )}
                    {submissionStatus === 'REJECTED' && (
                      <span className="status-badge rejected">Elutasítva</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default LessonView;
