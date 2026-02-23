# Genesis Test Execution Guide

**Created**: 2026-02-10
**Purpose**: Instructions for running the Genesis E2E test from clean database
**Test File**: [tests_e2e/test_00_genesis_clean_db_full_flow.py](tests_e2e/test_00_genesis_clean_db_full_flow.py)

---

## What is the Genesis Test?

The **Genesis Test** is a comprehensive end-to-end test that answers the question:

> "Can we start from a completely clean database and end up with a working system displaying CHAMPION badges correctly?"

This test is the **single source of truth** for system functionality and would have caught the bug fixed in commit `2f38506` (badge_metadata serialization).

---

## Prerequisites

### 1. Services Must Be Running

```bash
# Terminal 1: Start FastAPI backend
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
source venv/bin/activate
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Streamlit frontend
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
source venv/bin/activate
CHAMPION_DEBUG=0 streamlit run streamlit_app/🏠_Home.py --server.port 8501
```

### 2. PostgreSQL Database

- PostgreSQL server must be running
- Default credentials: `postgres:postgres@localhost:5432`
- Database name: `lfa_intern_system` (will be recreated by test)

### 3. Python Dependencies

```bash
pip install pytest playwright requests psycopg2-binary
playwright install chromium
```

---

## Running the Genesis Test

### Option 1: Run via pytest (Recommended)

```bash
# Navigate to project root
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system

# Run Genesis test only
pytest tests_e2e/test_00_genesis_clean_db_full_flow.py -v -s

# Run with markers
pytest -m genesis -v -s

# Run with full output
pytest tests_e2e/test_00_genesis_clean_db_full_flow.py -v -s --tb=short
```

### Option 2: Run directly (for debugging)

```bash
python tests_e2e/test_00_genesis_clean_db_full_flow.py
```

---

## Expected Test Flow

The test executes in 3 phases:

### Phase 1: Database Setup (~15 seconds)

```
🗑️  Dropping all tables...
   ✅ Database recreated

📦 Running migrations (alembic upgrade head)...
   ✅ Migrations complete

🌱 Seeding test data...
   ✅ Seed data created

🔍 Verifying DB integrity...
   ✅ Test user exists: junior.intern@lfa.com (onboarded=True)
   ✅ CHAMPION badge exists in DB
   ✅ badge_metadata valid: {'placement': 1, 'total_participants': 24}
   ✅ DB integrity verified
```

### Phase 2: API Verification (~5 seconds)

```
🔌 Verifying API badge_metadata serialization...
   ✅ Logged in, got token
   ✅ User ID: 123
   ✅ Fetched 1 badges from API
   ✅ CHAMPION badge found in API response
   ✅ API badge_metadata valid: {'placement': 1, 'total_participants': 24}
```

**This phase catches the bug from commit 2f38506:**
- ❌ If API returns "metadata" instead of "badge_metadata" → FAIL
- ✅ If API returns "badge_metadata" with correct data → PASS

### Phase 3: UI Verification (~40 seconds)

```
🔐 Logging in to UI...
   ✅ Logged in to UI

📊 Navigating to Player Dashboard...
   ✅ Navigated to dashboard

🏆 Verifying CHAMPION badge in UI...
   ✅ CHAMPION badge visible
   ✅ No 'No ranking data' text (bug fixed)
   ✅ Ranking data visible

📸 Screenshot saved: tests_e2e/screenshots/genesis_final_state.png
```

### Final Verdict

```
================================================================================
GENESIS TEST RESULTS
================================================================================
✅ GENESIS TEST PASSED
   - Database setup successful
   - API badge_metadata serialization correct
   - UI displays CHAMPION badge with ranking data
   - NO 'No ranking data' regression detected
```

---

## Test Output Files

After running, check:

```
tests_e2e/screenshots/
├── genesis_final_state.png  (success screenshot)
└── genesis_error.png         (only if test failed)
```

---

## What the Test Verifies

### Database Layer
- ✅ Clean database can be created
- ✅ Alembic migrations run successfully
- ✅ Seed data creates test user with CHAMPION badge
- ✅ `tournament_badges` table has `badge_metadata` column with correct JSON structure
- ✅ `badge_metadata` contains `placement` and `total_participants` keys

### API Layer (Catches commit 2f38506 bug)
- ✅ API endpoint `/api/v1/tournaments/badges/user/{user_id}` returns data
- ✅ API response uses **"badge_metadata"** key (NOT "metadata")
- ✅ `badge_metadata` is properly serialized as JSON object
- ✅ `placement` and `total_participants` are in API response

### UI Layer
- ✅ User can login
- ✅ Dashboard page loads
- ✅ CHAMPION badge is visible
- ✅ Ranking data displays (e.g., "#1 of 24 players")
- ✅ NO "No ranking data" text appears (the bug we fixed)

---

## Troubleshooting

### Test Fails at Database Setup

**Error**: `DROP DATABASE IF EXISTS lfa_intern_system;` fails

**Solution**:
```bash
# Kill all connections to database
psql -U postgres -h localhost -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'lfa_intern_system';"

# Run test again
pytest tests_e2e/test_00_genesis_clean_db_full_flow.py -v -s
```

### Test Fails at Migration Step

**Error**: `alembic upgrade head` fails

