-- ============================================================================
-- UPDATE EXISTING SEMESTER STATUSES
-- ============================================================================
-- Purpose: Set appropriate status for existing semesters based on instructors
-- Date: 2025-12-22
-- Author: Claude Code
--
-- Business Logic:
-- - DRAFT: No master instructor assigned
-- - INSTRUCTOR_ASSIGNED: Has master but checking for assistants
-- - READY_FOR_ENROLLMENT: Has master + at least one assistant
-- ============================================================================

BEGIN;

-- Show current status distribution BEFORE
SELECT
    '=== BEFORE UPDATE ===' as checkpoint,
    status,
    COUNT(*) as count,
    COUNT(CASE WHEN master_instructor_id IS NOT NULL THEN 1 END) as with_master,
    COUNT(CASE WHEN master_instructor_id IS NULL THEN 1 END) as without_master
FROM semesters
GROUP BY status
ORDER BY status;

-- ============================================================================
-- STEP 1: Update semesters that have master instructor
-- ============================================================================
-- Set to INSTRUCTOR_ASSIGNED (will check for assistants in next step)
UPDATE semesters
SET
    status = 'INSTRUCTOR_ASSIGNED',
    updated_at = NOW()
WHERE
    master_instructor_id IS NOT NULL
    AND status = 'DRAFT';

-- Show progress
SELECT
    '=== AFTER STEP 1: Masters Assigned ===' as checkpoint,
    status,
    COUNT(*) as count
FROM semesters
GROUP BY status
ORDER BY status;

-- ============================================================================
-- STEP 2: Check for assistant instructors and update to READY_FOR_ENROLLMENT
-- ============================================================================
-- Note: This checks for active instructor_assignments matching semester criteria
--
-- The challenge: InstructorAssignment doesn't have semester_id, so we match by:
-- - location (via location_city in semester, location_id in assignment)
-- - specialization_type
-- - Active assignments

UPDATE semesters s
SET
    status = 'READY_FOR_ENROLLMENT',
    updated_at = NOW()
WHERE
    s.master_instructor_id IS NOT NULL
    AND s.status = 'INSTRUCTOR_ASSIGNED'
    AND EXISTS (
        SELECT 1
        FROM instructor_assignments ia
        JOIN locations l ON ia.location_id = l.id
        WHERE
            l.city = s.location_city
            AND ia.specialization_type = s.specialization_type
            AND ia.is_active = true
    );

-- Show final status distribution
SELECT
    '=== AFTER STEP 2: Ready for Enrollment ===' as checkpoint,
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM semesters
GROUP BY status
ORDER BY status;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Show detailed breakdown by status and master assignment
SELECT
    '=== FINAL VERIFICATION ===' as checkpoint,
    status,
    CASE
        WHEN master_instructor_id IS NOT NULL THEN 'Has Master'
        ELSE 'No Master'
    END as master_status,
    COUNT(*) as count,
    STRING_AGG(DISTINCT location_city, ', ') as locations
FROM semesters
GROUP BY status, CASE WHEN master_instructor_id IS NOT NULL THEN 'Has Master' ELSE 'No Master' END
ORDER BY status, master_status;

-- Show semesters that are READY_FOR_ENROLLMENT
SELECT
    '=== SEMESTERS READY FOR ENROLLMENT ===' as checkpoint,
    s.id,
    s.code,
    s.location_city,
    s.specialization_type,
    s.start_date,
    s.end_date,
    u.name as master_instructor_name,
    (
        SELECT COUNT(*)
        FROM instructor_assignments ia
        JOIN locations l ON ia.location_id = l.id
        WHERE l.city = s.location_city
        AND ia.specialization_type = s.specialization_type
        AND ia.is_active = true
    ) as assistant_count
FROM semesters s
LEFT JOIN users u ON s.master_instructor_id = u.id
WHERE s.status = 'READY_FOR_ENROLLMENT'
ORDER BY s.location_city, s.specialization_type, s.start_date
LIMIT 20;

-- ============================================================================
-- COMMIT or ROLLBACK
-- ============================================================================
-- Uncomment ONE of the following lines:

COMMIT;  -- ✅ Apply changes
-- ROLLBACK;  -- ❌ Undo everything (for testing)

