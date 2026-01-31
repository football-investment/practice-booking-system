# 📋 Backlog: Location Venue Remaining Usage

**Epic**: EPIC-2026-W05-location-venue-cleanup
**Generated**: 2026-01-31
**Status**: Awaiting sprint scheduling

---

## Usage Summary

**Total Remaining**: 52 occurrences (excluding Sprint 2 completed work)

**Breakdown**:
- Pydantic Schemas: 1
- API Endpoints: 19
- Legacy Generator: 12
- Streamlit UI: 4
- Scripts/Dashboards: 10
- Alembic Migrations: 6 (historical, read-only)

---

## Sprint 3: API Schema & Endpoints (19 occurrences)

### 1. Pydantic Schema (1 occurrence)

**File**: `app/schemas/semester.py`
- **Line 21**: `location_venue: Optional[str] = None`
- **Action**: Add `@deprecated` decorator, add new relationship fields
- **Priority**: 🔴 CRITICAL (API contract)

### 2. LFA Player Generators (8 occurrences)

**File**: `app/api/api_v1/endpoints/periods/lfa_player_generators.py`

**Occurrences**:
- **Line 146**: `semester.location_venue = location.venue`
- **Line 161**: `location_venue=location.venue,`
- **Line 252**: `semester.location_venue = location.venue`
- **Line 267**: `location_venue=location.venue,`
- **Line 352**: `semester.location_venue = location.venue`
- **Line 367**: `location_venue=location.venue,`
- **Line 451**: `semester.location_venue = location.venue`
- **Line 466**: `location_venue=location.venue,`

**Pattern**: Setting `semester.location_venue` from `location.venue`
**Action**: Use relationship instead: `semester.location_id = location.id`
**Priority**: 🔴 HIGH

### 3. Semester Generator (1 occurrence)

**File**: `app/api/api_v1/endpoints/semester_generator.py`
- **Line 356**: `semester.location_venue = location.venue`
- **Action**: Use relationship: `semester.location_id = location.id`
- **Priority**: 🔴 HIGH

### 4. Dashboard Web Route (3 occurrences)

**File**: `app/api/web_routes/dashboard.py`
- **Line 96**: Comment - `# Set location_venue if not already set in DB`
- **Line 97**: `if not semester.location_venue:`
- **Line 99**: `semester.location_venue = f"{location_suffix.capitalize()} Campus"`

**Pattern**: Fallback venue name generation
**Action**: Remove, use `campus.venue` or `location.city`
**Priority**: 🟡 MEDIUM

### 5. Admin Web Route (7 occurrences)

**File**: `app/api/web_routes/admin.py`
- **Line 116**: Comment - `# Set location_venue if not already set in DB`
- **Line 117**: `if not semester.location_venue:`
- **Line 119**: `semester.location_venue = f"{location_suffix.capitalize()} Campus"`
- **Line 163**: Comment - `# Group by location_venue within this specialization`
- **Line 168**: Comment - `# Get the location_venue from the semester`
- **Line 169**: `location_key = enrollment.semester.location_venue if enrollment.semester.location_venue else "No Location"`
- **Line 174**: `location_key = semester.location_venue if semester.location_venue else "No Location"`
- **Line 180**: `for location_venue, enrollments in location_groups.items():`
- **Line 185**: `spec_location_groups[location_venue] = {`
- **Line 189**: `'location_venue': location_venue`

**Pattern**: Grouping and display logic
**Action**: Use `get_tournament_venue()` helper or property
**Priority**: 🟡 MEDIUM

---

## Sprint 4: Streamlit UI (4 occurrences)

### 6. Admin Overview Tab (1 occurrence)

**File**: `streamlit_app/components/admin/overview_tab.py`
- **Line 158**: `st.caption(f"🏟️ {sem.get('location_venue', 'N/A')}")`

**Action**: Use new location field from API
**Priority**: 🟡 MEDIUM

### 7. Semester Generation UI (3 occurrences)

**File**: `streamlit_app/components/semesters/semester_generation.py`
- **Line 94**: `location_venue = selected_location_data.get('venue')`
- **Line 103**: `if location_venue:`
- **Line 104**: `st.caption(f"🏟️ **Venue:** {location_venue}")`

**Pattern**: UI display of venue from location selection
**Action**: Update to use campus/location relationship
**Priority**: 🟡 MEDIUM

---

## Sprint 5: Scripts & Dashboards (10 occurrences)

### 8. Unified Workflow Dashboard (9 occurrences)

