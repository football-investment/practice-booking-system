# Scripts

This directory contains all utility scripts organized by purpose.

## Directory Structure

### `/startup`
Scripts for starting various components of the system.

**Key Files:**
- `start_streamlit_app.sh` - Start Streamlit frontend (development)
- `start_streamlit_production.sh` - Start Streamlit frontend (production)
- `start_unified_dashboard.sh` - Start unified testing dashboard
- `start_session_rules_dashboard.sh` - Start session rules testing dashboard

### `/setup`
Initial setup and installation scripts.

**Key Files:**
- `setup_new_database.sh` - Fresh database setup

### `/database`
Database initialization, migration, and management scripts.

**Key Files:**
- `create_fresh_database.py` - Create fresh database with all tables

### `/admin`
Admin user management and utility scripts.

**Key Files:**
- `reset_admin_password.py` - Reset admin password
- `reset_grandmaster_password.py` - Reset grandmaster password
- `reset_grandmaster_via_api.py` - Reset grandmaster via API

### `/test_data`
Test data generation and seeding scripts.

**Key Files:**
- `create_test_student.py` - Create test student users
- `create_test_sessions_with_scenarios.py` - Generate test sessions
- `create_grandmaster_all_licenses.py` - Create grandmaster with all licenses

### `/dashboards`
Interactive testing and workflow dashboards (Streamlit).

**Key Files:**
- `unified_workflow_dashboard.py` - Unified testing workflow
- `session_rules_testing_dashboard.py` - Session rules testing
- `credit_purchase_workflow_dashboard.py` - Credit purchase workflow
- `invitation_code_workflow_dashboard.py` - Invitation code workflow

### `/utility`
General utility scripts for maintenance and debugging.

**Key Files:**
- `check_api_keys.py` - Verify API keys and authentication
- `debug_bookings.py` - Debug booking issues
- `migrate_locations_to_campuses.py` - Data migration scripts
- `fix_license_endpoints.py` - Fix license-related endpoints

### `/deprecated`
Old scripts kept for reference (not actively used).

---

## Usage

Most scripts require the virtual environment to be activated:

```bash
source venv/bin/activate
```

For database scripts, ensure PostgreSQL is running:

```bash
brew services start postgresql@14
```

For Streamlit dashboards:

```bash
./scripts/startup/start_streamlit_app.sh
```

For backend server (from project root):

```bash
./start_backend.sh
```

---

## Navigation

- Project Root: `../`
- Documentation: `../docs/`
- Tests: `../tests/`
- Application Code: `../app/`
