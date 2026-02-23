# Lifecycle Suite Monitoring — First 10 CI Runs & Runtime Metrics

> **Status**: ACTIVE MONITORING
> **Start Date**: 2026-02-23
> **Goal**: Validate 0 flake tolerance + establish runtime baselines
> **Owner**: Engineering Team

---

## 1. First 10 CI Runs — Validation Checklist

### Monitoring Period

- **Start**: First PR merge after Phase F deployment
- **Duration**: 10 consecutive CI runs (main branch + PR merges)
- **Expected timeline**: 1-2 weeks (depending on PR velocity)

### Success Criteria

All 10 runs must show:
- ✅ **0 flake**: All Integration Critical tests pass 20/20 sequential runs
- ✅ **Parallel stable**: All tests pass `pytest -n auto` with no race conditions
- ✅ **Runtime stable**: No runs exceed baseline thresholds + 20%
- ✅ **No false positives**: No tests fail due to infrastructure issues

### Per-Run Checklist

For each CI run, verify:

```markdown
## CI Run #X (Date: YYYY-MM-DD, PR: #XXX, Branch: XXX)

### Gate Results
- [ ] Unit tests: PASSED
- [ ] Payment workflow E2E: PASSED (sequential 20x + parallel)
- [ ] Student lifecycle E2E: PASSED (sequential 20x + parallel)
- [ ] Instructor lifecycle E2E: PASSED (sequential 20x + parallel)
- [ ] Refund workflow E2E: PASSED (sequential 20x + parallel)
- [ ] Multi-campus E2E: PASSED (sequential 20x + parallel)

### Runtime Metrics
- Payment workflow: XXs (threshold: 5s baseline, 6s alert)
- Student lifecycle: XXs (threshold: 30s baseline, 36s alert)
- Instructor lifecycle: XXs (threshold: 30s baseline, 36s alert)
- Refund workflow: XXs (threshold: 20s baseline, 24s alert)
- Multi-campus: XXs (threshold: 30s baseline, 36s alert)
- **Total E2E suite runtime**: XXs (target: <10 minutes)

### Flake Analysis
- [ ] 0 intermittent failures (any test failed then passed on retry)
- [ ] 0 infrastructure timeouts (DB connection, API startup, etc.)
- [ ] 0 race condition failures (parallel execution clean)

### Issues Found
- [ ] None OR [Issue #XXX] [Description] [Root cause] [Fix status]

### Sign-off
- Reviewer: @username
- Status: ✅ PASS / ❌ FAIL (if fail, block next run until fixed)
```

### Escalation Policy

If **any** run shows flake or runtime regression:
1. **Immediate**: Create GitHub issue with `priority:critical` label
2. **Within 1 hour**: Team lead investigates root cause
3. **Within 4 hours**: Fix merged OR test temporarily disabled (with issue tracking re-enablement)
4. **Reset counter**: Start 10-run validation from scratch after fix

### Data Collection

Track all metrics in `CI_METRICS.csv`:
```csv
run_id,date,pr_number,branch,payment_ms,student_ms,instructor_ms,refund_ms,multicampus_ms,total_ms,flake_count,pass_fail
1,2026-02-23,#123,main,4200,28500,27800,18900,29100,580000,0,PASS
2,2026-02-24,#124,feature/X,4300,29000,28200,19100,29500,590000,0,PASS
...
```

---

## 2. Runtime Metrics Dashboard

### Overview

Real-time dashboard tracking E2E test performance and regression trends.

### Metrics to Track

| Metric | Formula | Alert Threshold | Action |
|--------|---------|-----------------|--------|
| **Average runtime** | sum(runtimes) / count(runs) | >15% above baseline | Investigate slow tests |
| **Max runtime** | max(runtimes) | >20% above baseline | **FAIL CI** (regression) |
| **p95 runtime** | 95th percentile | >20% above baseline | Warning (approaching limit) |
| **Flake rate** | flake_count / total_runs | >0% | **IMMEDIATE escalation** |
| **Parallel failure rate** | parallel_fails / total_runs | >0% | Race condition investigation |

