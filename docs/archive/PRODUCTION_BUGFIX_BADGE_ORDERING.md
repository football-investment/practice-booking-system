# Production Bugfix: CHAMPION Badge "No ranking data" Regression

## Bug Report
**Reported**: 2026-02-10
**Affected User**: `k1sqx1@f1rstteam.hu`
**Tournament**: SANDBOX-TEST-LEAGUE-2026-02-09
**Symptom**: User sees "No ranking data" despite CHAMPION badge having valid `badge_metadata: {"placement": 1, "total_participants": 8}`

## Root Cause

The CHAMPION guard in [performance_card.py](streamlit_app/components/tournaments/performance_card.py) was using `badges[0]` to read `badge_metadata`, but the API returns badges in **database order** (not priority order).

### The Bug (Lines 111-116, before fix):
```python
if badge_type == "CHAMPION" and not rank:
    if badges and len(badges) > 0:
        first_badge = badges[0]  # ❌ BUG: assumes CHAMPION is always first
        badge_metadata = first_badge.get('badge_metadata', {})
        if badge_metadata.get('placement'):
            rank = badge_metadata['placement']
```

### What Happened:
1. User earns 3 badges per tournament: `CHAMPION`, `PODIUM_FINISH`, `TOURNAMENT_PARTICIPANT`
2. API returns badges in arbitrary order (e.g., DB insertion order)
3. If `TOURNAMENT_PARTICIPANT` (with `badge_metadata=null`) comes before `CHAMPION` in the array:
   - `badges[0]` reads the TOURNAMENT_PARTICIPANT badge
   - `badge_metadata` is `null`
   - Guard silently fails → "No ranking data" shown
4. The component already computed `primary_badge` (sorted by priority), but fallback code ignored it

## The Fix

**Commit**: `2cbfce0` (previous commit fixed the guard logic, but this commit fixes badge ordering)

### Changes Made:

1. **Move `primary_badge` computation BEFORE fallbacks** (line 87-91)
2. **Use `primary_badge` for BOTH fallbacks** instead of `badges[0]`:
   - Total participants fallback (lines 94-98)
   - CHAMPION guard (lines 100-104)

### After Fix (Lines 87-104):
```python
# Get primary badge (highest priority) — MUST happen BEFORE fallbacks
primary_badge = _get_primary_badge(tournament_data.get('badges', []))
badge_type = primary_badge.get('badge_type') if primary_badge else None
badge_icon = get_badge_icon(badge_type) if badge_type else "🏅"
badge_title = get_badge_title(badge_type) if badge_type else "PARTICIPANT"

# Fallback: If metrics missing total_participants, try PRIMARY badge metadata
if not total_participants:
    if primary_badge:
        badge_metadata = primary_badge.get('badge_metadata', {})
        if badge_metadata and badge_metadata.get('total_participants'):
            total_participants = badge_metadata['total_participants']

# CRITICAL PRODUCT RULE: CHAMPION badge MUST have rank (force placement fallback from PRIMARY badge)
if badge_type == "CHAMPION" and not rank:
    if primary_badge:
        badge_metadata = primary_badge.get('badge_metadata', {})
        if badge_metadata and badge_metadata.get('placement'):
            rank = badge_metadata['placement']
```

## Verification

### Unit Test Coverage (15/15 passing in 0.14s)

**New regression test added**: `test_T15_champion_not_at_index_0_regression`

This test simulates the exact production scenario:
```python
tournament_participant = {
    "badge_type": "TOURNAMENT_PARTICIPANT",
    "badge_metadata": None,  # NULL in production DB
}
champion_badge = _champion_badge(placement=1, total_participants=8)

render_performance_card({
    "metrics": _minimal_metrics(rank=None, total_participants=None),
    "badges": [tournament_participant, champion_badge],  # CHAMPION NOT at index 0
})

# MUST show "#1 of 8 players", NOT "No ranking data"
```

### Production Data Verification

Query confirmed the affected user has valid CHAMPION badges with metadata:
```sql
SELECT tb.badge_type, tb.badge_metadata, u.email, s.code as semester_code
FROM tournament_badges tb
JOIN users u ON tb.user_id = u.id
JOIN semesters s ON tb.semester_id = s.id
WHERE u.email = 'k1sqx1@f1rstteam.hu'
ORDER BY s.code, tb.badge_type;
```

Result: Multiple CHAMPION badges with `{"placement": 1, "total_participants": 8}` — fix will work.

## Impact Assessment

**Severity**: HIGH (production user-facing regression)
**Scope**: All users with CHAMPION badges where `TOURNAMENT_PARTICIPANT` comes before `CHAMPION` in API response
**Fix Status**: VERIFIED (15/15 tests passing, including regression test)
**Deployment**: Ready (backward compatible, no breaking changes)

## Files Changed

- [streamlit_app/components/tournaments/performance_card.py](streamlit_app/components/tournaments/performance_card.py) (lines 85-116)
- [tests_e2e/test_performance_card_unit.py](tests_e2e/test_performance_card_unit.py) (new test T15)

## Lessons Learned

1. **Never assume array ordering from APIs** — always use business logic to determine priority
2. **Metadata fallbacks must use the PRIMARY badge** (highest priority), not `badges[0]`
3. **Unit tests must cover badge ordering scenarios** (T15 now guards this permanently)
4. **Production bugs that survive initial fixes** indicate missing test coverage for edge cases

## Next Steps

- [x] Fix applied
- [x] Regression test added (T15)
- [x] All 15 unit tests passing
- [ ] Deploy to production
- [ ] Verify fix on affected user's dashboard
- [ ] Monitor for similar issues on other badge types
