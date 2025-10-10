-- Add specialization_id to all quizzes for Hook 1 competency assessment

-- Step 1: Update quizzes based on their lessons' curriculum tracks
UPDATE quizzes q
SET specialization_id = ct.specialization_id
FROM lessons l
JOIN curriculum_tracks ct ON l.curriculum_track_id = ct.id
WHERE q.lesson_id = l.id
  AND q.specialization_id IS NULL;

-- Step 2: For standalone quizzes without lessons, set default to PLAYER
UPDATE quizzes
SET specialization_id = 'PLAYER'
WHERE lesson_id IS NULL
  AND specialization_id IS NULL;

-- Step 3: Verify the update
SELECT
    q.id,
    q.title,
    q.specialization_id,
    l.title as lesson_title,
    ct.specialization_id as track_specialization
FROM quizzes q
LEFT JOIN lessons l ON q.lesson_id = l.id
LEFT JOIN curriculum_tracks ct ON l.curriculum_track_id = ct.id
ORDER BY q.id;

-- Count quizzes by specialization
SELECT
    specialization_id,
    COUNT(*) as quiz_count
FROM quizzes
GROUP BY specialization_id
ORDER BY specialization_id;
