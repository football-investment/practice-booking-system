# E2E Testing Policy — Integration Critical Suite

> **Status**: ENFORCED (BLOCKING gates in CI)
> **Last Updated**: 2026-02-23
> **Owner**: Engineering Team

---

## 1. Overview

The **Integration Critical Suite** validates all revenue-critical and business-critical workflows end-to-end with **zero tolerance for flake** and **strict runtime thresholds**. All tests in this suite are **BLOCKING** in CI — no PR can merge if any test fails.

### Scope

- **Payment workflow**: Invoice → verification → credit allocation
- **Student lifecycle**: Enrollment → credit deduction → concurrent safety
- **Instructor lifecycle**: Assignment → check-in → result submission
- **Refund workflow**: Withdrawal → 50% refund → transaction audit
- **Multi-campus**: Round-robin distribution → campus isolation

---

## 2. Zero Flake Tolerance Policy

### Definition

**Flake** = any test that passes on retry after an initial failure without code changes.

### Requirements

- **Sequential validation**: Every test must pass 20 consecutive runs with 0 failures
- **Parallel validation**: Every test must pass `pytest -n auto` (race condition validation)
- **CI enforcement**: Tests run both sequentially (20x) and in parallel on every PR

### Rationale

Flaky tests:
- Mask real bugs (intermittent failures ignored as "just flake")
- Erode team confidence in test suite
- Waste engineering time on retries and investigation
- Block deployments with false negatives

