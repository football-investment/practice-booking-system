# Manual Tests

**Purpose:** Manual testing scripts for interactive validation and debugging

**Status:** ⚠️ Not part of CI/CD pipeline

---

## 📋 Overview

These tests require manual intervention or are used for interactive testing. They are not automated and should be run manually when needed for debugging or validation purposes.

---

## 📁 Files

### test_registration_validation.py
**Purpose:** Manual validation of user registration workflow

**Usage:**
```bash
python tests/manual/test_registration_validation.py
```

**When to Use:**
- Debugging registration issues
- Validating new registration fields
- Testing email verification flows

---

### test_validation.py
**Purpose:** General validation utilities and manual checks

**Usage:**
```bash
python tests/manual/test_validation.py
```

**When to Use:**
- Manual validation of business logic
- Ad-hoc testing of validation rules
- Debugging validation errors

---

### test_tournament_api.py
**Purpose:** Manual API testing for tournament endpoints

**Usage:**
```bash
python tests/manual/test_tournament_api.py
```

**When to Use:**
- Testing new tournament API endpoints
- Debugging API request/response issues
- Validating tournament creation flows

---

## ⚠️ Important Notes

**Not Automated:**
- These tests are NOT part of the automated test suite
- NOT run in CI/CD pipeline
- Require manual execution

**Interactive:**
- May require user input
- May display interactive prompts
- Results should be manually verified

**Debugging Only:**
- Use for development and debugging
- Not for regression testing
- Consider converting to automated tests if needed frequently

---

## 🔄 Converting to Automated Tests

If a manual test is run frequently, consider converting it to an automated test:

1. **Unit Test:** If testing isolated logic → `tests/unit/`
2. **Integration Test:** If testing multiple components → `tests/integration/`
3. **E2E Test:** If testing full workflows → `tests/e2e/` or `tests/e2e_frontend/`
4. **API Test:** If testing API endpoints → `tests/api/`

---

## 📚 See Also

- [tests/README.md](../README.md) - Main test documentation
- [tests/NAVIGATION_GUIDE.md](../NAVIGATION_GUIDE.md) - Test navigation guide
- [tests/api/](../api/) - Automated API tests
- [tests/e2e/](../e2e/) - Automated E2E tests

---

**Last Updated:** 2026-02-08
**Status:** ⚠️ Manual execution only
