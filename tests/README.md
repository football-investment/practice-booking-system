# Test Suite - Quick Start

**New here? Read this first. Takes < 3 minutes.**

---

## 🚀 Quick Start (30 seconds)

```bash
# Run all tests
pytest

# Run smoke tests (< 2 min target)
pytest -m smoke -v

# Run by tournament format
pytest -m h2h -v                  # HEAD_TO_HEAD
pytest -m individual_ranking -v   # INDIVIDUAL_RANKING
pytest -m group_knockout -v       # GROUP_AND_KNOCKOUT

# Run production critical (MUST pass before deploy)
pytest -m golden_path -v
```

---

## 📁 Test Organization (1 minute)

```
tests/
├── unit/           # 60-70% target - Fast, isolated (< 1s each)
│   └── services/   # Business logic unit tests
├── integration/    # 20-30% target - Multi-component (< 5s each)
│   └── tournament/ # Tournament integration tests
├── e2e/            # 5-10% target - Full workflow (< 30s each)
│   ├── golden_path/         # ⚠️ Production critical
│   └── instructor_workflow/ # Instructor E2E
├── e2e_frontend/   # Frontend E2E by format
│   ├── head_to_head/
│   ├── individual_ranking/
│   ├── group_knockout/
│   └── shared/     # Shared helpers
├── api/            # API endpoint tests
├── manual/         # Manual scripts (NOT in CI/CD)
├── debug/          # Debug tests (NOT in CI/CD)
└── .archive/       # Deprecated tests
```

**Rule:** Unit test first. Integration if database needed. E2E only for critical user journeys.

---

## 🏷️ Pytest Markers (30 seconds)

```bash
# By test level
pytest -m unit            # Unit tests only
pytest -m integration     # Integration tests only
pytest -m e2e             # E2E tests only

# By priority
pytest -m smoke           # Fast regression (< 2 min target)
pytest -m golden_path     # Production critical ⚠️

# By tournament format
pytest -m h2h                  # HEAD_TO_HEAD
pytest -m individual_ranking   # INDIVIDUAL_RANKING
pytest -m group_knockout       # GROUP_AND_KNOCKOUT
pytest -m group_stage          # GROUP_STAGE_ONLY

# By component
pytest -m tournament      # Tournament-related
pytest -m validation      # Validation logic
```

**See:** `pytest.ini` for all 11 registered markers

---

## 🎯 Test Pyramid (Critical)

**Target Ratio:**
- **60-70%** Unit Tests (fast, no dependencies)
- **20-30%** Integration Tests (database, multi-component)
- **5-10%** E2E Tests (full UI/API workflow)

**Why:**
- Unit tests are 100x faster than E2E
- Fast CI = developers actually run tests
- Slow CI = bypassed tests = broken main

---

## 📚 Detailed Documentation

### Quick Reference
- **[Stabilization Plan](../STABILIZATION_AND_EXECUTION_PLAN.md)** ← **READ THIS** for execution excellence
- **[Navigation Guide](NAVIGATION_GUIDE.md)** - Find tests by format

### Format-Specific READMEs
- [Golden Path](e2e/golden_path/README.md) - Production critical test
- [HEAD_TO_HEAD](e2e_frontend/head_to_head/README.md)
- [INDIVIDUAL_RANKING](e2e_frontend/individual_ranking/README.md)
- [GROUP_KNOCKOUT](e2e_frontend/group_knockout/README.md)
- [Manual Tests](manual/README.md)
- [Unit Tests](unit/README.md)

---

## ✍️ Contributing Tests

**Decision Tree:**
1. ☑️ Can this be a unit test? (YES → unit test)
2. ☑️ Requires database? (YES → integration test)
3. ☑️ Requires UI? (YES → E2E, get approval first)

**Default: UNIT TEST FIRST**

---

## ⚠️ Critical Rules

1. **Refactoring Freeze** (2-4 weeks) - No reorganization
2. **Test Pyramid** - 60-70% unit, 20-30% integration, 5-10% E2E
3. **CI Speed** - Full pipeline < 10 min, Smoke < 2 min
4. **Flaky Tests** - Quarantine immediately, fix or delete

---

**Last Updated:** 2026-02-08
**Phase:** Execution Excellence
