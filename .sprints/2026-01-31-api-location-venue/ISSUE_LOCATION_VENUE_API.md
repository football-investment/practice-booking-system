# 🎫 ISSUE: Location Venue API Migration

**Issue ID**: ISSUE-2026-W05-003
**Epic**: EPIC-2026-W05-location-venue-cleanup
**Sprint**: Sprint 3 - API Schema & Endpoints
**Created**: 2026-01-31
**Status**: 🟡 OPEN - Investigation Phase
**Priority**: 🔴 CRITICAL
**Assignee**: Claude Sonnet 4.5

---

## 📋 Issue Summary

Migrate all `location_venue` usage in API layer (schemas, endpoints, web routes) to use new location relationships established in P2 refactoring.

**Impact**: 19 occurrences across critical API paths
**Risk**: High - API contract changes may affect frontend and external consumers

---

## 🐛 Problem Description

### Background
- **P2 Refactoring**: Removed `location_venue` column from `semesters` table
- **Sprint 2**: Fixed session generators (12 occurrences) using `get_tournament_venue()` helper
- **Remaining**: 19 API-layer usages still reference deprecated field

### Current Issues
- Pydantic schema still defines `location_venue` field
- API endpoints assign values to non-existent column
- Web routes read from deprecated field
- Potential for AttributeError or data inconsistency

### Scope
**API Contract Critical Path**:
1. **Schemas**: Pydantic models that define API request/response structure
2. **Endpoints**: FastAPI routes that handle HTTP requests
3. **Web Routes**: Server-side rendering routes for Streamlit integration

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] All 19 `location_venue` usages replaced in API layer
- [ ] Pydantic schema properly deprecated (backward compatible)
- [ ] API responses include location data via new relationships
- [ ] No AttributeError in API endpoints
- [ ] E2E tests pass with API changes

### Should Have
- [ ] Backward compatibility maintained (dual-field approach if needed)
- [ ] API documentation updated
- [ ] Migration guide for API consumers

### Nice to Have
- [ ] Performance optimization (eager loading in API queries)
- [ ] OpenAPI schema updated with deprecation warnings

---

## 📦 Scope Breakdown

### 1. Pydantic Schema (1 occurrence) - 🔴 CRITICAL
**File**: `app/schemas/semester.py:21`
**Code**: `location_venue: Optional[str] = None`

**Migration Strategy**:
- Add `@deprecated` decorator
- Add new fields: `campus_id`, `location_id`, `campus`, `location`
- Maintain `location_venue` for backward compatibility (computed property?)

**Risk**: Breaking change for API consumers

### 2. LFA Player Generators (8 occurrences) - 🔴 HIGH
**File**: `app/api/api_v1/endpoints/periods/lfa_player_generators.py`
**Lines**: 146, 161, 252, 267, 352, 367, 451, 466

**Pattern**: Setting `semester.location_venue` from `location.venue`
**Migration Strategy**: Use relationship: `semester.location_id = location.id`

**Risk**: Medium - internal API, limited external exposure

### 3. Semester Generator (1 occurrence) - 🔴 HIGH
**File**: `app/api/api_v1/endpoints/semester_generator.py:356`
**Code**: `semester.location_venue = location.venue`

**Migration Strategy**: Same as LFA generators
**Risk**: Medium - semester creation flow

### 4. Dashboard Web Route (3 occurrences) - 🟡 MEDIUM
**File**: `app/api/web_routes/dashboard.py`
**Lines**: 96 (comment), 97, 99

**Pattern**: Fallback venue name generation
**Migration Strategy**: Remove, use `campus.venue` or `location.city`

**Risk**: Low - internal web route for Streamlit

### 5. Admin Web Route (7 occurrences) - 🟡 MEDIUM
**File**: `app/api/web_routes/admin.py`
**Lines**: 116, 117, 119, 163, 168, 169, 174

**Pattern**: Grouping/display logic using `location_venue`
**Migration Strategy**: Use `get_tournament_venue()` helper or computed property

**Risk**: Low - admin-only route

---

## 🔍 Investigation Phase Tasks

### Pre-Migration Analysis
- [ ] Read all 19 API locations and document current behavior
- [ ] Analyze API contract and backward compatibility requirements
- [ ] Check if Streamlit UI reads `location_venue` from API responses
- [ ] Verify external API consumers (webhooks, integrations)
- [ ] Document migration strategy for each file

### Decision Points
- [ ] **Schema Strategy**: Deprecate vs remove vs dual-field?
- [ ] **Backward Compatibility**: Required for external consumers?
- [ ] **Helper Function**: Reuse `get_tournament_venue()` or create property?
- [ ] **Eager Loading**: Add to API queries to prevent N+1?

