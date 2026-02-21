# Testing Guidelines — Unit Test Layer

> **Status:** Production-grade baseline achieved as of 2025-02-21
> **Baseline:** 921 passed, 0 failed, 12 xfailed (business logic mismatches documented)

---

## Core Principles

### 1. **No Hardcoded Foreign Keys**

**Rule:** Never use hardcoded IDs for foreign key references (user_id, campus_id, team_id, etc.)

**Why:** Hardcoded IDs create implicit seed dependencies and break test isolation. Tests fail unpredictably when run in different environments or when database state changes.

**Instead:**
```python
# ❌ BAD — Hardcoded FK
def test_user_enrollment(test_db):
    enrollment = SemesterEnrollment(
        user_id=1,              # Assumes user_id=1 exists
        semester_id=2,
        user_license_id=1       # Assumes license exists
    )

# ✅ GOOD — Dynamic creation via factories
def test_user_enrollment(test_db, user_factory):
    user = user_factory()
    license = UserLicense(user_id=user.id, ...)
    test_db.add(license)
    test_db.flush()

    enrollment = SemesterEnrollment(
        user_id=user.id,
        semester_id=2,
        user_license_id=license.id
    )
```

**Exception:** Mock/concurrency tests that don't touch the DB can use symbolic constants:
```python
# ✅ ACCEPTABLE — Mock test with symbolic IDs
TEST_USER_ID = 999
TEST_TOURNAMENT_ID = 42

def test_booking_concurrency_mock():
    # Pure mock test, no DB
    mock_user = SimpleNamespace(id=TEST_USER_ID)
```

---

### 2. **No Seed Dependency**

**Rule:** Tests must NOT rely on pre-seeded data from alembic seed scripts

**Why:** Seed data is environment-specific. CI runs on fresh DBs. Local DBs may have stale/modified seed data. Seed-dependent tests are brittle and non-deterministic.

**Instead:**
- Use **factory fixtures** (`user_factory`, `campus_factory`, `team_factory`) to create test data on-demand
- Each test creates exactly the data it needs
- Test data is scoped to the transaction and rolled back automatically

**Removed from CI:**
```yaml
# ❌ REMOVED — No longer running seed scripts before tests
# - name: Seed test database
#   run: python -m alembic.commands.seed
```

---

### 3. **Every Test Must Be Isolated**

**Rule:** Each test must run independently with no shared state between tests

**Why:** Shared state causes flaky tests. Test order should not matter. Tests must pass when run individually or as a suite.

**How:**
- Use the `postgres_db` fixture (transactional rollback after each test)
- Create all required data inside each test
- Don't modify global/shared fixtures
- Don't rely on test execution order

**Example:**
```python
# ✅ GOOD — Fully isolated test
def test_credit_deduction(test_db, user_factory):
    # Create user
    user = user_factory()

    # Create license
    license = UserLicense(user_id=user.id, current_level=1, ...)
    test_db.add(license)
    test_db.flush()

    # Create credits
    credit = CreditTransaction(user_id=user.id, amount=100, ...)
    test_db.add(credit)
    test_db.commit()

    # Test the logic
    result = deduct_credits(test_db, user.id, 50)
    assert result.success
    # Transaction rolls back automatically — no cleanup needed
```

---

## Factory Fixtures

Factory fixtures are **callable fixtures** that return a function to create test objects dynamically.

### Available Factories

| Factory | Location | Returns | Purpose |
|---------|----------|---------|---------|
| `user_factory` | `tests/unit/conftest.py` | Callable → User | Create users with unique emails |
| `location_factory` | `tests/unit/conftest.py` | Callable → Location | Create locations with cities |
| `campus_factory` | `tests/unit/conftest.py` | Callable → Campus | Create campuses (requires location) |
| `team_factory` | `tests/unit/conftest.py` | Callable → Team | Create teams with campuses |

### Usage Pattern

```python
def test_example(test_db, user_factory, campus_factory):
    # Create users
    user1 = user_factory()
    user2 = user_factory(username="custom_user")

    # Create campus
    campus = campus_factory()  # Automatically creates parent location

    # Use in test
    assert user1.id != user2.id
    assert campus.location_id is not None
```

### Creating New Factories

When adding a new factory, follow this pattern:

```python
@pytest.fixture
def model_factory(test_db, dependency_factory):
    """Factory for creating Model instances with unique values."""
    counter = 0

    def _create(**overrides):
        nonlocal counter
        counter += 1

        # Create dependencies if needed
        dependency = dependency_factory()

        # Create model with defaults + overrides
        model = Model(
            name=f"model_{counter}",
            dependency_id=dependency.id,
            **overrides
        )
        test_db.add(model)
        test_db.flush()
        return model

    return _create
```

---

## CI Guard Checks

### Prevent Hardcoded IDs (Regression Prevention)

A CI lint check prevents hardcoded FK patterns from being reintroduced:

```yaml
# .github/workflows/test-baseline-check.yml
- name: Check for hardcoded FK IDs
  run: |
    # Detect patterns like user_id=1, campus_id=5, etc.
    if grep -r "user_id=[0-9]" tests/unit/ --exclude-dir=__pycache__; then
      echo "❌ Hardcoded user_id found in unit tests"
      exit 1
    fi
```

**Blocked patterns:**
- `user_id=1`, `user_id=2`, etc.
- `campus_id=5`
- `team_id=3`
- `user_license_id=1`

**Allowed:**
- `user_id=user.id` (dynamic reference)
- `TEST_USER_ID = 999` (symbolic constant in mock tests)

---

## Test Execution

### Run Unit Tests Locally

