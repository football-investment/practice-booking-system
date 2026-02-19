# Unit Tests

**Purpose:** Isolated component testing for services, models, and utilities

**Status:** ✅ Active, part of CI/CD

---

## 📋 Overview

Unit tests validate individual components in isolation, without dependencies on databases, APIs, or external services. They should be fast, focused, and deterministic.

---

## 📁 Structure

```
tests/unit/
├── services/           # Business logic services
│   └── test_skill_progression_service.py
├── models/             # Data models (future)
└── utils/              # Utility functions (future)
```

---

## 🧪 Current Tests

### services/test_skill_progression_service.py
**Purpose:** Test skill progression calculation logic

**Coverage:**
- Skill level calculations
- XP progression formulas
- Skill unlock conditions

**Run:**
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run service tests only
pytest tests/unit/services/ -v

# Run specific test
pytest tests/unit/services/test_skill_progression_service.py -v
```

---

## ✅ Unit Test Best Practices

### 1. Isolation
- **No external dependencies** (no database, no API calls, no file I/O)
- Use mocks/stubs for external services
- Fast execution (< 1s per test)

### 2. Naming Convention
```python
def test_<function_name>_<scenario>_<expected_result>():
    # Example: test_calculate_xp_with_multiplier_returns_doubled_value
    pass
```

### 3. Test Structure (AAA Pattern)
```python
def test_example():
    # Arrange: Set up test data
    service = SkillProgressionService()
    initial_xp = 100

    # Act: Execute the function
    result = service.calculate_next_level(initial_xp)

    # Assert: Verify the result
    assert result == 150
```

### 4. Test Coverage
- **Happy path:** Normal, expected inputs
- **Edge cases:** Boundary values (0, negative, max)
- **Error cases:** Invalid inputs, exceptions

---

## 📊 Running Tests

### All Unit Tests
```bash
pytest tests/unit/ -v
```

### With Coverage
```bash
pytest tests/unit/ --cov=app --cov-report=html
```

### Specific Module
```bash
pytest tests/unit/services/ -v
```

### Watch Mode (Re-run on file changes)
```bash
pytest-watch tests/unit/
```

---

## 🎯 When to Write Unit Tests

Write unit tests for:
- ✅ Business logic functions
- ✅ Calculation formulas
- ✅ Data transformation utilities
- ✅ Validation logic
- ✅ State machines

Don't write unit tests for:
- ❌ Database queries (use integration tests)
- ❌ API endpoints (use API tests)
- ❌ UI workflows (use E2E tests)
- ❌ Simple getters/setters

---

## 🔄 Future Structure

As the codebase grows, organize unit tests by domain:

```
tests/unit/
├── services/
│   ├── tournament/
│   │   ├── test_bracket_generation.py
│   │   └── test_leaderboard_calculation.py
│   ├── user/
│   │   ├── test_authentication.py
│   │   └── test_permissions.py
│   └── skill/
│       └── test_skill_progression_service.py
├── models/
│   ├── test_tournament_model.py
│   └── test_user_model.py
└── utils/
    ├── test_date_utils.py
    └── test_validation_utils.py
```

---

## 📚 See Also

- [tests/README.md](../README.md) - Main test documentation
- [tests/integration/](../integration/) - Integration tests
- [tests/api/](../api/) - API endpoint tests
- [tests/e2e/](../e2e/) - End-to-end tests

---

**Last Updated:** 2026-02-08
**Status:** ✅ Active, CI/CD integrated
