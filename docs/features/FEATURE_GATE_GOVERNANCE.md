# Feature Gate Governance Rules
## Post-Baseline Development Standards

> **Baseline**: baseline-2026-02-23 (86.0% pass rate)
> **Enforcement**: Mandatory for all new features
> **Status**: ✅ ACTIVE

---

## 🚦 Feature Gate Criteria

### ✅ PASS - Feature MAY Proceed

**Criteria (ALL must be satisfied)**:
1. ✅ Test pass rate ≥ 85.0% (currently 86.0%)
2. ✅ 0 flaky tests introduced (deterministic behavior)
3. ✅ Warnings controlled (max +10 from baseline)
4. ✅ Critical flows protected (BookingFlow 100%)
5. ✅ All new code has tests (no untested code)

**Verification**:
```bash
# Run full test suite
pytest app/tests/ -v

# Check pass rate
# Expected: ≥ 85.0% (currently 86.0%)

# Check for flaky tests (run 3 times)
pytest app/tests/ --count=3

# Check warnings
pytest app/tests/ -v 2>&1 | grep -c "DeprecationWarning\|PydanticDeprecated"
# Expected: ≤ 446 (baseline 436 + tolerance 10)
```

---

### ❌ BLOCK - Feature MUST NOT Proceed

**Blocking Conditions (ANY triggers block)**:
1. ❌ Test pass rate < 85.0%
2. ❌ Any flaky test introduced
3. ❌ Critical flow broken (BookingFlow < 100%)
4. ❌ New test failures (FAILED count > 0)
5. ❌ Uncontrolled warning explosion (>500 warnings)

**Action**: Fix issues before merge

---

## 🔒 Protected Critical Flows

### BookingFlow (100% - DO NOT BREAK)

**Protected Tests**:
- `test_complete_booking_flow_success` ✅
- `test_booking_flow_rule_violations` ✅

**Requirements**:
- Must maintain 100% pass rate (2/2 passing)
- Must use `time_provider` for time-based logic
- Must use `monkeypatch` for deterministic time control
- Must not introduce flakiness

**Breaking BookingFlow = Immediate Rollback**

---

## 📋 Pre-Merge Checklist

### Before Creating PR

- [ ] Local tests pass: `pytest app/tests/ -xvs`
- [ ] Pass rate ≥ 85%: `pytest app/tests/ -v | grep passed`
- [ ] No flaky tests: `pytest app/tests/ --count=3`
- [ ] BookingFlow protected: `pytest app/tests/test_critical_flows.py::TestBookingFlow -v`
- [ ] Warnings controlled: `pytest app/tests/ 2>&1 | grep -c Warning`

### During Code Review

- [ ] New code has tests (coverage ≥ existing baseline)
- [ ] No time-based flakiness (uses `time_provider` pattern)
- [ ] No schema mismatches (fixtures match models)
- [ ] P3 skips documented (if applicable)

### Before Merge

- [ ] CI pipeline green ✅
- [ ] All quality gates pass ✅
- [ ] Code review approved ✅
- [ ] No merge conflicts ✅

---

## 🎯 Time-Based Logic Standards

### ✅ CORRECT Pattern (Use time_provider)

```python
from app.core import time_provider

def validate_booking_deadline(session):
    """Validate 24h booking deadline (deterministic)"""
    current_time = time_provider.now().replace(tzinfo=None)
    session_start = session.date_start.replace(tzinfo=None)
    deadline = session_start - timedelta(hours=24)

    if current_time > deadline:
        raise ValidationError("Booking deadline passed")
```

**Test (deterministic)**:
```python
def test_booking_deadline(monkeypatch):
    # Control time for deterministic testing
    test_time = session.date_start - timedelta(hours=12)
    monkeypatch.setattr("app.core.time_provider.now", lambda: test_time)

    # Test proceeds with known time
    validate_booking_deadline(session)  # Should fail (< 24h)
```

---

### ❌ INCORRECT Pattern (Database manipulation)

```python
def test_booking_deadline():
    # ❌ ANTI-PATTERN: Manipulating DB for time
    session.date_start = datetime.now() + timedelta(hours=12)
    db.commit()  # ❌ DB session boundary violation

    validate_booking_deadline(session)  # ❌ Flaky (timing dependent)
```

**Why This Fails**:
- TestClient has separate DB session
- Changes not visible across session boundaries
- Non-deterministic (depends on test execution speed)
- Violates separation of concerns

---

## 📊 Warning Control

### Baseline State
- **Current Warnings**: 436
- **Tolerance**: +10 (max 446)
- **Hard Limit**: 500

### Warning Categories

**Acceptable** (temporary technical debt):
- Pydantic V1 deprecation (P4 cleanup planned)
- datetime.utcnow() deprecation (P4 cleanup planned)
- pytest config warnings (P4 cleanup planned)

**Unacceptable** (must fix immediately):
- Security warnings (e.g., SQL injection, XSS)
- Data integrity warnings (e.g., foreign key violations)
- Performance warnings (e.g., N+1 queries)

### Action on Warning Growth

**+1 to +10 warnings**: ✅ Acceptable (document reason)
**+11 to +50 warnings**: ⚠️ Review required (justify or fix)
**+51+ warnings**: ❌ Block merge (fix before proceeding)

---

## 🔄 P3 Skip Documentation

