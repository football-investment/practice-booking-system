# 🎯 EPIC: Complete Location Venue Cleanup

**Epic ID**: EPIC-2026-W05-location-venue-cleanup
**Created**: 2026-01-31
**Status**: 🟡 IN PROGRESS - Sprint 3 Active
**Priority**: Medium
**Owner**: Claude Sonnet 4.5

---

## Epic Summary

Complete migration from deprecated `location_venue` field to proper FK relationships (`campus.venue` / `location.city`) across the entire codebase.

**Context**: Sprint 2 (2026-01-31) fixed the critical AttributeError in session generators (12 occurrences). However, extensive usage remains in API endpoints, schemas, UI, and scripts.

---

## Background

### ✅ What's Done (Sprint 2)

**Scope**: Session Generation Module ONLY
- Fixed: `app/services/tournament/session_generation/` (12 occurrences)
- Solution: `get_tournament_venue()` helper with fallback chain
- Commits: baa4697, 1fc55b1, 233374c
- Archive: `.sprints/2026-01-31-location-venue/`

### ❌ What Remains

**Total Remaining**: 50+ occurrences across codebase

**Breakdown by Component**:
1. **Pydantic Schemas** (1 occurrence) - API contract
2. **API Endpoints** (15+ occurrences) - Backend responses
3. **Legacy Session Generator** (12 occurrences) - ORIGINAL file (deprecated?)
4. **Streamlit UI** (4 occurrences) - Frontend display
5. **Scripts/Dashboards** (10+ occurrences) - Admin tools
6. **Alembic Migrations** (6 occurrences) - Historical (read-only)

---

## Epic Goals

1. **Eliminate deprecated field usage** across all active code
2. **Maintain backward compatibility** during migration
3. **Update API contracts** (Pydantic schemas)
4. **Migrate UI components** to use new location access pattern
5. **Clean up legacy code** (tournament_session_generator_ORIGINAL.py)

---

## Sprint Breakdown

### Sprint 3: API Schema & Endpoints (CRITICAL PATH)
**Priority**: 🔴 HIGH
**Estimated**: 3-4 hours
**Scope**: API layer migration
**Status**: 🟡 ACTIVE - Investigation Phase
**Started**: 2026-01-31

**Active Documents**:
- [ACTIVE_SPRINT_3.md](ACTIVE_SPRINT_3.md) - Sprint progress tracking
- [ISSUE_LOCATION_VENUE_API.md](ISSUE_LOCATION_VENUE_API.md) - Issue tracking

**Tasks**:
- [ ] Update `app/schemas/semester.py` - Add `campus` and `location` relationships
- [ ] Migrate `app/api/api_v1/endpoints/periods/lfa_player_generators.py` (8 occurrences)
- [ ] Migrate `app/api/api_v1/endpoints/semester_generator.py` (1 occurrence)
- [ ] Migrate `app/api/web_routes/dashboard.py` (3 occurrences)
- [ ] Migrate `app/api/web_routes/admin.py` (7 occurrences)
- [ ] Add deprecation warning to old field
- [ ] Test API backward compatibility

**Acceptance Criteria**:
- API responses include both old (deprecated) and new location fields
- No breaking changes to existing API consumers
- Deprecation warning logged when old field accessed

---

### Sprint 4: Streamlit UI Migration
**Priority**: 🟡 MEDIUM
**Estimated**: 2-3 hours
**Scope**: Frontend components
**Status**: ⏳ BACKLOG - Awaiting Sprint 3 completion

**Tasks**:
- [ ] Migrate `streamlit_app/components/admin/overview_tab.py` (1 occurrence)
- [ ] Migrate `streamlit_app/components/semesters/semester_generation.py` (3 occurrences)
- [ ] Update UI to display campus.venue → location.city fallback
- [ ] Test UI rendering with both old and new data

**Acceptance Criteria**:
- UI displays location using proper fallback chain
- No visual regressions
- Works with both legacy and new data

---

### Sprint 5: Scripts & Tools Cleanup
**Priority**: 🟢 LOW
**Estimated**: 2 hours
**Scope**: Admin scripts and dashboards
**Status**: ⏳ BACKLOG - Awaiting Sprint 3 completion

