# Test Structure Mapping - 2026-02-23

## Jelenlegi Teszt Struktúra (OPCIÓ B - Minimális változás)

### 📁 Test Directories

| Directory | Test Type | File Count | Purpose |
|-----------|-----------|------------|---------|
| `tests/unit/` | Unit Tests | ~150 | Izolált unit tesztek (services, models, utils) |
| `tests/integration/` | Integration Tests | ~30 | Integrácios tesztek (DB, API modulok) |
| `tests_e2e/integration_critical/` | E2E API Tests (Critical) | 8 | P0 kritikus E2E API flow-k |
| `app/tests/test_*_e2e.py` | E2E App Tests (P0/P1) | 15 | P0/P1 kritikus alkalmazás szintű E2E tesztek |
| `tests_cypress/` | E2E Frontend (Cypress) | ~20 | Frontend E2E browser tesztek |

### 🎯 Test Execution Order

1. **Unit Tests** - `pytest tests/unit/ -v --tb=short -ra`
2. **Integration Tests** - `pytest tests/integration/ -v --tb=short -ra`
3. **E2E API Tests (Critical)** - `pytest tests_e2e/integration_critical/ -v --tb=short -ra`
4. **E2E App Tests (P0/P1)** - `pytest app/tests/test_*_e2e.py -v --tb=short -ra`
5. **E2E Frontend (Optional)** - `cd tests_cypress && npx cypress run`

### 📊 Test Coverage by Type

#### Unit Tests (tests/unit/)
- Authentication
- Booking service
- Tournament logic
- Skill progression
- State machines
- Validation

#### Integration Tests (tests/integration/)
- Database constraints
- API endpoints
- Service integration
- Auth workflows

#### E2E API Tests (tests_e2e/integration_critical/)
- ✅ Payment workflow
- ✅ Student lifecycle
- ✅ Instructor lifecycle
- ✅ Refund workflow
- ✅ Multi-campus distribution

#### E2E App Tests (app/tests/)
- ✅ OPS manual mode (P0)
- ✅ Instructor assignment (P0)
- ✅ Booking flow (P1)
- ✅ Session management (P1)

### 🏷️ Pytest Markers (Future Enhancement)

```python
# Unit tests
@pytest.mark.unit

# Integration tests
@pytest.mark.integration

# E2E tests
@pytest.mark.e2e

# Critical P0 tests
@pytest.mark.p0
```

Usage:
```bash
pytest -m unit          # Run only unit tests
pytest -m e2e           # Run only E2E tests
pytest -m "not e2e"     # Skip E2E tests
```

### 📝 Notes

- Current structure is **functional** and **CI-integrated**
- Marker-based filtering can be added incrementally
- Full reorganization (Option A) is **optional** for future improvement
- Focus: Run tests systematically and document results

---

**Created:** 2026-02-23
**Status:** Active - Option B (Minimal Change)
