/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system/scripts/create_diverse_instructors.py:16: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  now = datetime.utcnow()

-- ============================================
-- Instructor Diversification Script
-- Date: 2025-12-23
-- ============================================
--
-- Creates 4 new instructors with LFA_COACH specializations:
-- 1. Marco Bellini (Italian) - Level 1-2 (Pre Football Coach)
-- 2. Hans Müller (German) - Level 3-4 (Youth Football Coach)
-- 3. Diego Rodríguez (Spanish) - Level 5-6 (Amateur Football Coach)
-- 4. James Thompson (English) - Level 7-8 (Pro Football Coach)
--
-- Updates Grand Master with all 8 LFA_COACH levels
--
-- Password for all: coach123
-- ============================================

BEGIN;

-- ============================================
-- 1. CREATE INSTRUCTOR USERS
-- ============================================

-- Marco Bellini (Italian - Pre Football Coach specialist)
INSERT INTO users (name, email, password_hash, role, is_active, payment_verified, nda_accepted, parental_consent, created_at, updated_at)
VALUES (
    'Marco Bellini',
    'marco.bellini@lfa.com',
    '$2b$10$97KB7X332P85I62SnhC4Uu3nsnt1ZmpasR247Yc737fFjcQgJIFKa',
    'INSTRUCTOR',
    true,
    false,
    true,
    false,
    '2025-12-23 14:14:02.267217',
    '2025-12-23 14:14:02.267217'
);

-- Hans Müller (German - Youth Football Coach specialist)
INSERT INTO users (name, email, password_hash, role, is_active, payment_verified, nda_accepted, parental_consent, created_at, updated_at)
VALUES (
    'Hans Müller',
    'hans.mueller@lfa.com',
    '$2b$10$97KB7X332P85I62SnhC4Uu3nsnt1ZmpasR247Yc737fFjcQgJIFKa',
    'INSTRUCTOR',
    true,
    false,
    true,
    false,
    '2025-12-23 14:14:02.267217',
    '2025-12-23 14:14:02.267217'
);

-- Diego Rodríguez (Spanish - Amateur Football Coach specialist)
INSERT INTO users (name, email, password_hash, role, is_active, payment_verified, nda_accepted, parental_consent, created_at, updated_at)
VALUES (
    'Diego Rodríguez',
    'diego.rodriguez@lfa.com',
    '$2b$10$97KB7X332P85I62SnhC4Uu3nsnt1ZmpasR247Yc737fFjcQgJIFKa',
    'INSTRUCTOR',
    true,
    false,
    true,
    false,
    '2025-12-23 14:14:02.267217',
    '2025-12-23 14:14:02.267217'
);

-- James Thompson (English - Pro Football Coach specialist)
INSERT INTO users (name, email, password_hash, role, is_active, payment_verified, nda_accepted, parental_consent, created_at, updated_at)
VALUES (
    'James Thompson',
    'james.thompson@lfa.com',
    '$2b$10$97KB7X332P85I62SnhC4Uu3nsnt1ZmpasR247Yc737fFjcQgJIFKa',
    'INSTRUCTOR',
    true,
    false,
    true,
    false,
    '2025-12-23 14:14:02.267217',
    '2025-12-23 14:14:02.267217'
);

-- ============================================
-- 2. ADD LFA_COACH SPECIALIZATIONS
-- ============================================

-- Note: instructor_specializations stores TYPE only (LFA_COACH), not individual levels
-- The specific level qualifications (1-8) are documented in the notes field

-- Marco Bellini: LFA_COACH (Level 1-2 qualified - Pre Football Coach specialist)
INSERT INTO instructor_specializations (user_id, specialization, is_active, certified_at, notes)
SELECT u.id, 'LFA_COACH', true, '2025-12-23 14:14:02.267217', 'Qualified: Level 1-2 (Pre Football Coach - Asszisztens + Vezetőedző)'
FROM users u WHERE u.email = 'marco.bellini@lfa.com';

-- Hans Müller: LFA_COACH (Level 3-4 qualified - Youth Football Coach specialist)
INSERT INTO instructor_specializations (user_id, specialization, is_active, certified_at, notes)
SELECT u.id, 'LFA_COACH', true, '2025-12-23 14:14:02.267217', 'Qualified: Level 3-4 (Youth Football Coach - Asszisztens + Vezetőedző)'
FROM users u WHERE u.email = 'hans.mueller@lfa.com';

-- Diego Rodríguez: LFA_COACH (Level 5-6 qualified - Amateur Football Coach specialist)
INSERT INTO instructor_specializations (user_id, specialization, is_active, certified_at, notes)
SELECT u.id, 'LFA_COACH', true, '2025-12-23 14:14:02.267217', 'Qualified: Level 5-6 (Amateur Football Coach - Asszisztens + Vezetőedző)'
FROM users u WHERE u.email = 'diego.rodriguez@lfa.com';

-- James Thompson: LFA_COACH (Level 7-8 qualified - Pro Football Coach specialist)
INSERT INTO instructor_specializations (user_id, specialization, is_active, certified_at, notes)
SELECT u.id, 'LFA_COACH', true, '2025-12-23 14:14:02.267217', 'Qualified: Level 7-8 (PRO Football Coach - Asszisztens + Vezetőedző)'
FROM users u WHERE u.email = 'james.thompson@lfa.com';

-- ============================================
-- 3. UPDATE GRAND MASTER - ADD LFA_COACH (All 8 Levels)
-- ============================================

-- Grand Master gets LFA_COACH with all 8 levels qualified
INSERT INTO instructor_specializations (user_id, specialization, is_active, certified_at, notes)
SELECT u.id, 'LFA_COACH', true, '2025-12-23 14:14:02.267217', 'Master certification - All 8 levels (1-8) qualified'
FROM users u WHERE u.email = 'grandmaster@lfa.com';

COMMIT;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check all instructors
SELECT id, name, email, role, is_active FROM users WHERE role = 'INSTRUCTOR' ORDER BY id;

-- Check all instructor specializations
SELECT
    u.name,
    u.email,
    isp.specialization,
    isp.is_active,
    isp.notes
FROM instructor_specializations isp
JOIN users u ON isp.user_id = u.id
WHERE u.role = 'INSTRUCTOR'
ORDER BY u.name, isp.specialization;

-- Summary by instructor
SELECT
    u.name,
    u.email,
    COUNT(isp.id) as total_specializations,
    COUNT(CASE WHEN isp.is_active THEN 1 END) as active_specializations,
    STRING_AGG(isp.specialization, ', ' ORDER BY isp.specialization) as specializations
FROM users u
LEFT JOIN instructor_specializations isp ON u.id = isp.user_id
WHERE u.role = 'INSTRUCTOR'
GROUP BY u.id, u.name, u.email
ORDER BY u.name;