### Baseline Values (Established from Local Runs)

| Test Suite | Baseline (avg) | p95 Threshold | Alert Threshold |
|------------|----------------|---------------|-----------------|
| Payment workflow | 4.5s | 5s | 6s (20% regression) |
| Student lifecycle | 28s | 30s | 36s (20% regression) |
| Instructor lifecycle | 27s | 30s | 36s (20% regression) |
| Refund workflow | 19s | 20s | 24s (20% regression) |
| Multi-campus | 29s | 30s | 36s (20% regression) |
| **Total E2E suite** | **~8 minutes** | **10 minutes** | **12 minutes** |

### Dashboard Implementation (GitHub Actions Summary)

Use GitHub Actions job summary to display metrics:

```yaml
- name: Runtime Metrics Dashboard
  run: |
    echo "## E2E Test Runtime Metrics" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "| Test Suite | Runtime | Baseline | Threshold | Status |" >> $GITHUB_STEP_SUMMARY
    echo "| --- | --- | --- | --- | --- |" >> $GITHUB_STEP_SUMMARY
    echo "| Payment workflow | ${PAYMENT_TIME}s | 5s | 6s | ✅ OK |" >> $GITHUB_STEP_SUMMARY
    echo "| Student lifecycle | ${STUDENT_TIME}s | 30s | 36s | ✅ OK |" >> $GITHUB_STEP_SUMMARY
    echo "| Instructor lifecycle | ${INSTRUCTOR_TIME}s | 30s | 36s | ✅ OK |" >> $GITHUB_STEP_SUMMARY
    echo "| Refund workflow | ${REFUND_TIME}s | 20s | 24s | ✅ OK |" >> $GITHUB_STEP_SUMMARY
    echo "| Multi-campus | ${MULTICAMPUS_TIME}s | 30s | 36s | ✅ OK |" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "**Total E2E Runtime**: ${TOTAL_TIME}s (Target: <600s)" >> $GITHUB_STEP_SUMMARY
```

### Weekly Report Template

```markdown
## Weekly E2E Performance Report (Week XX, YYYY)

### Summary
- Total CI runs: X
- Flake count: 0 ✅
- Average total runtime: Xs (target: <600s)
- Slowest run: Xs (run #X)
- Fastest run: Xs (run #X)

### Runtime Trends
| Test Suite | Avg Runtime | Min | Max | Trend |
|------------|-------------|-----|-----|-------|
| Payment | 4.5s | 4.2s | 4.8s | → Stable |
| Student | 28.5s | 27.8s | 29.2s | ↑ +1.5% |
| Instructor | 27.8s | 27.5s | 28.3s | → Stable |
| Refund | 19.2s | 18.9s | 19.5s | → Stable |
| Multi-campus | 29.3s | 29.0s | 29.6s | → Stable |

### Regression Alerts
- [ ] No regressions OR [Issue #XXX] [Test] [Regression %] [Status]

### Action Items
- [ ] None OR [Action] [Owner] [Deadline]
```

---

## 3. Lifecycle Suite = Release Gate Policy

### Official Policy Statement

**Effective Date**: 2026-02-23

> **All production releases MUST pass the full Lifecycle Suite (100% GREEN) before deployment.**
>
> The Lifecycle Suite is the **final quality gate** for all code changes. No exceptions.

### Release Checklist

Before any production deployment:

1. **Pre-Release Validation**:
   - [ ] All Integration Critical tests passing (20x sequential + parallel)
   - [ ] No flake detected in last 10 CI runs
   - [ ] Runtime metrics within thresholds
   - [ ] No skipped tests in critical suite

2. **Release Approval**:
   - [ ] CI baseline report shows "Safe to merge ✅"
   - [ ] All BLOCKING gates passed (11 gates total)
   - [ ] Manual smoke test passed (optional, for major releases)

3. **Post-Release Monitoring**:
   - [ ] Production health check passed (first 5 minutes)
   - [ ] Error rate within normal range (first 24 hours)
   - [ ] Rollback plan ready (in case of critical issues)

