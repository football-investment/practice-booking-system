# E2E Test Coverage Analysis & Gap Identification

**Date**: 2026-02-10
**Purpose**: Analyze existing Playwright E2E tests and identify gaps for clean DB testing
**Context**: CHAMPION badge fix complete, preparing for clean DB restart with full coverage

---

## Current E2E Test Inventory

### Existing Tests (16 files)

| Test File | Purpose | User Flow Covered | DB Mutations |
|-----------|---------|-------------------|--------------|
| `test_champion_badge_regression.py` | ✅ CHAMPION badge display verification | Login → Dashboard → Badge display | None (read-only) |
| `test_performance_card_unit.py` | ✅ Performance card unit tests (15 tests) | Component testing | None (mocked) |
| `test_01_quick_test_full_flow.py` | Tournament creation → Quick Test | Home → Create Tournament → Results | Creates tournament + badges |
| `test_01_create_new_tournament.py` | Tournament creation flow | Create tournament form | Creates tournament |
| `test_02_draft_continue.py` | Draft tournament continuation | Load draft → Continue | None (existing draft) |
| `test_03_in_progress_continue.py` | In-progress tournament continuation | Load in-progress → Continue | None (existing) |
| `test_04_history_tabs.py` | Tournament history navigation | History tabs switching | None (read-only) |
| `test_05_multiple_selection.py` | Multiple player selection | Bulk operations | Unknown |
| `test_06_error_scan.py` | Error detection across UI | Page scanning | None (read-only) |
| `test_00_screenshot.py` | Screenshot capture | Visual regression | None |
| `test_debug_*.py` (3 files) | Debug/development tests | Debug UI | Unknown |
| `test_quick_test_*.py` (3 duplicates) | Various quick test iterations | Tournament execution | Creates data |

---

## Critical User Flows for Clean DB Testing

### 1. User Onboarding & Authentication ❌ NOT COVERED

**Required Flow**:
```
1. Register new user (if self-registration enabled)
   OR
   Seed user exists in DB

2. Login with credentials
   ✅ COVERED by test_champion_badge_regression.py (line 39-70)

3. Verify redirect to appropriate dashboard based on role
   ❌ NOT TESTED

4. Onboarding completion (if required)
   ❌ NOT TESTED
```

**Gap**: No test for user creation → onboarding → first login flow

---

### 2. Tournament Creation & Execution ⚠️ PARTIALLY COVERED

**Required Flow**:
```
1. Admin/Instructor creates tournament
   ✅ COVERED by test_01_create_new_tournament.py

2. Tournament configuration (game type, mode, players)
   ✅ COVERED by test_01_quick_test_full_flow.py (lines 133-200)

3. Tournament execution
   ✅ COVERED by test_01_quick_test_full_flow.py

4. Results generation
   ✅ COVERED by test_01_quick_test_full_flow.py

5. Badge award
   ⚠️ PARTIALLY - Quick Test creates badges, but not verified

6. Ranking calculation
   ❌ NOT VERIFIED - No test checks tournament_rankings table
```

**Gap**: No test verifies:
- Tournament_rankings populated correctly
- Badge_metadata contains placement/total_participants
- XP/credits awarded correctly

---

### 3. Player Dashboard & Badge Display ✅ COVERED

**Required Flow**:
```
1. Login as player
   ✅ test_champion_badge_regression.py

2. Navigate to Tournament Achievements
   ✅ test_champion_badge_regression.py (line 92-110)

3. Verify CHAMPION badge displays with metadata
   ✅ test_champion_badge_regression.py (line 130-150)

4. Performance card shows "#1 of X players"
   ✅ test_champion_badge_regression.py
```

**Status**: WELL COVERED

---

### 4. Badge Metadata Consistency ⚠️ UNIT TESTED ONLY

**Required Verification**:
```
1. CHAMPION badge has badge_metadata in DB
   ❌ NOT TESTED in E2E

2. API response includes "badge_metadata" key (not "metadata")
   ❌ NOT TESTED in E2E

3. Frontend receives correct metadata
   ❌ NOT TESTED (only visual verification)

4. Primary badge logic works with multiple badges
   ✅ COVERED in unit tests (test_T15)
```

