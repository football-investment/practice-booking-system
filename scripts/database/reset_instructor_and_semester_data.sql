-- ============================================================================
-- SEMESTER & INSTRUCTOR DATA RESET SCRIPT
-- ============================================================================
-- Purpose: Clean reset of semester enrollments and instructor assignments
--          while preserving locations, campuses, and user structure
-- Date: 2025-12-22
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: BACKUP CRITICAL CONFIGURATION (for reference)
-- ============================================================================

-- Show current state before reset
SELECT 'BEFORE RESET - Active Locations' as info, COUNT(*) as count FROM locations WHERE is_active = true;
SELECT 'BEFORE RESET - Active Campuses' as info, COUNT(*) as count FROM campuses WHERE is_active = true;
SELECT 'BEFORE RESET - Active Semesters' as info, COUNT(*) as count FROM semesters WHERE is_active = true;
SELECT 'BEFORE RESET - Semester Enrollments' as info, COUNT(*) as count FROM semester_enrollments;
SELECT 'BEFORE RESET - Sessions' as info, COUNT(*) as count FROM sessions;

-- ============================================================================
-- STEP 2: DELETE INSTRUCTOR MANAGEMENT DATA (New Two-Tier System)
-- ============================================================================

-- Delete instructor assignments (assistant instructors)
DELETE FROM instructor_assignments;
SELECT 'DELETED: Instructor Assignments' as action;

-- Delete position applications
DELETE FROM position_applications;
SELECT 'DELETED: Position Applications' as action;

-- Delete instructor positions (job postings)
DELETE FROM instructor_positions;
SELECT 'DELETED: Instructor Positions' as action;

-- Delete master instructors
DELETE FROM location_master_instructors;
SELECT 'DELETED: Master Instructors' as action;

-- Delete old instructor assignment requests (legacy system)
DELETE FROM instructor_assignment_requests;
SELECT 'DELETED: Old Assignment Requests (Legacy)' as action;

-- ============================================================================
-- STEP 3: DELETE SEMESTER-RELATED DATA
-- ============================================================================

-- Delete attendance records (all types)
DELETE FROM attendance;
SELECT 'DELETED: Attendance Records' as action;

DELETE FROM lfa_player_attendance;
SELECT 'DELETED: LFA Player Attendance' as action;

DELETE FROM coach_attendance;
SELECT 'DELETED: Coach Attendance' as action;

DELETE FROM gancuju_attendance;
SELECT 'DELETED: Gancuju Attendance' as action;

DELETE FROM internship_attendance;
SELECT 'DELETED: Internship Attendance' as action;

DELETE FROM attendance_history;
SELECT 'DELETED: Attendance History' as action;

-- Delete bookings
DELETE FROM bookings;
SELECT 'DELETED: Bookings' as action;

-- Delete sessions and related data
DELETE FROM session_quizzes;
SELECT 'DELETED: Session Quizzes' as action;

DELETE FROM instructor_session_reviews;
SELECT 'DELETED: Instructor Session Reviews' as action;

DELETE FROM sessions;
SELECT 'DELETED: Sessions' as action;

-- Delete semester enrollments
DELETE FROM semester_enrollments;
SELECT 'DELETED: Semester Enrollments' as action;

-- Delete semesters (all - will regenerate from Smart Matrix)
DELETE FROM semesters;
SELECT 'DELETED: All Semesters' as action;

-- ============================================================================
-- STEP 4: RESET USER LICENSE STATES (Optional - Keep licenses but reset enrollment flags)
-- ============================================================================

-- Reset onboarding flags for users (they keep licenses but can re-enroll)
-- Uncomment if you want users to go through onboarding again:
-- UPDATE user_licenses SET is_active = false WHERE specialization_type LIKE 'LFA_PLAYER%';
-- SELECT 'RESET: User License Enrollment Flags' as action;

-- ============================================================================
-- STEP 5: VERIFY PRESERVED DATA
-- ============================================================================

-- Verify locations are preserved
SELECT 'AFTER RESET - Active Locations' as info, COUNT(*) as count FROM locations WHERE is_active = true;
SELECT 'AFTER RESET - Active Campuses' as info, COUNT(*) as count FROM campuses WHERE is_active = true;

-- Verify users are preserved
SELECT 'AFTER RESET - Total Users' as info, COUNT(*) as count FROM users;
SELECT 'AFTER RESET - User Licenses' as info, COUNT(*) as count FROM user_licenses;

-- ============================================================================
-- STEP 6: VERIFY DELETION
-- ============================================================================

SELECT 'AFTER RESET - Semesters' as info, COUNT(*) as count FROM semesters;
SELECT 'AFTER RESET - Semester Enrollments' as info, COUNT(*) as count FROM semester_enrollments;
SELECT 'AFTER RESET - Sessions' as info, COUNT(*) as count FROM sessions;
SELECT 'AFTER RESET - Bookings' as info, COUNT(*) as count FROM bookings;
SELECT 'AFTER RESET - Attendance' as info, COUNT(*) as count FROM attendance;
SELECT 'AFTER RESET - Master Instructors' as info, COUNT(*) as count FROM location_master_instructors;
SELECT 'AFTER RESET - Instructor Positions' as info, COUNT(*) as count FROM instructor_positions;
SELECT 'AFTER RESET - Position Applications' as info, COUNT(*) as count FROM position_applications;
SELECT 'AFTER RESET - Instructor Assignments' as info, COUNT(*) as count FROM instructor_assignments;
SELECT 'AFTER RESET - Old Assignment Requests' as info, COUNT(*) as count FROM instructor_assignment_requests;

-- ============================================================================
-- COMMIT OR ROLLBACK
-- ============================================================================

-- Review the output above. If everything looks correct, COMMIT.
-- If you want to undo, ROLLBACK.

COMMIT;  -- Applying changes NOW
-- ROLLBACK;  -- Not used - we want to commit

-- ============================================================================
-- NEXT STEPS AFTER COMMIT
-- ============================================================================

/*
After running this script successfully:

1. Go to Admin Dashboard → Smart Matrix
2. Select location(s)
3. Generate semesters for each age group/year using the matrix
4. Hire Master Instructors for each location (new feature)
5. Master Instructors can post positions and review applications
6. Students can enroll in new semesters

PRESERVED DATA:
✅ Locations & Campuses (structure intact)
✅ Users (all user accounts)
✅ User Licenses (license ownership)
✅ Credits & Payments (financial data)
✅ Coupons & Invoice Requests

DELETED DATA:
❌ All Semesters (will regenerate)
❌ Semester Enrollments (students can re-enroll)
❌ Sessions & Bookings (will recreate)
❌ Attendance Records (fresh start)
❌ Master Instructor assignments (can reassign)
❌ Instructor positions & applications (can repost)
❌ Assistant instructor assignments (can reassign)
*/

END;
