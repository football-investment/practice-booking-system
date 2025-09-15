-- =====================================================
-- PRACTICE BOOKING SYSTEM - DATABASE CLEANUP SCRIPT
-- =====================================================
-- 
-- ⚠️  WARNING: This script will delete ALL test data!
-- 
-- What will be PRESERVED:
-- ✅ Admin users (role = 'ADMIN')
-- ✅ Database structure (tables, indexes, etc.)
-- ✅ Semesters (may be needed for system)
-- ✅ Alembic version info
--
-- What will be DELETED:
-- ❌ All student and instructor test users
-- ❌ All quiz data and attempts
-- ❌ All bookings and sessions  
-- ❌ All projects and enrollments
-- ❌ All groups and memberships
-- ❌ All feedback and notifications
-- ❌ All user statistics and achievements
-- 
-- Run this ONLY after creating a database backup!
-- =====================================================

BEGIN;

-- Show current state before cleanup
SELECT 'BEFORE CLEANUP - Users by role:' as status;
SELECT role, COUNT(*) as count FROM users GROUP BY role;

SELECT 'BEFORE CLEANUP - Data counts:' as status;
SELECT 
    'bookings' as table_name, COUNT(*) as count FROM bookings
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL  
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'quizzes', COUNT(*) FROM quizzes
UNION ALL
SELECT 'quiz_attempts', COUNT(*) FROM quiz_attempts
UNION ALL
SELECT 'notifications', COUNT(*) FROM notifications;

-- =====================================================
-- PHASE 1: Delete quiz-related data
-- =====================================================
SELECT 'PHASE 1: Cleaning quiz data...' as status;

-- Delete quiz user answers (depends on quiz_attempts)
DELETE FROM quiz_user_answers;

-- Delete quiz attempts (depends on users and quizzes)
DELETE FROM quiz_attempts;

-- Delete quiz answer options (depends on quiz_questions)
DELETE FROM quiz_answer_options;

-- Delete quiz questions (depends on quizzes)
DELETE FROM quiz_questions;

-- Delete quizzes
DELETE FROM quizzes;

-- =====================================================
-- PHASE 2: Delete user activity data
-- =====================================================
SELECT 'PHASE 2: Cleaning user activity data...' as status;

-- Delete user achievements
DELETE FROM user_achievements;

-- Delete user statistics
DELETE FROM user_stats;

-- Delete notifications
DELETE FROM notifications;

-- Delete feedback
DELETE FROM feedback;

-- Delete attendance records
DELETE FROM attendance;

-- =====================================================
-- PHASE 3: Delete sessions and bookings
-- =====================================================
SELECT 'PHASE 3: Cleaning sessions and bookings...' as status;

-- Delete bookings (depends on sessions and users)
DELETE FROM bookings;

-- Delete sessions
DELETE FROM sessions;

-- =====================================================
-- PHASE 4: Delete project-related data
-- =====================================================
SELECT 'PHASE 4: Cleaning project data...' as status;

-- Delete project milestone progress (depends on project_milestones and users)
DELETE FROM project_milestone_progress;

-- Delete project sessions (depends on projects and sessions - sessions already deleted)
DELETE FROM project_sessions;

-- Delete project enrollments (depends on projects and users)
DELETE FROM project_enrollments;

-- Delete project milestones (depends on projects)
DELETE FROM project_milestones;

-- Delete projects
DELETE FROM projects;

-- =====================================================
-- PHASE 5: Delete groups
-- =====================================================
SELECT 'PHASE 5: Cleaning group data...' as status;

-- Delete group memberships
DELETE FROM group_users;

-- Delete groups
DELETE FROM groups;

-- =====================================================
-- PHASE 6: Delete test users (PRESERVE ADMINS!)
-- =====================================================
SELECT 'PHASE 6: Removing test users (preserving admins)...' as status;

-- Show admins that will be preserved
SELECT 'Preserving these admin users:' as status;
SELECT id, name, email FROM users WHERE role = 'ADMIN';

-- Delete non-admin users
DELETE FROM users WHERE role != 'ADMIN';

-- =====================================================
-- VERIFICATION: Show final state
-- =====================================================
SELECT 'CLEANUP COMPLETED - Final state:' as status;

SELECT 'Users remaining by role:' as status;
SELECT role, COUNT(*) as count FROM users GROUP BY role;

SELECT 'Data counts after cleanup:' as status;
SELECT 
    'bookings' as table_name, COUNT(*) as count FROM bookings
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL  
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'quizzes', COUNT(*) FROM quizzes
UNION ALL
SELECT 'quiz_attempts', COUNT(*) FROM quiz_attempts
UNION ALL
SELECT 'notifications', COUNT(*) FROM notifications
UNION ALL
SELECT 'feedback', COUNT(*) FROM feedback
UNION ALL
SELECT 'groups', COUNT(*) FROM groups
UNION ALL
SELECT 'user_achievements', COUNT(*) FROM user_achievements
UNION ALL
SELECT 'user_stats', COUNT(*) FROM user_stats;

-- =====================================================
-- RESET AUTO-INCREMENT SEQUENCES (OPTIONAL)
-- =====================================================
-- Uncomment these if you want to reset ID sequences:

-- SELECT 'Resetting ID sequences...' as status;
-- SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
-- SELECT setval('sessions_id_seq', 1, false);
-- SELECT setval('bookings_id_seq', 1, false);
-- SELECT setval('projects_id_seq', 1, false);
-- SELECT setval('quizzes_id_seq', 1, false);

COMMIT;

SELECT '🎉 Database cleanup completed successfully!' as status;
SELECT '💡 All admin accounts have been preserved.' as status;