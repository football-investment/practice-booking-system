# DB Schema Fixes — Tournament Lifecycle E2E Tests

**Date:** 2026-02-21
**Context:** E2E test stabilization - Tournament Lifecycle block
**Issue:** SQLAlchemy models out of sync with DB schema

---

## Applied Manual Schema Fixes

### 1. semester_enrollments.tournament_checked_in_at
```sql
ALTER TABLE semester_enrollments
ADD COLUMN IF NOT EXISTS tournament_checked_in_at TIMESTAMP WITH TIME ZONE NULL;
```
**Purpose:** Pre-tournament check-in timestamp (player confirms attendance)
**Model Reference:** `app/models/semester_enrollment.py:89`

### 2. tournament_participations.skill_rating_delta
```sql
ALTER TABLE tournament_participations
ADD COLUMN IF NOT EXISTS skill_rating_delta FLOAT DEFAULT 0.0;
```
**Purpose:** Skill rating change after tournament completion
**Model Reference:** `app/models/tournament_participation.py` (model file location TBD)

### 3. xp_transactions.idempotency_key
```sql
ALTER TABLE xp_transactions
ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100) UNIQUE NULL;
```
**Purpose:** Prevent duplicate XP transactions (idempotency guarantee)
**Model Reference:** `app/models/xp_transaction.py` (model file location TBD)

---

## Root Cause

**Migration System Not Running:**
- Alembic migrations exist (`alembic/versions/2026_02_21_0859-1ec11c73ea62_squashed_baseline_schema.py`)
- But `alembic current` shows no applied migrations
- DB was likely created manually or from old schema dump
- Models evolved but DB schema wasn't updated

---

## Recommended Solution

**Option A: Run Full Migration (Preferred)**
```bash
# Check current state
alembic current

# Apply all migrations
alembic upgrade head

# Verify
alembic current
```

**Option B: Continue Manual Fixes**
- Monitor backend error logs for missing columns
- Add columns via manual ALTER TABLE statements
- Document each fix in this file

---

## Known Remaining Issues

**Session Generation 500 Error:**
- Status: Database error during session generation
- Likely: Additional schema mismatches in `game_sessions` or related tables
- Next: Check backend logs or continue manual schema fixes

---

## Future Prevention

1. **Ensure Alembic migrations run in all environments**
2. **Add migration check to CI/CD pipeline**
3. **Document schema changes in migration files, not manual SQL**
4. **Periodic schema drift detection script**