### Deployment Flow

```mermaid
graph TD
    A[PR Created] --> B[CI Runs All Gates]
    B --> C{All Gates GREEN?}
    C -->|NO| D[❌ Block Merge]
    C -->|YES| E[✅ Merge Allowed]
    E --> F[Main Branch CI Validation]
    F --> G{Baseline GREEN?}
    G -->|NO| H[❌ Block Release]
    G -->|YES| I[🚀 Deploy to Production]
    I --> J[Post-Deploy Health Check]
```

### Enforcement Mechanism

GitHub branch protection rules:
- **Required status checks**: All 11 gates must pass
- **No bypass**: Even admins cannot skip checks
- **No force push**: Prevent accidental bypassing
- **Stale review dismissal**: Re-run CI on new commits

---

## 4. New Critical Feature Guidelines

### When to Add E2E Test + CI Gate

**Every new critical feature MUST include**:
1. E2E test in `tests_e2e/integration_critical/`
2. BLOCKING gate in `.github/workflows/test-baseline-check.yml`
3. Documentation in `E2E_TESTING_POLICY.md`

**Critical feature** = any feature that:
- Handles money (payments, refunds, credits)
- Affects user access (enrollment, authentication, authorization)
- Changes core business logic (tournament lifecycle, session scheduling)
- Impacts data integrity (concurrent operations, atomic updates)

### E2E Test Implementation Checklist

Before adding new E2E test:

1. **Plan**:
   - [ ] Define workflow (step-by-step user scenario)
   - [ ] Identify success criteria (what must be validated?)
   - [ ] Estimate runtime (will it stay under 30s?)
   - [ ] Plan isolation (CREATE + CLEANUP strategy)

2. **Implement**:
   - [ ] Write test following template (see `E2E_TESTING_POLICY.md` Section 7)
   - [ ] Validate locally: 20x sequential PASS (0 flake)
   - [ ] Validate locally: parallel PASS (`pytest -n auto`)
   - [ ] Measure runtime (must be <30s for lifecycle tests)

3. **Add CI Gate**:
   - [ ] Create new job in `test-baseline-check.yml`
   - [ ] Add sequential step (20x validation)
   - [ ] Add parallel step (race condition validation)
   - [ ] Add to `baseline-report` needs list

4. **Document**:
   - [ ] Update `E2E_TESTING_POLICY.md` with new test
   - [ ] Add test to `INTEGRATION_CRITICAL_BACKLOG.md` (mark complete)
   - [ ] Update baseline report success criteria

### CI Gate Template

```yaml
new-feature-gate:
  name: New Feature E2E (BLOCKING)
  runs-on: ubuntu-latest
  needs: unit-tests

  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
        POSTGRES_DB: lfa_intern_system_test
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
      ports:
        - 5432:5432

  steps:
  - uses: actions/checkout@v3

  - name: Set up Python 3.12
    uses: actions/setup-python@v4
    with:
      python-version: '3.12'
      cache: 'pip'

  - name: Install dependencies
    run: |
      python -m pip install --upgrade pip
      pip install -r requirements.txt
      pip install -r requirements-test.txt
      pip install pytest pytest-xdist pytest-repeat
      pip check

  - name: Run DB migrations
    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test
      SECRET_KEY: test-secret-key-for-ci-only-not-production
    run: alembic upgrade head

  - name: Start FastAPI backend
    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test
      SECRET_KEY: test-secret-key-for-ci-only-not-production
    run: |
      uvicorn app.main:app --host 0.0.0.0 --port 8000 &
      sleep 5
      curl --fail http://localhost:8000/health || exit 1

  - name: Run New Feature Tests (Sequential - 20x validation)
    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test
      SECRET_KEY: test-secret-key-for-ci-only-not-production
    run: |
      PYTHONPATH=. pytest tests_e2e/integration_critical/test_new_feature.py \
        --count=20 \
        -v \
        --tb=short \
        -ra

  - name: Run New Feature Tests (Parallel - race condition validation)
    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lfa_intern_system_test
      SECRET_KEY: test-secret-key-for-ci-only-not-production
    run: |
      PYTHONPATH=. pytest tests_e2e/integration_critical/test_new_feature.py \
        -n auto \
        -v \
        --tb=short \
        -ra

  - name: New feature gate failure
    if: failure()
    run: |
      echo "::error::New feature tests failed - merge blocked"
      echo "New feature workflow broken."
      echo "Required: 0 flake in 20 runs, <30s runtime, parallel execution stable"
      exit 1
```

