# Regression Test Suite

## Overview

This directory contains **regression tests** for critical tournament system functionality. These tests validate business-critical flows and protect against breaking changes during refactoring or feature development.

---

## Test Suite

### ✅ `test_reward_idempotency.sh` - Critical Path Idempotency

**Purpose**: Validate reward distribution idempotency and prevent double-awarding

**Critical Business Rules Tested**:
1. ✅ Reward distribution can only happen if tournament is `COMPLETED`
2. ✅ Duplicate calls WITHOUT `force_redistribution` are rejected (HTTP 400)
3. ✅ `force_redistribution=true` allows re-distribution (test scenario)
4. ✅ TournamentParticipation records act as idempotency guard
5. ✅ Status transition `COMPLETED → REWARDS_DISTRIBUTED` is atomic
6. ✅ Skills calculated correctly after multiple re-distributions

**What It Validates**:
- ✓ No duplicate TournamentParticipation records created
- ✓ No double XP/credits awarded
- ✓ `force_redistribution` flag works correctly
- ✓ V2 skill progression system works after re-distribution
- ✓ Status guard prevents duplicate reward calls
- ✓ Skill values remain consistent across re-distributions

**Risk Areas Covered**:
- Race conditions: Concurrent reward distribution calls
- Double XP/credits awarding
- Incorrect skill progression after re-distribution
- Status transition failures leaving orphaned participation records

**Runtime**: ~5-10 seconds

---

### ✅ `test_edge_cases.sh` - Edge Cases & Bad State Handling

**Purpose**: Validate system behavior with invalid inputs and edge conditions

**Critical Edge Cases Tested**:
1. ✅ Reward distribution with 0 participants
2. ✅ Reward distribution without rankings
3. ✅ Reward distribution with invalid tournament status
4. ✅ Tournament with missing reward_config
5. ✅ Reward distribution for non-existent tournament
6. ✅ Tournament completion with no sessions
7. ✅ Enrollment to non-existent tournament
8. ✅ Invalid user_id in enrollment

**What It Validates**:
- ✓ No NULL pointer exceptions
- ✓ No division by zero errors (0 participants)
- ✓ Proper HTTP error codes returned (400, 403, 404)
- ✓ Graceful degradation on missing data
- ✓ Missing reward_config handled with defaults
- ✓ Invalid status transitions rejected

**Risk Areas Covered**:
- NULL pointer exceptions
- Division by zero (0 participants)
- Missing required data
- Database constraint violations
- Authorization failures on invalid data

**Runtime**: ~10-15 seconds

---

**Usage**:
```bash
cd /path/to/practice_booking_system

# Run idempotency test
bash tests/regression/test_reward_idempotency.sh

# Run edge cases test
bash tests/regression/test_edge_cases.sh
```

**Expected Output (Idempotency Test)**:
```
✅ ALL IDEMPOTENCY TESTS PASSED

Test Results:
  ✅ Test 1: First distribution succeeded
  ✅ Test 2: Duplicate call (force=false) was idempotent (0 users rewarded)
  ✅ Test 3: Re-distribution (force=true) updated existing records
  ✅ Test 4: Status transition COMPLETED → REWARDS_DISTRIBUTED verified
  ✅ Test 5: Skill progression calculated correctly

Critical Validations:
  ✓ No duplicate TournamentParticipation records created
  ✓ No double XP/credits awarded
  ✓ force_redistribution flag works correctly
  ✓ V2 skill progression system works after re-distribution

Reward distribution idempotency is REGRESSION-FREE ✓
```

**Expected Output (Edge Cases Test)**:
```
✅ ALL EDGE CASE TESTS PASSED

Test Results:
  ✅ Test 1: 0 participants handled gracefully
  ✅ Test 2: Missing rankings handled gracefully
  ✅ Test 3: Invalid status (DRAFT) rejected with HTTP 400
  ✅ Test 4: Non-existent tournament rejected with HTTP 404
  ✅ Test 5: Enrollment to non-existent tournament rejected
  ✅ Test 6: Invalid user ID in enrollment rejected
  ✅ Test 7: Missing reward_config handled gracefully

Critical Validations:
  ✓ No NULL pointer exceptions
  ✓ No division by zero errors
  ✓ Proper HTTP error codes returned
  ✓ Graceful degradation on missing data

Edge case handling is ROBUST ✓
```

---

## How to Run All Regression Tests

