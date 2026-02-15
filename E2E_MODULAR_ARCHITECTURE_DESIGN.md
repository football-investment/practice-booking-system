# E2E Modular Architecture Design - Production-Grade Test Pipeline

**Date**: 2026-02-10
**Objective**: Snapshot-based, deterministic, modular E2E test architecture
**Philosophy**: Test REAL UI flows, not seed scripts. Snapshots for speed, not shortcuts.

---

## Architecture Principles

### ✅ DO's

1. **Test Real UI Flows**: Registration, onboarding, tournament creation via actual UI interactions
2. **Snapshot After Each Phase**: DB state saved after each successful lifecycle step
3. **Fast Rollback**: Jump to any lifecycle phase instantly (restore snapshot)
4. **Deterministic Execution**: Same inputs → same outputs, every time
5. **Headless CI-Ready**: All tests run in headless mode by default
6. **Modular Composition**: Each test is independent, orchestrator composes them

### ❌ DON'Ts

1. **No Seed Shortcuts**: Don't seed `onboarding_completed=true` to skip UI testing
2. **No Monolithic Tests**: Don't put entire lifecycle in one 10,000-line test
3. **No Shared State**: Each test starts from a known snapshot
4. **No Manual Cleanup**: Snapshots handle rollback automatically

---

## Lifecycle Phases & Test Modules

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FULL USER LIFECYCLE                            │
└─────────────────────────────────────────────────────────────────────┘

Phase 0: Clean DB
    ├─ Drop all tables
    ├─ Run migrations
    ├─ Seed MINIMAL system data (specializations, game types)
    └─ 📸 Snapshot: "00_clean_db"

Phase 1: User Registration (UI Test)
    ├─ Navigate to registration page
    ├─ Fill email, password, name
    ├─ Submit registration form
    ├─ Verify: User created in DB with onboarding_completed=false
    └─ 📸 Snapshot: "01_user_registered"

Phase 2: Onboarding Flow (UI Test)
    ├─ Login with registered user
    ├─ Onboarding wizard appears (specialization selection)
    ├─ Select specialization (e.g., LFA_FOOTBALL_PLAYER)
    ├─ Complete onboarding steps
    ├─ Verify: onboarding_completed=true in DB
    └─ 📸 Snapshot: "02_user_onboarded"

Phase 3: Sandbox Environment Check (UI Test)
    ├─ Verify user sees Player Dashboard
    ├─ Verify no errors on home screen
    ├─ Verify sidebar navigation works
    └─ 📸 Snapshot: "03_sandbox_ready"

Phase 4: Tournament Creation (UI Test)
    ├─ Click "New Tournament" button
    ├─ Fill tournament configuration form
    ├─ Select "Quick Test" mode
    ├─ Submit form
    ├─ Wait for tournament to complete
    ├─ Verify: Tournament created with status=COMPLETED
    └─ 📸 Snapshot: "04_tournament_completed"

Phase 5: Badge Award Verification (DB + API Test)
    ├─ Query DB: tournament_badges table has CHAMPION badge
    ├─ Verify: badge_metadata contains placement + total_participants
    ├─ Call API: /api/v1/tournaments/badges/user/{user_id}
    ├─ Verify: API response has "badge_metadata" key (not "metadata")
    └─ 📸 Snapshot: "05_badges_awarded"

Phase 6: UI Badge Display (UI Test)
    ├─ Navigate to Tournament Achievements
    ├─ Verify: CHAMPION badge visible
    ├─ Verify: "#1 of X players" text present
    ├─ Verify: NO "No ranking data" text
    └─ 📸 Snapshot: "06_ui_verified"
```

---

## File Structure

```
tests_e2e/
├── conftest.py                          # Shared fixtures (already exists)
├── snapshots/                           # DB snapshots directory
│   ├── 00_clean_db.sql
│   ├── 01_user_registered.sql
│   ├── 02_user_onboarded.sql
│   ├── 03_sandbox_ready.sql
│   ├── 04_tournament_completed.sql
│   ├── 05_badges_awarded.sql
│   └── 06_ui_verified.sql
│
├── lifecycle/                           # Modular lifecycle tests
│   ├── __init__.py
│   ├── test_00_clean_db.py             # Phase 0: Clean DB setup
│   ├── test_01_user_registration.py    # Phase 1: Registration UI
│   ├── test_02_onboarding.py           # Phase 2: Onboarding UI
│   ├── test_03_sandbox_check.py        # Phase 3: Sandbox verification
│   ├── test_04_tournament_creation.py  # Phase 4: Tournament UI
│   ├── test_05_badge_verification.py   # Phase 5: Badge DB/API check
│   └── test_06_ui_badge_display.py     # Phase 6: UI badge rendering
│
├── utils/                               # Shared utilities
│   ├── __init__.py
│   ├── snapshot_manager.py             # DB snapshot save/restore
│   ├── db_helpers.py                   # DB query helpers
│   └── ui_helpers.py                   # Common UI actions (login, navigate)
│
├── orchestrator.py                      # Pipeline orchestrator
└── pytest.ini                           # Pytest config (already exists)
```

---

## Snapshot Manager Design

### Core Functionality

```python
# tests_e2e/utils/snapshot_manager.py

