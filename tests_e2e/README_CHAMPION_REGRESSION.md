# Champion Badge Regression Test

## Overview

This E2E test protects against a critical production bug where Champion badges displayed "No ranking data" instead of showing the #1 ranking.

**Business Rule**: Champion badges MUST ALWAYS display ranking information (#1 of N players), never "No ranking data".

## Test Strategy

### What We Test
- ✅ Champion badge displays proper ranking format
- ✅ Champion badge does NOT show "No ranking data" text
- ✅ Ranking fallback from badge_metadata works correctly

### Test Flow
1. Login as `junior.intern@lfa.com` (user with Champion badge)
2. Navigate to Tournament Achievements section
3. Verify Champion badge shows ranking (e.g., "#1 of 24 players")
4. **FAIL** if "No ranking data" appears anywhere near Champion badge

## Running the Test

### Prerequisites
- Streamlit app running on `http://localhost:8501`
- Database with `junior.intern@lfa.com` user having Champion badge
- Playwright installed

### Local Execution

#### Option 1: Using the helper script (recommended)
```bash
# Make script executable (first time only)
chmod +x tests_e2e/run_champion_regression.sh

# Run the test
./tests_e2e/run_champion_regression.sh
```

#### Option 2: Direct pytest execution
```bash
# From project root
pytest tests_e2e/test_champion_badge_regression.py -v -m "golden_path"
```

#### Option 3: Run with debug screenshot (manual inspection)
```bash
# This will keep browser open and save full-page screenshot
pytest tests_e2e/test_champion_badge_regression.py -k debug -s
```

### CI/CD Execution

The test runs automatically on:
- Push to `main` branch
- Push to `feature/**` or `fix/**` branches
- Pull requests to `main`
- Manual workflow dispatch

**Workflow file**: `.github/workflows/champion-badge-regression.yml`

## Test Failure Handling

### What Happens on Failure?

1. **Build is BLOCKED** - The CI/CD pipeline will fail
2. **Screenshot is saved** to `tests_e2e/screenshots/champion_badge_regression_FAILED.png`
3. **Deployment is prevented** until the issue is fixed

### How to Debug Failure

1. **Check the screenshot**:
   ```bash
   open tests_e2e/screenshots/champion_badge_regression_FAILED.png
   ```

2. **Run debug mode locally**:
   ```bash
   pytest tests_e2e/test_champion_badge_regression.py -k debug -s
   ```
   This will:
   - Open browser in visible mode (headless=False)
   - Take full-page screenshot
   - Print page content to console
   - Keep browser open for 5 seconds

3. **Check the fix implementation**:
   - Verify `performance_card.py` has the fallback logic:
     ```python
     # Fallback: If metrics missing total_participants, try badge_metadata
     if not total_participants:
         if badges and len(badges) > 0:
             first_badge = badges[0]
             badge_metadata = first_badge.get('badge_metadata', {})
             if badge_metadata.get('total_participants'):
                 total_participants = badge_metadata['total_participants']

     # CRITICAL: CHAMPION badge MUST have rank
     if badge_type == "CHAMPION" and not rank:
         if badges and len(badges) > 0:
             first_badge = badges[0]
             badge_metadata = first_badge.get('badge_metadata', {})
             if badge_metadata.get('placement'):
                 rank = badge_metadata['placement']
     ```

4. **Verify database data**:
   ```sql
   -- Check if Champion badge has placement data
   SELECT
       b.badge_type,
       b.badge_metadata->>'placement' as placement,
       b.badge_metadata->>'total_participants' as total_participants
   FROM badges b
   JOIN users u ON b.user_id = u.id
   WHERE u.email = 'junior.intern@lfa.com'
   AND b.badge_type = 'CHAMPION';
   ```

## Test Markers

The test uses multiple pytest markers for filtering:

- `@pytest.mark.golden_path` - Production critical, blocks deployment
- `@pytest.mark.e2e` - End-to-end test with Playwright
- `@pytest.mark.smoke` - Fast regression check for CI

### Running Specific Test Categories

```bash
# Run only golden path tests (most critical)
pytest tests_e2e/ -m "golden_path"

# Run all E2E tests
pytest tests_e2e/ -m "e2e"

# Run smoke tests (fast)
pytest tests_e2e/ -m "smoke"
```

## Root Cause Reference

### The Original Bug

**Symptom**: Champion badge displayed "No ranking data" instead of "#1 of 24 players"

**Root Cause**:
1. `tournament_rankings` table had no entries for completed tournaments
2. Performance metrics query returned `NULL` for both `rank` and `total_participants`
3. UI displayed fallback text "No ranking data" even for Champion badges

**Fix Implemented**:
1. Added fallback logic to read `total_participants` from `badge_metadata`
2. Added CHAMPION guard to force `rank` from `badge_metadata.placement`
3. Performance card now uses badge metadata when metrics are missing

### Files Modified
- `streamlit_app/components/tournaments/performance_card.py` - Added fallback logic
- `streamlit_app/pages/02_My_Performance.py` - Metrics query (if needed)

## Maintenance

### When to Update This Test

Update the test when:
1. Login flow changes (update `_login()` helper)
2. Navigation structure changes (update `_navigate_to_tournament_achievements()`)
3. Badge display format changes (update `_verify_champion_badge_ranking()`)
4. New test users are added (update `TEST_USER_EMAIL` constant)

### Test Data Requirements

The test requires:
- User: `junior.intern@lfa.com` / password: `password123`
- User must have at least one CHAMPION badge
- Badge must have `badge_metadata.placement` populated
- Badge preferably has `badge_metadata.total_participants` populated

## Exit Codes

- `0` - Test passed (Champion badge displays correctly)
- `1` - Test failed (Champion badge shows "No ranking data" - **BLOCKS BUILD**)

## Questions?

For issues or questions about this test, contact the development team or check:
- Test file: `tests_e2e/test_champion_badge_regression.py`
- Implementation: `streamlit_app/components/tournaments/performance_card.py`
- CI Workflow: `.github/workflows/champion-badge-regression.yml`
