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

### Location Model (app/models/location.py:31-43)
```python
class Location(Base):
    """LFA Education Center locations (city-level)"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, unique=True)
    venue = Column(String(200), nullable=True)  # ⚠️ DEPRECATED - moved to Campus model
    address = Column(String(500), nullable=True)
    # ... other fields
```

**⚠️ Important**: `Location.venue` is also DEPRECATED (will be moved to Campus model)

### Campus Model (app/models/campus.py:20-33)
```python
class Campus(Base):
    """Campus/Venue model - specific facility within a location"""
    __tablename__ = "campuses"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "Buda Campus"
    venue = Column(String, nullable=True)  # ✅ Venue info here
    address = Column(String, nullable=True)
    # ... other fields
```

**Hierarchy**:
```
Location (City)
  └── Campus (Venue/Facility)
        └── Session (held at Campus)
```

**Recommended Fallback Chain**:
1. `tournament.campus.venue` (most specific) ✅
2. `tournament.location.city` (fallback to city name) ✅
3. `'TBD'` (if neither set)

---

## Affected Files

### ✅ Investigation Complete (2026-01-31)

**Search Command**:
```bash
grep -rn "location_venue" app/services/tournament/session_generation/ --include="*.py"
```

**Results**: **12 occurrences** across **5 files**

**Complete Usage Map**:

1. **league_generator.py** (2 occurrences)
   - Line 78: Individual ranking format session
   - Line 163: Head-to-head match session

2. **knockout_generator.py** (2 occurrences)
   - Line 94: Knockout match session
   - Line 135: Finals/playoff session

3. **swiss_generator.py** (2 occurrences)
   - Line 90: Swiss round session
   - Line 144: Swiss playoff session

4. **group_knockout_generator.py** (5 occurrences)
   - Line 123: Group stage match
   - Line 166: Group stage match (variant)
   - Line 225: Knockout stage match
   - Line 308: Finals match
   - Line 354: Playoff match

5. **individual_ranking_generator.py** (1 occurrence)
   - Line 88: Individual performance session

**Pattern**: All usages follow same format:
```python
'location': tournament.location_venue or 'TBD',
```

---

## Proposed Solution

### ✅ Investigation Findings (2026-01-31)

**Total Changes Required**: 12 occurrences across 5 files

**Current Pattern** (all 12 locations):
```python
'location': tournament.location_venue or 'TBD',
```

**Decision Matrix**:

| Option | Changes | N+1 Risk | Complexity | Refactoring Intent |
|--------|---------|----------|------------|-------------------|
| A: @property | 0 (backward compat) | Low | Low | ❌ Hides migration |
| B: location.city | 12 | Medium | Low | ⚠️ Less specific |
| C: campus.venue fallback | 12 | High | Medium | ✅ Best practice |

---

### Option A: Add @property (Quick Fix)

```python
# In app/models/semester.py
@property
def location_venue(self) -> str:
    """Backward compatibility property for location venue"""
    if self.campus and self.campus.venue:
        return self.campus.venue
    if self.location and self.location.city:
        return self.location.city
    return 'TBD'
```

**Pros**:
- Zero generator changes required
- Maintains API compatibility
- Quick to implement (< 30 min)

**Cons**:
- Hides P2 refactoring intent
- May encourage continued use of deprecated pattern
- Doesn't require eager loading awareness

**⚠️ Note**: Location.venue is ALSO deprecated, so can't use it

---

### Option B: Use campus.venue with Fallback (Recommended)

```python
# BEFORE (all 12 locations)
'location': tournament.location_venue or 'TBD',

# AFTER
'location': get_tournament_venue(tournament),
```

**Helper function**:
```python
def get_tournament_venue(tournament: Semester) -> str:
    """Get tournament venue with proper fallback chain"""
    if tournament.campus:
        if tournament.campus.venue:
            return tournament.campus.venue
        if tournament.campus.name:
            return f"{tournament.campus.name} ({tournament.campus.location.city})"

    if tournament.location:
        return tournament.location.city  # Fallback to city name

    return 'TBD'
```

**Pros**:
- Follows P2 refactoring intent
- Most specific location information
- Centralized logic (DRY)
- Explicit eager loading requirement

**Cons**:
- Requires changes to all 12 locations
- Need eager loading to prevent N+1 queries
- More implementation effort (2-3 hours)

---

## Recommended Approach

**Option B** (campus.venue fallback) with eager loading optimization:

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

### ✅ Phase 1: Investigation (COMPLETE)
- [x] Search all session generators for `location_venue` references → 12 found
- [x] Identify all affected files → 5 files mapped
- [x] Document current location access patterns → All use same pattern
- [x] Review Location/Campus model structure → Hierarchy documented
- [x] Determine recommended approach → Option B (helper function)

### ⏳ Phase 2: Implementation (PENDING)
- [ ] Create `get_tournament_venue()` helper function
- [ ] Update league_generator.py (2 locations)
- [ ] Update knockout_generator.py (2 locations)
- [ ] Update swiss_generator.py (2 locations)
- [ ] Update group_knockout_generator.py (5 locations)
- [ ] Update individual_ranking_generator.py (1 location)
- [ ] Add eager loading in TournamentSessionGenerator.generate_sessions()
- [ ] Verify no other deprecated location field usage

### ⏳ Phase 3: Testing (PENDING)
- [ ] Unit test: Helper function fallback logic
- [ ] Integration test: Sandbox flow with campus.venue
- [ ] Integration test: Sandbox flow with location.city fallback
- [ ] Regression test: Verify existing tournaments
- [ ] Validate session generation completes without AttributeError

### ⏳ Phase 4: Documentation (PENDING)
- [ ] Update ISSUE_LOCATION_VENUE_DEPRECATED.md with resolution
- [ ] Document eager loading requirements
- [ ] Create commit with clear message
- [ ] Update ACTIVE_SPRINT.md progress

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

### ✅ Revised Estimate (Post-Investigation)

**Total Time**: 2.5-3 hours

**Breakdown**:
- ✅ Investigation: 30 min (COMPLETE)
- ⏳ Helper function: 20 min
- ⏳ Update 5 generators (12 locations): 40 min
- ⏳ Eager loading: 15 min
- ⏳ Testing: 45 min
- ⏳ Documentation: 30 min

**Complexity**: Medium
- ✅ Pattern is consistent across all 12 locations (simplifies implementation)
- ⚠️ 5 separate files need changes (requires careful testing)
- ⚠️ Eager loading critical to prevent N+1 queries
- ⚠️ Need null-safe fallback chain

**Risk Assessment**:
- 🟢 Low Risk: All usages follow same pattern
- 🟡 Medium Risk: Need to ensure eager loading works
- 🟡 Medium Risk: Testing all 5 generator formats

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