---

## 🚀 Implementation Plan

### Phase 1: Investigation (Current)
**Goal**: Complete understanding before code changes
**Tasks**:
- Read all 5 files (19 locations)
- Document current API behavior
- Analyze backward compatibility needs
- Create migration strategy document

**Output**: Commit with investigation documentation only

### Phase 2: Schema Deprecation
**Goal**: Update API contract with deprecation
**Tasks**:
- Add `@deprecated` to `location_venue` field
- Add new relationship fields (`campus`, `location`)
- Validate OpenAPI schema generation
- Test API response structure

**Output**: Commit with schema changes only

### Phase 3: Endpoint Migration
**Goal**: Fix endpoint implementations
**Tasks**:
- Migrate LFA generators (8 occurrences)
- Migrate semester generator (1 occurrence)
- Add eager loading to prevent N+1 queries
- Test endpoint functionality

**Output**: Commit with endpoint changes

### Phase 4: Web Route Migration
**Goal**: Fix server-side rendering routes
**Tasks**:
- Migrate dashboard route (3 occurrences)
- Migrate admin route (7 occurrences)
- Validate Streamlit UI still works
- Test admin panel functionality

**Output**: Commit with web route changes

### Phase 5: Validation
**Goal**: Ensure everything works end-to-end
**Tasks**:
- Run E2E test suite
- Manual testing of API endpoints
- Verify Streamlit UI displays correctly
- Check admin panel functionality
- Update documentation

**Output**: Commit with validation results

---

## 🧪 Testing Strategy

### Unit Tests
- [ ] Pydantic schema validation (new fields)
- [ ] API endpoint responses (correct data structure)
- [ ] Web route rendering (no errors)

### Integration Tests
- [ ] API contract tests (backward compatibility)
- [ ] Database query tests (N+1 prevention)
- [ ] Relationship loading tests (eager loading)

### E2E Tests
- [ ] Semester creation flow with location data
- [ ] Tournament generation with location assignment
- [ ] Admin panel location display
- [ ] Dashboard location rendering

### Manual Testing
- [ ] Create tournament via API
- [ ] Verify location data in response
- [ ] Check Streamlit UI display
- [ ] Validate admin panel grouping

---

## 📊 Success Metrics

### Code Quality
- **Coverage**: All 19 occurrences migrated
- **No Errors**: 0 AttributeError or API failures
- **Tests Pass**: 100% E2E test success

### Performance
- **N+1 Queries**: Prevented with eager loading
- **API Response Time**: No regression

### Compatibility
- **Backward Compatible**: API consumers not broken
- **Frontend Works**: Streamlit UI displays correctly

---

## 🔗 Dependencies

### Blocked By
- None (Sprint 2 completed)

### Blocks
- Sprint 4: Streamlit UI migration (depends on API responses)
- Sprint 5: Scripts/Dashboard migration (may consume API)

### Related Issues
- ✅ CLOSED: ISSUE_LOCATION_VENUE_DEPRECATED (Sprint 2)
- 🟡 PLANNED: Sprint 4 UI migration
- 🟡 PLANNED: Sprint 5 Scripts migration
- 🟡 PLANNED: Sprint 6 Legacy cleanup

---

## 📝 Notes

### Sprint 2 Lessons Learned
- ✅ Investigation first prevents rework
- ✅ Separate commits for infrastructure vs usage
- ✅ Helper function pattern works well
- ✅ Eager loading is critical for performance

### API Migration Considerations
- **Breaking Changes**: Must maintain backward compatibility
- **Schema Evolution**: Use deprecation warnings
- **Documentation**: Update OpenAPI/Swagger docs
- **External Consumers**: Check webhooks, integrations

---

## 📅 Timeline

**Created**: 2026-01-31
**Started**: 2026-01-31 (Investigation Phase)
**Target Completion**: TBD (estimate 3-4 hours)

**Phase Breakdown**:
- Investigation: 0.5-1h
- Schema: 0.5h
- Endpoints: 1-1.5h
- Web Routes: 0.5-1h
- Validation: 0.5h

---

## 🏁 Resolution Criteria

**Issue Closed When**:
- All 19 API usages migrated
- E2E tests pass
- Backward compatibility verified
- Documentation updated
- Sprint 3 archived to `.sprints/`

---

**Last Updated**: 2026-01-31
**Current Status**: 🟡 OPEN - Investigation Phase
**Next Action**: Begin reading all 19 API locations for migration analysis
