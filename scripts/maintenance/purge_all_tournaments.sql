-- =============================================================================
-- TOURNAMENT CASCADE PURGE
-- =============================================================================
-- Deletes ALL tournament (semester) data from lfa_intern_system.
-- Users are completely preserved.
--
-- FK delete rules on semesters children:
--   CASCADE  → automatic: semester_enrollments, semester_instructors,
--               game_configurations, campus_schedule_configs,
--               instructor_assignments, instructor_assignment_requests,
--               teams → (team_members, tournament_team_enrollments CASCADE),
--               tournament_configurations, tournament_badges,
--               tournament_participations, tournament_rankings,
--               tournament_reward_configs, tournament_rewards,
--               tournament_skill_mappings, tournament_stats,
--               tournament_team_enrollments
--   SET NULL → stays alive (null FK): credit_transactions.semester_id,
--               xp_transactions.semester_id
--   NO ACTION → must be deleted MANUALLY FIRST:
--               sessions, groups, modules, projects,
--               tournament_status_history
--
-- Execution order: leaves → parents, NO ACTION tables first, semesters last.
-- =============================================================================

BEGIN;

-- ── Pre-flight row counts (for audit log in psql output) ──────────────────────
SELECT 'PRE-PURGE COUNTS' AS phase,
  (SELECT COUNT(*) FROM semesters)               AS semesters,
  (SELECT COUNT(*) FROM semester_enrollments)    AS enrollments,
  (SELECT COUNT(*) FROM sessions)                AS sessions,
  (SELECT COUNT(*) FROM attendance)              AS attendance,
  (SELECT COUNT(*) FROM bookings)                AS bookings,
  (SELECT COUNT(*) FROM credit_transactions)     AS credits,
  (SELECT COUNT(*) FROM xp_transactions)         AS xp,
  (SELECT COUNT(*) FROM tournament_status_history) AS t_status_hist,
  (SELECT COUNT(*) FROM users)                   AS users_untouched;

-- ── STEP 1 — attendance ──────────────────────────────────────────────────────
-- NO ACTION from: sessions.session_id, bookings.booking_id
-- Must be deleted before both sessions and bookings.
DELETE FROM attendance;

-- ── STEP 2 — bookings ────────────────────────────────────────────────────────
-- NO ACTION from: sessions.session_id, semester_enrollments.enrollment_id
-- Must be deleted before sessions and before the CASCADE on semester_enrollments.
DELETE FROM bookings;

-- ── STEP 3 — tournament_status_history ───────────────────────────────────────
-- NO ACTION from: semesters.tournament_id
DELETE FROM tournament_status_history;

-- ── STEP 4 — sessions ────────────────────────────────────────────────────────
-- NO ACTION from: semesters.semester_id (and optionally groups.group_id)
-- CASCADE children (auto-deleted when sessions rows go):
--   session_group_assignments → session_group_students (CASCADE)
--   session_quizzes (CASCADE)
-- Other session children (all 0 rows, but safe to clear):
DELETE FROM instructor_session_reviews WHERE session_id IS NOT NULL;
DELETE FROM student_performance_reviews WHERE session_id IS NOT NULL;
DELETE FROM project_sessions WHERE session_id IS NOT NULL;
DELETE FROM feedback WHERE session_id IS NOT NULL;

DELETE FROM sessions;

-- ── STEP 5 — credit_transactions (explicit purge, per user request) ───────────
-- The FK rules are SET NULL so the DB would NOT auto-delete these;
-- we remove them explicitly since they are all tournament-earned credits.
DELETE FROM credit_transactions
WHERE semester_id IS NOT NULL
   OR enrollment_id IS NOT NULL;

-- ── STEP 6 — xp_transactions (explicit purge, per user request) ──────────────
-- Same situation: SET NULL rule → must be deleted explicitly.
DELETE FROM xp_transactions
WHERE semester_id IS NOT NULL;

-- ── STEP 7 — DELETE ALL SEMESTERS ────────────────────────────────────────────
-- Triggers DB CASCADE for all remaining children:
--   semester_enrollments → (credit_transactions.enrollment_id SET NULL — already deleted)
--   semester_instructors, game_configurations, campus_schedule_configs,
--   instructor_assignments, instructor_assignment_requests,
--   teams → team_members, tournament_team_enrollments (CASCADE from teams)
--   tournament_configurations, tournament_badges, tournament_participations,
--   tournament_rankings, tournament_reward_configs, tournament_rewards,
--   tournament_skill_mappings, tournament_stats, tournament_team_enrollments
-- SET NULL on remaining xp_transactions.semester_id (already 0 rows after step 6)
DELETE FROM semesters;

-- ── Post-purge row counts ─────────────────────────────────────────────────────
SELECT 'POST-PURGE COUNTS' AS phase,
  (SELECT COUNT(*) FROM semesters)               AS semesters,
  (SELECT COUNT(*) FROM semester_enrollments)    AS enrollments,
  (SELECT COUNT(*) FROM sessions)                AS sessions,
  (SELECT COUNT(*) FROM attendance)              AS attendance,
  (SELECT COUNT(*) FROM bookings)                AS bookings,
  (SELECT COUNT(*) FROM credit_transactions)     AS credits,
  (SELECT COUNT(*) FROM xp_transactions)         AS xp,
  (SELECT COUNT(*) FROM tournament_status_history) AS t_status_hist,
  (SELECT COUNT(*) FROM users)                   AS users_untouched;

COMMIT;