**Gap**: No E2E test that:
- Creates tournament with CHAMPION badge
- Queries DB to verify badge_metadata
- Queries API to verify response structure
- Verifies frontend receives correct data

---

### 5. Clean DB Setup & Seed Data ❌ NOT COVERED

**Required**:
```
1. DB migration to latest schema
   ❌ NO TEST

2. Seed minimal test data (users, specializations)
   ❌ NO TEST

3. Verify seed data integrity
   ❌ NO TEST

4. Idempotent seed (can run multiple times)
   ✅ EXISTS: scripts/seed_champion_test_data.py (for CHAMPION test user)
```

**Gap**: No comprehensive E2E test that:
- Starts from empty DB
- Runs migrations
- Seeds test data
- Verifies data integrity
- Runs full user flow

---

## Coverage Matrix

| User Flow | Has E2E Test? | Verifies DB? | Verifies API? | Idempotent? |
|-----------|---------------|--------------|---------------|-------------|
| User login | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| User onboarding | ❌ No | ❌ No | ❌ No | ❌ No |
| Tournament creation | ✅ Yes | ⚠️ Partial | ❌ No | ❌ No |
| Tournament execution | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Badge award | ⚠️ Implied | ❌ No | ❌ No | ❌ No |
| Badge display | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| Rankings calculation | ❌ No | ❌ No | ❌ No | ❌ No |
| XP/Credits award | ❌ No | ❌ No | ❌ No | ❌ No |
| Clean DB setup | ❌ No | ❌ No | ❌ No | ⚠️ Partial |

**Coverage Score**: 4.5/9 flows = **50% coverage**

---

## Critical Gaps for Clean DB Testing

### Gap 1: No "Genesis" Test (Clean DB → Full Flow)

**Problem**: No single E2E test that:
1. Assumes clean/empty database
2. Runs migrations
3. Seeds minimal data
4. Executes full user journey
5. Verifies data integrity at each step

**Impact**: Cannot confidently restart from clean DB

---

### Gap 2: No DB Verification in E2E Tests

**Problem**: E2E tests verify UI only, not underlying data

**Example**: `test_01_quick_test_full_flow.py` creates a tournament and verifies "Results screen appears" but does NOT verify:
- `semesters` table has new tournament
- `tournament_badges` table has badges with metadata
- `tournament_rankings` table has rankings
- Badge metadata has correct placement/total_participants

**Impact**: Tests pass even if data is corrupt

---

### Gap 3: No API Contract Testing

**Problem**: No E2E test verifies API responses

**Example**: The `badge_metadata` serialization bug (commit `2f38506`) would NOT have been caught by existing E2E tests because:
- Tests only check UI text ("No ranking data")
- Don't verify API response structure

**Impact**: Backend changes can break frontend without test detection

---

### Gap 4: No Idempotency Testing

**Problem**: Most E2E tests assume specific DB state, can't run twice

**Example**: `test_01_create_new_tournament.py` creates a tournament but:
- Doesn't clean up after itself
- Can't run again without manual DB reset
- Relies on specific test data existing

**Impact**: Cannot run E2E suite multiple times without manual intervention

---

## Recommended New E2E Tests

### Priority 1: Genesis E2E Test (CRITICAL)

**File**: `test_00_genesis_clean_db_full_flow.py`

**Scope**:
```python
"""
GENESIS E2E TEST - Clean DB to CHAMPION Badge Display

Assumes EMPTY database (or runs migrations + cleanup first).
This is the SINGLE SOURCE OF TRUTH for "does the system work end-to-end?"

Steps:
1. Verify DB is clean (or clean it)
2. Run alembic migrations
3. Seed minimal test data:
   - 1 STUDENT user (junior.intern@lfa.com)
   - 1 INSTRUCTOR user
   - 1 LFA_FOOTBALL_PLAYER specialization
   - 1 semester with COMPLETED status
4. Login as student
5. Create tournament (or have instructor create it)
6. Complete tournament → award CHAMPION badge
7. Verify DB:
   - tournament_badges has CHAMPION with badge_metadata
   - tournament_rankings has rank=1
8. Navigate to Tournament Achievements
9. Verify UI:
   - CHAMPION badge visible
   - "#1 of X players" shown
   - NO "No ranking data"
10. Verify API response (using requests library):
    - GET /api/v1/tournaments/badges/user/{user_id}
    - Response has "badge_metadata" key (not "metadata")
11. Screenshot for visual regression
12. CLEANUP: Mark test data for cleanup (or use transaction rollback)

Markers: @pytest.mark.genesis, @pytest.mark.critical, @pytest.mark.slow
Runtime: ~60 seconds
"""
```

