-- ============================================
-- Add Instructor Availability Windows
-- Date: 2025-12-23
-- ============================================
--
-- Sets up diverse availability patterns for 2026 (Q1-Q4)
-- to enable comprehensive testing of the instructor system
--
-- Pattern Summary:
-- - Grand Master: Q1, Q2, Q3, Q4 (always available)
-- - Marco Bellini: Q1, Q3 (odd quarters - Pre Football)
-- - Hans Müller: Q2, Q4 (even quarters - Youth Football)
-- - Diego Rodríguez: Q1, Q2 (first half only - Amateur Football)
-- - James Thompson: Q3, Q4 (second half only - Pro Football)
-- ============================================

BEGIN;

-- ============================================
-- 1. ADD Q3 AND Q4 FOR GRAND MASTER
-- ============================================

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q3', true, 'Always available'
FROM users u WHERE u.email = 'grandmaster@lfa.com';

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q4', true, 'Always available'
FROM users u WHERE u.email = 'grandmaster@lfa.com';

-- ============================================
-- 2. MARCO BELLINI - Q1, Q3 (Odd Quarters)
-- ============================================

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q1', true, 'Pre Football Coach - Spring season'
FROM users u WHERE u.email = 'marco.bellini@lfa.com';

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q3', true, 'Pre Football Coach - Autumn season'
FROM users u WHERE u.email = 'marco.bellini@lfa.com';

-- ============================================
-- 3. HANS MÜLLER - Q2, Q4 (Even Quarters)
-- ============================================

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q2', true, 'Youth Football Coach - Summer season'
FROM users u WHERE u.email = 'hans.mueller@lfa.com';

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q4', true, 'Youth Football Coach - Winter season'
FROM users u WHERE u.email = 'hans.mueller@lfa.com';

-- ============================================
-- 4. DIEGO RODRÍGUEZ - Q1, Q2 (First Half Only)
-- ============================================

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q1', true, 'Amateur Football Coach - First half availability'
FROM users u WHERE u.email = 'diego.rodriguez@lfa.com';

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q2', true, 'Amateur Football Coach - First half availability'
FROM users u WHERE u.email = 'diego.rodriguez@lfa.com';

-- ============================================
-- 5. JAMES THOMPSON - Q3, Q4 (Second Half Only)
-- ============================================

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q3', true, 'Pro Football Coach - Second half availability'
FROM users u WHERE u.email = 'james.thompson@lfa.com';

INSERT INTO instructor_availability_windows (instructor_id, year, time_period, is_available, notes)
SELECT u.id, 2026, 'Q4', true, 'Pro Football Coach - Second half availability'
FROM users u WHERE u.email = 'james.thompson@lfa.com';

COMMIT;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check all instructor availability for 2026
SELECT
    u.name,
    u.email,
    iaw.year,
    iaw.time_period,
    iaw.is_available,
    iaw.notes
FROM instructor_availability_windows iaw
JOIN users u ON iaw.instructor_id = u.id
WHERE u.role = 'INSTRUCTOR' AND iaw.year = 2026
ORDER BY u.name, iaw.time_period;

-- Summary: Count available quarters per instructor
SELECT
    u.name,
    COUNT(iaw.id) as total_quarters_available,
    STRING_AGG(iaw.time_period, ', ' ORDER BY iaw.time_period) as available_quarters
FROM users u
LEFT JOIN instructor_availability_windows iaw ON u.id = iaw.instructor_id AND iaw.year = 2026 AND iaw.is_available = true
WHERE u.role = 'INSTRUCTOR'
GROUP BY u.id, u.name
ORDER BY u.name;
