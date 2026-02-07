# 🚨 CRITICAL BUG: Duplicate Reward Distribution

**Date**: 2026-02-01
**Priority**: P0 - CRITICAL
**Status**: 🔴 ACTIVE BUG

---

## Problem Summary

Tournament 220 ("Sprint Challenge Favela 🇧🇷 BR") distributed **DOUBLE REWARDS** to all 8 players, causing incorrect credit/XP balances.

### Impact:
- ❌ Players received 2x rewards (first from correct rank, then from duplicate rank)
- ❌ Leaderboard displays wrong totals (e.g., #7 received more than #1)
- ❌ Credit balances are inflated
- ❌ XP balances are inflated
- ❌ Financial integrity compromised

---

## Evidence

### Expected Behavior:
- **8 players** → **8 reward transactions** (1 per player)

### Actual Behavior:
- **8 players** → **16 reward transactions** (2 per player)
- Status history shows: `"rewards_count": 16` ✅ Confirms 16 iterations

### Example: Péter Nagy (user_id=5)

**Actual Ranking:**
- Rank: #7
- Result: 13.30s
- Expected: ~50-110 credits (participant tier)

**Received Instead:**
```
ID 919: 500 credits - "Rank #1 reward" (11:50:22)  ❌ WRONG RANK
ID 926:  50 credits - "Rank #8 reward" (11:50:22)  ❌ DUPLICATE
TOTAL: 550 credits (should be ~50-110)
```

---

## Transaction Timeline

### 11:43:33 - First Tournament (SANDBOX-TEST-LEAGUE)
Transactions ID 911-918: 8 transactions for "SANDBOX-TEST-LEAGUE-2026-02-01"
- **semester_id = 220** ⚠️ WRONG! This is a different tournament

### 11:50:22 - Second Distribution (Sprint Challenge)
Transactions ID 919-934: 16 transactions for "Sprint Challenge Favela 🇧🇷 BR"
- **semester_id = 220** ✅ CORRECT tournament
- **Ranks #1-16** ❌ BUT ONLY 8 PLAYERS EXIST!

---

## Root Cause Hypothesis

**Reward distribution loop ran TWICE on the same ranking data:**

1. **First iteration** (ranks #1-8): Correct assignments based on actual rankings
2. **Second iteration** (ranks #9-16): Duplicate assignments (cycling through players again)

### Possible Causes:

#### 1. **Duplicate Ranking Records**
```sql
-- Check if tournament_rankings has duplicates
SELECT user_id, COUNT(*)
FROM tournament_rankings
WHERE tournament_id = 220
GROUP BY user_id
HAVING COUNT(*) > 1;
```

#### 2. **Loop Logic Error in `distribute_tournament_rewards()`**
File: [app/api/api_v1/endpoints/tournaments/rewards.py:296-464](app/api/api_v1/endpoints/tournaments/rewards.py#L296-L464)

The loop iterates over:
```python
rankings = db.query(TournamentRanking).filter(
    TournamentRanking.tournament_id == tournament_id
).order_by(TournamentRanking.rank).all()

for ranking in rankings:
    # ... distribute rewards ...
```

**If `rankings` contains 16 records instead of 8**, the loop will run 16 times.

#### 3. **No Idempotency Protection**
The endpoint does NOT check if rewards were already distributed:
- No "already_distributed" flag
- No transaction uniqueness constraint
- No check for existing credit_transactions before creating new ones

---

## Data Integrity Issues

### Incorrect Rank Assignments:

| User | Actual Rank | Reward Rank #1 | Reward Rank #2 | Credits Received |
|------|-------------|----------------|----------------|------------------|
| Péter Nagy (5) | #7 (13.30s) | #1 (500cr) | #8 (50cr) | 550cr ❌ |
| Kylian Mbappé (13) | #1 (10.72s) | #2 (300cr) | #14 (50cr) | 350cr ❌ |
| Tibor Lénárt (7) | #2 (10.85s) | #3 (200cr) | #13 (50cr) | 250cr ❌ |
| Lamine Yamal (14) | #3 (11.45s) | #4 (50cr) | #10 (50cr) | 100cr ❌ |
| Martin Ødegaard (16) | #4 (11.68s) | #5 (50cr) | #11 (50cr) | 100cr ❌ |
| Cole Palmer (15) | #5 (11.79s) | #6 (50cr) | #15 (50cr) | 100cr ❌ |
| Péter Barna (6) | #6 (12.60s) | #7 (50cr) | #12 (50cr) | 100cr ❌ |
| Tamás Juhász (4) | #8 (14.85s) | #9 (50cr) | #16 (50cr) | 100cr ❌ |

**Observation:** Rank assignments are **shifted by 1 position** between actual and first reward!

---

## Immediate Actions Required

### 1. **Investigate Ranking Data**
```sql
-- Check for duplicate ranking records
SELECT id, tournament_id, user_id, rank, points
FROM tournament_rankings
WHERE tournament_id = 220
ORDER BY rank;

-- Expected: 8 rows (one per player)
-- If more than 8: DELETE duplicates before distribution
```

### 2. **Rollback Duplicate Rewards**
```sql
-- DELETE duplicate credit transactions (ranks #8-16)
DELETE FROM credit_transactions
WHERE id IN (926, 927, 928, 929, 930, 931, 932, 933, 934);

-- DELETE duplicate XP transactions
DELETE FROM xp_transactions
WHERE semester_id = 220
  AND transaction_type = 'TOURNAMENT_REWARD'
  AND description LIKE '%Rank #8%'
   OR description LIKE '%Rank #9%'
   OR description LIKE '%Rank #10%'
   -- ... (ranks 8-16)
```

### 3. **Recalculate User Balances**
```sql
-- Deduct duplicate credits from user accounts
UPDATE users
SET credit_balance = credit_balance - [duplicate_amount]
WHERE id IN (4, 5, 6, 7, 13, 14, 15, 16);

-- Deduct duplicate XP
UPDATE users
SET xp_balance = xp_balance - [duplicate_xp]
WHERE id IN (4, 5, 6, 7, 13, 14, 15, 16);
```

### 4. **Add Idempotency Protection**

**File**: [app/api/api_v1/endpoints/tournaments/rewards.py](app/api/api_v1/endpoints/tournaments/rewards.py)

```python
@router.post("/{tournament_id}/distribute-rewards", response_model=RewardDistributionResponse)
def distribute_tournament_rewards(...):
    # ✅ CHECK IF ALREADY DISTRIBUTED
    existing_rewards = db.query(CreditTransaction).filter(
        CreditTransaction.semester_id == tournament_id,
        CreditTransaction.transaction_type == TransactionType.TOURNAMENT_REWARD.value
    ).count()

    if existing_rewards > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rewards already distributed for this tournament ({existing_rewards} transactions exist). Use rollback endpoint to reset."
        )
```

---

## Fix Implementation Plan

### Phase 1: Data Cleanup (URGENT)
1. ✅ Analyze duplicate transaction data
2. ⏳ Delete duplicate credit/XP transactions
3. ⏳ Recalculate user balances
4. ⏳ Verify tournament_rankings has no duplicates

### Phase 2: Code Fix (HIGH PRIORITY)
1. ⏳ Add idempotency check to `distribute_tournament_rewards()`
2. ⏳ Add transaction uniqueness constraint
3. ⏳ Add `rewards_distributed_at` timestamp to prevent re-distribution
4. ⏳ Investigate why ranks are shifted by 1

### Phase 3: Testing
1. ⏳ Create new test tournament
2. ⏳ Verify rewards distributed correctly (8 players → 8 transactions)
3. ⏳ Verify idempotency protection works
4. ⏳ Verify balances match expected values

---

## Related Files

1. [app/api/api_v1/endpoints/tournaments/rewards.py](app/api/api_v1/endpoints/tournaments/rewards.py) - Reward distribution logic
2. [app/models/tournament_ranking.py](app/models/tournament_ranking.py) - Ranking model
3. [app/models/credit_transaction.py](app/models/credit_transaction.py) - Credit transaction model
4. [app/models/xp_transaction.py](app/models/xp_transaction.py) - XP transaction model

---

## User Feedback (Verbatim)

> "elemezzük alaposan hogy megfelelő e a kiosztás! nekem gyanus! '#7 Péter Nagy ↘️ aggression -6, ↗️ sprint_speed +6, ↘️ reactions -4, 125 XP, 560 credits' pedig:'#7 Péter Nagy 13,3'"

**Translation**: "Let's analyze carefully if the distribution is correct! It's suspicious to me! '#7 Péter Nagy ... 125 XP, 560 credits' but '#7 Péter Nagy 13.3s'"

**Status**: ✅ **USER'S SUSPICION WAS 100% CORRECT - CRITICAL BUG CONFIRMED**

---

**Bug Discoverer**: User (lovas.zoltan)
**Analyzed By**: Claude Code
**Next Steps**: Rollback duplicate transactions + Add idempotency protection