**Tasks**:
- [ ] Migrate `scripts/dashboards/unified_workflow_dashboard.py` (9 occurrences)
- [ ] Migrate `scripts/quick_regenerate_tournament.py` (1 occurrence)
- [ ] Review `scripts/database/create_fresh_database.py` (1 occurrence)
- [ ] Test script execution

**Acceptance Criteria**:
- Scripts work with new location access pattern
- No runtime errors

---

### Sprint 6: Legacy Code Removal
**Priority**: 🟢 LOW
**Estimated**: 1 hour
**Scope**: Cleanup deprecated files
**Status**: ⏳ BACKLOG - Awaiting Sprint 3 completion

**Tasks**:
- [ ] Investigate `app/services/tournament_session_generator_ORIGINAL.py`
- [ ] Confirm file is deprecated/unused
- [ ] Remove or migrate 12 occurrences
- [ ] Update any references to ORIGINAL file

**Acceptance Criteria**:
- ORIGINAL file removed or fully migrated
- No broken imports

---

## Technical Strategy

### Migration Pattern

**Current (Deprecated)**:
```python
# Direct field access
location_venue = semester.location_venue
```

**New (Recommended)**:
```python
# Use helper function
from app.services.tournament.session_generation import get_tournament_venue
venue = get_tournament_venue(tournament)
```

**Alternative (API Responses)**:
```python
# Compute dynamically in schema
@property
def location_display(self) -> str:
    if self.campus and self.campus.venue:
        return self.campus.venue
    if self.location:
        return self.location.city
    return 'TBD'
```

---

### Backward Compatibility Strategy

**Phase 1**: Dual-field approach (recommended)
- Keep deprecated field in schemas (marked `@deprecated`)
- Populate both old and new fields in responses
- Log deprecation warnings when old field accessed

**Phase 2**: Deprecation notice (future)
- API documentation updated with migration guide
- Frontend switches to new fields
- Old field still returned but marked for removal

**Phase 3**: Complete removal (future)
- Remove deprecated field from schemas
- Remove database column (if exists)
- Update all consumers

---

## Risk Assessment

### High Risk Areas

1. **API Breaking Changes** 🔴
   - **Risk**: Existing API consumers break
   - **Mitigation**: Dual-field approach, deprecation warnings
   - **Testing**: Integration tests for all affected endpoints

2. **UI Rendering Issues** 🟡
   - **Risk**: Location data missing in UI
   - **Mitigation**: Proper fallback chain testing
   - **Testing**: Manual UI testing with various data scenarios

3. **Data Migration** 🟡
   - **Risk**: Tournaments with missing location data
   - **Mitigation**: Helper function handles None gracefully
   - **Testing**: Test with null location_id and null campus_id

---

## Success Metrics

**Completion Criteria**:
- ✅ 0 active `location_venue` references (excluding historical migrations)
- ✅ All API endpoints return location via proper relationships
- ✅ UI displays location using fallback chain
- ✅ No breaking changes to existing consumers
- ✅ Legacy code removed or migrated

**Performance**:
- No N+1 queries introduced (eager loading where needed)
- API response time unchanged

---

## Out of Scope

❌ **Not Included in This Epic**:
- Database column removal (requires separate migration epic)
- Historical Alembic migration files (read-only)
- External API consumers migration (they migrate on their timeline)

---

## Dependencies

**Blockers**: None (Sprint 2 complete)

**Related Work**:
- [Sprint 2] Session generator migration (COMPLETE)
- [P2 Refactoring] Location field migration (original refactoring)

---

## Timeline

**Estimated Total**: 8-10 hours (4 sprints)

**Recommended Schedule**:
- Sprint 3 (API): Week 5 or 6
- Sprint 4 (UI): Week 6
- Sprint 5 (Scripts): Week 6 or 7
- Sprint 6 (Legacy): Week 7

**Flexibility**: Non-critical, can be scheduled around higher priority work

---

## Notes

**Important Decisions**:
- Sprint 2 scope was CORRECT - fixed critical blocker only
- This Epic is comprehensive cleanup, not urgent
- Dual-field approach ensures zero downtime migration

**Follow-up Work**:
- After Epic complete, schedule database column removal
- Update API documentation with migration guide
- Communicate deprecation to API consumers

---

**Created By**: Claude Sonnet 4.5
**Date**: 2026-01-31
**Related Sprint**: 2026-01-31-location-venue (Sprint 2)
**Status**: Ready for sprint planning