class SnapshotManager:
    """
    Manages PostgreSQL database snapshots for E2E testing.

    Features:
    - Save DB state after each lifecycle phase
    - Restore DB to any previous phase instantly
    - Validate snapshot integrity
    - List available snapshots
    """

    def __init__(self, db_url: str, snapshot_dir: str = "tests_e2e/snapshots"):
        self.db_url = db_url
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(exist_ok=True)

    def save_snapshot(self, phase_name: str) -> None:
        """
        Save current DB state to snapshot file.

        Example:
            snapshot_manager.save_snapshot("01_user_registered")

        Creates: tests_e2e/snapshots/01_user_registered.sql
        """
        snapshot_path = self.snapshot_dir / f"{phase_name}.sql"

        # Use pg_dump to create snapshot
        subprocess.run([
            "pg_dump",
            "--clean",              # Include DROP statements
            "--if-exists",          # Add IF EXISTS to DROP
            "--no-owner",           # Don't dump ownership
            "--no-privileges",      # Don't dump privileges
            "-f", str(snapshot_path),
            self.db_url
        ], check=True)

        print(f"📸 Snapshot saved: {snapshot_path}")

    def restore_snapshot(self, phase_name: str) -> None:
        """
        Restore DB to a previous snapshot.

        Example:
            snapshot_manager.restore_snapshot("02_user_onboarded")

        Restores: tests_e2e/snapshots/02_user_onboarded.sql
        """
        snapshot_path = self.snapshot_dir / f"{phase_name}.sql"

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

        # Use psql to restore snapshot
        subprocess.run([
            "psql",
            "-f", str(snapshot_path),
            self.db_url
        ], check=True)

        print(f"⏮️  Snapshot restored: {snapshot_path}")

    def list_snapshots(self) -> list[str]:
        """List all available snapshots."""
        return sorted([
            f.stem for f in self.snapshot_dir.glob("*.sql")
        ])

    def validate_snapshot(self, phase_name: str) -> bool:
        """Check if snapshot file exists and is valid SQL."""
        snapshot_path = self.snapshot_dir / f"{phase_name}.sql"

        if not snapshot_path.exists():
            return False

        # Basic validation: file has SQL content
        with open(snapshot_path) as f:
            content = f.read(100)
            return "PostgreSQL database dump" in content or "CREATE TABLE" in content
```

---

## Modular Test Example

### Phase 1: User Registration

```python
# tests_e2e/lifecycle/test_01_user_registration.py

import pytest
from playwright.sync_api import Page
from tests_e2e.utils.snapshot_manager import SnapshotManager
from tests_e2e.utils.db_helpers import get_user_by_email

@pytest.mark.lifecycle
@pytest.mark.phase_1
@pytest.mark.nondestructive
def test_01_user_registration(page: Page, snapshot_manager: SnapshotManager):
    """
    Phase 1: User Registration via UI

    Prerequisites: Snapshot "00_clean_db" must exist
    Postcondition: Snapshot "01_user_registered" created

    Steps:
    1. Restore clean DB snapshot
    2. Navigate to registration page
    3. Fill registration form (email, password, name)
    4. Submit form
    5. Verify: User created in DB with onboarding_completed=false
    6. Save snapshot
    """

    # Step 1: Restore to clean DB state
    snapshot_manager.restore_snapshot("00_clean_db")

    # Step 2: Navigate to registration page
    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")

    # Check if registration link exists (if not, we're on login page - need to find registration)
    # This is UI-specific - adjust based on actual UI
    registration_link = page.get_by_text("Sign Up") or page.get_by_text("Register")
    if registration_link.is_visible(timeout=3000):
        registration_link.click()
        page.wait_for_load_state("networkidle")

    # Step 3: Fill registration form
    email = "e2e_test_user@lfa.com"
    password = "SecurePass123!"
    name = "E2E Test User"

    page.fill('input[type="email"]', email)
    page.fill('input[type="password"]', password)
    page.fill('input[placeholder*="Name"]', name)  # Adjust selector as needed

    # Step 4: Submit form
    page.get_by_role("button", name="Register").click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Step 5: Verify user created in DB
    user = get_user_by_email(email)
    assert user is not None, f"User {email} not created in DB"
    assert user.onboarding_completed == False, "User should not be onboarded yet"
    assert user.email == email
    assert user.name == name

    print(f"✅ User registered: {user.email} (ID: {user.id})")

    # Step 6: Save snapshot
    snapshot_manager.save_snapshot("01_user_registered")
