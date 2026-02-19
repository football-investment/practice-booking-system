-- ============================================================================
-- CLEANUP SCRIPT: Remove Duplicate Tournament Rewards
-- ============================================================================
-- Date: 2026-02-01
-- Purpose: Clean up duplicate reward transactions caused by multiple
--          reward distribution runs before idempotency protection was added
--
-- Affected Tournaments:
-- - Tournament 220: Sprint Challenge Favela 🇧🇷 BR (16 rewards for 8 players)
-- - Tournament 221: LFA ⚡ Speed test (24 rewards for 8 players)
--
-- CRITICAL: This script will DELETE duplicate transactions and RECALCULATE
--           user credit/XP balances. Execute in a transaction!
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Backup current state (for audit trail)
-- ============================================================================

-- Check current state before cleanup
SELECT
    'BEFORE CLEANUP' as stage,
    tournament_id,
    COUNT(*) as transaction_count,
    SUM(amount) as total_credits
FROM credit_transactions
WHERE semester_id IN (220, 221)
  AND transaction_type = 'TOURNAMENT_REWARD'
GROUP BY tournament_id
ORDER BY tournament_id;

-- ============================================================================
-- STEP 2: Identify correct ranking records (keep only one per user)
-- ============================================================================

-- Tournament 220: Keep ranks #1-8 (IDs 738-745)
-- Delete ranks #9-16 (duplicate entries)

-- Tournament 221: Keep ranks #1-8 (IDs 754-761)
-- Delete ranks #9-16 (IDs 746-753, duplicate entries)

SELECT 'Duplicate rankings to delete:' as info;
SELECT id, tournament_id, user_id, rank, points
FROM tournament_rankings
WHERE tournament_id = 220 AND rank > 8
ORDER BY rank;

SELECT id, tournament_id, user_id, rank, points
FROM tournament_rankings
WHERE tournament_id = 221 AND rank > 8
ORDER BY rank;

-- ============================================================================
-- STEP 3: Calculate credits/XP to refund (duplicates only)
-- ============================================================================

-- For each user, calculate how much they received in DUPLICATE transactions
-- (We'll keep the FIRST correct transaction, delete the rest)

SELECT
    'Duplicate credits to remove (Tournament 220):' as info,
    ct.user_id,
    u.name,
    COUNT(*) as transaction_count,
    SUM(ct.amount) as total_duplicate_credits
FROM credit_transactions ct
JOIN users u ON ct.user_id = u.id
WHERE ct.semester_id = 220
  AND ct.transaction_type = 'TOURNAMENT_REWARD'
  -- Keep only the FIRST transaction per user (earliest created_at)
  AND ct.id NOT IN (
      SELECT MIN(id)
      FROM credit_transactions
      WHERE semester_id = 220
        AND transaction_type = 'TOURNAMENT_REWARD'
      GROUP BY user_id
  )
GROUP BY ct.user_id, u.name
ORDER BY ct.user_id;

-- ============================================================================
-- STEP 4: DELETE duplicate ranking records
-- ============================================================================

-- Tournament 220: Delete ranks #9-16
DELETE FROM tournament_rankings
WHERE tournament_id = 220 AND rank > 8;

-- Tournament 221: Delete ranks #9-16
DELETE FROM tournament_rankings
WHERE tournament_id = 221 AND rank > 8;

-- ============================================================================
-- STEP 5: DELETE duplicate credit transactions (keep only FIRST per user)
-- ============================================================================

-- Tournament 220: Delete all except the earliest transaction per user
DELETE FROM credit_transactions
WHERE semester_id = 220
  AND transaction_type = 'TOURNAMENT_REWARD'
  AND id NOT IN (
      SELECT MIN(id)
      FROM credit_transactions
      WHERE semester_id = 220
        AND transaction_type = 'TOURNAMENT_REWARD'
      GROUP BY user_id
  );

-- Tournament 221: Delete all except the earliest transaction per user
DELETE FROM credit_transactions
WHERE semester_id = 221
  AND transaction_type = 'TOURNAMENT_REWARD'
  AND id NOT IN (
      SELECT MIN(id)
      FROM credit_transactions
      WHERE semester_id = 221
        AND transaction_type = 'TOURNAMENT_REWARD'
      GROUP BY user_id
  );

-- ============================================================================
-- STEP 6: DELETE duplicate XP transactions
-- ============================================================================

DELETE FROM xp_transactions
WHERE semester_id = 220
  AND transaction_type = 'TOURNAMENT_REWARD'
  AND id NOT IN (
      SELECT MIN(id)
      FROM xp_transactions
      WHERE semester_id = 220
        AND transaction_type = 'TOURNAMENT_REWARD'
      GROUP BY user_id
  );

DELETE FROM xp_transactions
WHERE semester_id = 221
  AND transaction_type = 'TOURNAMENT_REWARD'
  AND id NOT IN (
      SELECT MIN(id)
      FROM xp_transactions
      WHERE semester_id = 221
        AND transaction_type = 'TOURNAMENT_REWARD'
      GROUP BY user_id
  );

-- ============================================================================
-- STEP 7: RECALCULATE user balances
-- ============================================================================

-- This requires RECALCULATING balances from ALL transactions
-- (Cannot simply subtract duplicates due to balance_after snapshot being wrong)

-- For each affected user, recalculate credit_balance from scratch
WITH user_credit_totals AS (
    SELECT
        user_id,
        SUM(CASE
            WHEN transaction_type IN ('PURCHASE', 'ADMIN_DEDUCTION', 'SESSION_BOOKING', 'TOURNAMENT_ENROLLMENT')
            THEN -amount  -- Deductions are negative
            ELSE amount   -- Credits/refunds are positive
        END) as correct_balance
    FROM credit_transactions
    WHERE user_id IN (4, 5, 6, 7, 13, 14, 15, 16)  -- Affected users
    GROUP BY user_id
)
UPDATE users u
SET credit_balance = uct.correct_balance
FROM user_credit_totals uct
WHERE u.id = uct.user_id;

-- Recalculate XP balances
WITH user_xp_totals AS (
    SELECT
        user_id,
        SUM(amount) as correct_xp_balance
    FROM xp_transactions
    WHERE user_id IN (4, 5, 6, 7, 13, 14, 15, 16)
    GROUP BY user_id
)
UPDATE users u
SET xp_balance = uxt.correct_xp_balance
FROM user_xp_totals uxt
WHERE u.id = uxt.user_id;

-- ============================================================================
-- STEP 8: Verify cleanup
-- ============================================================================

SELECT
    'AFTER CLEANUP' as stage,
    tournament_id,
    COUNT(*) as transaction_count,
    SUM(amount) as total_credits
FROM credit_transactions
WHERE semester_id IN (220, 221)
  AND transaction_type = 'TOURNAMENT_REWARD'
GROUP BY tournament_id
ORDER BY tournament_id;

-- Should show:
-- Tournament 220: 8 transactions (one per player)
-- Tournament 221: 8 transactions (one per player)

SELECT
    'Remaining rankings (should be 8 per tournament):' as info,
    tournament_id,
    COUNT(*) as ranking_count
FROM tournament_rankings
WHERE tournament_id IN (220, 221)
GROUP BY tournament_id;

-- ============================================================================
-- COMMIT or ROLLBACK
-- ============================================================================

-- REVIEW OUTPUT ABOVE BEFORE COMMITTING!
-- If everything looks correct:
-- COMMIT;

-- If something went wrong:
-- ROLLBACK;

SELECT 'Script completed. Review output and COMMIT or ROLLBACK.' as status;