**Zero tolerance** means:
- If a test fails once in 20 runs → investigate immediately
- If a test fails in parallel mode → race condition bug (FIX, don't skip)
- No retries, no "acceptable flake rate" — 100% pass or fail

### Flake Root Causes (and Solutions)

| Root Cause | Solution |
|------------|----------|
| Test state pollution | Isolated fixtures (`create_test_user()` per test) |
| Race conditions | Atomic operations (SELECT FOR UPDATE) + parallel validation |
| Timing dependencies | Polling with timeouts (not hardcoded sleeps) |
| External service flake | Mock external services in critical tests |
| Database state leakage | Transaction rollback in fixtures + fresh DB per test |

---

## 3. Runtime Threshold Policy

### Thresholds

| Test Suite | p95 Threshold | Enforcement |
|------------|---------------|-------------|
| Payment workflow | <5s | HARD FAIL if >6s (20% regression) |
| Student lifecycle | <30s | HARD FAIL if >36s (20% regression) |
| Instructor lifecycle | <30s | HARD FAIL if >36s (20% regression) |
| Refund workflow | <20s | HARD FAIL if >24s (20% regression) |
| Multi-campus | <30s | HARD FAIL if >36s (20% regression) |

### Regression Alert

CI fails if runtime exceeds **threshold + 20%**:
- Payment: 5s → 6s alert → **FAIL**
- Student/Instructor/Multi-campus: 30s → 36s alert → **FAIL**
- Refund: 20s → 24s alert → **FAIL**

### Runtime Monitoring

```yaml
# CI step example
- name: Run Student Lifecycle Tests (Sequential - 20x validation)
  run: |
    START_TIME=$(date +%s)
    pytest tests_e2e/integration_critical/test_student_lifecycle.py --count=20 -v
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))

    # Threshold: 30s * 20 runs = 600s baseline
    # Alert: 600s * 1.2 = 720s (20% regression)
    if [ $ELAPSED -gt 720 ]; then
      echo "::error::Runtime regression detected: ${ELAPSED}s (threshold: 720s)"
      exit 1
    fi
```

### Performance Budget

Test suite must stay **fast enough for pre-merge CI**:
- Total E2E suite runtime: <10 minutes (target: 5 minutes)
- Individual test runtime: <30s (except multi-campus, which involves 16 users)
- Payment tests: <5s (hot path, revenue-critical)

---

## 4. Test Isolation Requirements

### Per-Test Isolation

Every test must:
1. **CREATE** fresh test data (users, licenses, credits, tournaments)
2. **USE** isolated test data (no dependency on pre-existing state)
3. **CLEANUP** all created data in `finally` block

Example:
```python
@pytest.mark.integration_critical
def test_student_enrollment(api_url, admin_token):
    created_users = []

    try:
        # CREATE fresh student
        student = create_test_user(api_url, admin_token, timestamp=int(time.time() * 1000))
        created_users.append(student)

        # USE isolated student for test
        # ... test logic ...

    finally:
        # CLEANUP
        for user in created_users:
            delete_test_user(api_url, admin_token, user["id"])
```

### Fixture Reuse Policy

- ✅ **ALLOWED**: `api_url`, `admin_token`, `test_campus_ids` (infrastructure)
- ❌ **PROHIBITED**: `test_students`, `test_instructor` (state-dependent)
  - Reason: Shared fixtures cause state pollution between tests
  - Solution: Create fresh users per test

### Database Isolation

- Each test gets a **clean database state** (no residual data from previous tests)
- Use transactions + rollback in fixtures (where applicable)
- For E2E tests: explicit cleanup in `finally` block

---

## 5. Parallel Execution Requirements

### Race Condition Validation

All tests must pass with `pytest -n auto`:
- **Purpose**: Catch race conditions early (concurrent requests, shared state)
- **Enforcement**: CI runs both sequential (20x) AND parallel

### Atomic Operations

Tests involving concurrent requests must use **atomic UPDATE** operations:
```python
# Example: Credit deduction (atomic)
user_license = db.query(UserLicense).filter(
    UserLicense.user_id == user_id
).with_for_update().first()  # ← Row-level lock

if user_license.credit_balance < cost:
    raise InsufficientCreditsError()

user_license.credit_balance -= cost
db.commit()
```

### Isolation in Parallel Mode

- Each test creates **unique** test data (timestamp-based names)
- No shared state between parallel workers
- Database transactions isolated per worker

---

## 6. CI Enforcement

### BLOCKING Gates

All Integration Critical tests are **BLOCKING** in CI:

```yaml
# .github/workflows/test-baseline-check.yml
baseline-report:
  needs: [
    unit-tests,
    payment-workflow-gate,         # BLOCKING
    student-lifecycle-gate,        # BLOCKING (NEW)
    instructor-lifecycle-gate,     # BLOCKING (NEW)
    refund-workflow-gate,          # BLOCKING (NEW)
    multi-campus-gate,             # BLOCKING (NEW)
  ]
```

### Failure Policy

If **any** gate fails:
- ❌ PR cannot merge
- ⚠️ GitHub status check: "Test Baseline FAILED"
- 📋 Baseline report shows which gate failed
- 🔒 Deployment pipeline blocked

### Success Criteria

All gates must show:
- ✅ 20/20 sequential runs PASSED (0 flake)
- ✅ Parallel execution PASSED (race condition safe)
- ✅ Runtime within threshold (no >20% regression)

---

## 7. Test Development Guidelines

### Before Writing a New E2E Test

1. **Check if test exists**: Search for similar test before duplicating
2. **Define success criteria**:
   - What exact scenario are you testing?
   - What's the expected outcome?
   - What's the failure mode?
3. **Plan isolation**: How will you create/cleanup test data?
4. **Estimate runtime**: Will it stay under threshold?

### Test Structure Template

```python
@pytest.mark.e2e
@pytest.mark.integration_critical
def test_workflow_name(api_url: str, admin_token: str):
    """
    Brief description of workflow being tested.

    Workflow:
    1. CREATE fresh test data
    2. Execute workflow step 1
    3. Execute workflow step 2
    4. Verify expected outcome
    5. CLEANUP test data

    Expected Runtime: <Xs
    Priority: HIGH/MEDIUM/LOW
    Blocking: YES/NO
    """
    created_resources = []

    try:
        # STEP 1: CREATE fresh test data
        # ... (create users, credits, tournaments, etc.)

        # STEP 2-N: Execute workflow
        # ... (API calls, verifications)

        # FINAL: Assertions
        assert outcome == expected

    finally:
        # CLEANUP: Delete all created resources
        for resource in created_resources:
            delete_resource(api_url, admin_token, resource["id"])
```

### Debugging Flaky Tests

If a test fails intermittently:

1. **Reproduce locally**:
   ```bash
   pytest tests_e2e/integration_critical/test_workflow.py --count=20 -v
   ```

2. **Check for race conditions**:
   ```bash
   pytest tests_e2e/integration_critical/test_workflow.py -n auto -v
   ```

3. **Enable verbose logging**:
   ```bash
   pytest tests_e2e/integration_critical/test_workflow.py -v --tb=short -s
   ```

4. **Isolate the test**:
   - Run test alone (not in suite)
   - Check for database state pollution
   - Verify cleanup is working

5. **Fix root cause** (don't skip or retry):
   - Add missing locks (SELECT FOR UPDATE)
   - Fix state pollution (create fresh data)
   - Remove timing dependencies (use polling)

---

## 8. Maintenance and Monitoring

### Weekly Health Check

- [ ] All Integration Critical tests passing in CI (100% GREEN)
- [ ] No runtime regressions (check baseline report)
- [ ] No skipped tests in critical suite
- [ ] Documentation up to date

### Monthly Review

- [ ] Review test runtimes (identify slow tests)
- [ ] Check for duplicate tests (consolidate if needed)
- [ ] Update thresholds if infrastructure changes
- [ ] Archive obsolete tests

### Quarterly Audit

- [ ] Full suite refactoring (remove technical debt)
- [ ] Performance optimization (identify bottlenecks)
- [ ] Policy review (adjust thresholds if needed)
- [ ] Team training on test best practices

---

## 9. FAQ

### Q: Why 20x sequential validation? Why not 10x or 50x?

**A**: 20 runs strikes a balance:
- 10 runs: Not enough to catch rare flake (90% flake = 1 failure in 10)
- 20 runs: Catches 95% flake with high confidence
- 50 runs: Diminishing returns (runtime cost vs. flake detection)

Statistical confidence: If a test has 5% flake rate, probability of 20/20 passes = (0.95)^20 = 36% → we catch it 64% of the time.

### Q: What if a test genuinely needs >30s runtime?

**A**: Break it into smaller tests:
- Multi-step workflows → split into separate tests
- Large data sets → reduce to minimum viable scenario
- Multiple validations → separate test per validation

If truly irreducible: request threshold exception (requires team approval).

### Q: Can I skip parallel validation for a specific test?

**A**: No. Parallel execution is **mandatory** for all Integration Critical tests.
- If test fails in parallel → **fix the race condition** (don't skip)
- If test is not parallelizable → it doesn't belong in Integration Critical suite

### Q: What about flake from external services (Stripe, email, etc.)?

**A**: Mock external services in critical tests:
- Stripe payment: Mock webhook, use test mode API
- Email delivery: Mock SMTP, verify send() called (not delivery)
- File uploads: Mock S3, verify upload() called

Real external integrations belong in **smoke tests** (allowed to flake, not blocking).

---

## 10. References

- [INTEGRATION_CRITICAL_BACKLOG.md](../INTEGRATION_CRITICAL_BACKLOG.md) — Test implementation backlog
- [PAYMENT_WORKFLOW_GAP_SPECIFICATION.md](../PAYMENT_WORKFLOW_GAP_SPECIFICATION.md) — Payment test specs
- [PERFORMANCE_BASELINE_SPECIFICATION.md](../PERFORMANCE_BASELINE_SPECIFICATION.md) — Performance requirements
- [CI Workflow](.github/workflows/test-baseline-check.yml) — BLOCKING gates implementation

---

**Summary**: Zero flake tolerance + strict runtime thresholds = reliable, fast E2E test suite that blocks bugs before they reach production. No exceptions, no retries, no "acceptable flake rate" — 100% GREEN or fix the test.
