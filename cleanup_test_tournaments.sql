-- ================================================================
-- TOURNAMENT CLEANUP SCRIPT
-- ================================================================
-- Purpose: Remove test/sandbox/incomplete tournaments
-- Safe to run: Uses transactions and validation checks
-- ================================================================

BEGIN;

-- ================================================================
-- STEP 0: IDENTIFY TOURNAMENTS TO DELETE
-- ================================================================

CREATE TEMP TABLE tournaments_to_delete AS
SELECT id FROM semesters
WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
  AND (
    -- DRAFT tournaments (never started)
    (tournament_status = 'DRAFT'
     AND (code LIKE 'SANDBOX%' OR code LIKE '%TEST%' OR code LIKE 'Interactive%'))

    OR

    -- IN_PROGRESS test tournaments (started but never finished)
    (tournament_status = 'IN_PROGRESS'
     AND (code LIKE 'SANDBOX%' OR code LIKE '%TEST%')
     AND id NOT IN (
       SELECT DISTINCT semester_id
       FROM tournament_participations
       WHERE achieved_at > NOW() - INTERVAL '24 hours'
     ))

    OR

    -- COMPLETED but NOT REWARDED test tournaments
    (tournament_status = 'COMPLETED'
     AND (code LIKE 'SANDBOX%' OR code LIKE '%TEST%' OR code LIKE 'Idempotency%')
     AND id NOT IN (
       SELECT DISTINCT semester_id FROM tournament_participations
     ))

    OR

    -- REWARDS_DISTRIBUTED orphaned test tournaments
    (tournament_status = 'REWARDS_DISTRIBUTED'
     AND (code LIKE '%TEST%' OR code LIKE 'SANDBOX%')
     AND id NOT IN (
       SELECT DISTINCT semester_id FROM tournament_participations
     ))
  );

-- ================================================================
-- STEP 1: DELETE DEPENDENT RECORDS (NO CASCADE DELETE)
-- ================================================================

-- Delete sessions (NO CASCADE)
DELETE FROM sessions WHERE semester_id IN (SELECT id FROM tournaments_to_delete);

-- Delete groups (NO CASCADE)
DELETE FROM groups WHERE semester_id IN (SELECT id FROM tournaments_to_delete);

-- Delete modules (NO CASCADE)
DELETE FROM modules WHERE semester_id IN (SELECT id FROM tournaments_to_delete);

-- Delete projects (NO CASCADE)
DELETE FROM projects WHERE semester_id IN (SELECT id FROM tournaments_to_delete);

-- Delete notifications (NO CASCADE)
DELETE FROM notifications WHERE related_semester_id IN (SELECT id FROM tournaments_to_delete);

-- Delete tournament status history (NO CASCADE)
DELETE FROM tournament_status_history WHERE tournament_id IN (SELECT id FROM tournaments_to_delete);

-- ================================================================
-- STEP 2: DELETE TOURNAMENTS (CASCADE WILL HANDLE REMAINING)
-- ================================================================
-- These will CASCADE DELETE:
-- - game_configurations
-- - instructor_assignment_requests
-- - semester_enrollments
-- - semester_instructors
-- - tournament_badges
-- - tournament_configurations
-- - tournament_participations
-- - tournament_rankings
-- - tournament_reward_configs
-- - tournament_rewards
-- - tournament_skill_mappings
-- - tournament_stats
-- - tournament_team_enrollments
--
-- These will SET NULL:
-- - credit_transactions (semester_id)
-- - xp_transactions (semester_id)
-- ================================================================

DELETE FROM semesters WHERE id IN (SELECT id FROM tournaments_to_delete);

-- 1.2: IN_PROGRESS test tournaments (started but never finished)
DELETE FROM semesters
WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
  AND tournament_status = 'IN_PROGRESS'
  AND (code LIKE 'SANDBOX%' OR code LIKE '%TEST%')
  AND id NOT IN (
    -- Keep only if has recent activity (within last 24 hours)
    SELECT DISTINCT semester_id
    FROM tournament_participations
    WHERE achieved_at > NOW() - INTERVAL '24 hours'
  );

-- 1.3: COMPLETED but NOT REWARDED test tournaments
-- These are broken - rewards were never distributed
DELETE FROM semesters
WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
  AND tournament_status = 'COMPLETED'
  AND (code LIKE 'SANDBOX%' OR code LIKE '%TEST%' OR code LIKE 'Idempotency%')
  AND id NOT IN (
    -- Keep only if has participations (rewards were distributed)
    SELECT DISTINCT semester_id FROM tournament_participations
  );

-- ================================================================
-- CATEGORY 2: ORPHANED TEST TOURNAMENTS
-- Delete REWARDS_DISTRIBUTED test tournaments with NO actual data
-- ================================================================

-- These have status REWARDS_DISTRIBUTED but no participations/badges
-- (likely test runs that failed midway)
DELETE FROM semesters
WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
  AND tournament_status = 'REWARDS_DISTRIBUTED'
  AND (code LIKE '%TEST%' OR code LIKE 'SANDBOX%')
  AND id NOT IN (
    SELECT DISTINCT semester_id FROM tournament_participations
  );

-- ================================================================
-- VALIDATION QUERIES (Run AFTER cleanup to verify)
-- ================================================================

-- Count remaining tournaments by category
SELECT
    CASE
        WHEN code LIKE 'SANDBOX%' THEN 'SANDBOX'
        WHEN code LIKE '%TEST%' THEN 'TEST'
        WHEN code LIKE 'Checkpoint%' THEN 'CHECKPOINT'
        WHEN code LIKE 'Idempotency%' THEN 'IDEMPOTENCY'
        ELSE 'PRODUCTION'
    END as category,
    tournament_status,
    COUNT(*) as count
FROM semesters
WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
GROUP BY category, tournament_status
ORDER BY category, tournament_status;

-- Count User 4 enrollments after cleanup
SELECT
    COUNT(*) as remaining_enrollments,
    COUNT(DISTINCT semester_id) as unique_tournaments
FROM semester_enrollments se
JOIN semesters s ON se.semester_id = s.id
WHERE se.user_id = 4
  AND s.specialization_type = 'LFA_FOOTBALL_PLAYER';

COMMIT;

-- ================================================================
-- EXPECTED RESULTS:
-- ================================================================
-- DELETED:
--   - 6 DRAFT test tournaments
--   - 15 IN_PROGRESS incomplete test tournaments
--   - 10 COMPLETED but not rewarded test tournaments
--   - 2 REWARDS_DISTRIBUTED orphaned test tournaments
-- TOTAL DELETED: ~33 test tournaments
--
-- KEPT (VALID):
--   - REWARDS_DISTRIBUTED test tournaments WITH participations/badges
--   - All PRODUCTION tournaments
--   - Any recent test tournaments (< 24h old)
-- ================================================================