### When Skipping Tests

**Required Documentation**:
```python
@pytest.mark.skip(reason="P3: [Category] - [Root Cause]. [Resolution Path]. [Priority]")
def test_something():
    """Test description"""
    pass
```

**Example**:
```python
@pytest.mark.skip(reason="P3: Test references outdated API calculate_xp_for_attendance() which doesn't exist. "
                         "Production uses award_attendance_xp(attendance_id) from gamification/xp_service.py. "
                         "Requires test refactor to use existing gamification service API.")
def test_gamification_xp():
    """Test XP calculation"""
    pass
```

**Components**:
1. **Category**: API mismatch, feature gap, etc.
2. **Root Cause**: Why test is skipped
3. **Resolution Path**: How to fix
4. **Priority**: Always P3 (unless critical)

---

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Quality Gate

on: [pull_request]

jobs:
  quality-gate:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest app/tests/ -v --tb=short > test_results.txt

      - name: Check pass rate
        run: |
          # Extract pass rate
          PASSED=$(grep -oP '\d+(?= passed)' test_results.txt)
          TOTAL=$(grep -oP '\d+(?= passed)|(?<=, )\d+(?= skipped)' test_results.txt | awk '{s+=$1} END {print s}')
          PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")

          echo "Pass Rate: $PASS_RATE%"

          if (( $(echo "$PASS_RATE < 85.0" | bc -l) )); then
            echo "❌ FAIL: Pass rate $PASS_RATE% < 85.0%"
            exit 1
          fi

          echo "✅ PASS: Pass rate $PASS_RATE% ≥ 85.0%"

      - name: Check flaky tests
        run: |
          # Run tests 3 times
          pytest app/tests/ --count=3 -v

      - name: Check warnings
        run: |
          WARNINGS=$(pytest app/tests/ -v 2>&1 | grep -c "Warning" || true)

          if (( $WARNINGS > 500 )); then
            echo "❌ FAIL: $WARNINGS warnings > 500 limit"
            exit 1
          fi

          echo "✅ PASS: $WARNINGS warnings ≤ 500 limit"
```

---

## 📖 Developer Workflow

### Step-by-Step Feature Development

1. **Pre-Development**
   ```bash
   # Ensure baseline is clean
   git checkout main
   git pull origin main
   pytest app/tests/ -v  # Should show 86.0% pass rate
   ```

2. **Development**
   ```bash
   # Create feature branch
   git checkout -b feature/my-new-feature

   # Develop feature + tests
   # Use time_provider for time-based logic
   # Write deterministic tests
   ```

3. **Local Verification**
   ```bash
   # Run affected tests
   pytest app/tests/test_my_feature.py -xvs

   # Run full suite
   pytest app/tests/ -v

   # Check pass rate (must be ≥ 85%)
   pytest app/tests/ -v | grep passed

   # Check for flakiness (run 3x)
   pytest app/tests/ --count=3
   ```

4. **Pre-PR Checklist**
   - [ ] All local tests pass
   - [ ] Pass rate ≥ 85%
   - [ ] No flaky tests
   - [ ] BookingFlow 100%
   - [ ] Warnings controlled

5. **Create PR**
   - Wait for CI pipeline
   - Address any quality gate failures
   - Get code review approval

6. **Merge**
   - Squash commits (clean history)
   - Merge to main
   - Verify production deployment

---

## 🎓 Examples

### Example 1: Feature Passes Gate ✅

**Scenario**: Add new tournament type validation

**Metrics**:
- Tests: 230 passed, 37 skipped (86.2% pass rate) ✅
- Flaky: 0 ✅
- BookingFlow: 2/2 passing ✅
- Warnings: 440 (baseline 436 + 4 new) ✅

**Result**: ✅ PASS - Feature may proceed

---

### Example 2: Feature Fails Gate ❌

**Scenario**: Refactor booking logic

**Metrics**:
- Tests: 225 passed, 40 failed, 37 skipped (84.5% pass rate) ❌
- Flaky: 2 tests fail intermittently ❌
- BookingFlow: 1/2 passing ❌
- Warnings: 438 ✅

**Result**: ❌ BLOCK - Must fix before merge

**Action Required**:
1. Fix 40 failing tests (pass rate < 85%)
2. Fix 2 flaky tests (zero tolerance)
3. Fix BookingFlow regression (critical flow)
4. Re-run quality gate

---

## 📊 Monitoring & Reporting

### Weekly Baseline Health Check

```bash
# Run every Monday
pytest app/tests/ -v --tb=short > weekly_report.txt

# Check metrics
PASSED=$(grep -oP '\d+(?= passed)' weekly_report.txt)
PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/265)*100}")
WARNINGS=$(grep -c "Warning" weekly_report.txt || echo 0)

echo "Weekly Health Report:"
echo "- Pass Rate: $PASS_RATE% (baseline: 86.0%)"
echo "- Warnings: $WARNINGS (baseline: 436)"
echo "- Status: $([ $(echo "$PASS_RATE >= 85.0" | bc -l) -eq 1 ] && echo "✅ HEALTHY" || echo "❌ DEGRADED")"
```

---

**Created**: 2026-02-23 15:30 CET
**Enforcement Start**: Immediate
**Review Cycle**: Monthly
**Status**: ✅ ACTIVE
