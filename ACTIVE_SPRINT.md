# 🏃 ACTIVE SPRINT: Location Venue Migration

**Sprint Start**: 2026-01-31
**Sprint ID**: 2026-W05-location-venue
**Status**: 🔄 IN PROGRESS

---

## 🎯 Sprint Goal

**Single Focus**: Fix deprecated `location_venue` attribute in session generators

**Scope**: Location field migration ONLY - NO scope creep

---

## 📋 Active Ticket

### ISSUE_LOCATION_VENUE_DEPRECATED.md

**Priority**: Medium
**Component**: Tournament Session Generation
**Estimated**: 2-3 hours

**Problem**:
```python
AttributeError: 'Semester' object has no attribute 'location_venue'
```

**Goal**: Replace all `tournament.location_venue` references with proper FK relationship access

**Success Criteria**:
- ✅ Session generation completes without AttributeError
- ✅ Location data correctly populated in generated sessions
- ✅ No N+1 query issues (eager loading works)
- ✅ All session generator formats updated

---

## 🚫 Out of Scope (NO Scope Creep)

**Explicitly EXCLUDED from this sprint**:
- ❌ Tournament terminology refactoring
- ❌ Sandbox workflow improvements beyond location fix
- ❌ Performance optimizations (unless directly related to location queries)
- ❌ UI changes
- ❌ Game preset modifications
- ❌ Test infrastructure changes
- ❌ Documentation updates (except location fix documentation)

**If discovered during work**:
- Create separate ticket for next sprint
- Do NOT implement in current sprint
- Document as follow-up work

---

## 📊 Progress Tracking

### Phase 1: Investigation ✅ COMPLETE
- [x] Search all session generators for `location_venue` usage → **12 occurrences found**
- [x] Identify all affected files → **5 files mapped**
- [x] Document current location access patterns → **All use same pattern**

**Key Findings**:
- **12 total occurrences** across **5 generator files**
- **league_generator.py**: 2 occurrences (lines 78, 163)
- **knockout_generator.py**: 2 occurrences (lines 94, 135)
- **swiss_generator.py**: 2 occurrences (lines 90, 144)
- **group_knockout_generator.py**: 5 occurrences (lines 123, 166, 225, 308, 354)
- **individual_ranking_generator.py**: 1 occurrence (line 88)
- **Pattern**: All use `tournament.location_venue or 'TBD'`
- **Recommended Fix**: Helper function with `campus.venue → location.city → 'TBD'` fallback

### Phase 2: Implementation ⏳ READY TO START
- [ ] Create `get_tournament_venue()` helper function
- [ ] Update league_generator.py (2 locations)
- [ ] Update knockout_generator.py (2 locations)
- [ ] Update swiss_generator.py (2 locations)
- [ ] Update group_knockout_generator.py (5 locations)
- [ ] Update individual_ranking_generator.py (1 location)
- [ ] Add eager loading to prevent N+1 queries

### Phase 3: Testing ⏳ PENDING
- [ ] Unit test: Helper function fallback logic
- [ ] Integration test: Sandbox flow with campus.venue
- [ ] Integration test: Sandbox flow with location.city fallback
- [ ] Validate session generation completes without AttributeError

### Phase 4: Documentation ⏳ PENDING
- [ ] Update ISSUE_LOCATION_VENUE_DEPRECATED.md with final resolution
- [ ] Create commit with investigation findings
- [ ] Create commit with implementation
- [ ] Archive sprint when complete

---

## ⏱️ Time Tracking

**Estimated**: 2-3 hours
**Actual**: TBD

**Breakdown**:
- Investigation: 30 min
- Code changes: 1 hour
- Testing: 1 hour
- Documentation: 30 min

---

## 🎓 Sprint Discipline

**Rules for this sprint**:

1. **Single Ticket Focus**: Work ONLY on location_venue fix
2. **No Scope Creep**: If you find other issues, create tickets - don't fix them now
3. **Minimal Changes**: Change only what's necessary for the fix
4. **Test First**: Validate the fix works before moving on
5. **Document As You Go**: Update ticket with findings immediately

**If tempted to fix something else**:
1. Stop working on it
2. Create new ticket in root directory
3. Return to location_venue fix
4. Note the follow-up ticket in sprint summary

---

## 📁 Working Files

**Active**:
- `ISSUE_LOCATION_VENUE_DEPRECATED.md` (ticket being worked on)
- `ACTIVE_SPRINT.md` (this file - update as you progress)

**Read-Only**:
- `.sprints/2026-01-31-sandbox-enrollment/*` (archived sprint)

**Generated During Sprint**:
- Test scripts (if needed, delete after validation)
- Validation reports (if needed, archive at end)

---

## 🔄 Next Steps

**Immediate**: Start Phase 1 (Investigation)

```bash
# Search for location_venue usage
grep -rn "location_venue" app/services/tournament/session_generation/

# Document findings in ISSUE_LOCATION_VENUE_DEPRECATED.md
```

**After Investigation**: Proceed to Phase 2 (Implementation)

**After Implementation**: Proceed to Phase 3 (Testing)

**After Testing**: Close ticket and archive sprint

---

**Sprint Owner**: Claude Sonnet 4.5
**Started**: 2026-01-31
**Target Completion**: Same day (2-3 hours)