```

---

## Orchestrator Design

```python
# tests_e2e/orchestrator.py

"""
E2E Test Pipeline Orchestrator

Runs lifecycle tests in deterministic order, managing snapshots.

Usage:
    # Run full pipeline (all phases)
    python tests_e2e/orchestrator.py --mode full

    # Run specific phases
    python tests_e2e/orchestrator.py --phases 1,2,3

    # Start from specific phase (restore snapshot + continue)
    python tests_e2e/orchestrator.py --start-from 3

    # CI mode (headless, fail fast)
    python tests_e2e/orchestrator.py --mode ci
"""

import sys
import subprocess
from pathlib import Path
from tests_e2e.utils.snapshot_manager import SnapshotManager

class E2EOrchestrator:
    """
    Orchestrates modular E2E tests in lifecycle order.
    """

    LIFECYCLE_PHASES = [
        ("00_clean_db",           "Clean DB setup"),
        ("01_user_registration",  "User registration UI"),
        ("02_onboarding",         "Onboarding flow UI"),
        ("03_sandbox_check",      "Sandbox environment check"),
        ("04_tournament_creation", "Tournament creation UI"),
        ("05_badge_verification", "Badge DB/API verification"),
        ("06_ui_badge_display",   "UI badge display"),
    ]

    def __init__(self, headless: bool = True, fail_fast: bool = True):
        self.headless = headless
        self.fail_fast = fail_fast
        self.snapshot_manager = SnapshotManager(
            db_url=os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
        )

    def run_phase(self, phase_num: int) -> bool:
        """
        Run a single lifecycle phase test.

        Returns: True if passed, False if failed
        """
        phase_name, description = self.LIFECYCLE_PHASES[phase_num]
        test_file = f"tests_e2e/lifecycle/test_{phase_name}.py"

        print(f"\n{'='*80}")
        print(f"🧪 PHASE {phase_num}: {description}")
        print(f"{'='*80}\n")

        # Run pytest for this specific test
        env = os.environ.copy()
        env["PYTEST_HEADLESS"] = "true" if self.headless else "false"

        result = subprocess.run([
            "pytest",
            test_file,
            "-v",
            "--tb=short",
            "-s" if not self.headless else "",
        ], env=env)

        success = result.returncode == 0

        if success:
            print(f"\n✅ Phase {phase_num} PASSED: {description}")
        else:
            print(f"\n❌ Phase {phase_num} FAILED: {description}")

        return success

    def run_full_pipeline(self, start_from: int = 0) -> bool:
        """
        Run full E2E pipeline from specified phase.

        Args:
            start_from: Phase number to start from (0-6)

        Returns: True if all phases passed
        """
        print(f"\n{'='*80}")
        print(f"🚀 E2E PIPELINE - Full User Lifecycle")
        print(f"{'='*80}")
        print(f"Headless: {self.headless}")
        print(f"Fail Fast: {self.fail_fast}")
        print(f"Starting from Phase: {start_from}")
        print(f"{'='*80}\n")

        for i in range(start_from, len(self.LIFECYCLE_PHASES)):
            success = self.run_phase(i)

            if not success and self.fail_fast:
                print(f"\n❌ PIPELINE FAILED at Phase {i}")
                return False

        print(f"\n{'='*80}")
        print(f"✅ PIPELINE COMPLETE - All phases passed!")
        print(f"{'='*80}\n")

        return True

    def list_snapshots(self):
        """List all available snapshots."""
        snapshots = self.snapshot_manager.list_snapshots()

        print(f"\n📸 Available Snapshots ({len(snapshots)}):")
        for snapshot in snapshots:
            print(f"   - {snapshot}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E2E Test Pipeline Orchestrator")
    parser.add_argument("--mode", choices=["full", "ci"], default="full")
    parser.add_argument("--start-from", type=int, default=0, help="Phase to start from (0-6)")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--list-snapshots", action="store_true")

    args = parser.parse_args()

    orchestrator = E2EOrchestrator(
        headless=not args.headed,
        fail_fast=(args.mode == "ci")
    )

    if args.list_snapshots:
        orchestrator.list_snapshots()
        sys.exit(0)

    success = orchestrator.run_full_pipeline(start_from=args.start_from)

    sys.exit(0 if success else 1)
```

---

## Pytest Fixtures for Snapshot Support

```python
# tests_e2e/conftest.py (ADD to existing)

import pytest
from tests_e2e.utils.snapshot_manager import SnapshotManager

@pytest.fixture(scope="session")
def snapshot_manager():
    """Snapshot manager for DB state management."""
    return SnapshotManager(
        db_url=os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    )

