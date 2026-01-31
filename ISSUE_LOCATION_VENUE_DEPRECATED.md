# 🎫 NEW ISSUE: Fix deprecated location_venue attribute in session generator

**Status**: OPEN (Next Sprint)
**Priority**: Medium
**Created**: 2026-01-31
**Component**: Tournament Session Generation
**Sprint**: Q1 2026 - Week 5

---

## Issue Summary

**Title**: Session generation fails with AttributeError on deprecated location_venue field

**Severity**: Medium (blocks full sandbox flow completion after Step 1)

**Component**: League Generator / Session Generation

**Reported**: During sandbox enrollment fix validation testing

**Error Message**:
```python
AttributeError: 'Semester' object has no attribute 'location_venue'
```

---

## Error Details

**Stack Trace**:
```python
File "app/services/tournament/session_generation/session_generator.py", line 123, in generate_sessions
    sessions = self.league_generator.generate(
        tournament=tournament,
        tournament_type=tournament_type,
        player_count=player_count,
        parallel_fields=parallel_fields,
        session_duration=session_duration_minutes,
        break_minutes=break_minutes
    )

File "app/services/tournament/session_generation/formats/league_generator.py", line 47, in generate
    sessions = self._generate_head_to_head_pairings(
        tournament, tournament_type, player_count, parallel_fields, session_duration, break_minutes
    )

File "app/services/tournament/session_generation/formats/league_generator.py", line 163, in _generate_head_to_head_pairings
    'location': tournament.location_venue or 'TBD',
                ^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'Semester' object has no attribute 'location_venue'
```

**Failing Code**: [app/services/tournament/session_generation/formats/league_generator.py:163](app/services/tournament/session_generation/formats/league_generator.py#L163)

---

## Root Cause Analysis

The `Semester` model underwent location field refactoring (P2), replacing deprecated fields with FK relationships:

**Deprecated Fields** (removed from model):
- `location_venue`
- `location_city`
- `location_address`

**Current Fields** (P2 refactoring):
- `location_id` → FK to `locations` table
- `campus_id` → FK to `campuses` table

**Problem**: Session generators still reference deprecated `location_venue` attribute

---

## Current State

### Semester Model (app/models/semester.py:72-80)
```python
# 📍 LOCATION FIELDS (for semester-level location)
# NEW: Use campus_id FK for most specific location
campus_id = Column(Integer, ForeignKey('campuses.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment="FK to campuses table (most specific location - preferred)")

# Use location_id FK instead of denormalized city/venue/address fields
location_id = Column(Integer, ForeignKey('locations.id', ondelete='SET NULL'),
                    nullable=True, index=True,
                    comment="FK to locations table")
```

**Relationships**:
```python
campus = relationship("Campus", foreign_keys=[campus_id], backref="semesters")
location = relationship("Location", foreign_keys=[location_id], backref="semesters")
```

---

## Affected Files

Search for `location_venue` usage:

```bash
grep -rn "location_venue" app/services/tournament/session_generation/
```

**Files to Fix**:
1. `app/services/tournament/session_generation/formats/league_generator.py`
2. `app/services/tournament/session_generation/formats/knockout_generator.py` (potentially)
3. `app/services/tournament/session_generation/formats/swiss_generator.py` (potentially)
4. `app/services/tournament/session_generation/formats/group_knockout_generator.py` (potentially)
5. `app/services/tournament/session_generation/formats/individual_ranking_generator.py` (potentially)

---

## Proposed Solution

### Option A: Use location relationship (Preferred)

```python
# BEFORE (league_generator.py:163)
'location': tournament.location_venue or 'TBD',

# AFTER
'location': tournament.location.venue if tournament.location else 'TBD',
```

**Pros**: Uses proper FK relationship, type-safe
**Cons**: Requires eager loading or N+1 query handling

### Option B: Use campus relationship (Most specific)

```python
'location': tournament.campus.venue if tournament.campus else (
    tournament.location.venue if tournament.location else 'TBD'
)
```

**Pros**: Provides most specific location, follows P2 refactoring intent
**Cons**: More complex fallback chain

### Option C: Add @property for backward compatibility

```python
# In app/models/semester.py
@property
def location_venue(self) -> str:
    """Backward compatibility property for location venue"""
    if self.campus:
        return self.campus.venue
    if self.location:
        return self.location.venue
    return 'TBD'
```

**Pros**: Minimal changes to generators, maintains API compatibility
**Cons**: Hides refactoring intent, may encourage deprecated patterns

---

## Recommended Approach

**Option A** (Use location relationship) with eager loading optimization:

1. Update all session generators to use `tournament.location.venue`
2. Add eager loading in `TournamentSessionGenerator.generate_sessions()`:
   ```python
   tournament = self.tournament_repo.get_or_404(tournament_id)
   # Eager load relationships to avoid N+1
   db.refresh(tournament, ['location', 'campus'])
   ```

3. Add null-safe accessor:
   ```python
   def get_location_venue(tournament: Semester) -> str:
       """Get tournament venue with fallback chain"""
       if tournament.campus and hasattr(tournament.campus, 'venue'):
           return tournament.campus.venue
       if tournament.location and hasattr(tournament.location, 'venue'):
           return tournament.location.venue
       return 'TBD'
   ```

---

## Implementation Checklist

- [ ] Search all session generators for `location_venue` references
- [ ] Replace with proper FK relationship access
- [ ] Add eager loading to prevent N+1 queries
- [ ] Create helper function for location fallback logic
- [ ] Update tests to verify location data in generated sessions
- [ ] Validate with sandbox flow end-to-end
- [ ] Check for similar deprecated field usage (location_city, location_address)

---

## Testing Plan

1. **Unit Test**: Test location fallback logic
   - Campus set → returns campus.venue
   - Only location set → returns location.venue
   - Neither set → returns 'TBD'

2. **Integration Test**: Full sandbox flow
   - Create tournament with location_id
   - Generate sessions
   - Verify session location field populated correctly

3. **Regression Test**: Existing tournaments
   - Query existing tournaments with sessions
   - Verify location data accessible via new approach

---

## Dependencies

**Blocked By**: None
**Blocks**:
- Full sandbox flow completion
- Session generation for tournaments with location data

**Related Issues**:
- [RESOLVED] Sandbox enrollment fix (0f01004)

---

## Estimated Effort

**Time**: 2-3 hours
- Code changes: 1 hour
- Testing: 1 hour
- Documentation: 30 minutes

**Complexity**: Low-Medium
- Straightforward field migration
- Multiple files to update
- Needs careful null handling

---

## Acceptance Criteria

✅ Session generation completes without AttributeError
✅ Location data correctly populated in generated sessions
✅ No N+1 query issues (eager loading works)
✅ Backward compatibility maintained for existing tournaments
✅ All session generator formats updated (League, Knockout, Swiss, etc.)

---

**Created By**: Claude Sonnet 4.5
**Date**: 2026-01-31
**Related Commit**: 0f01004 (sandbox enrollment fix)
**Sprint**: Next (Q1 2026 - Week 5)
