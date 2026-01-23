# Legacy Session Migration Guide

**Date**: 2026-01-22
**Issue**: Existing tournaments show old UI because `match_format` is NULL
**Solution**: Database migration + backend defaults

---

## Problem Description

### Symptom
When opening the Match Command Center for existing tournaments (created before 2026-01-22), the UI shows:
```
Format: INDIVIDUAL_RANKING • Scoring: PLACEMENT
```

But the assignment dropdowns and validation work correctly.

### Root Cause
Sessions created **before** the Match Structure implementation (2026-01-22) have:
- `match_format = NULL`
- `scoring_type = NULL`
- `structure_config = NULL`

The frontend correctly defaults to `INDIVIDUAL_RANKING`, but the database should be updated for consistency.

---

## Solution Implemented

### 1. Backend Default Values ✅

**Location**: `app/api/api_v1/endpoints/tournaments/instructor.py:1618-1620`

```python
"match_format": active_session.match_format or 'INDIVIDUAL_RANKING',
"scoring_type": active_session.scoring_type or 'PLACEMENT',
"structure_config": active_session.structure_config
```

**Result**: API always returns valid values, even for legacy sessions.

### 2. Database Migration ✅

**Executed**: 2026-01-22

```sql
UPDATE sessions
SET
    match_format = 'INDIVIDUAL_RANKING',
    scoring_type = 'PLACEMENT',
    structure_config = '{"ranking_criteria": "final_placement"}'::jsonb
WHERE match_format IS NULL;
```

**Result**: 30 sessions updated

### 3. Migration Script ✅

**Location**: `scripts/migrate_legacy_sessions.py`

**Usage**:
```bash
DATABASE_URL="postgresql://..." python scripts/migrate_legacy_sessions.py
```

**Features**:
- Shows count of sessions needing update
- Shows sample of sessions to be updated
- Asks for confirmation before proceeding
- Verifies update success
- Provides summary statistics

---

## Verification

### Before Migration
```sql
SELECT id, title, match_format, scoring_type
FROM sessions
WHERE semester_id = 13
LIMIT 3;

 id |                    title                    | match_format | scoring_type
----+---------------------------------------------+--------------+--------------
 38 | ... Group A - Round 1                       |              |
 39 | ... Group A - Round 2                       |              |
 40 | ... Group A - Round 3                       |              |
```

### After Migration
```sql
SELECT id, title, match_format, scoring_type
FROM sessions
WHERE semester_id = 13
LIMIT 3;

 id |                    title                    |    match_format    | scoring_type
----+---------------------------------------------+--------------------+--------------
 38 | ... Group A - Round 1                       | INDIVIDUAL_RANKING | PLACEMENT
 39 | ... Group A - Round 2                       | INDIVIDUAL_RANKING | PLACEMENT
 40 | ... Group A - Round 3                       | INDIVIDUAL_RANKING | PLACEMENT
```

---

## Testing Steps

### 1. Check Existing Tournament
1. Navigate to Match Command Center
2. Select existing tournament (ID: 13)
3. Verify format shows: `Format: INDIVIDUAL_RANKING • Scoring: PLACEMENT`
4. Mark attendance
5. Verify placement dropdowns appear
6. Assign placements
7. Submit results
8. Verify leaderboard updates correctly

### 2. Check New Tournament
1. Create new tournament (after 2026-01-22)
2. Sessions should have `match_format` set during generation
3. Verify UI renders correctly from the start

---

## Future Considerations

### Alembic Migration

For production deployments, create an Alembic migration:

```python
# alembic/versions/2026_01_22_XXXX_backfill_match_format.py

def upgrade() -> None:
    op.execute("""
        UPDATE sessions
        SET
            match_format = 'INDIVIDUAL_RANKING',
            scoring_type = 'PLACEMENT',
            structure_config = COALESCE(
                structure_config,
                '{"ranking_criteria": "final_placement"}'::jsonb
            )
        WHERE match_format IS NULL OR scoring_type IS NULL
    """)

def downgrade() -> None:
    # Optional: Set back to NULL if needed for rollback
    pass
```

### Session Generator Updates

All session generators now set `match_format` and `scoring_type`:

```python
# League tournament generator
sessions.append({
    'title': f'{tournament.name} - Ranking Round {round_num}',
    'match_format': 'INDIVIDUAL_RANKING',  # ✅ Always set
    'scoring_type': 'PLACEMENT',           # ✅ Always set
    'structure_config': {
        'expected_participants': player_count,
        'ranking_criteria': 'final_placement'
    }
})
```

**Result**: New tournaments will always have these fields populated.

---

## Backward Compatibility

### NULL Values Handled Gracefully

1. **API Layer**: Defaults to `INDIVIDUAL_RANKING` / `PLACEMENT`
2. **Frontend**: Defaults to `INDIVIDUAL_RANKING` / `PLACEMENT`
3. **ResultProcessor**: Accepts NULL and uses defaults

### Migration is Optional

The system works correctly even if sessions have NULL values:
- API provides defaults
- Frontend renders INDIVIDUAL_RANKING form
- Backend processes results correctly

However, **migrating is recommended** for:
- Data consistency
- Analytics queries
- Future features that may assume non-NULL values

---

## Troubleshooting

### "Format shows NULL in UI"

**Cause**: Frontend caching or API not returning defaults

**Solution**:
1. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+F5)
2. Check API response in browser DevTools
3. Verify backend default logic at line 1618

### "Submit button disabled"

**Cause**: Validation logic may be too strict

**Solution**:
1. Check console for JavaScript errors
2. Verify all participants have placements assigned
3. Check for duplicate placements

### "Results not submitting"

**Cause**: API validation or backend processing error

**Solution**:
1. Check backend logs for errors
2. Verify ResultProcessor handles NULL match_format
3. Check `/submit-results` endpoint response

---

## Summary

| Item | Status | Notes |
|------|--------|-------|
| Backend defaults | ✅ Complete | API line 1618-1620 |
| Database migration | ✅ Complete | 30 sessions updated |
| Migration script | ✅ Complete | `scripts/migrate_legacy_sessions.py` |
| Session generators | ✅ Complete | All generators updated |
| Frontend compatibility | ✅ Complete | Handles NULL gracefully |
| Documentation | ✅ Complete | This document |

**All legacy sessions now work correctly with the new Match Structure system!**