@pytest.fixture(scope="function")
def restore_to_clean_db(snapshot_manager):
    """Restore DB to clean state before test."""
    snapshot_manager.restore_snapshot("00_clean_db")
    yield
    # No cleanup - next test will restore to its own snapshot

@pytest.fixture(scope="function")
def restore_to_phase(snapshot_manager):
    """
    Parametrizable fixture to restore to specific phase.

    Usage:
        @pytest.mark.parametrize("restore_to_phase", ["02_user_onboarded"], indirect=True)
        def test_something(restore_to_phase):
            # Test starts with user already onboarded
            ...
    """
    def _restore(phase_name: str):
        snapshot_manager.restore_snapshot(phase_name)

    return _restore
```

---

## Usage Examples

### Run Full Pipeline (CI Mode)

```bash
# Headless, fail fast, from clean DB
python tests_e2e/orchestrator.py --mode ci
```

**Output**:
```
================================================================================
🚀 E2E PIPELINE - Full User Lifecycle
================================================================================
Headless: True
Fail Fast: True
Starting from Phase: 0
================================================================================

================================================================================
🧪 PHASE 0: Clean DB setup
================================================================================

📸 Snapshot saved: tests_e2e/snapshots/00_clean_db.sql
✅ Phase 0 PASSED: Clean DB setup

================================================================================
🧪 PHASE 1: User registration UI
================================================================================

⏮️  Snapshot restored: tests_e2e/snapshots/00_clean_db.sql
✅ User registered: e2e_test_user@lfa.com (ID: 1)
📸 Snapshot saved: tests_e2e/snapshots/01_user_registered.sql
✅ Phase 1 PASSED: User registration UI

[... phases 2-6 ...]

================================================================================
✅ PIPELINE COMPLETE - All phases passed!
================================================================================
```

### Start from Specific Phase (Debug)

```bash
# Start from Phase 3 (sandbox check), headed mode for debugging
python tests_e2e/orchestrator.py --start-from 3 --headed
```

**Restores snapshot "02_user_onboarded"**, then runs phases 3-6.

### Run Single Phase Test

```bash
# Run just onboarding phase (headless)
PYTEST_HEADLESS=true pytest tests_e2e/lifecycle/test_02_onboarding.py -v -s
```

---

## Benefits of This Architecture

### ✅ Speed

- **Fast iteration**: Jump to any phase without re-running previous ones
- **Parallel testing**: Different phases can run in parallel (if independent)
- **Quick debugging**: Restore to failing phase, iterate

### ✅ Maintainability

- **Modular**: Each phase is a separate test file (~100-200 lines)
- **Reusable**: Snapshots can be used by multiple test suites
- **Clear**: Each test has single responsibility

### ✅ Production-Grade

- **Deterministic**: Same snapshot → same test results
- **CI-Ready**: Orchestrator has CI mode (fail fast, headless)
- **Scalable**: Add new phases without touching existing tests

### ✅ Real UI Testing

- **No seed shortcuts**: Registration, onboarding tested via actual UI
- **End-to-end**: Complete user journey validated
- **Regression protection**: Snapshots catch DB schema changes

---

## Implementation Plan

### Phase 1: Infrastructure (30 min)

1. Create `tests_e2e/utils/snapshot_manager.py`
2. Create `tests_e2e/utils/db_helpers.py`
3. Create `tests_e2e/lifecycle/` directory
4. Update `conftest.py` with snapshot fixtures

### Phase 2: Core Tests (2 hours)

5. `test_00_clean_db.py` - Clean DB setup
6. `test_01_user_registration.py` - Registration UI (IF UI exists, else skip)
7. `test_02_onboarding.py` - Onboarding UI (IF UI exists, else skip)
8. `test_04_tournament_creation.py` - Adapt existing `test_01_quick_test_full_flow.py`
9. `test_05_badge_verification.py` - DB + API checks
10. `test_06_ui_badge_display.py` - Adapt existing `test_champion_badge_regression.py`

### Phase 3: Orchestrator (1 hour)

11. Create `tests_e2e/orchestrator.py`
12. Add CLI arguments
13. Test full pipeline locally

### Phase 4: CI Integration (30 min)

14. Create GitHub Actions workflow
15. Test in CI environment

---

## Next Steps

**Question for User**:

1. **Does the UI have user registration/onboarding flows?**
   - If YES → We test them in Phases 1-2
   - If NO → We skip directly to Phase 3 (sandbox), user created via seed

2. **Should I start implementing this architecture now?**
   - Start with snapshot manager + Phase 0 (clean DB)
   - Then adapt existing tests into modular phases

3. **Any specific requirements for snapshots?**
   - Compression (gzip)?
   - Encryption (sensitive data)?
   - Retention policy?

