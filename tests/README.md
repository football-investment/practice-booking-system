# Tests

This directory contains all test files organized by type.

## Directory Structure

### `/unit`
Unit tests for individual components and functions.

**Currently:** To be populated with pytest unit tests for models, services, and utilities.

### `/integration`
Integration tests for API endpoints, database operations, and multi-component workflows.

**Key Files:**
- `test_*.py` - Integration tests for various features
- `test_api_integration.py` - API endpoint integration tests
- `test_complete_quiz_workflow.py` - Quiz workflow testing
- `test_semester_e2e.py` - Semester end-to-end tests
- `test_lfa_coach_service.py` - Coach service tests
- `test_lfa_internship_service.py` - Internship service tests
- `test_lfa_player_service.py` - Player service tests
- `test_license_authorization.py` - License authorization tests
- `test_session_rules_comprehensive.py` - Session rules testing

### `/e2e`
End-to-end tests simulating complete user journeys.

**Currently:** To be populated with playwright/selenium tests.

### `/scenarios`
Scenario-based tests for specific business cases.

**Currently:** To be populated with scenario tests.

### `/performance`
Performance and load testing results.

**Key Files:**
- `*_test_report_*.json` - Test result reports from various runs
- `session_rules_test_report_*.json` - Session rules test results
- `journey_test_report_*.json` - Journey test results

---

## Running Tests

### All Integration Tests
```bash
pytest tests/integration/ -v
```

### Specific Test File
```bash
pytest tests/integration/test_api_integration.py -v
```

### With Coverage
```bash
pytest tests/integration/ --cov=app --cov-report=html
```

### Run Test Dashboard (Interactive)
```bash
./scripts/startup/start_session_rules_dashboard.sh
```

---

## Test Reports

Performance test reports are stored in `/performance` directory with timestamps.

View latest test results:
```bash
ls -lt tests/performance/*.json | head -5
```

---

## Navigation

- Project Root: `../`
- Documentation: `../docs/`
- Scripts: `../scripts/`
- Application Code: `../app/`