### Review Process

All new E2E tests must be reviewed for:
- [ ] **Isolation**: Test creates + cleans up own data
- [ ] **Performance**: Runtime <30s (or justified exception)
- [ ] **Stability**: 20x local run shows 0 flake
- [ ] **Parallel safety**: No race conditions in parallel mode
- [ ] **Coverage**: Test validates critical business logic (not just happy path)

---

## 5. Maintenance Discipline

### Daily Checks (Automated)

CI automatically validates:
- ✅ All gates passing (no manual intervention)
- ✅ Runtime within thresholds (auto-fail on regression)
- ✅ Flake detection (immediate alert on any failure)

### Weekly Reviews (Manual)

Engineering lead reviews:
- [ ] Weekly runtime report (identify slow tests)
- [ ] Flake incidents (should be 0)
- [ ] CI queue times (are gates blocking PRs?)
- [ ] Test coverage gaps (new features without E2E?)

### Monthly Audits

Team meeting agenda:
1. Review runtime trends (any degradation?)
2. Identify duplicate tests (consolidate if needed)
3. Check for skipped tests (re-enable or delete)
4. Update thresholds if infrastructure changed
5. Plan test suite optimizations

### Quarterly Deep Dives

Full suite refactoring session:
- Remove technical debt (obsolete tests)
- Optimize slow tests (reduce runtime)
- Update policy if needed (adjust thresholds)
- Team training on best practices

---

## 6. Rollback Plan

### If Lifecycle Suite Becomes Unstable

Emergency procedures:

1. **Immediate (within 1 hour)**:
   - Identify failing test (which gate?)
   - Check if infrastructure issue (DB, API, network)
   - If infrastructure: fix and re-run
   - If test issue: proceed to step 2

2. **Short-term (within 4 hours)**:
   - Create hotfix branch
   - Fix root cause OR temporarily disable failing test
   - If disabled: create `priority:critical` issue for re-enablement
   - Merge hotfix with expedited review

3. **Long-term (within 24 hours)**:
   - Root cause analysis (why did test become flaky?)
   - Permanent fix (race condition, state pollution, etc.)
   - Re-enable test with 20x validation
   - Update documentation with lessons learned

### When to Disable a Gate

**ONLY disable a gate if**:
- Infrastructure issue cannot be fixed within 4 hours
- Test has fundamental design flaw requiring rewrite
- Feature was rolled back (test no longer applicable)

**NEVER disable a gate for**:
- "Temporary" flake (fix the flake, don't disable)
- "It passed locally" (debug CI environment, don't skip)
- "We need to ship fast" (fast shipping is not worth broken quality gate)

---

## 7. Success Metrics

### Week 1 Target
- 10/10 CI runs GREEN (0 flake)
- Average runtime: <10 minutes
- 0 false positives (infrastructure issues)

### Month 1 Target
- 40/40 CI runs GREEN (0 flake)
- Runtime stable (±5% variance)
- 0 disabled gates (all active)

### Quarter 1 Target
- 100% of PRs pass first CI run (no retries needed)
- Team adoption: All new critical features have E2E tests
- Documentation up to date: All tests documented in policy

---

**Summary**: First 10 runs validate stability → Metrics dashboard tracks performance → Lifecycle Suite = Release Gate → New features require E2E + CI gate → Discipline maintains quality forever. 🎯

**Status**: MONITORING ACTIVE — Track first 10 CI runs starting NOW.
