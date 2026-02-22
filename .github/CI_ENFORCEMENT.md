# CI Enforcement — Fast Suite Quality Gate

> **Status:** Production-ready baseline established
> **Baseline tag:** `e2e-fast-suite-stable-v1` (52/52 PASS)
> **Date:** 2026-02-22

---

## 🎯 Quality Rules (MANDATORY)

### New Feature Merge Requirements

A new feature is **ONLY** mergeable if:

1. ✅ **Fast Suite 100% PASS** — No regressions allowed
2. ✅ **No new flaky tests** — Deterministic assertions only
3. ✅ **Baseline updated** — [E2E_STABILITY_BASELINE.md](../E2E_STABILITY_BASELINE.md) reflects current state
4. ✅ **Fixture = authority** — Tests own their preconditions (no seed data dependency)

**Status:** No longer in firefighting mode → **Quality-driven development phase**

---

## 🔧 CI Configuration

### Default CI Run (Required)

**Command:**
```bash
pytest -m "not scale_suite" --tb=short -ra
```

**Coverage:**
- Fast Suite: 52 tests (blocks 1-6)
- Execution time: ~3-5 minutes
- Test isolation: Confirmed
- Migration state: Clean

**Failure mode:** Block PR merge if any test fails

---

### Scale Suite (Optional Capacity Validation)

**Trigger:** Nightly or manual workflow dispatch

**Command:**
```bash
pytest -m "scale_suite" --tb=short -ra
```

**Coverage:**
- 128-1024 player boundary tests
- Large-field tournament engine validation
- Infrastructure capacity checks

**Failure mode:** Informational (does not block merge)

---

## 📦 CI Workflow Structure

### Recommended GitHub Actions Workflow

```yaml
name: E2E Fast Suite

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  fast-suite:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          playwright install chromium

      - name: Run database migrations
        run: alembic upgrade head

      - name: Run Fast Suite
        run: |
          pytest tests_e2e/ \
            -m "not scale_suite" \
            --tb=short \
            -ra \
            --maxfail=1

      - name: Upload failure screenshots
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-screenshots
          path: tests_e2e/screenshots/*_FAILED.png

    # CRITICAL: Fast Suite must ALWAYS pass
    # No optional flags, no skip conditions
```

### Scale Suite Workflow (Separate)

```yaml
name: E2E Scale Suite (Nightly)

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
  workflow_dispatch:  # Manual trigger

jobs:
  scale-suite:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      # ... (same setup as Fast Suite) ...

      - name: Run Scale Suite
        run: |
          pytest tests_e2e/ \
            -m "scale_suite" \
            --tb=short \
            -ra

      - name: Notify on failure
        if: failure()
        # Send Slack/email notification (informational only)
```

---

## 🚫 Fast Suite is NEVER Optional

**Enforcement rules:**

1. **No skip markers** on Fast Suite tests (unless temporarily broken, with tracking issue)
2. **No CI bypass** — Even hotfixes must pass Fast Suite
3. **No "run tests later"** — Tests run BEFORE merge, not after
4. **No selective runs** — All 52 Fast Suite tests must execute

**Rationale:**
Fast Suite is production readiness validation. Skipping it is equivalent to deploying untested code.

---

## 📊 Baseline Regression Protection

### Reference Tag

```bash
git tag e2e-fast-suite-stable-v1
```

**Purpose:**
- Snapshot of 100% stable state (52/52 PASS)
- Reference point for all future regression investigations
- Rollback target if major instability introduced

### Regression Detection

If a test fails that was previously stable:

1. **Compare with baseline tag:**
   ```bash
   git diff e2e-fast-suite-stable-v1 -- tests_e2e/
   ```

2. **Identify root cause:**
   - Code change in PR?
   - Backend behavior change?
   - Test flakiness (unacceptable in Fast Suite)?

3. **Resolution path:**
   - Fix the regression (preferred)
   - OR revert the breaking change
   - OR fix the test expectation (only if backend behavior is intentional)

4. **Update baseline:**
   - If legitimate test update, document in [E2E_STABILITY_BASELINE.md](../E2E_STABILITY_BASELINE.md)
   - Create new stability tag when major milestone reached

---

## 🔬 Next Quality Upgrade (Future Work)

### Lifecycle Blocks Isolation (Blocks 4-5)

**Current state:**
- Blocks 4 (Tournament Lifecycle) and 5 (Skill Progression) have fixture dependencies
- Tests skip when run in isolation ("No ops_seed tests collected")
- Stable when run as part of comprehensive suite

**Goal:**
- Minimize fixture dependencies
- Achieve complete block independence
- Enable isolated block execution for faster debugging

**Not urgent:** Blocks are functionally stable (4/4 + 5/5 PASS in comprehensive runs)

**Priority:** Low (architectural improvement, not stability fix)

---

## 📌 Summary

| Item | Status |
|---|---|
| **Fast Suite** | ✅ 52/52 PASS (100%) — Production Ready |
| **Scale Suite** | ⏸️ 2 tests deferred (optional) |
| **Migration State** | ✅ Clean and production-ready |
| **Baseline Tag** | ✅ `e2e-fast-suite-stable-v1` |
| **CI Enforcement** | 🔧 To be implemented (this document) |
| **Quality Phase** | ✅ Firefighting → Quality-driven development |

**Next action:** Implement CI workflows per this specification.

---

**Maintained by:** E2E Test Stability Team
**Last updated:** 2026-02-22
**Reference:** [E2E_STABILITY_BASELINE.md](../E2E_STABILITY_BASELINE.md)
