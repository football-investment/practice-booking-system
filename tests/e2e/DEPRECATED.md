# ⚠️ DEPRECATED FOLDER

**This folder is deprecated and will be removed in a future version.**

## 📁 New Location

All Playwright E2E tests have been moved to:

```
tests/playwright/
```

## 🔄 Migration

The following files have been reorganized:

### Moved to `tests/playwright/`
- ✅ `test_user_registration_with_invites.py`
- ✅ `test_complete_onboarding_with_coupon_ui.py`
- ✅ `test_ui_instructor_application_workflow.py`
- ✅ `test_tournament_enrollment_protection.py`
- ✅ `demo_player_login.py`
- ✅ `run_all_e2e_tests.sh` (master test runner)
- ✅ `snapshot_manager.sh`
- ✅ `run_single_test.sh`

### Moved to `tests/playwright/utils/`
- ✅ `fixtures.py`
- ✅ `reward_policy_fixtures.py`
- ✅ `setup_onboarding_coupons.py`
- ✅ `conftest.py`

### Removed (Debug Files)
- ❌ All `debug_*.py` files (temporary debugging scripts)
- ❌ All `inspect_*.py` files (temporary inspection scripts)
- ❌ `streamlit_login_html.txt` (temporary HTML dump)
- ❌ `test_complete_registration_flow.py.backup` (old backup file)

### Remaining in `tests/e2e/` (Legacy)
The following files remain for backward compatibility but should be migrated or removed:
- `test_admin_create_tournament.py`
- `test_admin_invitation_code.py`
- `test_complete_business_workflow.py`
- `test_coupon_form_ui.py`
- `test_fixtures_validation.py`
- `test_hybrid_ui_player_workflow.py`
- `test_instructor_application_workflow.py`
- `test_instructor_assignment_cycle.py`
- `test_instructor_assignment_flows.py`
- `test_registration_validation_headed.py`
- `test_reward_policy_distribution.py`
- `test_reward_policy_user_validation.py`
- `test_simple_login.py`
- `test_streamlit_selectors.py`
- `test_tournament_attendance_complete.py`
- `test_tournament_creation_cycle.py`
- `test_tournament_workflow_happy_path.py`
- `test_ui_complete_business_workflow.py`
- `test_ui_navigation_exploration.py`
- `test_user_registration.py`

Many of these are duplicates or experimental tests and should be reviewed for removal.

## 🚀 How to Use New Structure

**Old way:**
```bash
./tests/e2e/run_all_e2e_tests.sh
```

**New way:**
```bash
./tests/playwright/run_all_e2e_tests.sh
```

**Old imports:**
```python
from tests.e2e.fixtures import admin_token
from tests.e2e.reward_policy_fixtures import API_BASE_URL
```

**New imports:**
```python
from tests.playwright.utils.fixtures import admin_token
from tests.playwright.utils.reward_policy_fixtures import API_BASE_URL
```

## 📚 Documentation

See the new structure documentation:
- [tests/playwright/README.md](../playwright/README.md) - Playwright E2E tests
- [tests/api/README.md](../api/README.md) - API tests

## 🗑️ Cleanup Plan

This folder will be cleaned up in phases:
1. ✅ **Phase 1 (DONE)**: Move core tests to `tests/playwright/`
2. ⏳ **Phase 2**: Review remaining tests for duplicates
3. ⏳ **Phase 3**: Migrate or remove legacy tests
4. ⏳ **Phase 4**: Delete this folder entirely

## ❓ Questions

If you have questions about the new structure, please refer to:
- [tests/playwright/README.md](../playwright/README.md)
- [tests/README.md](../README.md)
