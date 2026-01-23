-- Create 3 fully onboarded LFA Football Player students for tournament tests
-- Students: pwt.k1sqx1@f1stteam.hu, pwt.p3t1k3@f1stteam.hu, pwt.V4lv3rd3jr@f1stteam.hu

-- 1. Reset existing licenses (if any)
DELETE FROM user_licenses
WHERE user_id IN (
    SELECT id FROM users
    WHERE email IN ('pwt.k1sqx1@f1stteam.hu', 'pwt.p3t1k3@f1stteam.hu', 'pwt.V4lv3rd3jr@f1stteam.hu')
);

-- 2. Give each student 100 credits (enough for 1 specialization unlock)
UPDATE users
SET credit_balance = 100
WHERE email IN ('pwt.k1sqx1@f1stteam.hu', 'pwt.p3t1k3@f1stteam.hu', 'pwt.V4lv3rd3jr@f1stteam.hu');

-- 3. Create LFA_FOOTBALL_PLAYER licenses with onboarding completed
INSERT INTO user_licenses (user_id, specialization_type, current_level, max_achieved_level, started_at, payment_verified, payment_verified_at, is_active, onboarding_completed, renewal_cost, credit_balance, credit_purchased, created_at, updated_at)
SELECT
    u.id,
    'LFA_FOOTBALL_PLAYER',
    1,
    1,
    NOW(),
    TRUE,
    NOW(),
    TRUE,
    TRUE,  -- Onboarding completed!
    1000,  -- renewal_cost (required field)
    0,     -- credit_balance
    0,     -- credit_purchased
    NOW(),
    NOW()
FROM users u
WHERE u.email IN ('pwt.k1sqx1@f1stteam.hu', 'pwt.p3t1k3@f1stteam.hu', 'pwt.V4lv3rd3jr@f1stteam.hu');

-- 4. Verify creation
SELECT
    u.email,
    u.credit_balance,
    ul.specialization_type,
    ul.onboarding_completed,
    ul.payment_verified,
    ul.is_active
FROM users u
JOIN user_licenses ul ON u.id = ul.user_id
WHERE u.email IN ('pwt.k1sqx1@f1stteam.hu', 'pwt.p3t1k3@f1stteam.hu', 'pwt.V4lv3rd3jr@f1stteam.hu')
ORDER BY u.email;
