import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiService from '../../services/apiService';
import './ExerciseSubmission.css';

const ExerciseSubmission = () => {
  const { specializationId, lessonId, exerciseId } = useParams();
  const navigate = useNavigate();

  const [exercise, setExercise] = useState(null);
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Form state
  const [submissionText, setSubmissionText] = useState('');
  const [submissionUrl, setSubmissionUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchExerciseData();
  }, [exerciseId]);

  const fetchExerciseData = async () => {
    try {
      setLoading(true);

      // Fetch exercise details
      const exerciseResponse = await apiService.get(`/curriculum/exercise/${exerciseId}`);
      setExercise(exerciseResponse.data);

      // Fetch existing submission (if any)
      try {
        const submissionResponse = await apiService.get(`/curriculum/exercise/${exerciseId}/submission`);
        setSubmission(submissionResponse.data);
        setSubmissionText(submissionResponse.data.submission_text || '');
        setSubmissionUrl(submissionResponse.data.submission_url || '');
      } catch (err) {
        // No submission yet - that's okay
        if (err.response?.status !== 404) {
          throw err;
        }
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching exercise:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    const requirements = exercise?.requirements;
    if (requirements?.file_type) {
      const allowedTypes = requirements.file_type;
      if (!allowedTypes.includes(file.type)) {
        alert(`Nem megfelelő fájl típus! Engedélyezett típusok: ${allowedTypes.join(', ')}`);
        return;
      }
    }

    // Validate file size
    if (requirements?.max_size_mb) {
      const maxBytes = requirements.max_size_mb * 1024 * 1024;
      if (file.size > maxBytes) {
        alert(`A fájl túl nagy! Maximum méret: ${requirements.max_size_mb} MB`);
        return;
      }
    }

    setSelectedFile(file);
  };

  const handleFileUpload = async () => {
    if (!selectedFile) return null;

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await apiService.post(
        `/curriculum/exercise/submission/${submission?.id || 'new'}/upload`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(percentCompleted);
          }
        }
      );

      return response.data.file_url;
    } catch (err) {
      console.error('File upload error:', err);
      throw new Error('Fájl feltöltés sikertelen');
    }
  };

  const handleSaveDraft = async () => {
    try {
      setSaving(true);

      let fileUrl = submissionUrl;
      if (selectedFile) {
        fileUrl = await handleFileUpload();
      }

      const payload = {
        exercise_id: exerciseId,
        submission_type: getSubmissionType(),
        submission_text: submissionText,
        submission_url: fileUrl,
        status: 'DRAFT'
      };

      if (submission) {
        // Update existing draft
        await apiService.put(`/curriculum/exercise/submission/${submission.id}`, payload);
      } else {
        // Create new draft
        await apiService.post(`/curriculum/exercise/${exerciseId}/submit`, payload);
      }

      alert('✅ Vázlat mentve!');
      fetchExerciseData(); // Refresh
      setSaving(false);
    } catch (err) {
      console.error('Save draft error:', err);
      alert('❌ Hiba a mentés során: ' + err.message);
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    try {
      // Validation
      if (!validateSubmission()) {
        return;
      }

      setSubmitting(true);

      let fileUrl = submissionUrl;
      if (selectedFile) {
        fileUrl = await handleFileUpload();
      }

      const payload = {
        exercise_id: exerciseId,
        submission_type: getSubmissionType(),
        submission_text: submissionText,
        submission_url: fileUrl,
        status: 'SUBMITTED'
      };

      if (submission) {
        // Update and submit
        await apiService.put(`/curriculum/exercise/submission/${submission.id}`, payload);
      } else {
        // Create and submit
        await apiService.post(`/curriculum/exercise/${exerciseId}/submit`, payload);
      }

      alert('🎉 Gyakorlat sikeresen leadva!');
      navigate(`/student/curriculum/${specializationId}/lesson/${lessonId}`);
    } catch (err) {
      console.error('Submit error:', err);
      alert('❌ Hiba a leadás során: ' + err.message);
      setSubmitting(false);
    }
  };

  const validateSubmission = () => {
    const type = exercise?.exercise_type;

    if (type === 'VIDEO_UPLOAD' || type === 'DOCUMENT') {
      if (!submissionUrl && !selectedFile) {
        alert('Kérlek tölts fel egy fájlt!');
        return false;
      }
    }

    if (type === 'TEXT' || type === 'REFLECTION') {
      if (!submissionText || submissionText.trim().length < 50) {
        alert('A szöveges válasz túl rövid! Minimum 50 karakter szükséges.');
        return false;
      }
    }

    return true;
  };

  const getSubmissionType = () => {
    const type = exercise?.exercise_type;
    if (type === 'VIDEO_UPLOAD') return 'VIDEO';
    if (type === 'DOCUMENT') return 'DOCUMENT';
    if (type === 'REFLECTION') return 'TEXT';
    return 'FILE';
  };

  const getStatusBadge = (status) => {
    const badges = {
      DRAFT: { text: 'Vázlat', class: 'draft' },
      SUBMITTED: { text: 'Leadva', class: 'submitted' },
      UNDER_REVIEW: { text: 'Értékelés alatt', class: 'review' },
      APPROVED: { text: 'Elfogadva ✅', class: 'approved' },
      REJECTED: { text: 'Elutasítva', class: 'rejected' },
      REVISION_REQUESTED: { text: 'Javítás szükséges', class: 'revision' }
    };

    const badge = badges[status] || { text: status, class: 'default' };
    return <span className={`status-badge ${badge.class}`}>{badge.text}</span>;
  };

  const canEdit = () => {
    if (!submission) return true;
    return submission.status === 'DRAFT' ||
           submission.status === 'REVISION_REQUESTED' ||
           (submission.status === 'REJECTED' && exercise?.allow_resubmission);
  };

  if (loading) {
    return (
      <div className="exercise-submission">
        <div className="loading-spinner">Betöltés...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="exercise-submission">
        <div className="error-message">Hiba: {error}</div>
      </div>
    );
  }

  return (
    <div className="exercise-submission">
      {/* Header */}
      <div className="submission-header">
        <button
          className="back-button"
          onClick={() => navigate(`/student/curriculum/${specializationId}/lesson/${lessonId}`)}
        >
          ← Vissza a leckéhez
        </button>

        <h1>{exercise?.title}</h1>
        {submission && getStatusBadge(submission.status)}
      </div>

      {/* Exercise Details */}
      <div className="exercise-details">
        <p className="exercise-description">{exercise?.description}</p>

        <div className="exercise-meta">
          <span>⏱️ Becsült idő: {exercise?.estimated_time_minutes} perc</span>
          <span>⭐ Jutalom: {exercise?.xp_reward} XP</span>
          <span>📊 Pontszám: {exercise?.max_points} pont</span>
          <span>✅ Min. teljesítés: {exercise?.passing_score}%</span>
          {exercise?.deadline_days && (
            <span>📅 Határidő: {exercise.deadline_days} nap</span>
          )}
        </div>

        {/* Instructions */}
        <div className="exercise-instructions">
          <h3>📋 Feladat leírás</h3>
          <div dangerouslySetInnerHTML={{ __html: exercise?.instructions }} />
        </div>

        {/* Requirements */}
        {exercise?.requirements && (
          <div className="exercise-requirements">
            <h3>⚠️ Követelmények</h3>
            {exercise.requirements.file_type && (
              <p><strong>Fájl típus:</strong> {exercise.requirements.file_type.join(', ')}</p>
            )}
            {exercise.requirements.max_size_mb && (
              <p><strong>Max. fájlméret:</strong> {exercise.requirements.max_size_mb} MB</p>
            )}
            {exercise.requirements.min_duration && (
              <p><strong>Min. hossz:</strong> {exercise.requirements.min_duration} másodperc</p>
            )}
            {exercise.requirements.criteria && (
              <div>
                <p><strong>Értékelési szempontok:</strong></p>
                <ul>
                  {exercise.requirements.criteria.map((c, idx) => (
                    <li key={idx}>{c.name}: {c.max_points} pont</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Existing Submission Feedback */}
      {submission && submission.status === 'APPROVED' && (
        <div className="feedback-section approved-feedback">
          <h3>✅ Elfogadott munka</h3>
          <p><strong>Pontszám:</strong> {submission.score} / {exercise?.max_points}</p>
          <p><strong>XP megszerzett:</strong> {submission.xp_awarded}</p>
          {submission.instructor_feedback && (
            <div className="instructor-feedback">
              <p><strong>Oktató visszajelzés:</strong></p>
              <p>{submission.instructor_feedback}</p>
            </div>
          )}
        </div>
      )}

      {submission && (submission.status === 'REJECTED' || submission.status === 'REVISION_REQUESTED') && (
        <div className="feedback-section revision-feedback">
          <h3>📝 Javítás szükséges</h3>
          {submission.instructor_feedback && (
            <div className="instructor-feedback">
              <p><strong>Oktató megjegyzései:</strong></p>
              <p>{submission.instructor_feedback}</p>
            </div>
          )}
        </div>
      )}

      {/* Submission Form */}
      {canEdit() && (
        <div className="submission-form">
          <h3>📤 Leadás</h3>

          {/* File Upload */}
          {(exercise?.exercise_type === 'VIDEO_UPLOAD' || exercise?.exercise_type === 'DOCUMENT') && (
            <div className="form-group">
              <label>Fájl feltöltés</label>
              <input
                type="file"
                onChange={handleFileSelect}
                accept={exercise?.requirements?.file_type?.join(',')}
              />
              {selectedFile && (
                <p className="file-info">
                  Kiválasztott fájl: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              )}
              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="upload-progress">
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
                  </div>
                  <p>{uploadProgress}% feltöltve</p>
                </div>
              )}
              {submissionUrl && (
                <p className="current-file">
                  Jelenlegi fájl: <a href={submissionUrl} target="_blank" rel="noopener noreferrer">Megtekintés</a>
                </p>
              )}
            </div>
          )}

          {/* URL Input */}
          {exercise?.exercise_type === 'PROJECT' && (
            <div className="form-group">
              <label>Link (YouTube, Google Drive, stb.)</label>
              <input
                type="url"
                value={submissionUrl}
                onChange={(e) => setSubmissionUrl(e.target.value)}
                placeholder="https://..."
              />
            </div>
          )}

          {/* Text Input */}
          {(exercise?.exercise_type === 'REFLECTION' || exercise?.exercise_type === 'TEXT') && (
            <div className="form-group">
              <label>Szöveges válasz (min. 50 karakter)</label>
              <textarea
                value={submissionText}
                onChange={(e) => setSubmissionText(e.target.value)}
                rows={10}
                placeholder="Írd le a válaszodat..."
              />
              <p className="char-count">{submissionText.length} karakter</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="form-actions">
            <button
              className="btn-draft"
              onClick={handleSaveDraft}
              disabled={saving || submitting}
            >
              {saving ? 'Mentés...' : '💾 Vázlat mentése'}
            </button>

            <button
              className="btn-submit"
              onClick={handleSubmit}
              disabled={saving || submitting}
            >
              {submitting ? 'Leadás...' : '🚀 Végleges leadás'}
            </button>
          </div>
        </div>
      )}

      {/* Read-only view */}
      {!canEdit() && submission && (
        <div className="submission-readonly">
          <h3>📄 Beadott munka</h3>
          {submission.submission_url && (
            <p>
              <strong>Fájl:</strong>{' '}
              <a href={submission.submission_url} target="_blank" rel="noopener noreferrer">
                Megtekintés
              </a>
            </p>
          )}
          {submission.submission_text && (
            <div>
              <strong>Szöveg:</strong>
              <p className="submission-text">{submission.submission_text}</p>
            </div>
          )}
          <p className="submission-date">
            Leadva: {new Date(submission.submitted_at).toLocaleDateString('hu-HU')}
          </p>
        </div>
      )}
    </div>
  );
};

export default ExerciseSubmission;
