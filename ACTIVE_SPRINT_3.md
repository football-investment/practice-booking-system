# 🏃 ACTIVE SPRINT 3: API Schema & Endpoints Migration

**Sprint ID**: 2026-W05-location-venue-api
**Epic**: EPIC-2026-W05-location-venue-cleanup
**Started**: 2026-01-31
**Status**: 🟡 ACTIVE - Investigation Phase
**Priority**: 🔴 CRITICAL

---

## 📋 Sprint Goal

Migrate all `location_venue` usage in **API layer** (Pydantic schemas, endpoints, web routes) to use new location relationships.

**Scope**: 19 occurrences (Sprint 3 from BACKLOG_LOCATION_VENUE.md)

---

## 🎯 Sprint Scope (Strict Discipline)

### ✅ IN SCOPE
1. Pydantic Schema deprecation (1 occurrence)
2. LFA Player Generator endpoints (8 occurrences)
3. Semester Generator endpoint (1 occurrence)
4. Dashboard web route (3 occurrences)
5. Admin web route (7 occurrences)

### ❌ OUT OF SCOPE
- Streamlit UI (Sprint 4)
- Scripts/Dashboards (Sprint 5)
- Legacy generators (Sprint 6)
- Any refactoring beyond location_venue migration
- New features or improvements

---

## 📦 Deliverables

### Phase 1: Investigation (Current)
- [ ] Complete usage analysis for all 19 API occurrences
- [ ] Document migration strategy for each file
- [ ] Identify backward compatibility requirements
- [ ] Create commit with ONLY investigation documentation

### Phase 2: Schema Deprecation
- [ ] Add `@deprecated` decorator to `semester.py` schema
- [ ] Add new location relationship fields to schema
- [ ] Validate API contract backward compatibility
- [ ] Commit schema changes separately

### Phase 3: Endpoint Migration (Part 1)
- [ ] Migrate LFA player generators (8 occurrences)
- [ ] Migrate semester generator (1 occurrence)
- [ ] Add tests for migrated endpoints
- [ ] Commit endpoint changes

### Phase 4: Web Route Migration (Part 2)
- [ ] Migrate dashboard web route (3 occurrences)
- [ ] Migrate admin web route (7 occurrences)
- [ ] Validate UI still works with new API responses
- [ ] Commit web route changes

### Phase 5: Validation & Documentation
- [ ] Run E2E tests to validate API changes
- [ ] Verify backward compatibility
- [ ] Update API documentation
- [ ] Final commit with validation results

---

## 📊 Progress Tracking

**Total**: 19 occurrences
**Investigated**: 0 / 19
**Migrated**: 0 / 19
**Tested**: 0 / 19

### File-by-File Progress

#### 1. Pydantic Schema (1 occurrence)
**File**: `app/schemas/semester.py`
- [ ] Line 21: `location_venue: Optional[str] = None`
- **Strategy**: TBD (investigation phase)

#### 2. LFA Player Generators (8 occurrences)
**File**: `app/api/api_v1/endpoints/periods/lfa_player_generators.py`
- [ ] Line 146: `semester.location_venue = location.venue`
- [ ] Line 161: `location_venue=location.venue,`
- [ ] Line 252: `semester.location_venue = location.venue`
- [ ] Line 267: `location_venue=location.venue,`
- [ ] Line 352: `semester.location_venue = location.venue`
- [ ] Line 367: `location_venue=location.venue,`
- [ ] Line 451: `semester.location_venue = location.venue`
- [ ] Line 466: `location_venue=location.venue,`
- **Strategy**: TBD (investigation phase)

#### 3. Semester Generator (1 occurrence)
**File**: `app/api/api_v1/endpoints/semester_generator.py`
- [ ] Line 356: `semester.location_venue = location.venue`
- **Strategy**: TBD (investigation phase)

#### 4. Dashboard Web Route (3 occurrences)
**File**: `app/api/web_routes/dashboard.py`
- [ ] Line 96: Comment
- [ ] Line 97: `if not semester.location_venue:`
- [ ] Line 99: `semester.location_venue = f"{location_suffix.capitalize()} Campus"`
- **Strategy**: TBD (investigation phase)

#### 5. Admin Web Route (7 occurrences)
**File**: `app/api/web_routes/admin.py`
- [ ] Line 116: Comment
- [ ] Line 117: `if not semester.location_venue:`
- [ ] Line 119: `semester.location_venue = f"{location_suffix.capitalize()} Campus"`
- [ ] Line 163: Comment
- [ ] Line 168: Comment
- [ ] Line 169: `location_key = enrollment.semester.location_venue if enrollment.semester.location_venue else "No Location"`
- [ ] Line 174: `location_key = semester.location_venue if semester.location_venue else "No Location"`
- **Strategy**: TBD (investigation phase)

---

## 🚫 Sprint Discipline Rules

### Investigation First
- ✅ Read all 19 locations
- ✅ Document migration strategy for each
- ✅ Identify dependencies and risks
- ✅ Commit investigation BEFORE any code changes

### Minimal Changes
- Only touch files listed in scope
- Only change location_venue references
- No refactoring, no improvements
- No scope creep

### Separate Commits
- Investigation: documentation only
- Schema: Pydantic changes only
- Endpoints: API endpoint changes
- Web Routes: Web route changes
- Validation: test results

### Testing
- Run tests after each phase
- Validate backward compatibility
- Document any breaking changes

---

## 📝 Investigation Notes

**To be filled during Phase 1**:

### Migration Strategy Options
- **Option A**: Use `get_tournament_venue()` helper (Sprint 2 pattern)
- **Option B**: Use relationship properties directly (`campus.venue`, `location.city`)
- **Option C**: Add computed property to Semester model

### Backward Compatibility
- API responses: Need to include both old and new fields?
- Database: Column already removed in P2
- Frontend: Does UI expect `location_venue` in responses?

### Dependencies
- Does Streamlit UI read `location_venue` from API responses?
- Do scripts consume API with this field?
- Are there webhook/external consumers?

---

## 🔗 Related Documents

- **Epic**: [EPIC_LOCATION_VENUE_CLEANUP.md](EPIC_LOCATION_VENUE_CLEANUP.md)
- **Backlog**: [BACKLOG_LOCATION_VENUE.md](BACKLOG_LOCATION_VENUE.md)
- **Previous Sprint**: [.sprints/2026-01-31-location-venue/](file://.sprints/2026-01-31-location-venue/)

---

## ⏱️ Time Tracking

**Estimate**: 3-4 hours (API migration is more complex than generators)
**Actual**: TBD

**Breakdown**:
- Investigation: 0.5-1h (19 locations, API contract analysis)
- Schema deprecation: 0.5h (careful with API breaking changes)
- Endpoint migration: 1-1.5h (9 occurrences, testing)
- Web route migration: 0.5-1h (10 occurrences, UI validation)
- Validation: 0.5h (E2E tests, backward compatibility)

---

## 🏁 Definition of Done

- [ ] All 19 `location_venue` usages replaced in API layer
- [ ] Pydantic schema properly deprecated
- [ ] API responses maintain backward compatibility (if needed)
- [ ] E2E tests pass
- [ ] No AttributeError or API errors
- [ ] Documentation updated
- [ ] Sprint archived to `.sprints/`

---

**Last Updated**: 2026-01-31
**Phase**: Investigation (not started)
**Next Action**: Begin Investigation Phase - read all 19 API locations
