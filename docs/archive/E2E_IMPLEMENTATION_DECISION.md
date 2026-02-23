# E2E Modular Architecture - Implementation Decision

**Date**: 2026-02-10
**Decision Required**: Proceed with snapshot-based modular E2E architecture?

---

## Current Findings

### ✅ UI Flows Available for E2E Testing

1. **Registration UI**: ✅ EXISTS
   - File: `streamlit_app/🏠_Home.py` (lines 116-200+)
   - Type: Invitation code-based registration
   - Fields: Name, email, password, phone, DOB, address, nationality
   - **Can be tested via Playwright**

2. **Onboarding UI**: ✅ EXISTS
   - File: `streamlit_app/pages/LFA_Player_Onboarding.py`
   - Type: 6-step wizard (Profile → Position → Skills → Goals)
   - Prerequisite: User must have `LFA_FOOTBALL_PLAYER` license
   - Sets: `onboarding_completed=true` on completion
   - **Can be tested via Playwright**

3. **Tournament Creation UI**: ✅ EXISTS
   - File: `test_01_quick_test_full_flow.py` already tests this
   - Type: Quick Test mode (auto-complete tournament)
   - **Already working, can be adapted**

4. **Badge Display UI**: ✅ EXISTS
   - File: `test_champion_badge_regression.py` already tests this
   - Type: CHAMPION badge verification
   - **Already working in headless mode**

---

## Proposed Modular Lifecycle Phases

```
Phase 0: Clean DB
    ├─ Drop tables, run migrations
    ├─ Seed: specializations, game types, semesters
    ├─ Seed: Invitation code for registration
    └─ 📸 Snapshot: "00_clean_db"

Phase 1: User Registration (UI)
    ├─ Navigate to Home page
    ├─ Click "Register with Invitation Code"
    ├─ Fill form (name, email, password, etc.)
    ├─ Submit with valid invitation code
    ├─ Verify: User created, onboarding_completed=false
    └─ 📸 Snapshot: "01_user_registered"

Phase 2: Onboarding (UI)
    ├─ Login as registered user
    ├─ User auto-redirected to Specialization Hub
    ├─ Unlock LFA_FOOTBALL_PLAYER license
    ├─ Navigate to LFA Player Onboarding
    ├─ Complete 6-step wizard (position, skills, goals)
    ├─ Verify: onboarding_completed=true
    └─ 📸 Snapshot: "02_user_onboarded"

Phase 3: Sandbox Check (UI)
    ├─ Login as onboarded user
    ├─ Verify: User sees LFA_Player_Dashboard
    ├─ Verify: No errors on dashboard
    └─ 📸 Snapshot: "03_sandbox_ready"

Phase 4: Tournament Creation (UI)
    ├─ ADAPT: test_01_quick_test_full_flow.py
    ├─ Navigate to Tournament Sandbox
    ├─ Create tournament (Quick Test mode)
    ├─ Wait for completion
    ├─ Verify: Tournament status=COMPLETED
    └─ 📸 Snapshot: "04_tournament_completed"

Phase 5: Badge Verification (DB + API)
    ├─ Query DB: tournament_badges has CHAMPION
    ├─ Verify: badge_metadata correct
    ├─ Call API: /badges/user/{id}
    ├─ Verify: Response has "badge_metadata" key
    └─ 📸 Snapshot: "05_badges_awarded"

Phase 6: UI Badge Display (UI)
    ├─ ADAPT: test_champion_badge_regression.py
    ├─ Navigate to Tournament Achievements
    ├─ Verify: CHAMPION badge visible
    ├─ Verify: "#1 of X players" shown
    └─ 📸 Snapshot: "06_ui_verified"
```

---

## Implementation Complexity

### Option A: Full Modular Architecture (Recommended)

**Effort**: ~4-5 hours
**Components**:
- Snapshot Manager (30 min)
- DB Helpers (15 min)
- UI Helpers (15 min)
- Phase 0-6 tests (2.5 hours)
- Orchestrator (1 hour)

**Benefits**:
- ✅ Production-grade, scalable
- ✅ Fast iteration (jump to any phase)
- ✅ Clear phase boundaries
- ✅ CI-ready from day 1

**Risks**:
- Snapshot management overhead
- More files to maintain

---

### Option B: Simplified Single Test (Quick Win)

**Effort**: ~2 hours
**Components**:
- One test file: `test_master_e2e_full_lifecycle.py`
- No snapshots, just runs full flow

**Benefits**:
- ✅ Faster to implement
- ✅ Simpler structure

