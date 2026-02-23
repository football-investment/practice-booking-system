# Contributing to Football Investment Practice Booking System

## Development Workflow

### Baseline Policy

**Baseline Definition:** The test count baseline (`.baseline/test_count.txt`) represents the minimum passing test count that must be maintained across all feature development.

#### When to Update Baseline

**✅ ALLOWED:**
- **After feature tag creation** - Update baseline only AFTER creating a feature tag (e.g., `tournament-workflow-v1`)
- **Feature delivery complete** - All phases implemented, validated, and tagged
- **Pass rate maintained** - New baseline must maintain >= 90% pass rate
- **BookingFlow preserved** - Critical flows (4/4 = 100%) must remain intact

**❌ NOT ALLOWED:**
- **Mid-feature development** - Do not update baseline while feature is in progress
- **Before tag creation** - Tag must exist before baseline update
- **Decreasing test count** - Baseline can only increase or stay the same
- **Without validation** - Must run 3× validation (0 flaky tests) before update

#### Baseline Update Process

```bash
# 1. Complete feature implementation (all phases)
git commit -m "feat: Complete feature implementation"

# 2. Validate test suite (3× runs, 0 flaky tests)
pytest app/tests/ -v --tb=no -q  # Run 3 times

# 3. Create feature tag
git tag -a feature-name-v1 -m "Feature description"

# 4. Update baseline
PASS_COUNT=$(pytest app/tests/ -v --tb=no -q 2>&1 | grep "passed" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+")
echo $PASS_COUNT > .baseline/test_count.txt

# 5. Commit baseline update
git add .baseline/test_count.txt
git commit -m "chore: Update baseline to $PASS_COUNT passed tests (Feature Name delivery)"
```

#### Example Timeline

```
✅ CORRECT:
1. Implement Phase 1 → commit
2. Implement Phase 2 → commit
3. Implement Phase 3 → commit
4. Create tag: feature-v1
5. Update baseline → commit
6. Push to remote

❌ INCORRECT:
1. Implement Phase 1 → commit + baseline update  ← TOO EARLY
2. Implement Phase 2 → commit + baseline update  ← TOO EARLY
3. Tag creation
```

#### Validation Requirements

Before updating baseline, ensure:

1. **Pass Rate:** >= 90% (current: 92.2%)
2. **BookingFlow:** 4/4 (100%) maintained
3. **Flaky Tests:** 0 (validate with 3× runs)
4. **Critical Flows:** All maintained (License API: 10/10)
5. **Feature Tag:** Created with descriptive message
6. **Documentation:** Feature documented in tag message

#### Current Baseline

```
File: .baseline/test_count.txt
Value: 261
Last Updated: 2026-02-23 (Tournament Workflow v1 delivery)
```

---

## Test Categorization

### Unit Tests
- **Location:** `app/tests/test_*.py`
- **Marker:** None (default)
- **Run:** Every commit (CI fast lane)
- **Purpose:** Fast, isolated functionality validation

### Integration Tests
- **Location:** `app/tests/test_*_integration.py` or marked with `@pytest.mark.integration`
- **Marker:** `@pytest.mark.integration`
- **Run:** Separate pipeline stage (CI slow lane)
- **Purpose:** Complex dependency validation (staging/production)

### E2E Tests (Business Regression Shield)
- **Location:** `app/tests/test_*_e2e.py` or marked with `@pytest.mark.e2e`
- **Marker:** `@pytest.mark.e2e`
- **Run:** Separate pipeline stage (see CI Policy below)
- **Purpose:** Business value chain validation, regression shield for revenue-critical flows
- **Scope:** Complete user journeys (enrollment → credit deduction → session visibility → audit)
- **Coverage:** Happy path + negative variants (insufficient credits, idempotency, etc.)

**CI Policy for E2E Tests:**

```yaml
# Pull Request Pipeline (Smoke E2E only)
- Run: @pytest.mark.e2e and @pytest.mark.smoke
- Duration: <5s
- Purpose: Fast feedback, blocks broken business flows

# Main Branch Pipeline (Full E2E suite)
- Run: @pytest.mark.e2e
- Duration: <30s
- Purpose: Full regression validation after merge

# Nightly Pipeline (Full E2E + stress tests)
- Run: @pytest.mark.e2e --count=10
- Duration: <5min
- Purpose: Flaky test detection, concurrency validation
```

**E2E Expansion Policy:**
- ❌ Do NOT add new E2E tests without explicit business justification
- ✅ Add negative variants to existing E2E flows (e.g., insufficient credits, idempotency)
- ✅ Focus: E2E as regression shield, not feature expansion
- ✅ Business metrics measured: enrollment success rate, credit consistency, transaction idempotency

### Running Tests by Category

```bash
# Unit tests only (default)
pytest app/tests/ -v

# Integration tests only
pytest app/tests/ -v -m integration

# E2E tests only
pytest app/tests/ -v -m e2e

# Smoke E2E tests (for PR pipeline)
pytest app/tests/ -v -m "e2e and smoke"

# Exclude integration and E2E tests (fast unit tests only)
pytest app/tests/ -v -m "not integration and not e2e"

# Full E2E suite with 10× validation (nightly)
pytest app/tests/ -v -m e2e --count=10
```

---

## Feature Development Guidelines

### Feature Tag Naming Convention

```
<feature-type>-<feature-name>-v<version>

Examples:
- tournament-workflow-v1
- booking-flow-v1
- payment-refund-v1
```

### Feature Tag Message Template

```
<Feature Name> v<version> - Complete

## Summary
[Brief description of feature phases]

## Metrics
- Pass Rate: X/Y (Z%)
- BookingFlow: 4/4 (100%)
- New Tests: +N
- Flaky Tests: 0

## Features Delivered
[List phases with descriptions]

## Production Readiness
✅ Pass rate >= 90%
✅ BookingFlow preserved
✅ 0 flaky tests
✅ [Other checklist items]

Built with Claude Sonnet 4.5
Tag: <tag-name>
Date: YYYY-MM-DD
```

---

## Commit Message Guidelines

### Format

```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `perf`: Performance improvement
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `docs`: Documentation
- `chore`: Maintenance (baseline updates, etc.)

### Scopes
- `tournament`: Tournament-related features
- `booking`: Booking flow features
- `session`: Session management
- `license`: License API
- `audit`: Audit logging
- `tests`: Test infrastructure

---

## Quality Gates

### Pre-Commit Checklist

- [ ] All tests pass (`pytest app/tests/ -v`)
- [ ] Pass rate >= 90%
- [ ] BookingFlow 4/4 (100%) maintained
- [ ] No flaky tests (3× validation)
- [ ] Code formatted (linter passes)
- [ ] Commit message follows convention

### Pre-Tag Checklist

- [ ] All feature phases complete
- [ ] All commits pushed to remote
- [ ] Validation complete (3× runs, 0 flaky)
- [ ] Feature documentation complete
- [ ] Tag message prepared with metrics

### Pre-Baseline Update Checklist

- [ ] Feature tag created
- [ ] Pass count verified
- [ ] BookingFlow preserved
- [ ] Critical flows maintained
- [ ] No flaky tests

---

## Contact

For questions or clarifications, contact the development team.

**Last Updated:** 2026-02-23
**Baseline Version:** 261 passed tests (Tournament Workflow v1)