---

### Priority 2: Badge Metadata Verification E2E Test

**File**: `test_badge_metadata_api_contract.py`

**Scope**:
```python
"""
API Contract Test - Badge Metadata Serialization

Verifies the bug fixed in commit 2f38506 stays fixed.

Steps:
1. Login as user with existing CHAMPION badge
2. Call API directly: GET /api/v1/tournaments/badges/user/{user_id}
3. Parse JSON response
4. Verify:
   - Response is JSON array
   - Each badge has "badge_metadata" key (NOT "metadata")
   - CHAMPION badge has badge_metadata.placement
   - CHAMPION badge has badge_metadata.total_participants
5. Verify DB matches API response:
   - Query tournament_badges table
   - Compare badge_metadata column to API response
6. Fail if mismatch

Markers: @pytest.mark.api_contract, @pytest.mark.regression
Runtime: ~5 seconds
"""
```

---

### Priority 3: Tournament Ranking Calculation E2E Test

**File**: `test_tournament_ranking_calculation.py`

**Scope**:
```python
"""
Tournament Ranking Calculation Verification

Ensures tournament_rankings table is populated correctly.

Steps:
1. Create tournament with 8 players
2. Set different scores for each player
3. Complete tournament
4. Verify DB:
   - tournament_rankings has 8 rows
   - rank values are 1-8 (no gaps, no duplicates)
   - total_participants = 8 for all rows
   - Highest score has rank=1
5. Verify badges:
   - Rank 1 player has CHAMPION badge
   - Rank 2 player has RUNNER_UP badge
   - Rank 3 player has THIRD_PLACE badge
6. Verify badge_metadata matches rankings:
   - badge_metadata.placement == tournament_rankings.rank
   - badge_metadata.total_participants == 8

Markers: @pytest.mark.ranking, @pytest.mark.data_integrity
Runtime: ~30 seconds
"""
```

---

### Priority 4: Idempotent Seed Data Test

**File**: `test_seed_data_idempotency.py`

**Scope**:
```python
"""
Seed Data Idempotency Verification

Ensures seed scripts can run multiple times without errors.

Steps:
1. Run scripts/seed_champion_test_data.py
2. Verify test user exists with correct data
3. Run seed script AGAIN
4. Verify no duplicates created
5. Verify data unchanged
6. Run seed script 10 times in loop
7. Verify still only 1 test user

Markers: @pytest.mark.seed, @pytest.mark.idempotency
Runtime: ~10 seconds
"""
```

---

## Clean DB Testing Strategy

### Option A: Transaction-Based Testing (Recommended)

```python
# pytest fixture
@pytest.fixture(scope="function")
def clean_db_transaction(db_session):
    """
    Each test runs in a transaction that's rolled back after.
    Fastest, but doesn't test migrations.
    """
    transaction = db_session.begin_nested()
    yield db_session
    transaction.rollback()
```

**Pros**: Fast, isolated, no cleanup needed
**Cons**: Doesn't test migrations, not truly "clean DB"

---

### Option B: Full DB Reset Per Test (Slowest, Most Realistic)

```python
@pytest.fixture(scope="function")
def clean_db_full_reset():
    """
    Drop all tables, run migrations, seed minimal data.
    Slowest but most realistic.
    """
    drop_all_tables()
    run_alembic_migrations()
    seed_minimal_data()
    yield
    # No cleanup - next test will reset anyway
```

**Pros**: Tests real-world scenario, catches migration bugs
**Cons**: VERY slow (~10s per test)

**Recommendation**: Use for `test_00_genesis_clean_db_full_flow.py` ONLY

---

### Option C: Hybrid (Best Balance)

```python
# Fast tests use transactions
@pytest.mark.fast
def test_ui_only():
    with clean_db_transaction():
        ...

# Critical path uses full reset
@pytest.mark.genesis
def test_00_genesis_clean_db_full_flow():
    with clean_db_full_reset():
        ...
```