**Risks**:
- ❌ Slow iteration (must re-run full flow)
- ❌ Hard to debug (can't jump to failing phase)
- ❌ Not scalable

---

## Recommendation

**Proceed with Option A: Full Modular Architecture**

**Rationale**:
1. User explicitly requested **snapshot-based, rollback-capable** architecture
2. UI flows exist for full lifecycle testing (registration, onboarding, tournament)
3. Initial time investment pays off in maintenance + debugging speed
4. Aligns with "production-grade, scalable E2E structure" requirement

---

## Implementation Plan

### Step 1: Core Infrastructure (1 hour)

```bash
# Create directory structure
mkdir -p tests_e2e/lifecycle
mkdir -p tests_e2e/utils
mkdir -p tests_e2e/snapshots

# Create utility modules
tests_e2e/utils/snapshot_manager.py  # DB snapshot save/restore
tests_e2e/utils/db_helpers.py         # DB query helpers
tests_e2e/utils/ui_helpers.py          # Common UI actions
```

### Step 2: Phase 0 - Clean DB (30 min)

```python
# tests_e2e/lifecycle/test_00_clean_db.py
- Drop all tables
- Run alembic migrations
- Seed: specializations, game types, semesters
- Seed: Invitation code for test registration
- Save snapshot: "00_clean_db"
```

### Step 3: Phase 1 - Registration (45 min)

```python
# tests_e2e/lifecycle/test_01_user_registration.py
- Restore snapshot: "00_clean_db"
- Navigate to Home page
- Click "Register with Invitation Code" button
- Fill registration form with test data
- Submit form
- Verify: User created in DB with correct data
- Verify: onboarding_completed = false
- Save snapshot: "01_user_registered"
```

### Step 4: Phase 2 - Onboarding (60 min)

```python
# tests_e2e/lifecycle/test_02_onboarding.py
- Restore snapshot: "01_user_registered"
- Login as registered user
- Navigate to Specialization Hub
- Unlock LFA_FOOTBALL_PLAYER license
- Navigate to LFA Player Onboarding
- Complete wizard (6 steps)
- Verify: onboarding_completed = true
- Save snapshot: "02_user_onboarded"
```

### Step 5: Adapt Existing Tests (60 min)

```python
# tests_e2e/lifecycle/test_04_tournament_creation.py
# ADAPT from test_01_quick_test_full_flow.py
- Restore snapshot: "02_user_onboarded" (or "03_sandbox_ready")
- Run existing tournament creation flow
- Save snapshot: "04_tournament_completed"

# tests_e2e/lifecycle/test_06_ui_badge_display.py
# ADAPT from test_champion_badge_regression.py
- Restore snapshot: "05_badges_awarded"
- Run existing badge display verification
- Save snapshot: "06_ui_verified"
```

### Step 6: Orchestrator (60 min)

```python
# tests_e2e/orchestrator.py
- CLI argument parsing
- Phase execution loop
- Snapshot management integration
- Error handling + reporting
```

---

## User Decisions Needed

### Decision 1: Invitation Code Handling

**Question**: How should we handle invitation codes for registration testing?

**Options**:
1. **Seed a test invitation code** in Phase 0 (e.g., `TEST-E2E-2026`)
2. **Generate invitation code dynamically** via API call
3. **Use admin account to create invitation** before registration test

**Recommendation**: Option 1 (seed test invitation code) - simplest, most deterministic

---

### Decision 2: Snapshot Retention

**Question**: Should snapshots be committed to git or gitignored?

**Options**:
1. **Commit snapshots** - Team shares same baseline, but large files in repo
2. **Gitignore snapshots** - Each dev generates their own, smaller repo
3. **Hybrid** - Commit only Phase 0 (clean DB), others gitignored

**Recommendation**: Option 3 (hybrid) - Commit `00_clean_db.sql` for consistency, gitignore others

---

### Decision 3: Test Data Cleanup

**Question**: Should we clean up test data after full pipeline run?

**Options**:
1. **Leave data in DB** - Faster for debugging, but accumulates over time
2. **Clean up after each run** - Restores DB to Phase 0 snapshot
3. **Manual cleanup** - User decides when to reset

**Recommendation**: Option 2 (auto cleanup) - Restore to `00_clean_db` after pipeline completes

---

## Next Steps

**If approved, I will**:

1. Create snapshot manager (`tests_e2e/utils/snapshot_manager.py`)
2. Create Phase 0 test (`tests_e2e/lifecycle/test_00_clean_db.py`)
3. Run Phase 0 to generate first snapshot
4. Create Phase 1 test (registration UI)
5. Create Phase 2 test (onboarding UI)
6. Adapt existing tests for Phases 4 & 6
7. Create orchestrator
8. Test full pipeline locally
9. Document usage

**Estimated time**: 4-5 hours for complete implementation

---

## Questions for User

1. ✅ **Approve modular architecture with snapshots?**
   - If yes → Proceed with implementation
   - If no → Propose alternative

2. ✅ **Invitation code strategy?**
   - Seed test code in Phase 0?
   - Generate dynamically?

3. ✅ **Snapshot retention policy?**
   - Commit to git?
   - Gitignore?

4. ✅ **Auto-cleanup after pipeline?**
   - Restore to Phase 0?
   - Leave data in DB?

**Ready to proceed pending your approval.** 🚀
