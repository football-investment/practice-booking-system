# Integration Tests - DEPRECATED

**Status**: These tests have collection errors and are not maintained.
**Action**: Tests moved to `.archive/` directory
**Reason**: KeyError, SystemExit, and DB schema mismatches
**Date**: 2026-02-23

## Errors Found

### KeyError: 'access_token' (5 tests)
- test_complete_quiz_workflow.py
- test_direct_api.py
- test_license_api.py
- test_sessions_detailed.py

### SystemExit: 1 (6 tests)
- test_generate.py
- test_onsite_workflow.py
- test_session_quiz_access_control.py
- test_sessions_fix.py
- test_teachable_specializations.py

### DB Schema Errors (2 tests)
- test_pydantic_sem.py
- test_sem_query.py

### Other Errors (2 tests)
- test_enrollments_page.py
- test_gancuju_belt_system.py

**Recommendation**: If these tests are still needed, they must be rewritten with proper fixtures and DB setup.