```bash
#!/bin/bash
cd /path/to/practice_booking_system

echo "Running Regression Test Suite..."
echo "================================="

PASSED=0
FAILED=0

# Test 1: Reward Idempotency
echo ""
echo "TEST 1: Reward Distribution Idempotency"
if bash tests/regression/test_reward_idempotency.sh > /dev/null 2>&1; then
    echo "✅ PASSED"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAILED"
    FAILED=$((FAILED + 1))
fi

# Test 2: Edge Cases
echo ""
echo "TEST 2: Edge Cases & Bad State Handling"
if bash tests/regression/test_edge_cases.sh > /dev/null 2>&1; then
    echo "✅ PASSED"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAILED"
    FAILED=$((FAILED + 1))
fi

# Future tests go here...

echo ""
echo "================================="
echo "RESULTS: $PASSED passed, $FAILED failed"
if [ $FAILED -eq 0 ]; then
    echo "✅ ALL REGRESSION TESTS PASSED"
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    exit 1
fi
```

---

## When to Run Regression Tests

### Mandatory (CI/CD):
- ✅ Before merging any PR that touches:
  - `app/services/tournament/tournament_reward_orchestrator.py`
  - `app/api/api_v1/endpoints/tournaments/rewards_v2.py`
  - `app/services/skill_progression_service.py`
  - Tournament lifecycle endpoints

### Recommended:
- After database schema changes
- Before major releases
- After refactoring tournament-related code
- When adding new tournament types

### Optional:
- Daily as part of nightly build
- On-demand during development

---

## Adding New Regression Tests

### Template for New Tests

```bash
#!/bin/bash

################################################################################
# REGRESSION TEST: [Test Name]
#
# Purpose: [Brief description]
#
# Critical Business Rules Tested:
#   1. [Rule 1]
#   2. [Rule 2]
#   ...
#
# Risk Areas:
#   - [Risk 1]
#   - [Risk 2]
################################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "\n${BLUE}════════════════════════════════════════${NC}"
echo -e "${BLUE}   REGRESSION TEST: [Test Name]${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

# [Test implementation]

echo -e "\n${GREEN}✅ ALL TESTS PASSED${NC}"
```

### Guidelines:
1. **Self-contained**: Test should create its own data and clean up after itself
2. **Fast**: Target runtime < 30 seconds
3. **Deterministic**: Same input = same output (no random data)
4. **Clear output**: Use colored output and clear assertions
5. **Cleanup**: Always clean up test data (use `> /dev/null 2>&1` for SQL)

---

## Maintenance

### Updating Tests
When business rules change, update the corresponding regression test FIRST, then implement the change. This is **TDD for regressions**.

### Deprecating Tests
If a feature is removed, mark the test as deprecated but keep it for historical reference:

```bash
echo "⚠️  DEPRECATED: This test is no longer relevant (feature removed in v2.3.0)"
exit 0
```

---

## Test Data

### Test Users
Regression tests use production test users (IDs 4-16) with known baseline skills:
- User 4: passing ~80.0, dribbling ~50.0
- User 5: passing ~60.0, dribbling ~50.0
- User 6: passing ~70.0, dribbling ~50.0
- Users 14-16: passing ~90-100, dribbling ~50.0

### Test Tournaments
Tests create temporary tournaments with prefix `IDEMPOTENCY-TEST-*`, `REGRESSION-TEST-*`, etc.
All test tournaments are cleaned up at the end of the test.

---

## Troubleshooting

### Test Fails: "Authentication failed"
**Cause**: Backend not running or admin credentials changed
**Fix**: Ensure backend is running at `http://localhost:8000` and admin credentials are `admin@lfa.com` / `admin123`

### Test Fails: Foreign key constraint violation during cleanup
**Cause**: Missing cascade delete or new related tables added
**Fix**: Update cleanup SQL to delete from all related tables first

### Test Fails: Unexpected HTTP response
**Cause**: API behavior changed or test assumptions outdated
**Fix**: Review API changes and update test assertions

---

## Related Documentation

- [E2E Test Documentation](../tournament_types/README.md)
- [Manual Verification Guide](../../docs/E2E_SKILL_PROGRESSION_MANUAL_VERIFICATION.md)
- [Technical Debt](../../docs/TECHNICAL_DEBT.md)

---

## Contact

For questions about regression tests, contact the tournament team or check the internal wiki.