```bash
# Full unit suite
python -m pytest tests/unit/ -v

# Specific file
python -m pytest tests/unit/services/test_credit_service.py -v

# With coverage
python -m pytest tests/unit/ --cov=app --cov-report=html
```

### Expected Baseline (2025-02-21)

```
921 passed, 0 failed, 2 skipped, 12 xfailed
```

**xfailed tests** are marked with business logic mismatches requiring requirements clarification (see individual test docstrings for reasons).

### CI Execution

GitHub Actions runs:
1. Database setup (PostgreSQL with TimescaleDB)
2. Alembic migrations (NO seed scripts)
3. Unit test suite
4. Hardcoded ID lint check

**Expected CI result:** Same as local baseline (no seed dependency)

---

## Common Patterns

### Test with User + License

```python
def test_with_user_license(test_db, user_factory):
    user = user_factory()

    license = UserLicense(
        user_id=user.id,
        specialization_type="PLAYER",
        current_level=1,
        max_achieved_level=1,
        started_at=datetime.now(timezone.utc)
    )
    test_db.add(license)
    test_db.flush()

    # Use license.id for FK references
    enrollment = SemesterEnrollment(user_license_id=license.id, ...)
```

### Test with Tournament Context

```python
def test_tournament_enrollment(test_db, user_factory, tournament_semester_with_instructor):
    user = user_factory()

    # tournament_semester_with_instructor is a pre-configured fixture
    # but we still create our own user dynamically

    enrollment = SemesterEnrollment(
        user_id=user.id,
        semester_id=tournament_semester_with_instructor.id,
        ...
    )
    test_db.add(enrollment)
    test_db.commit()
```

### Mock Tests (No DB)

```python
# For concurrency/race condition tests that don't need real DB
TEST_USER_ID = 999
TEST_TOURNAMENT_ID = 42

def test_concurrent_booking_mock():
    mock_db = MagicMock()
    mock_user = SimpleNamespace(id=TEST_USER_ID)

    # Pure logic test
    result = process_booking(mock_db, mock_user, TEST_TOURNAMENT_ID)
    assert result.user_id == TEST_USER_ID
```

---

## Troubleshooting

### Test fails locally but passes in CI (or vice versa)

**Cause:** Likely relying on local seed data or residual DB state

**Fix:**
1. Check for hardcoded IDs (user_id=1, campus_id=5, etc.)
2. Create all required data inside the test using factories
3. Run test in isolation: `pytest tests/unit/path/to/test.py::test_name -v`

### IntegrityError: violates foreign key constraint

**Cause:** Missing parent record (e.g., creating enrollment with user_id that doesn't exist)

**Fix:**
```python
# ❌ Missing user
enrollment = SemesterEnrollment(user_id=123, ...)

# ✅ Create user first
user = user_factory()
enrollment = SemesterEnrollment(user_id=user.id, ...)
```

### Factory creates duplicate values (email, username, etc.)

**Cause:** Factory not incrementing counter properly

**Fix:** Use `nonlocal counter` and f-strings:
```python
def _create(**overrides):
    nonlocal counter
    counter += 1
    return User(email=f"user{counter}@test.com", **overrides)
```

---

## Migration from Seed-Based to Factory-Based

If you encounter a test with hardcoded IDs:

1. **Identify hardcoded FKs:** Look for `user_id=1`, `campus_id=5`, etc.
2. **Add factory fixture:** `def test_example(test_db, user_factory):`
3. **Create data dynamically:** `user = user_factory()`
4. **Replace hardcoded IDs:** `user_id=1` → `user_id=user.id`
5. **Create dependent objects:** If test needs UserLicense, create it in the test
6. **Run test in isolation:** Verify it passes without seed data

**Example refactoring:**

```python
# ❌ BEFORE — Seed-dependent
def test_enrollment(test_db):
    enrollment = SemesterEnrollment(
        user_id=1,  # Assumes seed data
        semester_id=2,
        user_license_id=1
    )
    test_db.add(enrollment)
    test_db.commit()

# ✅ AFTER — Factory-based
def test_enrollment(test_db, user_factory):
    user = user_factory()
    license = UserLicense(user_id=user.id, current_level=1, ...)
    test_db.add(license)
    test_db.flush()

    enrollment = SemesterEnrollment(
        user_id=user.id,
        semester_id=2,
        user_license_id=license.id
    )
    test_db.add(enrollment)
    test_db.commit()
```

---

## Future: E2E Test Layer

Once the unit layer is stable (0 failed baseline maintained), we can build E2E tests with:

- API endpoint integration tests
- Full user flows (registration → enrollment → attendance)
- Database state verification across transactions
- Multi-service interaction tests

**Prerequisite:** Unit layer must remain clean (no hardcoded IDs, no seed dependency, deterministic)

---

## Maintenance

### Adding New Tests

1. Use factory fixtures for all FK references
2. Don't assume any pre-existing data
3. Create exactly the data you need inside the test
4. Run test in isolation before committing
5. Verify CI passes (no seed scripts available)

### Modifying Existing Tests

1. If you see hardcoded IDs → refactor to factories
2. If test is marked `xfail` → read the reason before removing
3. If test relies on seed data → migrate to factory-based
4. Always run full unit suite before push

### Reviewing PRs

**Red flags:**
- ❌ New hardcoded FK IDs (user_id=1, campus_id=5)
- ❌ Removing xfail without fixing underlying issue
- ❌ Tests that only pass with seed scripts
- ❌ Shared state between tests

**Green flags:**
- ✅ Using factory fixtures
- ✅ Creating test data dynamically
- ✅ Tests pass in isolation
- ✅ No seed dependency

---

**Last Updated:** 2025-02-21
**Maintained By:** Engineering Team
**Contact:** See PROJECT_STRUCTURE.md for team contact info