---

## Proposed Test Suite Structure

```
tests_e2e/
├── test_00_genesis_clean_db_full_flow.py  (NEW - CRITICAL)
├── test_badge_metadata_api_contract.py     (NEW - API verification)
├── test_tournament_ranking_calculation.py  (NEW - Data integrity)
├── test_seed_data_idempotency.py           (NEW - Seed verification)
├── test_champion_badge_regression.py       (EXISTING - Keep)
├── test_performance_card_unit.py           (EXISTING - Keep)
├── test_01_quick_test_full_flow.py         (EXISTING - Keep)
├── conftest.py                             (NEW - Fixtures)
└── fixtures/
    ├── db_fixtures.py                      (NEW - DB setup/teardown)
    ├── api_fixtures.py                     (NEW - API client)
    └── user_fixtures.py                    (NEW - Test users)
```

---

## Database Seed Requirements for Clean Testing

### Minimal Seed Data (Required for ANY test)

```sql
-- 1. Specializations (required for user creation)
INSERT INTO specialization_types (code, name) VALUES
  ('LFA_FOOTBALL_PLAYER', 'LFA Football Player');

-- 2. Test Users
INSERT INTO users (email, password_hash, name, role, specialization, onboarding_completed) VALUES
  ('junior.intern@lfa.com', '<bcrypt_hash>', 'Junior Intern', 'STUDENT', 'LFA_FOOTBALL_PLAYER', true),
  ('instructor@lfa.com', '<bcrypt_hash>', 'Test Instructor', 'INSTRUCTOR', NULL, true);

-- 3. User License (for student)
INSERT INTO user_licenses (user_id, specialization_type, status) VALUES
  ((SELECT id FROM users WHERE email='junior.intern@lfa.com'), 'LFA_FOOTBALL_PLAYER', 'ACTIVE');

-- 4. Semester (for tournament badges)
INSERT INTO semesters (code, name, specialization_type, start_date, end_date, status) VALUES
  ('E2E-TEST-CHAMPION', 'E2E Test Tournament', 'LFA_FOOTBALL_PLAYER', '2026-01-01', '2026-12-31', 'COMPLETED');
```

### Full Seed Data (For comprehensive testing)

```sql
-- Above + additional test data:
-- - 8 student users (for tournament with 8 players)
-- - Multiple tournaments (DRAFT, IN_PROGRESS, COMPLETED)
-- - Sample badges (CHAMPION, RUNNER_UP, THIRD_PLACE)
-- - Sample rankings
-- - Sample XP/credits transactions
```

---

## Recommendations

### Immediate Actions (Before Clean DB Restart)

1. ✅ **Keep existing tests** - Don't delete, they provide value
2. ✅ **Create `test_00_genesis_clean_db_full_flow.py`** - CRITICAL
3. ✅ **Create `test_badge_metadata_api_contract.py`** - Catches serialization bugs
4. ✅ **Create `conftest.py`** with DB fixtures
5. ✅ **Document seed data requirements** in `tests_e2e/README.md`

### Medium-term (Next Sprint)

6. ⏳ Create `test_tournament_ranking_calculation.py`
7. ⏳ Create `test_seed_data_idempotency.py`
8. ⏳ Add DB verification to existing E2E tests
9. ⏳ Add API contract assertions to existing tests
10. ⏳ Implement transaction-based fixtures for fast tests

### Long-term (Continuous Improvement)

11. 📅 Add visual regression testing (Percy, Chromatic)
12. 📅 Add performance benchmarks
13. 📅 Add stress testing (1000+ users, 100+ tournaments)
14. 📅 Add chaos engineering (DB failures, network failures)

---

## Summary

**Current E2E Coverage**: ~50% of critical user flows
**Critical Gaps**: No clean DB test, no DB verification, no API contract testing
**Recommendation**: Create 4 new E2E tests (Priority 1-4) before clean DB restart
**Estimated Effort**: 4-6 hours for Priority 1-2, 2-3 hours for Priority 3-4
**Risk if skipped**: Clean DB restart may reveal bugs not caught by current tests

**Next Step**: Create `test_00_genesis_clean_db_full_flow.py` as proof-of-concept