**File**: `scripts/dashboards/unified_workflow_dashboard.py`
- **Line 2825**: `semester_venue = semester.get('location_venue', '')`
- **Line 3484**: `semester_location_venue = selected_semester.get('location_venue', '')`
- **Line 3489**: `if semester_location_venue:`
- **Line 3490**: `location_parts.append(semester_location_venue)`
- **Line 3660**: `semester_location_venue = selected_semester.get('location_venue', '')`
- **Line 3665**: `if semester_location_venue:`
- **Line 3666**: `location_parts.append(semester_location_venue)`
- **Line 3747**: `semester_location_venue = selected_semester.get('location_venue', '')`
- **Line 3751**: `if semester_location_venue:`
- **Line 3752**: `location_parts.append(semester_location_venue)`
- **Line 3853**: `campus_venue = semester.get('location_venue', 'Unknown Campus')`

**Pattern**: Dashboard UI display
**Action**: Use new location field from API
**Priority**: 🟢 LOW

### 9. Quick Regenerate Script (1 occurrence)

**File**: `scripts/quick_regenerate_tournament.py`
- **Line 50**: `location_venue,` (in SELECT query)

**Action**: Update SQL query to use relationship
**Priority**: 🟢 LOW

---

## Sprint 6: Legacy Code (12 occurrences)

### 10. Original Session Generator (12 occurrences)

**File**: `app/services/tournament_session_generator_ORIGINAL.py`
- **Line 253**: `'location': tournament.location_venue or 'TBD',`
- **Line 494**: `'location': tournament.location_venue or 'TBD',`
- **Line 632**: `'location': tournament.location_venue or 'TBD',`
- **Line 673**: `'location': tournament.location_venue or 'TBD',`
- **Line 795**: `'location': tournament.location_venue or 'TBD',`
- **Line 838**: `'location': tournament.location_venue or 'TBD',`
- **Line 897**: `'location': tournament.location_venue or 'TBD',`
- **Line 980**: `'location': tournament.location_venue or 'TBD',`
- **Line 1026**: `'location': tournament.location_venue or 'TBD',`
- **Line 1117**: `'location': tournament.location_venue or 'TBD',`
- **Line 1171**: `'location': tournament.location_venue or 'TBD',`
- **Line 1270**: `'location': tournament.location_venue or 'TBD',`

**Pattern**: Same as Sprint 2 (session generation)
**Action**:
- **Option A**: Delete file if truly deprecated/unused
- **Option B**: Migrate using same pattern as Sprint 2
**Priority**: 🟢 LOW (investigate first)

---

## Out of Scope (Historical/Read-Only)

### 11. Alembic Migrations (6 occurrences)

**Files**:
- `scripts/database/create_fresh_database.py:47` - DDL statement
- `alembic/versions/2025_11_26_1500-add_instructor_materials.py:30` - Add column
- `alembic/versions/2025_11_26_1500-add_instructor_materials.py:53` - Drop column
- `alembic/versions/2026_01_28_2110-cac420a0d9b1_p0_1_remove_deprecated_tournament_fields.py:23` - Comment
- `alembic/versions/2026_01_28_2110-cac420a0d9b1_p0_1_remove_deprecated_tournament_fields.py:29` - Drop column
- `alembic/versions/2026_01_28_2110-cac420a0d9b1_p0_1_remove_deprecated_tournament_fields.py:45` - Add column
- `alembic/versions/2025_12_04_1824-574791caded6_add_coupon_management_system.py:170` - Drop column
- `alembic/versions/2025_12_04_1824-574791caded6_add_coupon_management_system.py:331` - Add column
- `alembic/versions/2025_12_04_1034-b12e6da58167_add_semester_location_fields.py:23` - Add column
- `alembic/versions/2025_12_04_1034-b12e6da58167_add_semester_location_fields.py:32` - Drop column

**Action**: None (historical migrations, should not be modified)
**Priority**: N/A

---

## Implementation Order

**Recommended Sequence**:
1. Sprint 3 (API) - Establishes new data contract
2. Sprint 4 (UI) - Consumes new API fields
3. Sprint 5 (Scripts) - Admin tools cleanup
4. Sprint 6 (Legacy) - Final cleanup

**Rationale**: API → UI → Tools ensures each layer has what it needs before migration

---

## Testing Checklist

**Per Sprint**:
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing with real data
- [ ] Backward compatibility verified
- [ ] No performance regression

**Final Epic Validation**:
- [ ] Search for `location_venue` returns 0 active usage
- [ ] All API endpoints return location data
- [ ] UI displays location correctly
- [ ] Scripts execute without errors
- [ ] Documentation updated

---

**Generated**: 2026-01-31
**Tool Used**: `grep -rn "location_venue" . --include="*.py"`
**Excludes**: `.sprints/`, `venv/`, `__pycache__/`