**Solution**:
```bash
# Check alembic is installed
alembic --version

# Run migrations manually to see full error
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" alembic upgrade head
```

### Test Fails at API Verification

**Error**: `API response missing 'badge_metadata' key`

**This is the bug from commit 2f38506!**

**Check**:
```bash
# Verify commit 2f38506 is applied
git log --oneline | grep 2f38506

# If not found, check app/models/tournament_achievement.py line 201
# Should be: "badge_metadata": self.badge_metadata
# NOT:       "metadata": self.badge_metadata
```

### Test Fails at UI Verification

**Error**: `Found 'No ranking data' - REGRESSION DETECTED!`

**This indicates the performance card bug!**

**Check**:
```bash
# Verify commits are applied:
git log --oneline | grep -E "(a013113|569808f)"

# Check streamlit_app/components/tournaments/performance_card.py
# Should use: primary_badge = _get_primary_badge(...)
# NOT:        first_badge = badges[0]
```

### Services Not Running

**Error**: `Connection refused` or `Failed to connect to localhost:8000`

**Solution**:
```bash
# Check if services are running
lsof -ti:8000  # FastAPI
lsof -ti:8501  # Streamlit

# If not running, start them (see Prerequisites section)
```

---

## Understanding Test Failures

### PASS Criteria

All 3 phases must pass:
1. ✅ Database has CHAMPION badge with `badge_metadata` JSON
2. ✅ API returns `"badge_metadata"` key (not `"metadata"`)
3. ✅ UI shows ranking data (NOT "No ranking data")

### FAIL Scenarios

| Phase | Error Message | Root Cause | Fix |
|-------|--------------|------------|-----|
| DB | `CHAMPION badge has NULL badge_metadata in DB` | Seed script not creating metadata | Check seed script |
| API | `API response missing 'badge_metadata' key` | Commit 2f38506 not applied | Apply serialization fix |
| API | `API response has 'metadata' key` | Old bug present | Apply commit 2f38506 |
| UI | `Found 'No ranking data'` | Performance card bug | Apply commits a013113, 569808f |
| UI | `CHAMPION badge not visible` | Navigation or rendering issue | Check Streamlit logs |

---

## Integration with CI/CD

### Add to pytest.ini

```ini
[pytest]
markers =
    genesis: Clean database to full flow test (slowest, most comprehensive)
    critical: Build blocker tests
    slow: Tests that take >30 seconds
```

### Run in CI Pipeline

```yaml
# .github/workflows/e2e-tests.yml
- name: Run Genesis Test
  run: |
    pytest tests_e2e/test_00_genesis_clean_db_full_flow.py -v -s --tb=short
  env:
    DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test
    BASE_URL: http://localhost:8501
    API_URL: http://localhost:8000
```

---

## Test Maintenance

### When to Update This Test

Update the Genesis test when:
1. Database schema changes (update seed data)
2. New critical badges added (add to verification)
3. Authentication flow changes (update login logic)
4. API endpoints change (update API verification)

### What NOT to Change

DO NOT modify:
- The 3-phase structure (DB → API → UI)
- The `badge_metadata` key check (catches commit 2f38506 regression)
- The "No ranking data" check (catches performance card regression)

These are **regression guards** for bugs we've already fixed.

---

## Related Documentation

- [E2E_TEST_COVERAGE_ANALYSIS.md](E2E_TEST_COVERAGE_ANALYSIS.md) - Full coverage analysis
- [PRODUCTION_BUGFIX_BADGE_ORDERING.md](PRODUCTION_BUGFIX_BADGE_ORDERING.md) - Performance card bug details
- [PATCH_NOTE_PERFORMANCE_CARD_FIX.md](PATCH_NOTE_PERFORMANCE_CARD_FIX.md) - Fix changelog
- [SANDBOX_UI_TEST_INSTRUCTIONS.md](SANDBOX_UI_TEST_INSTRUCTIONS.md) - Manual UI testing guide

---

## Quick Reference Commands

```bash
# Full test run (recommended)
pytest tests_e2e/test_00_genesis_clean_db_full_flow.py -v -s

# Run only Genesis tests
pytest -m genesis -v -s

# Run all critical tests (including Genesis)
pytest -m critical -v -s

# Debug mode (shows all print statements)
pytest tests_e2e/test_00_genesis_clean_db_full_flow.py -v -s --tb=long

# Run and save output
pytest tests_e2e/test_00_genesis_clean_db_full_flow.py -v -s 2>&1 | tee genesis_test_output.log
```

---

## Success Metrics

A successful Genesis test run means:

1. ✅ System can be deployed from scratch
2. ✅ Migrations are up-to-date and working
3. ✅ Seed scripts are functional
4. ✅ API serialization is correct (commit 2f38506 fix verified)
5. ✅ Frontend correctly renders CHAMPION badges (commits a013113, 569808f verified)
6. ✅ NO regressions in badge display logic

**Expected Runtime**: ~60 seconds
**Expected Result**: 1 passed

---

## Contact

If the Genesis test fails, check:
1. This troubleshooting guide
2. Service logs (FastAPI, Streamlit)
3. Screenshot in `tests_e2e/screenshots/genesis_error.png`
4. Related documentation linked above
